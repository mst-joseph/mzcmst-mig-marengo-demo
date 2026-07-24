# ==============================================================================================================================
#      File     : lambdas/validate_media/handler.py
#      Project  : MZCMST AI Migration PoC
#      Description: 영상/이미지 파일 검증 — mime/확장자/크기 한도. 실패 시 BadMediaException.
#      Author   : Joseph Kim <josephkim@mz.co.kr>
#      Date     : 2026-05-11
#      Branch   : feature/ai-mig-poc-lambdas
#      Usage    : Step Functions Task State 'ValidateMedia' 에서 호출
#      Notes    : 문의 — Media Service Team(mzc_tm_mediaserv@megazone.com).
#
#      Copyright 2026. MEGAZONE CLOUD Corp. All rights reserved.
#      This file is part of the Professional Offering Services of Megazone Cloud Media Services Team.
# ==============================================================================================================================
from __future__ import annotations

import os
from typing import Any

import boto3

from _common.logging import get_logger
from _common.media import classify, is_supported
from _common.status import StatusStore

log = get_logger(__name__)
s3 = boto3.client("s3")
status = StatusStore()

MAX_BYTES = int(os.getenv("MAX_BYTES", str(5 * 1024 * 1024 * 1024)))  # 5 GiB default
MIN_BYTES = int(os.getenv("MIN_BYTES", "1024"))  # 1 KiB


class BadMediaException(Exception):
    """Raised when the input fails validation. Caught by SFN Catch."""


def lambda_handler(event: dict[str, Any], _context: Any) -> dict[str, Any]:
    file_id = event["file_id"]
    bucket = event["s3_bucket"]
    s3_key = event["s3_key"]

    if not is_supported(s3_key):
        status.update_status(file_id, "FAILED", failure_reason="unsupported_extension")
        raise BadMediaException(f"unsupported extension: {s3_key}")

    head = s3.head_object(Bucket=bucket, Key=s3_key)
    size = int(head["ContentLength"])
    content_type = str(head.get("ContentType") or "")
    media_type = classify(s3_key)

    if size < MIN_BYTES:
        status.update_status(file_id, "FAILED", failure_reason=f"file_too_small:{size}")
        raise BadMediaException(f"file too small: {size} bytes")
    if size > MAX_BYTES:
        status.update_status(file_id, "FAILED", failure_reason=f"file_too_large:{size}")
        raise BadMediaException(f"file too large: {size} bytes")

    status.update_status(
        file_id,
        "IN_PROGRESS",
        size=size,
        content_type=content_type,
        media_type=media_type,
    )
    log.info(
        "validated",
        extra={"ctx": {"file_id": file_id, "size": size, "media_type": media_type}},
    )
    return {
        "file_id": file_id,
        "s3_bucket": bucket,
        "s3_key": s3_key,
        "media_type": media_type,
        "size": size,
        "content_type": content_type,
    }
