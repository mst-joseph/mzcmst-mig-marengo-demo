#!/usr/bin/env bash
# ==============================================================================================================================
#      File     : scripts/package_lambda.sh
#      Project  : MZCMST AI Migration PoC
#      Description: Lambda 함수 1개를 zip 으로 패키징 — handler + _common + pip 의존성 포함
#      Author   : Joseph Kim <josephkim@mz.co.kr>
#      Date     : 2026-05-11
#      Branch   : feature/ai-mig-poc-lambdas
#      Usage    : scripts/package_lambda.sh <function_dir>  (예: lambdas/dispatcher)
#      Notes    : 문의 — Media Service Team(mzc_tm_mediaserv@megazone.com).
#
#      Copyright 2026. MEGAZONE CLOUD Corp. All rights reserved.
#      This file is part of the Professional Offering Services of Megazone Cloud Media Services Team.
# ==============================================================================================================================
set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "usage: $0 <function_dir>" >&2
  exit 2
fi

FN_DIR="${1%/}"                       # e.g. lambdas/dispatcher
FN_NAME="$(basename "$FN_DIR")"       # e.g. dispatcher
ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
COMMON_DIR="$ROOT_DIR/lambdas/_common"
OUT_DIR="$ROOT_DIR/build/lambdas"
STAGE_DIR="$OUT_DIR/_stage/$FN_NAME"
ZIP_PATH="$OUT_DIR/$FN_NAME.zip"

mkdir -p "$OUT_DIR"
rm -rf "$STAGE_DIR" "$ZIP_PATH"
mkdir -p "$STAGE_DIR"

# 1) Copy handler sources
cp -R "$ROOT_DIR/$FN_DIR/." "$STAGE_DIR/"

# 2) Copy shared _common package
cp -R "$COMMON_DIR" "$STAGE_DIR/_common"

# 3) Install dependencies if requirements.txt exists and is non-empty
REQ="$ROOT_DIR/$FN_DIR/requirements.txt"
if [[ -f "$REQ" ]] && [[ -s "$REQ" ]]; then
  # --platform manylinux2014_aarch64 ensures wheels compatible with Lambda arm64.
  # --only-binary :all: avoids source builds in CI.
  python3 -m pip install \
    --quiet \
    --target "$STAGE_DIR" \
    --platform manylinux2014_aarch64 \
    --implementation cp \
    --python-version 3.12 \
    --only-binary=:all: \
    --upgrade \
    -r "$REQ" \
    || python3 -m pip install --quiet --target "$STAGE_DIR" --upgrade -r "$REQ"
fi

# 4) Trim pip metadata to reduce zip size
find "$STAGE_DIR" -type d \( -name "__pycache__" -o -name "*.dist-info" -o -name "*.egg-info" \) -prune -exec rm -rf {} +

# 5) Build the zip (deterministic-ish ordering)
( cd "$STAGE_DIR" && zip -qr "$ZIP_PATH" . )

echo "[package_lambda] wrote $ZIP_PATH ($(du -h "$ZIP_PATH" | cut -f1))"
