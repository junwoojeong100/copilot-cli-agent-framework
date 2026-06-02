# 실습 3 — GroupChat 워크플로우를 Hosted Agent로 배포

이 저장소 `src/03_group_chat.py`의 다중 협업 토론(**기획자 → 개발자 → 디자이너**)을
그대로 가져와, `Workflow.as_agent()`로 감싼 뒤 Foundry **Hosted Agent**로 배포합니다.

## 핵심 코드 (`main.py`)

```python
from agent_framework.orchestrations import GroupChatBuilder
from agent_framework_foundry_hosting import ResponsesHostServer

workflow_agent = (
    GroupChatBuilder(participants=[...], selection_func=select_next_speaker, max_rounds=6)
    .build()
    .as_agent()
)
server = ResponsesHostServer(workflow_agent)
server.run()
```

각 참여 에이전트에 `default_options={"store": False}`를 지정해 호스팅 인프라가
관리하는 대화 이력과 중복 저장을 피합니다.

## 환경 변수

| 변수 | 설명 |
| --- | --- |
| `FOUNDRY_PROJECT_ENDPOINT` | Hosted Agent 표준. 런타임이 자동 주입 |
| `AZURE_AI_MODEL_DEPLOYMENT_NAME` | 모델 배포 이름. 런타임이 자동 주입 |
| `PROJECT_ENDPOINT` / `MODEL_DEPLOYMENT_NAME` | 저장소 로컬 호환용 폴백 (선택) |

## 로컬 실행 & 배포

```bash
azd ext install azure.ai.agents && azd auth login
azd ai agent init -m ./agent.manifest.yaml

export FOUNDRY_PROJECT_ENDPOINT="https://<account>.services.ai.azure.com/api/projects/<project>"
export AZURE_AI_MODEL_DEPLOYMENT_NAME="gpt-5.4"

azd ai agent run                                   # 로컬 호스트(:8088)
azd ai agent invoke --local "AI 기반 개인화 추천 시스템 도입을 함께 기획해줘"

azd provision   # (필요 시) 리소스 생성
azd deploy      # Foundry에 배포
```

배포 후 포털 **Assets → 에이전트 → Traces 탭**에서 발화 순서별 모델 호출을
추적할 수 있습니다.

> Hosted Agents는 현재 **preview**이며 `linux/amd64` 이미지를 요구합니다.
