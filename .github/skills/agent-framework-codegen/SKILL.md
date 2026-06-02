---
name: agent-framework-codegen
description: "Microsoft Agent Framework SDK를 사용한 AI 에이전트·워크플로우 코드 생성. USE FOR: Agent Framework 코드 생성, 에이전트 추가, Handoff/GroupChat/Custom 워크플로우 구성, Foundry 연동. DO NOT USE FOR: Azure 리소스 배포·관리."
---

# Microsoft Agent Framework 코드 생성 스킬

이 프로젝트에서 Microsoft Agent Framework SDK로 에이전트·워크플로우를 작성할 때 따라야 하는
패턴과 레퍼런스입니다. 모든 예제는 `src/`의 콘솔 스크립트 형태입니다.

---

## 1. SDK Import 경로

```python
from agent_framework import Agent, MCPStreamableHTTPTool   # MCP 도구 연동(7절)
from agent_framework.foundry import FoundryChatClient
from agent_framework.orchestrations import (
    HandoffBuilder,      # Handoff 워크플로우
    GroupChatBuilder,    # GroupChat 워크플로우
    GroupChatState,      # GroupChat 발화자 선택 상태
)
from azure.identity import AzureCliCredential
```

> **주의**: 핵심 클래스(`Agent`), Foundry 연동(`agent_framework.foundry`), 오케스트레이션
> (`agent_framework.orchestrations`)은 서로 다른 서브모듈이다. 경로를 혼동하지 않는다.

---

## 2. 공통 골격

모든 예제는 다음 골격을 따른다:

```python
import asyncio
import os
import sys
from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", ".env"))

from agent_framework import Agent
from agent_framework.foundry import FoundryChatClient
from azure.identity import AzureCliCredential


async def main():
    project_endpoint = os.getenv("PROJECT_ENDPOINT")
    model = os.getenv("MODEL_DEPLOYMENT_NAME", "gpt-4o")
    if not project_endpoint:
        print("오류: PROJECT_ENDPOINT 환경 변수를 설정해주세요.")
        sys.exit(1)

    client = FoundryChatClient(
        project_endpoint=project_endpoint,
        model=model,
        credential=AzureCliCredential(),
    )
    # ... 에이전트/워크플로우 구성 ...


if __name__ == "__main__":
    asyncio.run(main())
```

- 클라이언트는 한 번만 생성하여 모든 에이전트에 공유한다.
- 모든 에이전트 호출은 `await`로 한다.

---

## 3. 에이전트 생성 (Single Agent)

```python
agent = Agent(
    client=client,
    name="기술_어시스턴트",
    instructions="당신은 ... 한국어로 답변합니다.",   # 역할 지시문 (한국어)
)
result = await agent.run("질문 내용")
print(result)
```

- 역할·도메인·말투는 `instructions`로 부여한다.
- 단일 에이전트의 `name`은 한국어도 가능하다. **단, Handoff에서는 `name`이 `handoff_to_<name>`
  도구명이 되므로 ASCII(영문/숫자/`_`)만 사용**한다 (Foundry/OpenAI 도구명 규칙 `^[a-zA-Z0-9_.-]+$`).

---

## 4. Handoff 워크플로우

접수(Coordinator) 에이전트가 요청을 분석해 전문가 에이전트에게 위임한다.

```python
from agent_framework.orchestrations import HandoffBuilder

# 전문가 + 접수 에이전트 생성 (Handoff는 모든 참여 Agent에 이 플래그가 필수)
# 주의: name은 handoff_to_<name> 도구명이 되므로 ASCII만 사용(페르소나는 instructions로 한국어 부여)
tech_agent = Agent(client=client, name="tech_support", instructions="당신은 기술 지원 전문가입니다. ...",
                   require_per_service_call_history_persistence=True)
billing_agent = Agent(client=client, name="billing", instructions="당신은 결제 지원 전문가입니다. ...",
                      require_per_service_call_history_persistence=True)
triage_agent = Agent(client=client, name="triage", instructions=(
    "당신은 접수 담당자입니다. 요청을 분석하여 적절한 전문가에게 연결합니다.\n"
    "- 기술 문제 → handoff_to_tech_support 도구 호출\n"
    "- 결제 문제 → handoff_to_billing 도구 호출"
), require_per_service_call_history_persistence=True)

workflow = (
    HandoffBuilder(name="고객_지원",
                   participants=[triage_agent, tech_agent, billing_agent])
    .with_start_agent(triage_agent)                       # 시작 에이전트
    .add_handoff(triage_agent, [tech_agent, billing_agent])  # 위임 대상 명시
    .with_autonomous_mode()                               # 사용자 개입 없이 자동 진행
    .build()
)
result = await workflow.run("결제 오류가 발생했어요.")
for output in result.get_outputs():   # 최종 응답만 추출
    print(output)
```

| 메서드 | 용도 |
|--------|------|
| `HandoffBuilder(name=..., participants=...)` | 워크플로우 빌더 생성 (키워드 인자) |
| `.with_start_agent(agent)` | 시작(접수) 에이전트 지정 |
| `.add_handoff(from, [to...])` | 위임 가능 대상 명시 → LLM에 `handoff_to_*` 도구 노출 |
| `.with_autonomous_mode()` | 사용자 입력 없이 자동 진행 |
| `.build()` | 워크플로우 객체 생성 |

> **핵심**: `add_handoff`로 대상을 명시하지 않으면 handoff 도구가 노출되지 않는다.
> 또한 **모든 참여 Agent**에 `require_per_service_call_history_persistence=True`를 지정해야 한다
> (누락 시 `build()`가 `ValueError`를 발생시킨다).

---

## 5. GroupChat 워크플로우

여러 에이전트가 한 대화에 참여해 협업한다. 발화자는 `selection_func`으로 결정한다.

```python
from agent_framework.orchestrations import GroupChatBuilder, GroupChatState

def select_next_speaker(state: GroupChatState) -> str:
    """라운드 로빈으로 다음 발화자 선택."""
    speakers = ["기획자", "개발자", "디자이너"]
    return speakers[state.current_round % len(speakers)]

workflow = GroupChatBuilder(
    participants=[planner_agent, developer_agent, designer_agent],
    selection_func=select_next_speaker,
    max_rounds=6,          # 무한 토론 방지 (필수)
).build()
result = await workflow.run("토론 주제")
```

- `GroupChatState`: `current_round`, `participants`, `conversation` 제공.
- `max_rounds`로 수렴 조건을 둔다.
- 참여자 `name`은 도구명이 아니므로 한국어도 가능하다(Handoff와 다른 점).
- 최종 토론 내용은 `result.get_outputs()`(종료 메시지)가 아니라 이벤트의 `AgentExecutorResponse`에서
  추출한다. `from agent_framework import AgentExecutorResponse` 후 `isinstance` 필터로 발언을 모은다.

---

## 6. Custom 순차 워크플로우 (조건부 라우팅)

SDK 빌더 없이 **일반 Python 제어 흐름**으로 에이전트를 순차 연결한다.

```python
analysis = await agents["topic_analyzer"].run(input_topic)   # 1) 분석
route = "tech_writer" if "기술" in str(analysis).split("\n")[0] else "general_writer"  # 2) 라우팅
draft = await agents[route].run(f"...{analysis}...")          # 3) 초안
final = await agents["editor"].run(f"...{draft}...")          # 4) 편집
print(final)
```

- 라우팅 함수는 이전 에이전트의 출력 텍스트를 파싱해 다음 경로를 결정한다.
- 더 복잡한 그래프가 필요하면 `WorkflowBuilder` + `Case`/`Default`로 선언적 분기를 구성할 수 있다.

---

## 7. MCP 도구 연동 (외부 시스템 호출)

에이전트가 외부 MCP 서버의 도구를 런타임에 호출하게 한다. `tools=` 인자로 전달한다.

```python
from agent_framework import Agent, MCPStreamableHTTPTool

# HTTP(SSE) 원격 MCP 서버. 인증 필요 시 headers={"Authorization": "Bearer ..."}
learn_mcp = MCPStreamableHTTPTool(
    name="MicrosoftLearn",
    url="https://learn.microsoft.com/api/mcp",
    description="Microsoft/Azure 공식 문서 검색",
)

# async with 안에서만 세션 활성화 (진입=connect, 종료=close)
async with learn_mcp:
    agent = Agent(
        client=client,
        name="문서_리서치_어시스턴트",
        instructions="답변 전 도구로 검색해 출처와 함께 답한다.",
        tools=learn_mcp,
    )
    result = await agent.run("질문")
```

| 클래스 | 연결 방식 |
|--------|-----------|
| `MCPStreamableHTTPTool` | HTTP/SSE 원격 서버 |
| `MCPStdioTool` | 로컬 프로세스(stdio) 서버 |
| `MCPWebsocketTool` | WebSocket 서버 |

- 반드시 `async with mcp_tool:` 컨텍스트 안에서 에이전트를 생성·실행한다.
- 여러 도구는 `tools=[tool_a, tool_b]` 리스트로 전달한다.
- **Copilot CLI의 `.copilot/mcp-config.json`(개발자용)과 혼동하지 않는다.** 이 절은 *생성된
  MAF 에이전트가 런타임에 쓰는 도구*다.

---

## 8. RAG (검색 증강 생성)

질문 관련 문서를 먼저 검색해 컨텍스트로 주입한 뒤 답하게 한다: 검색 → 증강 → 생성.

```python
docs = retrieve(question, top_k=2)          # 1) 검색 (지식 베이스에서 추출)
context = build_context(docs)               # 검색 결과를 문자열로
augmented = (                               # 2) 증강 (프롬프트에 주입)
    f"다음 참고 문서를 바탕으로 답하세요.\n\n--- 참고 문서 ---\n{context}\n\n"
    f"--- 질문 ---\n{question}"
)
agent = Agent(client=client, name="RAG_어시스턴트",
              instructions="제공된 문서 안의 정보만 근거로 답하고, 없으면 모른다고 한다.")
result = await agent.run(augmented)          # 3) 생성
```

- 정확도를 좌우하는 두 축: **(1) 검색 품질**, **(2) "문서 밖은 추측 금지" 지시문**.
- 실습은 인메모리 키워드 검색. 운영은 `retrieve()`를 Azure AI Search(Foundry IQ)·벡터 검색으로
  교체한다 (`SEARCH_SERVICE_ENDPOINT`, `KNOWLEDGE_BASE_NAME` 사용).

---

## 9. 트러블슈팅

| 증상 | 원인 / 해결 |
|------|-------------|
| `PROJECT_ENDPOINT 환경 변수를 설정해주세요` | 루트 `.env` 작성 + `load_dotenv` 경로 확인 |
| 인증 실패 | `az login` 재실행, `az account set`으로 구독 선택 |
| `handoff_to_*` 도구가 안 보임 | `add_handoff(from, [to...])` 호출 누락 |
| `400 Invalid 'tools[0].name'` (handoff) | Agent `name`에 한글/공백 사용 — handoff 도구명은 ASCII(`^[a-zA-Z0-9_.-]+$`)만 허용. name을 영문으로 변경 |
| Handoff `build()`가 `ValueError`(persistence) | 일부 Agent에 `require_per_service_call_history_persistence=True` 누락 — 모든 참여 Agent에 지정 |
| GroupChat이 끝나지 않음 | `max_rounds` 미설정 |
| GroupChat 결과가 종료 메시지만 나옴 | `get_outputs()`는 종료 메시지만 반환 — 토론 내용은 이벤트의 `AgentExecutorResponse`에서 추출 |
| MCP 도구를 호출하지 않음 | `tools=` 전달 누락, 또는 `async with mcp_tool:` 밖에서 실행 |
| RAG가 엉뚱한 답을 함 | 검색 결과가 빈약하거나 "문서 밖 추측 금지" 지시문 누락 |
| `ImportError: agent_framework...` | `pip install -U agent-framework`, 가상환경 활성화 확인 |

