# ==============================================================================================================================
#      File     : lambdas/dispatcher/handler.py
#      Project  : MZCMST AI Migration PoC
#      Description: SQS 에 도착한 S3 ObjectCreated 이벤트를 파싱 → DDB PENDING 기록 → Step Functions 실행 시작
#      Author   : Joseph Kim <josephkim@mz.co.kr>
#      Date     : 2026-05-11
#      Branch   : feature/ai-mig-poc-lambdas
#      Usage    : SQS event source mapping 이 자동 호출. 직접 실행 금지.
#      Notes    : 문의 — Media Service Team(mzc_tm_mediaserv@megazone.com).
#
#      Copyright 2026. MEGAZONE CLOUD Corp. All rights reserved.
#      This file is part of the Professional Offering Services of Megazone Cloud Media Services Team.
# ==============================================================================================================================
from __future__ import annotations

import json
import os
import time
import urllib.parse
from typing import Any

import boto3
from botocore.exceptions import ClientError

from _common.logging import get_logger
from _common.media import classify, is_supported
from _common.status import StatusStore, make_file_id

log = get_logger(__name__)
sfn = boto3.client("stepfunctions")
status = StatusStore()

STATE_MACHINE_ARN = os.environ["STATE_MACHINE_ARN"]


def _parse_s3_records(body: str) -> list[dict[str, Any]]:
    """Extract S3 ObjectCreated records from an SQS message body."""
    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        log.warning("non-json SQS body", extra={"ctx": {"body_head": body[:200]}})
        return []
    records = payload.get("Records") or []
    return [r for r in records if r.get("eventSource") == "aws:s3"]


def _start_pipeline(file_id: str, bucket: str, s3_key: str, media_type: str, size: int) -> str:
    payload = {
        "file_id": file_id,
        "s3_bucket": bucket,
        "s3_key": s3_key,
        "media_type": media_type,
        "size": size,
    }
    # SFN execution name 은 24시간 unique 보장 필요. file_id 만으로는 deterministic 이라
    # 같은 파일 재업로드 / SQS 재전달 시 ExecutionAlreadyExists 발생.
    # → file_id 앞 12자 + epoch seconds 로 매번 다른 name 생성 (SFN name 80자 한도 내).
    execution_name = f"{file_id[:12]}-{int(time.time())}"
    try:
        response = sfn.start_execution(
            stateMachineArn=STATE_MACHINE_ARN,
            name=execution_name,
            input=json.dumps(payload),
        )
        return response["executionArn"]
    except ClientError as err:
        code = err.response.get("Error", {}).get("Code", "")
        if code == "ExecutionAlreadyExists":
            log.warning(
                "duplicate execution skipped",
                extra={"ctx": {"execution_name": execution_name, "file_id": file_id}},
            )
            return ""
        raise


def _handle_record(rec: dict[str, Any]) -> None:
    s3_info = rec.get("s3", {})
    bucket = s3_info.get("bucket", {}).get("name")
    raw_key = s3_info.get("object", {}).get("key")
    if not bucket or not raw_key:
        log.warning("malformed s3 record", extra={"ctx": {"record": rec}})
        return
    s3_key = urllib.parse.unquote_plus(raw_key)
    size = int(s3_info.get("object", {}).get("size", 0))
    etag = s3_info.get("object", {}).get("eTag")

    if not is_supported(s3_key):
        log.info("skip unsupported", extra={"ctx": {"s3_key": s3_key}})
        return

    file_id = make_file_id(s3_key, etag)
    media_type = classify(s3_key)

    status.put_pending(
        file_id=file_id,
        s3_key=s3_key,
        bucket=bucket,
        media_type=media_type,
        size=size,
        source_etag=etag or "",
    )
    execution_arn = _start_pipeline(file_id, bucket, s3_key, media_type, size)
    log.info(
        "pipeline started",
        extra={"ctx": {"file_id": file_id, "s3_key": s3_key, "execution_arn": execution_arn}},
    )


def lambda_handler(event: dict[str, Any], _context: Any) -> dict[str, Any]:
    failures: list[dict[str, str]] = []
    for sqs_record in event.get("Records", []):
        message_id = sqs_record.get("messageId", "?")
        try:
            for s3_rec in _parse_s3_records(sqs_record.get("body", "")):
                _handle_record(s3_rec)
        except Exception:  # noqa: BLE001 — surface to SQS partial batch retry
            log.exception("dispatch failed", extra={"ctx": {"message_id": message_id}})
            failures.append({"itemIdentifier": message_id})
    return {"batchItemFailures": failures}
