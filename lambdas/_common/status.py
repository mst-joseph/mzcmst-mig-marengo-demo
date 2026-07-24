# ==============================================================================================================================
#      File     : lambdas/_common/status.py
#      Project  : MZCMST AI Migration PoC
#      Description: DynamoDB Status 테이블 헬퍼 — 파일별 처리 상태(PUT/UPDATE), file_id 생성 규칙 일원화
#      Author   : Joseph Kim <josephkim@mz.co.kr>
#      Date     : 2026-05-11
#      Branch   : feature/ai-mig-poc-lambdas
#      Usage    : from _common.status import StatusStore, make_file_id
#      Notes    : 문의 — Media Service Team(mzc_tm_mediaserv@megazone.com).
#
#      Copyright 2026. MEGAZONE CLOUD Corp. All rights reserved.
#      This file is part of the Professional Offering Services of Megazone Cloud Media Services Team.
# ==============================================================================================================================
from __future__ import annotations

import hashlib
import os
from datetime import datetime, timezone
from typing import Any, Literal

import boto3

Status = Literal["PENDING", "IN_PROGRESS", "SUCCESS", "FAILED"]
DEFAULT_VERSION = "v1"


def make_file_id(s3_key: str, etag: str | None = None) -> str:
    """Deterministic file_id derived from S3 key (and ETag when available)."""
    raw = f"{s3_key}|{etag or ''}"
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:24]


def utcnow_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class StatusStore:
    """Thin DynamoDB wrapper for the Status table."""

    def __init__(self, table_name: str | None = None) -> None:
        name = table_name or os.environ["STATUS_TABLE"]
        self._table = boto3.resource("dynamodb").Table(name)

    def put_pending(self, file_id: str, s3_key: str, bucket: str, **extra: Any) -> None:
        item = {
            "file_id": file_id,
            "version": DEFAULT_VERSION,
            "status": "PENDING",
            "s3_key": s3_key,
            "s3_bucket": bucket,
            "updated_at": utcnow_iso(),
            "retry_cnt": 0,
            **extra,
        }
        self._table.put_item(Item=item)

    def update_status(self, file_id: str, status: Status, **attrs: Any) -> None:
        names: dict[str, str] = {"#s": "status", "#u": "updated_at"}
        values: dict[str, Any] = {":s": status, ":u": utcnow_iso()}
        expr = "SET #s = :s, #u = :u"
        for idx, (k, v) in enumerate(attrs.items()):
            placeholder = f":a{idx}"
            name_placeholder = f"#a{idx}"
            names[name_placeholder] = k
            values[placeholder] = v
            expr += f", {name_placeholder} = {placeholder}"
        self._table.update_item(
            Key={"file_id": file_id, "version": DEFAULT_VERSION},
            UpdateExpression=expr,
            ExpressionAttributeNames=names,
            ExpressionAttributeValues=values,
        )

    def get(self, file_id: str) -> dict[str, Any] | None:
        response = self._table.get_item(Key={"file_id": file_id, "version": DEFAULT_VERSION})
        return response.get("Item")

    def count(self) -> int:
        """Approximate count via DDB DescribeTable (eventual consistency, cheap)."""
        client = boto3.client("dynamodb")
        meta = client.describe_table(TableName=self._table.name)
        return int(meta["Table"].get("ItemCount", 0))
