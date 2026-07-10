# 실습 1 — 단일 에이전트를 Hosted Agent로 배포

이 저장소 `src/01_single_agent.py`의 **기술 어시스턴트** 에이전트를 그대로 가져와,
Microsoft Foundry **Hosted Agent**(관리형 컨테이너)로 배포합니다.

> **호환성 고정**: MAF `1.8.1` + hosting `1.0.0a260528` + Responses `1.0.0` +
> azd `azure.ai.agents` 확장 `0.1.37-preview` 조합입니다. 최신 확장/hosting으로
> 개별 업그레이드하면 Responses 2.0·MAF core 1.10 이상 요구사항과 충돌할 수 있습니다.

## 핵심 코드 (`main.py`)

```python
from agent_framework import Agent
from agent_framework.foundry import FoundryChatClient
from agent_framework_foundry_hosting import ResponsesHostServer
from azure.identity import DefaultAzureCredential

credential = DefaultAzureCredential()
client = FoundryChatClient(project_endpoint=..., model=..., credential=credential)
agent = Agent(client=client, instructions="...", default_options={"store": False})

server = ResponsesHostServer(agent)   # /responses 엔드포인트 노출
try:
    server.run()                      # 동기 호출 (asyncio.run으로 감싸지 않음)
finally:
    credential.close()
```

## 기존 예제 vs Hosted Agent

| 기존 `src/01_single_agent.py` | 이 Hosted Agent 예제 |
| --- | --- |
| 질문 1건 처리 후 종료 | `/responses` HTTP 서버 상시 구동 |
| `asyncio.run(main())` | `server.run()` (동기) |
| `AzureCliCredential` | `DefaultAzureCredential` (컨테이너의 관리형 ID, Managed Identity) |
| 저장소 `.env` 이름 | Foundry 주입 환경 변수(`FOUNDRY_PROJECT_ENDPOINT` 등) |

## 환경 변수

| 변수 | 설명 |
| --- | --- |
| `FOUNDRY_PROJECT_ENDPOINT` | Hosted Agent 표준. 런타임이 자동 주입 |
| `AZURE_AI_MODEL_DEPLOYMENT_NAME` | 모델 배포 이름. 런타임이 자동 주입 |
| `PROJECT_ENDPOINT` / `MODEL_DEPLOYMENT_NAME` | 저장소 로컬 호환용 폴백 (선택) |

## 파일 구성

> 이 폴더는 `azd init`/`azd ai agent init`의 **산출물이 아니라 입력(소스)** 입니다.
> `azd`가 자동 생성하는 `azure.yaml`·`infra/`·`.azure/`는 여기에 없으며, 빈 작업 폴더에서
> `azd ai agent init`을 실행할 때 생성됩니다(아래 *로컬 실행* 참고).

| 역할 | 파일 | 설명 |
| --- | --- | --- |
| **앱 본체 (배포 페이로드)** | `main.py` | 에이전트 정의 + `ResponsesHostServer`로 `/responses` 서버 구동(진입점) |
| | `requirements.txt` | 코드(ZIP) 원격 빌드가 설치할 런타임 의존성. 메타패키지 대신 하위 패키지만 명시 |
| **azd 입력·배포 정의** | `agent.manifest.yaml` | **`azd ai agent init -m`의 입력 파일(딱 1개)**. 이름·프로토콜·env·기본 모델 선언 |
| | `agent.yaml` | 배포 런타임 스펙(CPU·메모리·프로토콜·env). `azd deploy`가 참조 |
| | `Dockerfile` | 컨테이너 배포 모드 전용 이미지 정의. **코드(ZIP) 모드에선 미사용** |
| **로컬·보조** | `.env.example` | 로컬 테스트용 환경변수 템플릿(`cp .env.example .env`) |
| | `.azdignore`·`.dockerignore` | 업로드·이미지에서 제외할 파일(`.venv`·`__pycache__`·매니페스트 등) |

## 사전 준비

```bash
# Azure Developer CLI + AI agent 확장
azd extension install azure.ai.agents --version 0.1.37-preview --force
azd auth login
```

## 로컬 실행

```bash
# 1) 매니페스트로 azd 프로젝트 초기화 (빈 폴더에서 실행)
mkdir -p ~/deploy/single-agent && cd ~/deploy/single-agent
REPO="/path/to/agent-framework-labs"
azd ai agent init --no-prompt \
  -m "$REPO/src/hosted_agents/01_single_agent/agent.manifest.yaml" \
  --agent-name maf-lab-single-agent \
  --project-id "<Foundry 프로젝트 리소스 ID>" \
  --model-deployment gpt-5.4 \
  --deploy-mode code --runtime python_3_14 --entry-point main.py \
  --protocol responses --force

# 2) 환경 변수 설정
export FOUNDRY_PROJECT_ENDPOINT="https://<account>.services.ai.azure.com/api/projects/<project>"
export AZURE_AI_MODEL_DEPLOYMENT_NAME="gpt-5.4"

# 배포 시 기존 모델 배포를 그대로 사용하려면 init이 만든 azure.yaml의
# deployments 블록을 제거하고 azd 환경값을 고정합니다.
azd env set AZURE_AI_MODEL_DEPLOYMENT_NAME "$AZURE_AI_MODEL_DEPLOYMENT_NAME"
azd env set AI_AGENT_PENDING_PROVISION ""

# 3) 터미널 1: 로컬 호스트 실행 (http://localhost:8088, 블로킹)
azd ai agent run

# 4) 터미널 2: 다른 터미널에서 호출 테스트
azd ai agent invoke --local "Microsoft Agent Framework가 무엇인가요?"
#  또는
curl -X POST http://localhost:8088/responses \
  -H "Content-Type: application/json" \
  -d '{"input": "Microsoft Agent Framework가 무엇인가요?"}'
```

## Foundry에 배포

```bash
# 코드 ZIP 원격 빌드 → Foundry Agent Service 배포
azd provision --no-prompt
azd deploy --no-prompt
```

배포가 끝나면 전용 Foundry 엔드포인트와 포털 플레이그라운드 링크가 출력됩니다.

## 관리형 trace / monitoring

Foundry는 Hosted Agent의 **server-side trace를 자동 수집**합니다.
포털에서 **Assets → 해당 에이전트 → Traces 탭**으로 모델 호출·도구 호출을
추적하고, Application Insights에서 토큰·비용 메트릭을 확인할 수 있습니다.
(런타임이 `APPLICATIONINSIGHTS_CONNECTION_STRING`을 자동 주입합니다.)

> **배포 전에 트레이싱을 먼저 켜야 하나요?** 필수는 아닙니다. server-side 트레이싱은
> **코드 변경 없이** Foundry 프로젝트에 **Application Insights를 연결**하면 켜지고, 이미
> 배포된 에이전트에도 **재배포 없이** 적용됩니다(연결 후 수 분 내). 다만 **배포 전에
> 연결**해두면 첫 호출부터 빠짐없이 추적되므로 권장합니다. 연결은 포털 **프로젝트 →
> Agents → Traces → `Connect`**(또는 Project details → Connected resources → Add
> connection → Application Insights)에서 합니다.

> Hosted Agents는 현재 **preview**입니다. 권장 코드 ZIP 배포 모드는 로컬 Docker가
> 필요 없습니다. 컨테이너 배포 모드를 선택하는 경우에만 `linux/amd64` 이미지가
> 필요합니다.
