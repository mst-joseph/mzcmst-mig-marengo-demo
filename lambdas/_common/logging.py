# ==============================================================================================================================
#      File     : lambdas/_common/logging.py
#      Project  : MZCMST AI Migration PoC
#      Description: 구조화 JSON 로깅 헬퍼 — CloudWatch Logs Insights 에서 검색이 쉽도록 단일 JSON 라인 출력
#      Author   : Joseph Kim <josephkim@mz.co.kr>
#      Date     : 2026-05-11
#      Branch   : feature/ai-mig-poc-lambdas
#      Usage    : from _common.logging import get_logger ; log = get_logger(__name__)
#      Notes    : 문의 — Media Service Team(mzc_tm_mediaserv@megazone.com).
#
#      Copyright 2026. MEGAZONE CLOUD Corp. All rights reserved.
#      This file is part of the Professional Offering Services of Megazone Cloud Media Services Team.
# ==============================================================================================================================
from __future__ import annotations

import json
import logging
import os
import sys
from typing import Any


class _JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)
        # Attach any structured context provided via extra={"ctx": {...}}
        ctx = getattr(record, "ctx", None)
        if isinstance(ctx, dict):
            payload.update(ctx)
        return json.dumps(payload, ensure_ascii=False, default=str)


def get_logger(name: str) -> logging.Logger:
    """Return a JSON-structured logger that writes a single line per record to stdout."""
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger
    handler = logging.StreamHandler(stream=sys.stdout)
    handler.setFormatter(_JsonFormatter())
    logger.addHandler(handler)
    logger.setLevel(os.getenv("LOG_LEVEL", "INFO"))
    logger.propagate = False
    return logger
