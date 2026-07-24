# ==============================================================================================================================
#      File     : lambdas/start_embed/handler.py
#      Project  : MZCMST AI Migration PoC
#      Description: Bedrock Marengo Embed 3.0 StartAsyncInvoke 호출 — 영상은 6초 segment, 이미지는 단일 임베딩
#      Author   : Joseph Kim <josephkim@mz.co.kr>
#      Date     : 2026-05-11
#      Branch   : feature/ai-mig-poc-lambdas
#      Usage    : Step Functions Task 'StartEmbed'. inference profile prefix(apac.*) 금지 — base modelId 만.
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
from _common.status import StatusStore

log = get_logger(__name__)
bedrock = boto3.client("bedrock-runtime")
status = StatusStore()

BEDROCK_MODEL_ID = os.environ["BEDROCK_MODEL_ID"]
LANDING_BUCKET = os.environ["LANDING_BUCKET"]
BUCKET_OWNER = os.environ["BUCKET_OWNER"]
EMBED_OUTPUT_PREFIX = os.getenv("EMBED_OUTPUT_PREFIX", "embeddings/")
EMBED_SEGMENT_SEC = int(os.getenv("EMBED_SEGMENT_SEC", "6"))


def _build_model_input(media_type: str, s3_uri: str) -> dict[str, Any]:
    # Marengo 3.0 schema: top-level inputType + property of the same name carrying details.
    # e.g. {"inputType":"video","video":{...}} — NOT {"inputType":"video","mediaSource":{...}}
    # bucketOwner is required by the Bedrock s3Location schema (cross-account safety guard).
    s3_location = {"uri": s3_uri, "bucketOwner": BUCKET_OWNER}
    if media_type == "video":
        return {
            "inputType": "video",
            "video": {
                "mediaSource": {"s3Location": s3_location},
                "segmentation": {
                    "method": "fixed",
                    "fixed": {"durationSec": EMBED_SEGMENT_SEC},
                },
                "embeddingOption": ["visual", "audio"],
                "embeddingScope": ["clip"],
            },
        }
    if media_type == "image":
        return {
            "inputType": "image",
            "image": {
                "mediaSource": {"s3Location": s3_location},
            },
        }
    raise ValueError(f"unsupported media_type for embed: {media_type}")


def lambda_handler(event: dict[str, Any], _context: Any) -> dict[str, Any]:
    file_id = event["file_id"]
    bucket = event["s3_bucket"]
    s3_key = event["s3_key"]
    media_type = event["media_type"]

    s3_uri = f"s3://{bucket}/{s3_key}"
    output_s3_uri = f"s3://{LANDING_BUCKET}/{EMBED_OUTPUT_PREFIX}{file_id}/"

    model_input = _build_model_input(media_type, s3_uri)
    response = bedrock.start_async_invoke(
        modelId=BEDROCK_MODEL_ID,
        modelInput=model_input,
        outputDataConfig={
            "s3OutputDataConfig": {"s3Uri": output_s3_uri, "bucketOwner": BUCKET_OWNER},
        },
    )
    invocation_arn = response["invocationArn"]

    status.update_status(
        file_id,
        "IN_PROGRESS",
        embed_arn=invocation_arn,
        embed_output_uri=output_s3_uri,
    )
    log.info(
        "embed started",
        extra={"ctx": {"file_id": file_id, "invocationArn": invocation_arn, "outputS3Uri": output_s3_uri}},
    )
    return {
        **event,
        "invocationArn": invocation_arn,
        "outputS3Uri": output_s3_uri,
    }
