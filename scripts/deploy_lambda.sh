#!/usr/bin/env bash
# ==============================================================================================================================
#      File     : scripts/deploy_lambda.sh
#      Project  : MZCMST AI Migration PoC
#      Description: 단일 Lambda zip 을 aws lambda update-function-code 로 교체 배포
#      Author   : Joseph Kim <josephkim@mz.co.kr>
#      Date     : 2026-05-11
#      Branch   : feature/ai-mig-poc-lambdas
#      Usage    : scripts/deploy_lambda.sh <function_name_short> <project_name> <region> [profile]
#                 예: scripts/deploy_lambda.sh dispatcher mzcmst-ai-mig-test ap-northeast-2
#      Notes    : 문의 — Media Service Team(mzc_tm_mediaserv@megazone.com).
#
#      Copyright 2026. MEGAZONE CLOUD Corp. All rights reserved.
#      This file is part of the Professional Offering Services of Megazone Cloud Media Services Team.
# ==============================================================================================================================
set -euo pipefail

FN_SHORT="${1:?function name required (e.g. dispatcher)}"
PROJECT="${2:?project name required}"
REGION="${3:?region required}"
PROFILE="${4:-}"

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
ZIP_PATH="$ROOT_DIR/build/lambdas/${FN_SHORT}.zip"

if [[ ! -f "$ZIP_PATH" ]]; then
  echo "[deploy_lambda] zip not found: $ZIP_PATH — run 'make package-lambdas' first" >&2
  exit 1
fi

# Lambda function name follows the CFN naming convention: ${ProjectName}-<short>
# but with underscores in directory names rewritten to hyphens.
LAMBDA_SHORT="${FN_SHORT//_/-}"
FN_NAME="${PROJECT}-${LAMBDA_SHORT}"

PROFILE_FLAG=""
[[ -n "$PROFILE" ]] && PROFILE_FLAG="--profile $PROFILE"

echo "[deploy_lambda] updating $FN_NAME"
aws $PROFILE_FLAG --region "$REGION" lambda update-function-code \
  --function-name "$FN_NAME" \
  --zip-file "fileb://$ZIP_PATH" \
  --publish \
  --no-cli-pager \
  > /dev/null

aws $PROFILE_FLAG --region "$REGION" lambda wait function-updated \
  --function-name "$FN_NAME"

echo "[deploy_lambda] $FN_NAME updated"
