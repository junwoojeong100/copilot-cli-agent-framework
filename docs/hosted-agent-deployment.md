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
azd deploy --no-prompt                       # 코드(ZIP) 빌드 → Foundry 배포 (Docker·ACR 불필요)
```

배포 후 포털 **Assets → 에이전트 → Traces 탭**에서 단계별 모델 호출을 추적하고,
Application Insights에서 토큰·비용 메트릭을 확인할 수 있습니다(런타임이
`APPLICATIONINSIGHTS_CONNECTION_STRING`을 자동 주입).

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

> ⚠️ Hosted Agents는 현재 **preview**입니다. 코드(ZIP) 배포 모드(권장)는 Docker가 불필요합니다.
> 컨테이너 모드를 사용하는 경우 `linux/amd64` 이미지가 필요합니다(`--platform linux/amd64`).
> 자세한 단계는 각 폴더의 `README.md`를 참고하세요.
