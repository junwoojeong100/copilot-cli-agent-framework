# (심화) Microsoft Foundry Hosted Agent (Hosted Agent) 배포 실습

MAF로 만든 **에이전트**와 **워크플로우**를 **Hosted Agent**
(관리형 컨테이너)로 배포하는 실습입니다. 기존 `src/01~06` 코드는 **그대로 두고**,
같은 에이전트 설계를 호스팅용으로 재구성해 배포하는 방법을 보여줍니다.

## 왜 Hosted Agent인가

Foundry Agent SDK v2로 **재작성하지 않아도**, MAF 에이전트/워크플로우를
컨테이너로 패키징해 Foundry에 배포하면 관리형 서비스의 이점을 그대로 얻습니다.

- **관리형 인프라** — 컨테이너·웹서버·스케일링을 직접 구성할 필요 없음
- **세션 관리 내장** — 대화 이력·업로드 파일을 플랫폼이 영속화
- **전용 에이전트 ID** — 모델·도구 접근용 Entra ID 자동 부여
- **자동 trace/monitoring** — 포털 Traces 탭 + Application Insights 연동
- **OpenAI 호환 엔드포인트** — `/responses` 프로토콜로 호출

## 핵심 패턴

```python
from agent_framework_foundry_hosting import ResponsesHostServer

# 단일 에이전트
server = ResponsesHostServer(agent)
server.run()

# 워크플로우 → .as_agent()로 감싸 동일하게 호스팅
workflow_agent = SequentialBuilder(participants=[...]).build().as_agent()
server = ResponsesHostServer(workflow_agent)
server.run()
```

## 예제 목록

| 폴더 | 원본 | 내용 |
| --- | --- | --- |
| [`01_single_agent/`](01_single_agent/) | `src/01_single_agent.py` | 단일 에이전트(기술 어시스턴트) 호스팅 |
| [`02_sequential_workflow/`](02_sequential_workflow/) | `src/02_sequential_workflow.py` | 순차 워크플로우(분석가→작가→편집자) 호스팅 |
| [`03_group_chat/`](03_group_chat/) | `src/03_group_chat.py` | GroupChat 워크플로우(기획자·개발자·디자이너) 호스팅 |
| [`04_concurrent_workflow/`](04_concurrent_workflow/) | `src/04_concurrent_workflow.py` | 동시 워크플로우(보안·성능·UX 리뷰어) 호스팅 |
| [`05_mcp_agent/`](05_mcp_agent/) | `src/05_mcp_agent.py` | MCP 도구 연동 에이전트(`get_mcp_tool`) 호스팅 |
| [`06_rag_agent/`](06_rag_agent/) | `src/06_rag_agent.py` | RAG 에이전트(하이브리드 검색 함수 도구) 호스팅 |
| [`06_rag_agent_foundry_iq/`](06_rag_agent_foundry_iq/) | `src/06_rag_agent_foundry_iq.py` | RAG 변형(Foundry IQ 지식 베이스 + agentic retrieval) 호스팅 |

> 02~04 워크플로우는 `Workflow.as_agent()`로 감싸 호스팅하고, 05는 서버 측
> `client.get_mcp_tool(...)`, 06은 하이브리드 검색을 **함수 도구**로 노출합니다.
> 06 Foundry IQ 변형은 검색을 지식 베이스에 위임하는 **컨텍스트 프로바이더**
> (`AzureAISearchContextProvider` agentic 모드)를 연결합니다.

각 폴더는 독립 배포 가능한 azd 프로젝트로, 다음 파일을 포함합니다:
`main.py`, `requirements.txt`, `Dockerfile`, `agent.yaml`, `agent.manifest.yaml`,
`.env.example`, `.dockerignore`, `.azdignore`, `README.md`.

> `agent.manifest.yaml` 은 `azd ai agent init -m`의 **입력**이고,
> `agent.yaml` 은 init 후 azd가 **배포에 사용하는 런타임 스펙**입니다.

## 기존 실습과의 차이

| 기존 실습(01~06) | Hosted Agent 실습 |
| --- | --- |
| 프롬프트 1건 처리 후 종료 | `/responses` HTTP 서버 상시 구동 |
| `asyncio.run(main())` | `server.run()` (동기) |
| `AzureCliCredential` | `DefaultAzureCredential` (컨테이너의 관리형 ID, Managed Identity) |
| 저장소 `.env`(`PROJECT_ENDPOINT`) | Foundry 주입 env(`FOUNDRY_PROJECT_ENDPOINT`) |

> 호스팅 `main.py`는 자체 완결적이라 `src/_streaming.py` 같은 저장소 헬퍼를
> import하지 않습니다(컨테이너 빌드 시 폴더 외부 파일에 의존하지 않도록).

## 사전 준비

```bash
azd ext install azure.ai.agents     # Foundry 에이전트 azd 확장(프리뷰)
azd auth login                      # azd 자체 로그인(az login과 별개)
```

> `requirements.txt`에는 메타패키지 `agent-framework` 대신 필요한 하위 패키지만
> 명시되어 있습니다. 메타패키지는 `linux/x86_64` 전용 `agent-framework-hyperlight`를
> 끌어와 **원격 빌드에서 의존성 충돌**을 일으키기 때문입니다.

## 빠른 시작 — 코드(ZIP) 배포 (Docker 불필요, 권장)

아래는 **기존 Foundry 프로젝트**에 배포하는 검증된 흐름입니다.
`azd ai agent init`은 매니페스트 디렉터리와 분리된 **빈 작업 폴더**에서 실행하세요
(같은 폴더에서 실행하면 "target is inside the manifest directory" 오류가 납니다).

```bash
mkdir -p ~/deploy/single && cd ~/deploy/single
REPO="/path/to/copilot-cli-agent-framework"

# 1) 기존 프로젝트에 코드(ZIP) 배포 모드로 초기화
azd ai agent init --no-prompt \
  -m "$REPO/src/hosted_agents/01_single_agent/agent.manifest.yaml" \
  --agent-name maf-lab-single-agent \
  --project-id "<Foundry 프로젝트 리소스 ID>" \
  --model-deployment gpt-5.4 \
  --deploy-mode code --runtime python_3_13 --entry-point main.py \
  --protocol responses --force

# 2) (선택) 기존 모델 배포를 그대로 사용: azure.yaml의 deployments 블록 제거 후
azd env set AZURE_AI_MODEL_DEPLOYMENT_NAME gpt-5.4
azd env set AI_AGENT_PENDING_PROVISION ""

# 3) 배포(원격 빌드) → 호출
azd provision --no-prompt
azd deploy --no-prompt
azd ai agent invoke "안녕!"   # 동작 확인
azd ai agent monitor --follow # 세션 로그(트러블슈팅)
```

> 로컬에서 먼저 돌려보려면 `azd ai agent run` 으로 `:8088`에 호스트할 수 있습니다.

## 트러블슈팅 (실제 배포에서 검증)

| 증상 | 원인 | 해결 |
| --- | --- | --- |
| `hyperlight-sandbox-backend-wasm ... ResolutionImpossible` | 메타패키지 `agent-framework`가 끌어오는 의존성 충돌 | `core`/`foundry`/`foundry-hosting` 등 **하위 패키지만** 명시 |
| `ModuleNotFoundError: No module named 'mcp'` | 호스팅 패키지가 `mcp`를 import하지만 의존성으로 선언하지 않음 | `mcp>=1.24.0,<2` 추가(모든 예제 공통) |
| `'agent-framework-orchestrations' is not installed` | `SequentialBuilder` 등은 별도 패키지 | 02~04에 `agent-framework-orchestrations` 추가 |
| 모델이 `gpt-4.1`로 신규 프로비저닝됨 | init이 매니페스트의 모델 ID를 기본 채택 | azure.yaml `deployments` 제거 + env를 기존 배포(`gpt-5.4`)로 |
| (RAG) `VectorizedQuery ... unexpected keyword 'k'` | `azure-search-documents` 버전별 인자명 차이 | 검증본 버전 핀(`==11.7.0b2`) |
| (RAG) `session_not_ready` / 검색 함수 실패 | 인스턴스 ID에 데이터 접근 권한 없음 | 에이전트 인스턴스 ID에 **Search Index Data Reader** + **Cognitive Services OpenAI User** 부여 |

> ⚠️ Hosted Agent 배포는 현재 **preview**입니다. 컨테이너(Docker) 배포 모드를 쓰려면
> `linux/amd64` 이미지가 필요합니다(Apple Silicon은 `--platform linux/amd64`).
> 위 코드(ZIP) 모드는 Foundry가 원격에서 빌드하므로 로컬 Docker가 필요 없습니다.
