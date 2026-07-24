# ==============================================================================================================================
#      File     : lambdas/search_handler/handler.py
#      Project  : MZCMST AI Migration PoC
#      Description: API Gateway 진입 — POST /search (text → Marengo → S3 Vectors), GET /healthz
#      Author   : Joseph Kim <josephkim@mz.co.kr>
#      Date     : 2026-05-11
#      Branch   : feature/ai-mig-poc-lambdas
#      Usage    : API Gateway proxy 통합. CORS 응답 헤더 자체 부여.
#      Notes    : 문의 — Media Service Team(mzc_tm_mediaserv@megazone.com).
#
#      Copyright 2026. MEGAZONE CLOUD Corp. All rights reserved.
#      This file is part of the Professional Offering Services of Megazone Cloud Media Services Team.
# ==============================================================================================================================
from __future__ import annotations

import json
import os
import time
from typing import Any

import boto3

from _common.logging import get_logger
from _common.status import StatusStore

log = get_logger(__name__)
bedrock = boto3.client("bedrock-runtime")
s3 = boto3.client("s3")
s3vectors = boto3.client("s3vectors")
status = StatusStore()

BEDROCK_MODEL_ID = os.environ["BEDROCK_MODEL_ID"]
VECTOR_BUCKET_NAME = os.environ["VECTOR_BUCKET_NAME"]
VECTOR_INDEX_NAME = os.environ["VECTOR_INDEX_NAME"]
LANDING_BUCKET = os.environ["LANDING_BUCKET"]
TOP_K_MAX = int(os.environ.get("TOP_K_MAX", "24"))
PRESIGN_TTL_SEC = int(os.environ.get("PRESIGN_TTL_SEC", "600"))
AWS_REGION = os.environ.get("AWS_REGION", "ap-northeast-2")

CORS_HEADERS = {
    "Content-Type": "application/json",
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "GET,POST,OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type",
}


def _response(status_code: int, body: dict[str, Any]) -> dict[str, Any]:
    return {
        "statusCode": status_code,
        "headers": CORS_HEADERS,
        "body": json.dumps(body, ensure_ascii=False),
    }


def _embed_text(query: str) -> list[float]:
    # Marengo 3.0 schema: {"inputType":"text","text":{"inputText":"..."}}
    payload = {"inputType": "text", "text": {"inputText": query}}
    response = bedrock.invoke_model(
        modelId=BEDROCK_MODEL_ID,
        body=json.dumps(payload),
        contentType="application/json",
    )
    body = json.loads(response["body"].read())
    embedding = _extract_embedding(body)
    if embedding is None:
        preview = json.dumps(body, ensure_ascii=False)[:300]
        raise RuntimeError(f"unexpected Marengo response shape: {preview}")
    return [float(v) for v in embedding]


def _extract_embedding(body: Any) -> list[float] | None:
    """Walk a Marengo response (dict, list, nested) and return the first embedding array found."""
    if isinstance(body, list):
        for item in body:
            emb = _extract_embedding(item)
            if emb is not None:
                return emb
        return None
    if isinstance(body, dict):
        candidate = body.get("embedding")
        if isinstance(candidate, list):
            return candidate
        data = body.get("data")
        if data is not None:
            emb = _extract_embedding(data)
            if emb is not None:
                return emb
        embeddings = body.get("embeddings")
        if isinstance(embeddings, list):
            return _extract_embedding(embeddings)
    return None


def _query_vectors(vector: list[float], top_k: int) -> list[dict[str, Any]]:
    response = s3vectors.query_vectors(
        vectorBucketName=VECTOR_BUCKET_NAME,
        indexName=VECTOR_INDEX_NAME,
        queryVector={"float32": vector},
        topK=top_k,
        returnMetadata=True,
        returnDistance=True,
    )
    return response.get("vectors", []) or []


def _presign(bucket: str, key: str) -> str:
    return s3.generate_presigned_url(
        ClientMethod="get_object",
        Params={"Bucket": bucket, "Key": key},
        ExpiresIn=PRESIGN_TTL_SEC,
    )


def _to_result(hit: dict[str, Any]) -> dict[str, Any]:
    metadata = hit.get("metadata", {}) or {}
    file_path = str(metadata.get("file_path", ""))
    distance = float(hit.get("distance", 1.0))
    score = max(0.0, 1.0 - distance)  # cosine distance → similarity
    playback_url = _presign(LANDING_BUCKET, file_path) if file_path else ""
    return {
        "key": hit.get("key", ""),
        "file_path": file_path,
        "media_type": metadata.get("media_type", "video"),
        "segment_start": float(metadata.get("segment_start", 0.0)),
        "segment_end": float(metadata.get("segment_end", 0.0)),
        "score": round(score, 4),
        "thumbnail_url": "",  # PoC: not generated yet
        "playback_url": playback_url,
    }


def _handle_search(body: dict[str, Any]) -> dict[str, Any]:
    query = str(body.get("query") or "").strip()
    if not query:
        return _response(400, {"error": "query is required"})
    top_k = min(int(body.get("topK") or 12), TOP_K_MAX)

    start = time.perf_counter()
    try:
        vector = _embed_text(query)
        hits = _query_vectors(vector, top_k)
    except Exception as err:  # noqa: BLE001 — return upstream errors as 502
        log.exception("search upstream failure")
        return _response(502, {"error": "upstream failure", "detail": str(err)})

    results = [_to_result(h) for h in hits]
    results.sort(key=lambda r: r["score"], reverse=True)
    took_ms = int((time.perf_counter() - start) * 1000)
    log.info("search ok", extra={"ctx": {"query": query, "topK": top_k, "took_ms": took_ms, "hits": len(results)}})
    return _response(200, {"query": query, "took_ms": took_ms, "results": results})


def _handle_healthz() -> dict[str, Any]:
    try:
        count = status.count()
    except Exception:  # noqa: BLE001
        count = -1
    return _response(200, {"ok": True, "region": AWS_REGION, "indexed_count": count})


def lambda_handler(event: dict[str, Any], _context: Any) -> dict[str, Any]:
    path = str(event.get("path") or event.get("rawPath") or "")
    method = str(event.get("httpMethod") or (event.get("requestContext", {}).get("http") or {}).get("method") or "")

    if method == "OPTIONS":
        return _response(200, {"ok": True})
    if path.endswith("/healthz") and method == "GET":
        return _handle_healthz()
    if path.endswith("/search") and method == "POST":
        raw_body = event.get("body") or "{}"
        try:
            body = json.loads(raw_body) if isinstance(raw_body, str) else dict(raw_body)
        except json.JSONDecodeError:
            return _response(400, {"error": "invalid json body"})
        return _handle_search(body)
    return _response(404, {"error": "not found", "path": path, "method": method})
