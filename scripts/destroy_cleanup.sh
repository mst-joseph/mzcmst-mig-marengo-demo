#!/usr/bin/env bash
# ==============================================================================================================================
#      File     : scripts/destroy_cleanup.sh
#      Project  : MZCMST AI Migration PoC
#      Description: make destroy 사전 단계 — S3 버킷 비우기 + S3 Vectors 인덱스/버킷 삭제 (멱등)
#      Author   : Joseph Kim <josephkim@mz.co.kr>
#      Date     : 2026-05-11
#      Branch   : feature/ai-mig-poc-infra
#      Usage    : scripts/destroy_cleanup.sh <stack> <region> <profile-or-empty> <project_name>
#      Notes    : 문의 — Media Service Team(mzc_tm_mediaserv@megazone.com).
#
#      Copyright 2026. MEGAZONE CLOUD Corp. All rights reserved.
#      This file is part of the Professional Offering Services of Megazone Cloud Media Services Team.
# ==============================================================================================================================
set -uo pipefail

STACK="${1:?stack name required}"
REGION="${2:?region required}"
PROFILE="${3:-}"
PROJECT="${4:?project name required}"

PROFILE_FLAG=""
[[ -n "${PROFILE}" ]] && PROFILE_FLAG="--profile ${PROFILE}"

AWS="aws ${PROFILE_FLAG} --region ${REGION}"

echo "[cleanup] stack=${STACK} region=${REGION} project=${PROJECT}"

# --- 1. Landing bucket 비우기 (Outputs 에서 이름 조회) ---
LANDING_BUCKET=$(${AWS} cloudformation describe-stacks \
  --stack-name "${STACK}" \
  --query "Stacks[0].Outputs[?OutputKey=='LandingBucketName'].OutputValue | [0]" \
  --output text 2>/dev/null || echo "")

if [[ -n "${LANDING_BUCKET}" && "${LANDING_BUCKET}" != "None" ]]; then
  echo "[cleanup] emptying s3://${LANDING_BUCKET}"
  ${AWS} s3 rm "s3://${LANDING_BUCKET}" --recursive 2>/dev/null || true
else
  echo "[cleanup] landing bucket not found (stack may already be deleted)"
fi

# --- 2. S3 Vectors 인덱스/버킷 삭제 (CFN 이 처리하지만 잔존 대비) ---
VECTOR_BUCKET="${PROJECT}-vectors"
echo "[cleanup] attempting s3vectors index delete: ${VECTOR_BUCKET}/media-index"
${AWS} s3vectors delete-index \
  --vector-bucket-name "${VECTOR_BUCKET}" \
  --index-name media-index 2>/dev/null || true

echo "[cleanup] attempting s3vectors bucket delete: ${VECTOR_BUCKET}"
${AWS} s3vectors delete-vector-bucket \
  --vector-bucket-name "${VECTOR_BUCKET}" 2>/dev/null || true

echo "[cleanup] done"
