# ==============================================================================================================================
#      File     : Makefile
#      Project  : MZCMST AI Migration PoC
#      Description: 배포·정리·검증 단축 명령 — make deploy / make destroy / make validate / make web
#      Author   : Joseph Kim <josephkim@mz.co.kr>
#      Date     : 2026-05-11
#      Branch   : feature/ai-mig-poc-infra
#      Usage    : make <target> [STACK=...] [PROJECT_NAME=...] [REGION=...] [PROFILE=...]
#      Notes    : 문의 — Media Service Team(mzc_tm_mediaserv@megazone.com).
#
#      Copyright 2026. MEGAZONE CLOUD Corp. All rights reserved.
#      This file is part of the Professional Offering Services of Megazone Cloud Media Services Team.
# ==============================================================================================================================
SHELL := /bin/bash

# ---- Configurable overrides ----
STACK        ?= ai-mig-poc
PROJECT_NAME ?= ai-migration-poc
REGION       ?= ap-northeast-2
PROFILE      ?=

# AWS CLI profile flag (empty if PROFILE not set)
AWS_PROFILE_FLAG := $(if $(PROFILE),--profile $(PROFILE),)
AWS              := aws $(AWS_PROFILE_FLAG) --region $(REGION)

# ---- Paths ----
INFRA_DIR     := infra
TEMPLATE_SRC  := $(INFRA_DIR)/template.yaml
ASL_SRC       := $(INFRA_DIR)/statemachine/pipeline.asl.json
BUILD_DIR     := build
TEMPLATE_OUT  := $(BUILD_DIR)/template.yaml
PARAMS_FILE   := $(INFRA_DIR)/parameters.example.json

LAMBDAS := dispatcher validate_media extract_metadata start_embed poll_embed index_vectors search_handler

# ---- Help ----
.PHONY: help
help:
	@echo "Infra:"
	@echo "  make validate          — cfn-lint + aws cloudformation validate-template"
	@echo "  make build             — ASL JSON 을 template.yaml DefinitionString 으로 인라인화"
	@echo "  make deploy            — 빌드된 template 으로 stack 배포"
	@echo "  make destroy           — S3/Vectors 비우고 stack 삭제 (멱등)"
	@echo "  make outputs           — 배포된 stack 의 Outputs 출력"
	@echo ""
	@echo "Lambda code:"
	@echo "  make package-lambdas   — 7개 함수 zip 빌드 -> build/lambdas/<fn>.zip"
	@echo "  make package-lambda FN=dispatcher    — 단일 함수 빌드"
	@echo "  make deploy-lambdas    — 7개 함수 모두 update-function-code 배포"
	@echo "  make deploy-lambda FN=dispatcher     — 단일 함수 배포"
	@echo "  make update-handlers   — Handler 설정만 handler.lambda_handler 로 갱신"
	@echo ""
	@echo "Other:"
	@echo "  make web               — FE 개발 서버 (web/ 디렉토리에서 pnpm dev)"
	@echo "  make clean             — build/ 정리"
	@echo ""
	@echo "Variables: STACK=$(STACK) PROJECT_NAME=$(PROJECT_NAME) REGION=$(REGION) PROFILE=$(PROFILE)"

# ---- Build: ASL JSON 을 template 의 DefinitionString 으로 주입 ----
# PoC 단계에선 항상 재빌드 — 의존성 기반 캐싱은 오히려 혼란을 유발함.
.PHONY: build
build:
	@mkdir -p $(BUILD_DIR)
	@python3 scripts/build_template.py $(TEMPLATE_SRC) $(ASL_SRC) $(TEMPLATE_OUT)
	@echo "[build] generated $(TEMPLATE_OUT)"

# ---- Validate ----
.PHONY: validate
validate: build
	@echo "[validate] aws cloudformation validate-template"
	@$(AWS) cloudformation validate-template --template-body file://$(TEMPLATE_OUT) > /dev/null
	@command -v cfn-lint >/dev/null 2>&1 && cfn-lint $(TEMPLATE_OUT) || echo "[validate] cfn-lint not installed — skipping"
	@echo "[validate] OK"

# ---- Deploy ----
.PHONY: deploy
deploy: build
	@echo "[deploy] stack=$(STACK) region=$(REGION) project=$(PROJECT_NAME)"
	@$(AWS) cloudformation deploy \
	  --stack-name $(STACK) \
	  --template-file $(TEMPLATE_OUT) \
	  --capabilities CAPABILITY_NAMED_IAM \
	  --parameter-overrides ProjectName=$(PROJECT_NAME) \
	  --no-fail-on-empty-changeset
	@$(MAKE) outputs

# ---- Outputs ----
.PHONY: outputs
outputs:
	@$(AWS) cloudformation describe-stacks \
	  --stack-name $(STACK) \
	  --query "Stacks[0].Outputs" \
	  --output table

# ---- Destroy (idempotent) ----
.PHONY: destroy
destroy:
	@echo "[destroy] emptying buckets and vector index..."
	@bash scripts/destroy_cleanup.sh $(STACK) $(REGION) "$(PROFILE)" $(PROJECT_NAME)
	@echo "[destroy] deleting stack $(STACK)..."
	@$(AWS) cloudformation delete-stack --stack-name $(STACK) || true
	@$(AWS) cloudformation wait stack-delete-complete --stack-name $(STACK) || true
	@echo "[destroy] done"

# ---- Lambda packaging / deployment ----
.PHONY: package-lambdas
package-lambdas:
	@for fn in $(LAMBDAS); do \
	  echo "[package-lambdas] $$fn"; \
	  bash scripts/package_lambda.sh lambdas/$$fn || exit 1; \
	done

.PHONY: package-lambda
package-lambda:
	@if [ -z "$(FN)" ]; then echo "usage: make package-lambda FN=<function_short>"; exit 2; fi
	@bash scripts/package_lambda.sh lambdas/$(FN)

.PHONY: deploy-lambdas
deploy-lambdas: package-lambdas
	@for fn in $(LAMBDAS); do \
	  echo "[deploy-lambdas] $$fn"; \
	  bash scripts/deploy_lambda.sh $$fn $(PROJECT_NAME) $(REGION) "$(PROFILE)" || exit 1; \
	done

.PHONY: deploy-lambda
deploy-lambda:
	@if [ -z "$(FN)" ]; then echo "usage: make deploy-lambda FN=<function_short>"; exit 2; fi
	@bash scripts/package_lambda.sh lambdas/$(FN)
	@bash scripts/deploy_lambda.sh $(FN) $(PROJECT_NAME) $(REGION) "$(PROFILE)"

# Handler 설정만 갱신 (code 는 건드리지 않음).
# 초기 CFN 의 placeholder 가 Handler: index.lambda_handler 로 만들어진 함수를
# 우리 zip 의 handler.lambda_handler 로 매핑한다. CFN 템플릿도 함께 수정되어 있으므로
# 이후 make deploy 시점에도 동일 값이 유지된다.
.PHONY: update-handlers
update-handlers:
	@for fn in $(LAMBDAS); do \
	  short=$$(echo $$fn | tr '_' '-'); \
	  echo "[update-handlers] $(PROJECT_NAME)-$$short"; \
	  $(AWS) lambda update-function-configuration \
	    --function-name $(PROJECT_NAME)-$$short \
	    --handler handler.lambda_handler \
	    --no-cli-pager > /dev/null || exit 1; \
	  $(AWS) lambda wait function-updated \
	    --function-name $(PROJECT_NAME)-$$short || exit 1; \
	done
	@echo "[update-handlers] all 7 functions updated"

# ---- FE dev server passthrough ----
.PHONY: web
web:
	cd web && pnpm install && pnpm dev

# ---- Clean build artifacts ----
.PHONY: clean
clean:
	rm -rf $(BUILD_DIR)
