# ==============================================================================================================================
#      File     : lambdas/extract_metadata/handler.py
#      Project  : MZCMST AI Migration PoC
#      Description: 메타데이터 추출 — PoC 단계는 ffprobe 미사용. S3 HeadObject + 확장자로 fallback.
#      Author   : Joseph Kim <josephkim@mz.co.kr>
#      Date     : 2026-05-11
#      Branch   : feature/ai-mig-poc-lambdas
#      Usage    : Step Functions Task 'ExtractMetadata'. ffprobe layer 도입 시 본 모듈 보강.
#      Notes    : 문의 — Media Service Team(mzc_tm_mediaserv@megazone.com).
#
#      Copyright 2026. MEGAZONE CLOUD Corp. All rights reserved.
#      This file is part of the Professional Offering Services of Megazone Cloud Media Services Team.
# ==============================================================================================================================
from __future__ import annotations

from typing import Any

import boto3

from _common.logging import get_logger
from _common.media import classify, extension_of
from _common.status import StatusStore

log = get_logger(__name__)
s3 = boto3.client("s3")
status = StatusStore()


def lambda_handler(event: dict[str, Any], _context: Any) -> dict[str, Any]:
    file_id = event["file_id"]
    bucket = event["s3_bucket"]
    s3_key = event["s3_key"]

    head = s3.head_object(Bucket=bucket, Key=s3_key)
    size = int(head["ContentLength"])
    content_type = str(head.get("ContentType") or "")
    media_type = classify(s3_key)
    ext = extension_of(s3_key)

    # PoC fallback metadata. Real ffprobe values populated when layer is wired up.
    metadata = {
        "size": size,
        "content_type": content_type,
        "media_type": media_type,
        "extension": ext,
        "duration_sec": None,
        "resolution": None,
        "codec": None,
        "bitrate": None,
    }

    status.update_status(
        file_id,
        "IN_PROGRESS",
        size=size,
        content_type=content_type,
        media_type=media_type,
    )
    log.info("metadata fallback", extra={"ctx": {"file_id": file_id, **metadata}})
    return {**event, "metadata": metadata}
