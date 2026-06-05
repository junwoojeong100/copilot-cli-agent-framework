# (심화) Hosted Agent 배포 — MAF 에이전트·워크플로우를 관리형으로

> 코드를 그대로 둔 채 MAF 에이전트·워크플로우를 Microsoft Foundry Hosted Agent(관리형 컨테이너)로
> 배포하는 심화 가이드입니다.

---

[Foundry Agent SDK v2 심화 가이드](foundry-sdk-v2-orchestration.md)가 **에이전트 "생성"을 SDK v2로**
바꾸는 접근이라면, 이 가이드는 코드를 **그대로 둔 채** MAF 에이전트·워크플로우를
**Microsoft Foundry Hosted Agent**(관리형 컨테이너)로 **배포**합니다. SDK v2로 재작성하지
않아도 관리형 인프라와 **자동 trace/monitoring**을 그대로 얻는 것이 핵심입니다.

> 위치: [`src/hosted_agents/`](../src/hosted_agents/) · 의존성: `agent-framework-foundry-hosting`

## 핵심 패턴 — `ResponsesHostServer`로 호스팅

```python
from agent_framework_foundry_hosting import ResponsesHostServer

# 단일 에이전트
server = ResponsesHostServer(agent)
server.run()                       # /responses 엔드포인트(:8088), 동기 호출

# 워크플로우 → .as_agent()로 감싸 동일하게 호스팅
workflow_agent = SequentialBuilder(participants=[...]).build().as_agent()
server = ResponsesHostServer(workflow_agent)
server.run()
```

- 대화 이력은 호스팅 인프라가 관리하므로 각 에이전트에 `default_options={"store": False}`를 지정합니다.
- 컨테이너에서는 전용 관리 ID로 인증되므로 `DefaultAzureCredential`을 사용합니다.

## 예제 목록

| 폴더 | 원본 | 내용 |
|------|------|------|
| [`01_single_agent/`](../src/hosted_agents/01_single_agent/) | `src/01_single_agent.py` | 단일 에이전트 호스팅 |
| [`02_sequential_workflow/`](../src/hosted_agents/02_sequential_workflow/) | `src/02_sequential_workflow.py` | 순차 워크플로우(`Workflow.as_agent()`) |
| [`03_group_chat/`](../src/hosted_agents/03_group_chat/) | `src/03_group_chat.py` | GroupChat 워크플로우(`Workflow.as_agent()`) |
| [`04_concurrent_workflow/`](../src/hosted_agents/04_concurrent_workflow/) | `src/04_concurrent_workflow.py` | 동시 워크플로우(`Workflow.as_agent()`) |
| [`05_mcp_agent/`](../src/hosted_agents/05_mcp_agent/) | `src/05_mcp_agent.py` | MCP 도구 연동(서버 측 `get_mcp_tool`) |
| [`06_rag_agent/`](../src/hosted_agents/06_rag_agent/) | `src/06_rag_agent.py` | RAG(하이브리드 검색 함수 도구) |
| [`06_rag_agent_foundry_iq/`](../src/hosted_agents/06_rag_agent_foundry_iq/) | `src/06_rag_agent_foundry_iq.py` | RAG 변형(Foundry IQ 지식 베이스 + agentic retrieval, 컨텍스트 프로바이더) |

각 폴더는 독립 배포 가능한 azd 프로젝트로 `main.py`·`Dockerfile`·`agent.yaml`·
`agent.manifest.yaml` 등을 포함합니다(`agent.manifest.yaml`은 `azd ai agent init`의
입력, `agent.yaml`은 배포 런타임 스펙).

## 배포 흐름

```bash
# ① 로컬 테스트용 패키지 설치 (배포 빌드는 각 폴더의 requirements.txt 사용)
pip install agent-framework-core agent-framework-foundry agent-framework-foundry-hosting mcp
azd ext install azure.ai.agents && azd auth login

# ② azd ai agent init 은 매니페스트 디렉터리와 분리된 빈 폴더에서 실행해야 합니다.
#    같은 폴더에서 실행하면 "target is inside the manifest directory" 오류가 납니다.
MANIFEST=$(pwd)/src/hosted_agents/01_single_agent/agent.manifest.yaml
mkdir -p ~/deploy/single-agent && cd ~/deploy/single-agent
azd ai agent init --no-prompt \
  -m "$MANIFEST" \
  --agent-name maf-lab-single-agent \
  --project-id "<Foundry 프로젝트 리소스 ID>" \
  --model-deployment gpt-5.4 \
  --deploy-mode code --runtime python_3_13 --entry-point main.py \
  --protocol responses --force

# ③ 기존 모델 배포를 그대로 사용: azure.yaml의 deployments 블록이 있으면 제거 후 설정
azd env set AZURE_AI_MODEL_DEPLOYMENT_NAME gpt-5.4
azd env set AI_AGENT_PENDING_PROVISION ""

# ④ 로컬 테스트
azd ai agent run                             # 로컬 호스트(:8088) — 블로킹
azd ai agent invoke --local "질문"            # 별도 터미널에서 실행

# ⑤ 배포
azd provision --no-prompt                    # (필요 시) 리소스 생성
azd deploy --no-prompt                       # 소스를 ZIP으로 업로드 → 클라우드에서 빌드·호스팅
```

### 코드(ZIP) 배포 모드 이해하기

`--deploy-mode code`(권장)는 **로컬 Docker 없이** 소스 폴더를 `.zip`으로 압축해 업로드하면
Foundry가 클라우드에서 빌드·호스팅하는 방식입니다(이미지·ACR 불필요). 의존성 처리 방식은
두 가지입니다.

| 모드 | 동작 | 언제 |
|------|------|------|
| **remote_build**(기본·권장) | 업로드한 `requirements.txt`를 **클라우드에서 설치** | 업로드 용량이 작고 가장 단순한 첫 배포 |
| **bundled** | 미리 빌드한 Linux 의존성을 `packages/`에 담아 **그대로 실행** | 재현 가능 빌드·사설 휠 등 서버 빌드가 어려운 경우 |

> 💡 `azd deploy`가 ZIP 패키징을 자동으로 처리하므로 직접 압축할 필요는 없습니다. 이 저장소 예제는
> `requirements.txt`만 두는 **remote_build** 방식이라 추가 준비가 없습니다. (`agent-framework`
> 메타패키지 대신 하위 패키지만 명시하는 이유는 각 폴더 `requirements.txt` 주석을 참고하세요.)

배포 후 포털 **Assets → 에이전트 → Traces 탭**에서 단계별 모델 호출을 추적하고,
Application Insights에서 토큰·비용 메트릭을 확인할 수 있습니다(런타임이
`APPLICATIONINSIGHTS_CONNECTION_STRING`을 자동 주입).

## 배포된 에이전트 원격 호출·테스트

배포가 끝나면 `azd deploy` 출력에 **포털 플레이그라운드 링크**와 **전용 에이전트 엔드포인트**
(`.../api/projects/<project>/agents/<name>/versions/<n>`)가 표시됩니다. 다음 방법으로 원격
에이전트(단일·워크플로우 공통)를 호출·검증합니다.

### 1) azd로 상태 확인 → 호출 → 로그 스트리밍

```bash
# 상태 확인 — "Active"가 되어야 호출 가능
azd ai agent show

# 원격 호출 — --local 을 빼면 배포된 엔드포인트로 전송됩니다
azd ai agent invoke "Microsoft Agent Framework가 무엇인가요?"

# (선택) 컨테이너 로그·트레이스 실시간 확인
azd ai agent monitor --follow
```

### 2) REST로 직접 호출 (언어 무관·CI 연동)

전용 엔드포인트에 Entra 토큰을 실어 호출합니다. 워크플로우 예제도 동일한 `/responses`
프로토콜로 호출됩니다.

```bash
BASE_URL="https://<account>.services.ai.azure.com/api/projects/<project>"
API_VERSION="v1"
TOKEN=$(az account get-access-token --resource https://ai.azure.com --query accessToken -o tsv)

curl -X POST "$BASE_URL/agents/maf-lab-single-agent/endpoint/protocols/openai/responses?api-version=$API_VERSION" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"input": "Microsoft Agent Framework가 무엇인가요?", "store": false}'
```

> 💡 요청 본문에 `"stream": true`를 추가하면 서버-전송 이벤트(SSE)로 토큰을 스트리밍받습니다.
> 컨테이너 안의 호출 신원은 **에이전트 전용 관리 ID**이며, 호출하는 사용자/서비스는 해당 Foundry
> 프로젝트에 대한 호출 권한이 필요합니다.

### 3) 포털 플레이그라운드

[Foundry 포털](https://ai.azure.com) → **Build → Agents → 해당 에이전트 → Open in playground**
에서 UI로 바로 대화하며 테스트할 수 있습니다.

## (대안) 컨테이너 방식으로 배포

코드(ZIP) 모드 대신 **직접 빌드한 컨테이너 이미지**로 배포할 수도 있습니다. 각 폴더의
`Dockerfile`(`python:3.13-slim` 기반, 포트 `8088` 노출)이 이 용도로 포함되어 있습니다.

```bash
# 코드 모드와 차이는 --deploy-mode 뿐입니다. 런타임은 Dockerfile이 정의하므로 --runtime은 생략합니다.
azd ai agent init --no-prompt \
  -m "$MANIFEST" \
  --agent-name maf-lab-single-agent \
  --project-id "<Foundry 프로젝트 리소스 ID>" \
  --model-deployment gpt-5.4 \
  --deploy-mode container --entry-point main.py \
  --protocol responses --force

# azd deploy가 Dockerfile 이미지를 빌드 → Azure Container Registry로 push → Hosted Agent 등록
azd provision --no-prompt
azd deploy --no-prompt
```

| 항목 | 코드(ZIP) 모드 | 컨테이너 모드 |
|------|----------------|----------------|
| 배포 정의 | `code_configuration` | `container_configuration`(둘은 상호 배타) |
| 로컬 Docker | **불필요** | 필요(이미지 빌드) |
| 추가 인프라 | 없음 | **Azure Container Registry** 사용 |
| 의존성 제어 | 클라우드 `remote_build` 또는 `bundled` | `Dockerfile`에서 직접 제어 |
| 적합한 경우 | 가장 빠른 첫 배포 | 시스템 패키지 설치·재현 빌드 등 세밀한 제어 |

> ⚠️ 호스팅 플랫폼은 **`linux/amd64`** 이미지를 요구합니다. Apple Silicon 등 ARM 머신에서
> 로컬 빌드할 때는 `docker build --platform linux/amd64 .`로 빌드하세요. ACR에 대한
> **AcrPull**(프로젝트 관리 ID) 권한이 필요하며, azd가 자동으로 할당합니다.

## 기존 실습과의 차이

| 기존 실습(01~06) | Hosted Agent 실습 |
|------------------|-------------------|
| 프롬프트 1건 처리 후 종료 | `/responses` HTTP 서버 상시 구동 |
| `asyncio.run(main())` | `server.run()` (동기) |
| `AzureCliCredential` | `DefaultAzureCredential` (컨테이너 관리 ID) |
| 저장소 `.env`(`PROJECT_ENDPOINT`) | Foundry 주입 env(`FOUNDRY_PROJECT_ENDPOINT`) |

> 💡 **환경변수 이름 차이**: 기존 실습(01~06)은 `PROJECT_ENDPOINT` / `MODEL_DEPLOYMENT_NAME`을 사용하고,
> Hosted Agent는 Foundry 런타임 표준인 `FOUNDRY_PROJECT_ENDPOINT` / `AZURE_AI_MODEL_DEPLOYMENT_NAME`을 우선 사용합니다.
> 각 폴더의 `main.py`는 Foundry 표준 변수를 먼저 읽고, 없으면 기존 이름으로 폴백하므로
> 로컬 테스트 시 루트 `.env`를 그대로 쓸 수 있습니다. 각 폴더의 `.env.example`을 참고하세요.

> ⚠️ Hosted Agents는 현재 **preview**입니다. 코드(ZIP) 모드는 Docker가 불필요하고, 컨테이너 모드만
> `linux/amd64` 이미지가 필요합니다(위 "[(대안) 컨테이너 방식으로 배포](#대안-컨테이너-방식으로-배포)" 참고).
> 폴더별 단계 예시는 각 폴더의 `README.md`도 함께 참고하세요.
