# 실습 4 — 동시(Concurrent) 워크플로우를 Hosted Agent로 배포

이 저장소 `src/04_concurrent_workflow.py`의 병렬 검토(**보안·성능·UX 리뷰어**)를
그대로 가져와, `Workflow.as_agent()`로 감싼 뒤 Foundry **Hosted Agent**로 배포합니다.

> **Hosted 전용 호환성**: MAF core `1.11.0` + foundry/openai `1.10.1` +
> orchestrations `1.0.0` + hosting `1.0.0a260709` + Responses `2.0.0` +
> azd `azure.ai.agents>=1.0.0-beta.5` 조합입니다.
> 콘솔 예제의 MAF 1.8.1 환경과 분리된 가상환경에 설치하세요.
> 배포 계정에는 Foundry 프로젝트 범위의 **Foundry Project Manager** 역할이 필요합니다.

## 핵심 코드 (`main.py`)

```python
from agent_framework.orchestrations import ConcurrentBuilder
from agent_framework_foundry_hosting import ResponsesHostServer

workflow_agent = (
    ConcurrentBuilder(participants=[security_agent, performance_agent, ux_agent])
    .build()
    .as_agent()
)
server = ResponsesHostServer(workflow_agent)
server.run()
```

각 리뷰어 에이전트에 `default_options={"store": False}`를 지정합니다.

## 환경 변수

| 변수 | 설명 |
| --- | --- |
| `FOUNDRY_PROJECT_ENDPOINT` | Hosted Agent 표준. 런타임이 자동 주입 |
| `AZURE_AI_MODEL_DEPLOYMENT_NAME` | 모델 배포 이름. 런타임이 자동 주입 |
| `PROJECT_ENDPOINT` / `MODEL_DEPLOYMENT_NAME` | 저장소 로컬 호환용 폴백 (선택) |

## 로컬 실행 & 배포

```bash
azd ext install microsoft.foundry
azd auth login
mkdir -p ~/deploy/concurrent-workflow && cd ~/deploy/concurrent-workflow
REPO="/path/to/agent-framework-labs"
azd ai agent init . --no-prompt \
  -m "$REPO/src/hosted_agents/04_concurrent_workflow/azure.yaml" \
  --project-id "<Foundry 프로젝트 리소스 ID>" \
  --model-deployment gpt-5.4
azd env set AZURE_AI_MODEL_DEPLOYMENT_NAME gpt-5.4

azd ai agent run                                   # 터미널 1: 로컬 호스트(:8088, 블로킹)
azd ai agent invoke --local "게스트 결제 + 단말 캐시 설계안을 검토해줘"  # 터미널 2

# 배포는 로컬 서버를 중지한 뒤 실행합니다.
azd provision --no-prompt   # (필요 시) 리소스 생성
azd deploy --no-prompt      # 코드 ZIP 원격 빌드 → Foundry에 배포
```

배포 후 포털 **Assets → 에이전트 → Traces 탭**에서 병렬 리뷰 각각의 모델
호출을 추적할 수 있습니다.

> Hosted Agents는 현재 **preview**입니다. 권장 코드 ZIP 배포 모드는 로컬 Docker가
> 필요 없습니다. 컨테이너 배포 모드를 선택하는 경우에만 `linux/amd64` 이미지가
> 필요합니다.
