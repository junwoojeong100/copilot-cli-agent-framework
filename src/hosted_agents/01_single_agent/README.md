# 실습 1 — 단일 에이전트를 Hosted Agent로 배포

이 저장소 `src/01_single_agent.py`의 **기술 어시스턴트** 에이전트를 그대로 가져와,
Microsoft Foundry **Hosted Agent**(관리형 컨테이너)로 배포합니다.

> **Hosted 전용 호환성**: MAF core `1.11.0` + foundry/openai `1.10.1` +
> hosting `1.0.0a260709` + Responses `2.0.0` +
> azd `azure.ai.agents>=1.0.0-beta.5` 조합입니다.
> 콘솔 예제의 MAF 1.8.1 환경과 분리된 가상환경에 설치하세요.
> 배포 계정에는 Foundry 프로젝트 범위의 **Foundry Project Manager** 역할이 필요합니다.

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

> 이 폴더는 `azure.yaml`과 앱 소스를 함께 제공하는 **완결된 azd 샘플**입니다.
> `azd ai agent init -m <azure.yaml>`이 이를 작업 폴더로 복사하고, 로컬 구독·리소스
> 상태만 `.azure/`에 생성합니다.

| 역할 | 파일 | 설명 |
| --- | --- | --- |
| **앱 본체 (배포 페이로드)** | `main.py` | 에이전트 정의 + `ResponsesHostServer`로 `/responses` 서버 구동(진입점) |
| | `requirements.txt` | 코드(ZIP) 원격 빌드가 설치할 Responses 2.0 호환 런타임 의존성 |
| **azd 입력·배포 정의** | `azure.yaml` | Foundry 프로젝트 연결, 에이전트 이름, 코드 배포, Responses 2.0, env, CPU·메모리를 통합 선언 |
| | `Dockerfile` | 컨테이너 배포 모드 전용 이미지 정의. **코드(ZIP) 모드에선 미사용** |
| **로컬·보조** | `.env.example` | 로컬 테스트용 환경변수 템플릿(`cp .env.example .env`) |
| | `.gitignore`·`.agentignore`·`.dockerignore` | Git·코드 ZIP·이미지에서 제외할 파일(`.env`·`.azure/`·`.venv`·`__pycache__`·`azure.yaml` 등) |

> `agent.manifest.yaml`과 독립 `agent.yaml`은 공식 문서에서 deprecated되었습니다.
> 이 예제는 최신 단일 `azure.yaml` 방식만 사용합니다.

## 사전 준비

```bash
# Azure Developer CLI + Microsoft Foundry 확장
azd ext install microsoft.foundry
azd auth login
```

## 로컬 실행

```bash
# 1) 통합 azure.yaml로 azd 프로젝트 초기화 (빈 폴더에서 실행)
mkdir -p ~/deploy/single-agent && cd ~/deploy/single-agent
REPO="/path/to/agent-framework-labs"
azd ai agent init . --no-prompt \
  -m "$REPO/src/hosted_agents/01_single_agent/azure.yaml" \
  --project-id "<Foundry 프로젝트 리소스 ID>" \
  --model-deployment gpt-5.4

# 2) 환경 변수 설정
azd env set AZURE_AI_MODEL_DEPLOYMENT_NAME gpt-5.4

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
