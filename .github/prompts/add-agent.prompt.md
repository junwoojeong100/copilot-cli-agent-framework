---
description: "새로운 Agent Framework 에이전트 시나리오를 추가합니다"
mode: "agent"
---

# 새 에이전트 시나리오 추가

## 요청사항

아래 시나리오에 맞는 새 에이전트(또는 워크플로우)를 `src/`에 추가해주세요.

- 파일명: {{file_name}}  (예: 05_my_workflow.py)
- 에이전트/워크플로우명: {{agent_name}}
- 역할: {{role_description}}
- 패턴: 단일 에이전트 / Handoff / GroupChat / Custom 순차

## 현재 시나리오 구조 (`src/`)

1. **단일 에이전트** (`01_single_agent.py`) — `Agent(client, name=..., instructions=...)` + `await agent.run(...)`
2. **Handoff** (`02_handoff_workflow.py`) — `HandoffBuilder` + `add_handoff(from, [to...])`
3. **GroupChat** (`03_group_chat.py`) — `GroupChatBuilder(participants=..., selection_func=..., max_rounds=...)`
4. **Custom 순차** (`04_custom_workflow.py`) — 일반 Python 제어 흐름으로 에이전트 순차 연결 + 조건부 라우팅

## 규칙

- 기존 예제의 구조를 따른다:
  ```python
  client = FoundryChatClient(
      project_endpoint=os.getenv("PROJECT_ENDPOINT"),
      model=os.getenv("MODEL_DEPLOYMENT_NAME", "gpt-4o"),
      credential=AzureCliCredential(),
  )
  agent = Agent(client=client, name="...", instructions="...")
  ```
- 모든 호출은 `async/await`, 진입점은 `asyncio.run(main())`
- `PROJECT_ENDPOINT` 누락 시 한국어 오류 메시지 후 `sys.exit(1)`
- `instructions`와 콘솔 출력은 한국어로 작성
- 무한 루프 방지를 위해 워크플로우에는 `max_rounds`/수렴 조건을 둔다
- 작성 후 `agent-framework-codegen` 스킬의 API 규칙과 일치하는지 확인
