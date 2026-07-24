# ==============================================================================================================================
#      File     : scripts/marengo_first_invoke.py
#      Project  : MZCMST AI Migration PoC
#      Description: TwelveLabs Marengo 3.0 계정 전체 활성화용 1회성 동기 invoke 스크립트
#                   StartAsyncInvoke 는 Marketplace EULA 자동 구독을 트리거하지 못하므로
#                   admin/marketplace 권한 가진 profile 로 동기 InvokeModel 을 한 번 실행해야 한다.
#      Author   : Joseph Kim <josephkim@mz.co.kr>
#      Date     : 2026-05-11
#      Branch   : feature/ai-mig-poc-infra
#      Usage    : python3 scripts/marengo_first_invoke.py [profile_name]
#                   profile_name 생략 시 default profile 사용. region 은 ap-northeast-2 고정.
#      Notes    : 문의 — Media Service Team(mzc_tm_mediaserv@megazone.com).
#
#      Copyright 2026. MEGAZONE CLOUD Corp. All rights reserved.
#      This file is part of the Professional Offering Services of Megazone Cloud Media Services Team.
# ==============================================================================================================================
from __future__ import annotations

import json
import sys

import boto3

MODEL_ID = "twelvelabs.marengo-embed-3-0-v1:0"
REGION = "ap-northeast-2"


def main() -> int:
    profile = sys.argv[1] if len(sys.argv) > 1 else None
    session = boto3.Session(profile_name=profile, region_name=REGION)

    try:
        caller = session.client("sts").get_caller_identity()
        print(f"[caller] {caller['Arn']}")
    except Exception as err:  # noqa: BLE001
        print(f"[FAIL] STS GetCallerIdentity failed: {err}")
        return 2

    client = session.client("bedrock-runtime")
    try:
        response = client.invoke_model(
            modelId=MODEL_ID,
            body=json.dumps({"inputType": "text", "text": {"inputText": "hello"}}),
            contentType="application/json",
        )
        body = json.loads(response["body"].read())
        # 응답 구조가 다양할 수 있어 raw 를 먼저 보여준 뒤 robust 하게 embedding 추출.
        preview = json.dumps(body, ensure_ascii=False)
        print(f"[raw_top_type] {type(body).__name__}")
        print(f"[raw_preview ] {preview[:600]}")

        embedding = _extract_embedding(body)
        if embedding:
            print(f"[OK] embedding dim={len(embedding)} first3={embedding[:3]}")
            print("[done] Marengo account-wide activation triggered. Lambda 재시도 가능.")
            return 0
        print("[FAIL] embedding not found in response. Inspect [raw_preview] above.")
        return 1
    except Exception as err:  # noqa: BLE001
        print(f"[FAIL] {type(err).__name__}: {err}")
        return 1


def _extract_embedding(body):  # type: ignore[no-untyped-def]
    """Marengo response 의 임베딩 배열을 어떤 wrapper 라도 찾아낸다."""
    if isinstance(body, list) and body:
        for item in body:
            if isinstance(item, dict):
                emb = _extract_embedding(item)
                if emb:
                    return emb
    if isinstance(body, dict):
        if isinstance(body.get("embedding"), list):
            return body["embedding"]
        data = body.get("data")
        if isinstance(data, dict) and isinstance(data.get("embedding"), list):
            return data["embedding"]
        if isinstance(data, list):
            return _extract_embedding(data)
        embeddings = body.get("embeddings")
        if isinstance(embeddings, list):
            return _extract_embedding(embeddings)
    return None


if __name__ == "__main__":
    raise SystemExit(main())
