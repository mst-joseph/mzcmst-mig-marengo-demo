# AI Migration PoC — 시연용 인프라 + 데모

**Author:** Joseph Kim &lt;josephkim@megazone.com&gt; · Megazone Cloud Media Service Team

> 영상을 S3에 업로드하면 자동으로 Bedrock Marengo 3.0 임베딩을 추출해 S3 Vectors에 적재하고,
> 자연어 쿼리로 시맨틱 검색이 가능한 PoC 환경. 내부 + 고객 시연 목적.

- **Region**: `ap-northeast-2` (Seoul) 단일 구성
- **Vector DB**: Amazon S3 Vectors (2025.12 GA)
- **임베딩 모델**: `twelvelabs.marengo-embed-3-0-v1:0` (base modelId, dim=1024)

> **Status — v0.1 (PoC, End-to-end pipeline 동작 확인 완료).**
> 시연 및 사내·고객 검토용. Production hardening (E2E 테스트, rate limiting, 모니터링/알람, CORS production-only 등) 은 별도 작업 필요.
> 환경별 배포는 §1.5 환경변수 export 후 §2 콘솔 또는 §3 CLI 절차 진행.

---

## 0. 한눈에 보는 배포 흐름

```
[로컬]                                        [AWS 콘솔]
make build  ─────►  build/template.yaml ───►  CloudFormation > Create stack
   │                                                  │
   │                                                  ▼
   └─ AWS 호출 없음                              파라미터 입력 + IAM 동의
       (Python 3 만 있으면 됨)                          │
                                                      ▼
                                                  ~10분 대기 → CREATE_COMPLETE
                                                      │
                                                      ▼
                                                  Outputs 탭에서 SearchApiEndpoint 확인
```

---

## 1. 사전 준비 (최초 1회만)

### 1.1 로컬 환경
- Python 3.10 이상 (`python3 --version` 확인) — `make build` 만 돌리면 됨
- macOS / Linux 권장. Windows 는 WSL2

### 1.2 AWS 계정 준비
- 배포 대상 AWS 계정에 콘솔 접근 가능해야 함
- 다음 권한 필요: CloudFormation full, IAM CreateRole, Lambda/SQS/DDB/S3/StepFunctions/APIGateway full,
  `s3vectors:*`, `bedrock:*`
- 리전: `ap-northeast-2` 고정

### 1.3 Bedrock Marengo 모델 활성화 (가장 자주 놓치는 단계)

Marengo 3.0 은 **Bedrock Marketplace** 모델입니다. 기존 `Model access` 페이지의 토글만으로는 활성화되지 않으며, 계정에 **EULA 자동 구독을 트리거하는 1회성 호출**이 필요합니다.

**왜 별도 호출이 필요한가**: Lambda 파이프라인이 사용하는 비동기 API (`StartAsyncInvoke`) 는 Marketplace EULA 자동 구독을 트리거하지 **않습니다**. 따라서 활성화 전에 stack 을 배포해 영상을 올리면 `StartEmbed` Lambda 에서 `AccessDeniedException` 또는 `ValidationException` 으로 실패합니다.

**해결 — 동기 `InvokeModel` 1회 호출**: 동기 호출은 EULA 자동 구독을 트리거합니다. 한 번 성공하면 계정 전체에서 비동기 API 도 즉시 사용 가능합니다.

```bash
# admin 또는 marketplace 권한 가진 AWS CLI 프로필로 실행 (기본은 default 프로필)
python3 scripts/marengo_first_invoke.py [profile_name]
```

성공 출력 예:
```
[caller] arn:aws:iam::xxxxxxxxxxxx:user/joseph
[OK] embedding dim=1024 first3=[...]
[done] Marengo account-wide activation triggered. Lambda 재시도 가능.
```

이후 §2 / §3 의 stack 배포가 정상 작동합니다.

> **호출 프로필에 필요한 권한**: `bedrock:InvokeModel` + `aws-marketplace:Subscribe / Unsubscribe / ViewSubscriptions`. Lambda role 에도 동일 권한이 template 에 포함되지만 최초 EULA 동의는 사용자 권한으로 한 번 트리거하는 게 안정적.

> 콘솔 `Bedrock > Model access` 페이지에 TwelveLabs Marengo 토글이 보이면 함께 켜두는 것을 권장하지만, **그것만으로는 충분하지 않습니다** — 위 동기 invoke 호출이 실질적 활성화 단계입니다.

### 1.4 S3 Vectors 활성화 확인
`ap-northeast-2` 에서 S3 Vectors 서비스가 활성화되어 있는지 확인합니다.
콘솔에서 `S3` 서비스 → 좌측 메뉴에 `Vector buckets` 항목이 보이면 OK.

### 1.5 환경변수 사전 설정 (Makefile 기본값과 다를 때)
Makefile 기본값(`STACK=ai-mig-poc`, `PROJECT_NAME=ai-migration-poc`) 이 아닌 이름으로 배포할 경우,
모든 make 명령에서 동일한 변수를 사용해야 합니다. 매 명령에 붙이는 대신 한 번 export 권장.

```bash
export STACK=mzcmst-ai-mig-test
export PROJECT_NAME=mzcmst-ai-mig-test
# (선택) AWS CLI 프로필이 default 가 아니면
export PROFILE=mzcmst
```

이후 이 README 의 모든 `make` 명령이 해당 환경에 자동 적용됩니다.
**새 터미널/세션에서 작업 재개할 때 반드시 다시 export** 하세요.
변수 불일치 시 `aws lambda update-function-code` 에서 `Function not found` 가 발생합니다.

---

## 2. 배포 — 콘솔 방식 (권장 · 1차 검증용)

### 2.1 로컬에서 빌드
```bash
cd /Users/joseph/Desktop/01_Project/mzc/26-04-AI_Migration/ai-migration-demo
make build
```

`build/template.yaml` 파일이 생성됩니다. (이 단계는 AWS 호출 없음 — 순수 로컬 파일 변환)

### 2.2 CloudFormation 콘솔 업로드
1. AWS 콘솔 → CloudFormation → **Create stack** → **With new resources (standard)**
2. *Prepare template*: **Choose an existing template**
3. *Specify template*: **Upload a template file** → `build/template.yaml` 선택 → **Next**

### 2.3 Stack 설정
- **Stack name**: `ai-mig-poc` (자유 변경 가능, 소문자/하이픈 권장)
- **Parameters** (대부분 기본값 유지):

| 파라미터 | 기본값 | 비고 |
|---|---|---|
| `ProjectName` | `ai-migration-poc` | 모든 리소스 prefix |
| `BedrockModelId` | `twelvelabs.marengo-embed-3-0-v1:0` | **변경 금지** (inference profile 미지원) |
| `VectorDimension` | `1024` | Marengo 3.0 고정 |
| `LandingBucketName` | (빈 값) | 비우면 자동 명명 |
| `EnableEventBridge` | `true` | S3→SQS 트리거 on |
| `LogRetentionDays` | `14` | CW Logs 보존 |
| `EmbedSegmentDurationSec` | `6` | 영상 segment 길이 |
| `SearchTopKMax` | `24` | API topK 상한 |

→ **Next**

### 2.4 Stack options
- *Tags*: 비워둠 (template 안에서 리소스별 4종 태그 자동 부여)
- *Permissions*: 비워둠 (현재 콘솔 사용자 권한으로 배포)
- *Stack failure options*: `Roll back all stack resources` (기본)
- → **Next**

### 2.5 Review & Create
- 화면 맨 아래 **Capabilities** 체크박스 필수:
  - ☑ I acknowledge that AWS CloudFormation might create IAM resources with custom names.
- **Submit**

### 2.6 배포 진행 모니터링
- 우측 *Events* 탭에서 실시간 리소스 생성 로그 확인
- 일반적으로 8~12분 소요
- 상태가 **CREATE_COMPLETE** 로 바뀌면 완료
- *Outputs* 탭에서 다음 5개 값을 확인 / 메모:
  - `LandingBucketName` — 영상 업로드 대상
  - `SearchApiEndpoint` — FE `.env.local` 의 `NEXT_PUBLIC_API_BASE`
  - `StateMachineArn` — Step Functions 실행 추적
  - `StatusTableName` — DDB 상태 조회
  - `VectorBucketName` / `VectorIndexName` — S3 Vectors

### 2.7 만약 실패하면
- **CREATE_FAILED** 가 뜨면 Events 탭에서 첫 번째 실패 리소스를 확인
- 가장 흔한 원인:
  - **S3 Vectors 네이티브 리소스 미지원**: `Resource type AWS::S3Vectors::* not found` 류 메시지
    → 이 경우 Custom Resource 방식으로 전환 필요 (별도 작업)
  - **권한 부족**: 콘솔 사용자에게 `iam:CreateRole` 등이 없는 경우
  - **이름 중복**: 같은 `ProjectName` 으로 이전 stack 잔재가 남은 경우 → `make destroy` 후 재시도

---

## 3. 배포 — CLI 방식 (재현용)

콘솔에서 1차 검증 완료 후, 재현/CI 용으로 CLI 사용 가능.

### 3.1 CFN 스택 배포
```bash
# §1.5 의 환경변수 export 가 끝나 있다는 전제. 아니면 명령마다 STACK= 등을 붙임.
make deploy

# Outputs 확인
make outputs
```

내부 동작:
1. `make build` 자동 호출 → `infra/template.yaml` + `infra/statemachine/pipeline.asl.json` 을 합쳐 `build/template.yaml` 생성
2. `aws cloudformation deploy --capabilities CAPABILITY_NAMED_IAM` 로 `build/template.yaml` 배포

> 주의: 절대 `infra/template.yaml` 을 CFN 에 직접 업로드하지 마세요. ASL 가 placeholder Stub 인 채로 배포되어 파이프라인이 무력화됩니다.

### 3.2 Lambda 코드 배포

CFN 의 Lambda `Code: ZipFile` 은 placeholder 입니다. 실제 코드는 별도로 패키징/업로드합니다.

```bash
# 7개 함수 전체
make deploy-lambdas

# 단일 함수만 (개발 중 자주 사용)
make deploy-lambda FN=start_embed

# Handler 설정만 placeholder index.lambda_handler → handler.lambda_handler 로 매핑 (1회성 보정)
make update-handlers
```

함수 목록: `dispatcher`, `validate_media`, `extract_metadata`, `start_embed`, `poll_embed`, `index_vectors`, `search_handler`.

### 3.3 코드/인프라 수정 후 반복 배포 흐름

| 수정한 파일 | 실행 명령 | 비고 |
|---|---|---|
| `infra/template.yaml` (CFN 리소스/IAM/env) | `make deploy` | build 자동 재생성 |
| `infra/statemachine/pipeline.asl.json` | `make deploy` | ASL 가 template 에 재주입됨 |
| `lambdas/<fn>/handler.py` (Lambda 코드) | `make deploy-lambda FN=<fn>` | zip 새로 생성 후 update-function-code |
| `lambdas/_common/*` (공유 모듈) | `make deploy-lambdas` | 모든 함수에 포함되므로 전체 재배포 |
| `web/**` (FE) | `cd web && pnpm dev` | HMR 자동 |

**자주 빠지는 함정**
- 환경변수를 새로 추가하고 코드에서 `os.environ[...]` 으로 읽도록 했다면 **CFN(env var) 먼저 배포 → Lambda 코드 나중** 순서. 반대로 하면 cold start 시 `KeyError`.
- 변경이 반영 안 된 듯하면 `ls -la build/template.yaml build/lambdas/<fn>.zip` 으로 mtime 확인. 오래됐으면 stale 빌드 — `make build` 또는 `rm build/lambdas/<fn>.zip && make deploy-lambda FN=<fn>` 으로 강제 재생성.
- `aws lambda get-function-configuration --function-name $PROJECT_NAME-<fn> --query 'LastModified'` 로 실제 갱신 시각 확인.

---

## 4. 시연 흐름

### 4.1 시연 전 준비 (1회)
1. 위 §2 절차로 stack 배포 완료
2. 샘플 영상 50건 정도를 사전 인덱싱 (검색 품질 시연 안정성 확보)
   - `aws s3 cp <영상> s3://<LandingBucketName>/raw/<영상명>` 으로 업로드
   - DynamoDB `<ProjectName>-status` 테이블에서 모두 `SUCCESS` 인 것 확인
3. 시연용 라이브 데모 영상 1건을 별도로 준비 (시연 중 신규 업로드용)

### 4.2 시연 시나리오 (총 ~7분)

**(1) 업로드 — 30초**
- AWS 콘솔 → S3 → `<LandingBucketName>` → `raw/` prefix 열기 → 시연용 영상 업로드
- "이제 파이프라인이 자동으로 돕니다" 멘트

**(2) 추출 진행 모니터링 — ~5분**
- 새 탭에서 Step Functions 콘솔 → `<ProjectName>-pipeline` → 방금 시작된 실행 클릭
- ValidateMedia → ExtractMetadata → StartEmbed → Wait/Poll loop → IndexVectors → MarkSuccess 가
  순차적으로 색깔 바뀌며 진행되는 것을 화면으로 보여줌
- 이 시간 동안:
  - 사전 인덱싱된 데이터로 검색 데모(다음 단계)를 먼저 보여주고
  - 마지막에 다시 돌아와 라이브 영상 완료 확인

**(3) 검색 데모 페이지 — 2분**
- 데모 페이지 접속 → 예시 쿼리 칩 클릭 또는 자연어 입력
- Top 12 결과 카드 그리드 표시 (thumbnail / 파일명 / segment 시간 / score)
- 카드 1개 클릭 → 새 탭에서 해당 segment 부터 영상 재생
- "이 결과는 영상 segment 단위로 정확히 매칭된 것입니다" 강조

**(4) API 직접 시연 — 1분**
- 터미널에서 curl 또는 Postman 으로 같은 쿼리를 호출
  ```bash
  curl -X POST "$SEARCH_API/search" \
    -H 'Content-Type: application/json' \
    -d '{"query": "비 오는 도시 야경", "topK": 5}' | jq
  ```
- 응답 JSON 화면에 띄움:
  > "이 응답에 segment 시작/끝, score, metadata 가 모두 포함되어 있습니다.
  >  고객사는 이걸 받아 검색 UI, 추천 시스템, 자동 태깅 등 자유롭게 구현 가능합니다."

**(5) 클로징 — 라이브 영상 검색 — 30초**
- (1) 에서 업로드한 라이브 영상이 인덱싱 완료됐는지 확인
- 그 영상에 특화된 쿼리로 검색 → 방금 업로드한 영상이 결과에 등장
- "지금 5분 전에 업로드한 영상도 자동으로 검색됩니다"

---

## 5. 구성

### 5.1 CloudFormation 파라미터
위 §2.3 표 참조.

### 5.2 모든 리소스에 자동 부여되는 태그
| Key | Value | 비고 |
|---|---|---|
| `Application` | `MediaMig` | 고정 |
| `Name` | `${ProjectName}-<용도>` | 리소스별 고유 (e.g., `ai-migration-poc-landing`) |
| `Service` | AWS 서비스 타입 | `Lambda` / `S3` / `S3Vectors` / `DynamoDB` / `SQS` / `StepFunctions` / `APIGateway` / `IAM` / `CloudWatchLogs` |
| `Team` | `MZCMST` | 고정 |

총 33개 taggable 리소스에 자동 적용.
일부 리소스(BucketPolicy, QueuePolicy, EventSourceMapping, APIGateway Resource/Method/Deployment, Lambda Permission)는 AWS 가 Tags 속성을 지원하지 않아 미적용.

### 5.3 S3 Prefix 컨벤션
| Prefix | 용도 | 트리거 |
|---|---|---|
| `raw/` | 원본 미디어 업로드 | **ObjectCreated → SQS** |
| `embeddings/` | Marengo async 결과 JSON | 없음 (트리거 X — 루프 방지) |
| `pending/` | 처리 중 staging (옵션) | 없음 |
| `processed/` | 처리 완료 표시 (옵션) | 없음 |

> `raw/` 이외 prefix 에 영상을 올리면 파이프라인이 시작되지 않습니다.

---

## 6. API

### POST /search
```json
// Request
{ "query": "비 오는 도시 야경", "topK": 12 }

// Response (200)
{
  "query": "비 오는 도시 야경",
  "took_ms": 312,
  "results": [
    {
      "key": "task-abc_clip_7",
      "file_path": "raw/news/seoul_night.mp4",
      "media_type": "video",
      "segment_start": 42.0,
      "segment_end": 48.0,
      "score": 0.8132,
      "thumbnail_url": "https://...presigned...",
      "playback_url": "https://...presigned..."
    }
  ]
}
```

### GET /healthz
```json
{ "ok": true, "region": "ap-northeast-2", "indexed_count": 12345 }
```

CORS: `*` (PoC 한정)

`score` 해석: S3 Vectors 의 cosine distance 를 `1 - distance` 로 변환한 유사도. **1.0 에 가까울수록 유사**.
검색 UI 는 score 내림차순 정렬 + 임계값 미만은 노이즈로 간주해 숨김 (현재 `web/app/page.tsx` 의 `MATCH_THRESHOLD = 0.1`).

---

## 7. 정리 (Cleanup)

### 7.1 콘솔 방식
1. **S3 버킷 비우기 먼저** (안 비우면 stack 삭제 실패)
   - S3 콘솔 → `<LandingBucketName>` → Empty
2. **S3 Vectors 인덱스 / 버킷 삭제**
   - S3 콘솔 → Vector buckets → `<ProjectName>-vectors` → 인덱스 삭제 후 버킷 삭제
3. CloudFormation → 해당 stack → **Delete**

### 7.2 CLI 방식 (멱등)
```bash
make destroy STACK=ai-mig-poc PROFILE=default REGION=ap-northeast-2
```
S3 / Vectors 자동 비우기 + stack 삭제까지 한 번에. 부분 실패 시 재실행 안전.

### 7.3 잔여 확인
```bash
aws resourcegroupstaggingapi get-resources \
  --tag-filters Key=Application,Values=MediaMig \
  --region ap-northeast-2
```
결과가 비어 있어야 완전 정리.

---

## 8. 트러블슈팅

| 증상 | 원인 / 대처 |
|---|---|
| stack `CREATE_FAILED` — `AWS::S3Vectors::*` 미지원 | CFN 네이티브 미지원 리전/계정. Custom Resource 방식 전환 필요 (별도 작업) |
| 영상 업로드 후 파이프라인 미작동 | `raw/` 이외 prefix 사용. 또는 `EnableEventBridge=false` 로 배포됨 |
| Step Functions 실행이 `StartEmbed` 에서 실패 (AccessDenied / ValidationException — subscription) | Marengo Marketplace EULA 미구독. §1.3 의 동기 invoke 스크립트 1회 실행 후 재시도 |
| `search` API 가 `502 Bad Gateway` | SearchHandler Lambda 로그 확인. Bedrock throttling 가능성 |
| 영상 업로드 후 5분이 지나도 `SUCCESS` 안 됨 | SFN 콘솔에서 해당 실행의 실패 state 확인. `PollEmbed` 가 40회 한도 도달 시 `MarkTimedOut` |
| stack 삭제 실패 — 버킷이 비어있지 않음 | §7.1 의 S3 / Vectors 수동 비우기 먼저 |
| `StartEmbed` 에서 `ValidationException: ... bucketOwner not found` | Bedrock s3Location 스키마가 bucketOwner 요구. Lambda env `BUCKET_OWNER` 가 `${AWS::AccountId}` 로 주입되어 있는지 확인 (`aws lambda get-function-configuration ... --query 'Environment.Variables.BUCKET_OWNER'`) |
| Lambda 가 IAM `AccessDenied` (s3:ListBucket / s3vectors:GetVectors 등) | `infra/template.yaml` 의 해당 FnRole inline policy 에 권한 추가 → `make deploy`. 정책 반영 후 `aws iam get-role-policy` 로 검증 |
| 코드를 수정했는데 Lambda 동작이 그대로 | `build/lambdas/<fn>.zip` mtime 이 수정 시각 이전이면 stale. `rm` 후 `make deploy-lambda FN=<fn>` 재실행 |
| `update-function-code` 에서 `Function not found` | `PROJECT_NAME` 환경변수가 배포된 스택과 다름. §1.5 의 export 다시 확인 |
| Step Functions execution 이 Succeeded 인데 결과 없음 | Catch 가 `MarkFailed` 로 라우팅한 케이스. State machine Graph view 에서 어느 state 가 마지막으로 실행됐는지 확인 + DDB Status 의 `failure_reason` 조회 |

---

## 9. 디렉토리 구조

```
ai-migration-demo/
├── README.md                              # 이 파일
├── Makefile                               # make build / deploy / destroy
├── .gitignore
├── infra/
│   ├── template.yaml                      # 메인 CFN 템플릿 (1400 lines)
│   ├── parameters.example.json
│   └── statemachine/
│       ├── pipeline.asl.json              # Step Functions ASL
│       └── pipeline.asl.HEADER.md
├── scripts/
│   ├── build_template.py                  # ASL 인라인화
│   └── destroy_cleanup.sh                 # 멱등 정리
├── lambdas/                               # 7개 함수 실제 코드 + 공유 _common 모듈
│   ├── _common/                           # logging, status (DDB), media util 공유
│   ├── dispatcher/                        # SQS → Step Functions 트리거
│   ├── validate_media/                    # 미디어 형식/크기 검증
│   ├── extract_metadata/                  # ffprobe 메타데이터 추출
│   ├── start_embed/                       # Bedrock Marengo StartAsyncInvoke
│   ├── poll_embed/                        # 비동기 임베딩 상태 폴링
│   ├── index_vectors/                     # 임베딩 결과 → S3 Vectors PutVectors
│   └── search_handler/                    # API Gateway 진입: /search, /healthz
├── web/                                   # Next.js 데모 페이지 (검색 UI)
│   ├── app/                               # page.tsx, layout.tsx
│   ├── components/                        # SearchBar, ResultGrid, ResultCard, MediaThumbnail
│   └── lib/                               # api 클라이언트, 타입 정의
├── tests/
└── docs/
    ├── decisions/                         # ADR
    └── prd/
```

---

## 10. 문의

Joseph Kim — josephkim@megazone.com
