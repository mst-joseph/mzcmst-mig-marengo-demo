# ==============================================================================================================================
#      File     : lambdas/_common/media.py
#      Project  : MZCMST AI Migration PoC
#      Description: 미디어 파일 확장자/타입 분류 헬퍼 — ffprobe 부재 시 fallback 메타데이터 생성
#      Author   : Joseph Kim <josephkim@mz.co.kr>
#      Date     : 2026-05-11
#      Branch   : feature/ai-mig-poc-lambdas
#      Usage    : from _common.media import classify, MediaType
#      Notes    : 문의 — Media Service Team(mzc_tm_mediaserv@megazone.com).
#
#      Copyright 2026. MEGAZONE CLOUD Corp. All rights reserved.
#      This file is part of the Professional Offering Services of Megazone Cloud Media Services Team.
# ==============================================================================================================================
from __future__ import annotations

from pathlib import PurePosixPath
from typing import Literal

MediaType = Literal["video", "image", "unknown"]

VIDEO_EXTS = {".mp4", ".mov", ".webm", ".mkv", ".m4v", ".avi"}
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp"}


def extension_of(s3_key: str) -> str:
    """Return lowercased extension including the leading dot, or empty string."""
    return PurePosixPath(s3_key).suffix.lower()


def classify(s3_key: str) -> MediaType:
    ext = extension_of(s3_key)
    if ext in VIDEO_EXTS:
        return "video"
    if ext in IMAGE_EXTS:
        return "image"
    return "unknown"


def is_supported(s3_key: str) -> bool:
    return classify(s3_key) != "unknown"
