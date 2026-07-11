# 실습 2 — 순차 워크플로우를 Hosted Agent로 배포

이 저장소 `src/02_sequential_workflow.py`의 순차 파이프라인
(**분석가 → 작가 → 편집자**)을 그대로 가져와, `Workflow.as_agent()`로
단일 에이전트처럼 감싼 뒤 Microsoft Foundry **Hosted Agent**로 배포합니다.

> 핵심: MAF 워크플로우는 Foundry Agent SDK v2로 재작성하지 않고도
> `.as_agent()` 한 줄로 Hosted Agent가 됩니다.

> **Hosted 전용 호환성**: MAF core `1.11.0` + foundry/openai `1.10.1` +
> orchestrations `1.0.0` + hosting `1.0.0a260709` + Responses `2.0.0` +
> azd `azure.ai.agents>=1.0.0-beta.5` 조합입니다.
> 콘솔 예제의 MAF 1.8.1 환경과 분리된 가상환경에 설치하세요.
> 배포 계정에는 Foundry 프로젝트 범위의 **Foundry Project Manager** 역할이 필요합니다.

## 핵심 코드 (`main.py`)

```python
from agent_framework.orchestrations import SequentialBuilder
from agent_framework_foundry_hosting import ResponsesHostServer

workflow_agent = (
    SequentialBuilder(participants=[analyzer_agent, writer_agent, editor_agent])
    .build()
    .as_agent()          # 워크플로우 → 단일 에이전트로 변환
)

server = ResponsesHostServer(workflow_agent)
server.run()             # 동기 호출
```

각 참여 에이전트에는 `default_options={"store": False}`를 지정해
호스팅 인프라가 관리하는 대화 이력과 중복 저장을 피합니다.

## 모델 권장

워크플로우는 직전 에이전트의 출력(assistant 메시지)을 이어받아 처리하므로,
성능이 좋은 모델을 권장합니다(이 저장소 기본값 `gpt-5.4`로 검증).

## 기존 예제 vs Hosted Agent

| 기존 `src/02_sequential_workflow.py` | 이 Hosted Agent 예제 |
| --- | --- |
| `stream_workflow`로 1회 실행 후 종료 | `/responses` HTTP 서버 상시 구동 |
| `asyncio.run(main())` | `server.run()` (동기) |
| `AzureCliCredential` | `DefaultAzureCredential` (컨테이너의 관리형 ID, Managed Identity) |
| Workflow 직접 실행 | `Workflow.as_agent()`로 감싸 호스팅 |

## 환경 변수

| 변수 | 설명 |
| --- | --- |
| `FOUNDRY_PROJECT_ENDPOINT` | Hosted Agent 표준. 런타임이 자동 주입 |
| `AZURE_AI_MODEL_DEPLOYMENT_NAME` | 모델 배포 이름. 런타임이 자동 주입 |
| `PROJECT_ENDPOINT` / `MODEL_DEPLOYMENT_NAME` | 저장소 로컬 호환용 폴백 (선택) |

## 로컬 실행

```bash
azd ext install microsoft.foundry
azd auth login

# 통합 azure.yaml로 azd 프로젝트 초기화 (빈 폴더에서 실행)
mkdir -p ~/deploy/sequential-workflow && cd ~/deploy/sequential-workflow
REPO="/path/to/agent-framework-labs"
azd ai agent init . --no-prompt \
  -m "$REPO/src/hosted_agents/02_sequential_workflow/azure.yaml" \
  --project-id "<Foundry 프로젝트 리소스 ID>" \
  --model-deployment gpt-5.4
azd env set AZURE_AI_MODEL_DEPLOYMENT_NAME gpt-5.4

# 터미널 1: 로컬 호스트 실행 (http://localhost:8088, 블로킹)
azd ai agent run

# 터미널 2: 다른 터미널에서 호출 테스트
azd ai agent invoke --local "Kubernetes 클러스터 비용 최적화 전략"
#  또는
curl -X POST http://localhost:8088/responses \
  -H "Content-Type: application/json" \
  -d '{"input": "Kubernetes 클러스터 비용 최적화 전략"}'
```

## Foundry에 배포

```bash
azd provision --no-prompt   # (필요 시) 리소스 생성
azd deploy --no-prompt      # 코드 ZIP 원격 빌드 → Foundry Agent Service 배포
```

## 관리형 trace / monitoring

배포 후 포털 **Assets → 에이전트 → Traces 탭**에서 분석가·작가·편집자
각 단계의 모델 호출을 추적할 수 있고, Application Insights에서 토큰·비용
메트릭을 확인할 수 있습니다(런타임이 연결 문자열을 자동 주입).

> Hosted Agents는 현재 **preview**입니다. 권장 코드 ZIP 배포 모드는 로컬 Docker가
> 필요 없습니다. 컨테이너 배포 모드를 선택하는 경우에만 `linux/amd64` 이미지가
> 필요합니다.
