# 실습 3 — GroupChat 워크플로우를 Hosted Agent로 배포

이 저장소 `src/03_group_chat.py`의 다중 협업 토론(**기획자 → 개발자 → 디자이너**)을
그대로 가져와, `Workflow.as_agent()`로 감싼 뒤 Foundry **Hosted Agent**로 배포합니다.

## 핵심 코드 (`main.py`)

```python
from agent_framework.orchestrations import GroupChatBuilder
from agent_framework_foundry_hosting import ResponsesHostServer

workflow_agent = (
    GroupChatBuilder(participants=[...], selection_func=select_next_speaker, max_rounds=3)
    .build()
    .as_agent()
)
server = ResponsesHostServer(workflow_agent)
server.run()
```

각 참여 에이전트에 `default_options={"store": False}`를 지정해 호스팅 인프라가
관리하는 대화 이력과 중복 저장을 피합니다.
`/responses` 호출은 최종 응답을 한 번에 반환하므로, 호스팅 예제는 각 발화를
3문장 이내·3라운드로 제한해 로컬 호출이 안정적으로 끝나게 합니다.

## 환경 변수

| 변수 | 설명 |
| --- | --- |
| `FOUNDRY_PROJECT_ENDPOINT` | Hosted Agent 표준. 런타임이 자동 주입 |
| `AZURE_AI_MODEL_DEPLOYMENT_NAME` | 모델 배포 이름. 런타임이 자동 주입 |
| `PROJECT_ENDPOINT` / `MODEL_DEPLOYMENT_NAME` | 저장소 로컬 호환용 폴백 (선택) |

## 로컬 실행 & 배포

```bash
azd ext install azure.ai.agents && azd auth login
mkdir -p ~/deploy/group-chat && cd ~/deploy/group-chat
REPO="/path/to/copilot-cli-agent-framework"
azd ai agent init --no-prompt \
  -m "$REPO/src/hosted_agents/03_group_chat/agent.manifest.yaml" \
  --agent-name maf-lab-group-chat \
  --project-id "<Foundry 프로젝트 리소스 ID>" \
  --model-deployment gpt-5.4 \
  --deploy-mode code --runtime python_3_13 --entry-point main.py \
  --protocol responses --force

export FOUNDRY_PROJECT_ENDPOINT="https://<account>.services.ai.azure.com/api/projects/<project>"
export AZURE_AI_MODEL_DEPLOYMENT_NAME="gpt-5.4"

# 배포 시 기존 모델 배포를 그대로 사용하려면 init이 만든 azure.yaml의
# deployments 블록을 제거하고 azd 환경값을 고정합니다.
azd env set AZURE_AI_MODEL_DEPLOYMENT_NAME "$AZURE_AI_MODEL_DEPLOYMENT_NAME"
azd env set AI_AGENT_PENDING_PROVISION ""

azd ai agent run                                   # 터미널 1: 로컬 호스트(:8088, 블로킹)
azd ai agent invoke --local "AI 기반 개인화 추천 시스템 도입을 함께 기획해줘"  # 터미널 2

# 배포는 로컬 서버를 중지한 뒤 실행합니다.
azd provision --no-prompt   # (필요 시) 리소스 생성
azd deploy --no-prompt      # 코드 ZIP 원격 빌드 → Foundry에 배포
```

배포 후 포털 **Assets → 에이전트 → Traces 탭**에서 발화 순서별 모델 호출을
추적할 수 있습니다.

> Hosted Agents는 현재 **preview**입니다. 권장 코드 ZIP 배포 모드는 로컬 Docker가
> 필요 없습니다. 컨테이너 배포 모드를 선택하는 경우에만 `linux/amd64` 이미지가
> 필요합니다.
