# ==============================================================================================================================
#      File     : lambdas/poll_embed/handler.py
#      Project  : MZCMST AI Migration PoC
#      Description: Bedrock GetAsyncInvoke 상태 폴링 — Step Functions Wait+Poll 루프에서 호출
#      Author   : Joseph Kim <josephkim@mz.co.kr>
#      Date     : 2026-05-11
#      Branch   : feature/ai-mig-poc-lambdas
#      Usage    : Step Functions Task 'PollEmbed'. 'Completed' / 'Failed' / 'InProgress' 반환.
#      Notes    : 문의 — Media Service Team(mzc_tm_mediaserv@megazone.com).
#
#      Copyright 2026. MEGAZONE CLOUD Corp. All rights reserved.
#      This file is part of the Professional Offering Services of Megazone Cloud Media Services Team.
# ==============================================================================================================================
from __future__ import annotations

from typing import Any

import boto3

from _common.logging import get_logger

log = get_logger(__name__)
bedrock = boto3.client("bedrock-runtime")


def lambda_handler(event: dict[str, Any], _context: Any) -> dict[str, Any]:
    invocation_arn = event["invocationArn"]
    poll_count = int(event.get("pollCount", 0)) + 1
    output_s3_uri = event.get("outputS3Uri", "")

    response = bedrock.get_async_invoke(invocationArn=invocation_arn)
    raw_status = str(response.get("status", "")).strip()
    normalized = raw_status if raw_status in {"Completed", "Failed", "InProgress"} else "InProgress"

    log.info(
        "poll",
        extra={"ctx": {"invocationArn": invocation_arn, "status": normalized, "pollCount": poll_count}},
    )
    return {
        "status": normalized,
        "pollCount": poll_count,
        "outputS3Uri": output_s3_uri,
        "rawStatus": raw_status,
    }
