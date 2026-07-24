# ==============================================================================================================================
#      File     : lambdas/index_vectors/handler.py
#      Project  : MZCMST AI Migration PoC
#      Description: Bedrock Marengo async 결과(JSON) 다운로드 → S3 Vectors PutVectors 배치 적재
#      Author   : Joseph Kim <josephkim@mz.co.kr>
#      Date     : 2026-05-11
#      Branch   : feature/ai-mig-poc-lambdas
#      Usage    : Step Functions Task 'IndexVectors' — Embed 완료 후 호출
#      Notes    : 문의 — Media Service Team(mzc_tm_mediaserv@megazone.com).
#
#      Copyright 2026. MEGAZONE CLOUD Corp. All rights reserved.
#      This file is part of the Professional Offering Services of Megazone Cloud Media Services Team.
# ==============================================================================================================================
from __future__ import annotations

import json
import os
from typing import Any
from urllib.parse import urlparse

import boto3

from _common.logging import get_logger
from _common.status import StatusStore

log = get_logger(__name__)
s3 = boto3.client("s3")
s3vectors = boto3.client("s3vectors")
status = StatusStore()

VECTOR_BUCKET_NAME = os.environ["VECTOR_BUCKET_NAME"]
VECTOR_INDEX_NAME = os.environ["VECTOR_INDEX_NAME"]
BATCH_SIZE = int(os.getenv("VECTOR_PUT_BATCH", "500"))


def _split_s3_uri(uri: str) -> tuple[str, str]:
    parsed = urlparse(uri)
    return parsed.netloc, parsed.path.lstrip("/")


def _iter_output_keys(output_uri: str) -> list[str]:
    bucket, prefix = _split_s3_uri(output_uri)
    keys: list[str] = []
    token: str | None = None
    while True:
        kwargs: dict[str, Any] = {"Bucket": bucket, "Prefix": prefix}
        if token:
            kwargs["ContinuationToken"] = token
        resp = s3.list_objects_v2(**kwargs)
        for obj in resp.get("Contents", []) or []:
            key = obj["Key"]
            if key.endswith(".json"):
                keys.append(key)
        if resp.get("IsTruncated"):
            token = resp.get("NextContinuationToken")
        else:
            break
    return keys


def _load_segments(bucket: str, key: str) -> list[dict[str, Any]]:
    body = s3.get_object(Bucket=bucket, Key=key)["Body"].read()
    payload = json.loads(body)
    # Marengo 3.0 async output shapes:
    #   single segment  → {"data": {"embedding": [...], "startSec": .., "endSec": ..}}
    #   multiple        → {"data": [{"embedding": ...}, ...]}  or  [{"data": {...}}, ...]
    if isinstance(payload, list):
        out: list[dict[str, Any]] = []
        for item in payload:
            if isinstance(item, dict):
                inner = item.get("data")
                out.append(inner if isinstance(inner, dict) else item)
        return out
    data = payload.get("data")
    if isinstance(data, list):
        return [d for d in data if isinstance(d, dict)]
    if isinstance(data, dict):
        return [data]
    embeddings = payload.get("embeddings")
    if isinstance(embeddings, list):
        return [e for e in embeddings if isinstance(e, dict)]
    return []


def _build_vector_record(file_id: str, file_path: str, media_type: str, idx: int, seg: dict[str, Any]) -> dict[str, Any]:
    embedding = seg.get("embedding") or seg.get("vector") or []
    seg_start = float(seg.get("startSec", seg.get("segment_start", 0.0)))
    seg_end = float(seg.get("endSec", seg.get("segment_end", seg_start)))
    return {
        "key": f"{file_id}_clip_{idx}",
        "data": {"float32": [float(v) for v in embedding]},
        "metadata": {
            "file_id": file_id,
            "file_path": file_path,
            "media_type": media_type,
            "segment_start": seg_start,
            "segment_end": seg_end,
        },
    }


def _put_batch(vectors: list[dict[str, Any]]) -> None:
    for i in range(0, len(vectors), BATCH_SIZE):
        chunk = vectors[i : i + BATCH_SIZE]
        s3vectors.put_vectors(
            vectorBucketName=VECTOR_BUCKET_NAME,
            indexName=VECTOR_INDEX_NAME,
            vectors=chunk,
        )


def lambda_handler(event: dict[str, Any], _context: Any) -> dict[str, Any]:
    file_id = event["file_id"]
    file_path = event["s3_key"]
    media_type = event["media_type"]
    # outputS3Uri is nested under $.embed by the state machine's StartEmbed/PollEmbed ResultPath.
    output_s3_uri = event["embed"]["outputS3Uri"]

    bucket, _ = _split_s3_uri(output_s3_uri)
    result_keys = _iter_output_keys(output_s3_uri)
    if not result_keys:
        raise RuntimeError(f"no embed output found under {output_s3_uri}")

    indexed = 0
    for key in result_keys:
        segments = _load_segments(bucket, key)
        vectors = [
            _build_vector_record(file_id, file_path, media_type, idx, seg)
            for idx, seg in enumerate(segments)
            if seg.get("embedding") or seg.get("vector")
        ]
        if not vectors:
            continue
        _put_batch(vectors)
        indexed += len(vectors)

    status.update_status(file_id, "IN_PROGRESS", indexed_count=indexed)
    log.info("indexed", extra={"ctx": {"file_id": file_id, "indexed": indexed}})
    return {**event, "indexed": indexed}
