---
name: agent-framework-codegen
description: "Microsoft Agent Framework(Python, agent-framework 1.8.x) SDK로 AI 에이전트·워크플로우 코드 생성. USE FOR: Agent Framework 코드 생성, 에이전트 추가, Sequential·Concurrent·GroupChat·Handoff·Magentic 오케스트레이션, WorkflowBuilder 조건부 그래프, 에이전트 합성(as_tool), MCP 도구 연동, RAG(컨텍스트 프로바이더), Microsoft Foundry 연동. DO NOT USE FOR: Azure 리소스 배포·관리."
---

# Microsoft Agent Framework 코드 생성 스킬

이 프로젝트에서 **Microsoft Agent Framework(MAF)** SDK로 에이전트·워크플로우를 작성할 때
따라야 하는 패턴과 레퍼런스입니다. 핵심 예제(`01`~`06`)는 `src/`의 콘솔 스크립트이며,
`FoundryChatClient`로 Microsoft Foundry에 연결합니다.

> **기준 버전**: MAF core/foundry `1.8.1`. 메타패키지 `agent-framework`는 사용하지 않고,
> 아래처럼 예제에 필요한 하위 패키지를 정확히 고정합니다. 아래 API 시그니처는 이 조합으로
> 검증되었습니다.

| 용도 | 고정 버전 |
|------|-----------|
| Core / OpenAI / Foundry | `agent-framework-core==1.8.1` · `agent-framework-openai==1.8.1` · `agent-framework-foundry==1.8.1` |
| 오케스트레이션 | `agent-framework-orchestrations==1.0.0rc3` |
| Azure AI Search 컨텍스트 프로바이더 | `agent-framework-azure-ai-search==1.0.0b260521` |
| Hosted Agent | `agent-framework-foundry-hosting==1.0.0a260528` |
| Hosted 프로토콜 / azd 확장 | Responses `1.0.0` / `azure.ai.agents==0.1.37-preview` |

> `agent-framework-orchestrations==1.0.0`과 최신 Azure AI Search/hosting 프리릴리스는
> MAF core 1.9 이상을 요구할 수 있습니다. 개별 패키지만 임의로 업그레이드하지 말고
> 저장소의 `requirements.txt` 조합을 함께 갱신·검증합니다.

## 1. SDK Import 경로

```python
# 핵심 (최상위)
from agent_framework import (
    Agent,                     # 에이전트
    MCPStreamableHTTPTool,     # MCP 도구 연동 (12절)
    WorkflowBuilder, Case, Default,   # 조건부 라우팅 그래프 (9절)
    AgentResponseUpdate,       # 스트리밍 토큰 청크 (3절)
    AgentExecutorResponse,     # 워크플로우 참여자 완성 응답 (6·7절)
)
# Foundry 연동 (별도 서브패키지)
from agent_framework.foundry import FoundryChatClient
# 오케스트레이션 (별도 서브패키지)
from agent_framework.orchestrations import (
    SequentialBuilder,   # 순차 (4절)
    ConcurrentBuilder,   # 동시 (5절)
    GroupChatBuilder, GroupChatState,   # GroupChat (6절)
    HandoffBuilder,      # Handoff (7절)
    MagenticBuilder,     # Magentic — 매니저 주도 (8절)
)
# Azure AI Search 컨텍스트 프로바이더 (13절, RAG agentic)
from agent_framework.azure import AzureAISearchContextProvider
from azure.identity import AzureCliCredential
```

> **주의**: `Agent`·`WorkflowBuilder`·`Case`·`Default`·MCP 도구는 **`agent_framework` 최상위**,
> Foundry 연동은 **`agent_framework.foundry`**, 오케스트레이션 빌더는
> **`agent_framework.orchestrations`** 에 있다. 경로를 혼동하지 않는다.

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

async def main() -> None:
    project_endpoint = os.getenv("PROJECT_ENDPOINT")
    model = os.getenv("MODEL_DEPLOYMENT_NAME", "gpt-5.4")
    if not project_endpoint:
        print("오류: PROJECT_ENDPOINT 환경 변수를 설정해주세요.")
        sys.exit(1)

    credential = AzureCliCredential()
    try:
        client = FoundryChatClient(
            project_endpoint=project_endpoint,
            model=model,
            credential=credential,
        )
        # ... 에이전트/워크플로우 구성·실행 ...
    finally:
        credential.close()

if __name__ == "__main__":
    asyncio.run(main())
```

- `FoundryChatClient`의 인자는 **키워드 전용**이다(`project_endpoint=`, `model=`, `credential=`).
- 인증은 키리스(`AzureCliCredential` = 로컬 `az login` 세션)로 한다.
- 자격 증명은 `finally`에서 닫아 내부 전송 리소스를 정리한다.

## 3. 단일 에이전트 (생성·실행·반환 타입)

```python
agent = Agent(
    client=client,
    name="기술_어시스턴트",
    instructions="당신은 ... 한국어로 답변합니다.",   # 역할·말투는 instructions로 부여
)

# 방법 A (이 repo 표준): 스트리밍 — 토큰 단위 실시간 출력
from _streaming import stream_agent
text = await stream_agent(agent, "질문 내용", label="에이전트 응답")

# 방법 B: 비스트리밍 — 완성된 응답을 한 번에
response = await agent.run("질문 내용")   # -> AgentResponse
print(response)            # str(response) == 최종 텍스트
print(response.text)       # 텍스트 필드 직접 접근
```

- `Agent(client, instructions=..., *, name=..., tools=..., context_providers=..., middleware=...)`.
  `client`만 위치 인자이고 나머지는 키워드로 넘기는 것을 권장한다.
- `await agent.run(msg)` → **`AgentResponse`** (텍스트는 `str(response)` 또는 `response.text`).
- `agent.run(msg, stream=True)` → **비동기 이터레이터**(`AgentResponseUpdate`, `.text` 청크).
  **이 프로젝트 표준**은 `src/_streaming.py`의 `stream_agent()`/`stream_workflow()` 헬퍼 사용이다.
- `name`은 단일/그룹 에이전트에서는 한국어도 가능하지만, **Handoff에서는 도구명이 되므로
  ASCII(`^[a-zA-Z0-9_.-]+$`)만** 사용한다(7절).

## 4. Sequential 워크플로우 (순차 파이프라인)

참여자 순서대로 출력을 다음 단계 입력으로 전달한다.

```python
from agent_framework.orchestrations import SequentialBuilder

workflow = SequentialBuilder(
    participants=[analyzer_agent, writer_agent, editor_agent]
).build()

from _streaming import stream_workflow
await stream_workflow(workflow, "Kubernetes 비용 최적화 전략")
```

- `SequentialBuilder(*, participants=[...])` — 키워드 전용. `.build()`로 `Workflow` 생성.
- 비스트리밍이면 `result = await workflow.run(msg)` 후 `result.get_outputs()`로 최종 출력 추출.

## 5. Concurrent 워크플로우 (병렬 검토)

같은 입력을 여러 전문가가 **동시에** 검토한다(팬아웃→팬인).

```python
from agent_framework.orchestrations import ConcurrentBuilder

workflow = ConcurrentBuilder(
    participants=[security_agent, perf_agent, ux_agent]
).build()
await stream_workflow(workflow, design_doc)
```

- `ConcurrentBuilder(*, participants=[...])`. 기본 취합 대신 커스텀 집계가 필요하면
  `.with_aggregator(...)`를 체이닝한다.

## 6. GroupChat 워크플로우 (협업 토론)

여러 에이전트가 하나의 대화를 공유하며 협업한다. 다음 발화자는 `selection_func`으로 정한다.

```python
from agent_framework.orchestrations import GroupChatBuilder, GroupChatState

def select_next_speaker(state: GroupChatState) -> str:
    speakers = ["기획자", "개발자", "디자이너"]
    return speakers[state.current_round % len(speakers)]

workflow = GroupChatBuilder(
    participants=[planner_agent, developer_agent, designer_agent],
    selection_func=select_next_speaker,
    max_rounds=6,            # 무한 토론 방지 (권장)
).build()
await stream_workflow(workflow, "토론 주제")
```

- 종료 제어: 생성자 인자 `max_rounds=` 또는 빌더 메서드 `.with_max_rounds(n)` /
  `.with_termination_condition(...)`. **반드시 하나는 설정**한다(미설정 시 종료되지 않을 수 있음).
- `GroupChatState`는 `current_round`·`participants`·`conversation`을 제공한다.
- 참여자 `name`은 도구명이 아니므로 한국어도 가능하다(Handoff와 다른 점).
- 토론 내용은 종료 메시지(`get_outputs()`)가 아니라 이벤트의 **`AgentExecutorResponse`** 에서
  추출한다(`stream_workflow` 헬퍼가 이를 처리한다).

## 7. Handoff 워크플로우 (접수→전문가 위임)

접수(triage) 에이전트가 요청을 분석해 전문가에게 위임한다.

```python
from agent_framework.orchestrations import HandoffBuilder

# 주의: name은 handoff_to_<name> 도구명이 되므로 ASCII만 사용(페르소나는 instructions로 한국어)
# 모든 참여 Agent에 require_per_service_call_history_persistence=True 필수
tech = Agent(client=client, name="tech_support", instructions="당신은 기술 지원 전문가입니다. ...",
             require_per_service_call_history_persistence=True)
billing = Agent(client=client, name="billing", instructions="당신은 결제 지원 전문가입니다. ...",
                require_per_service_call_history_persistence=True)
triage = Agent(client=client, name="triage", instructions=(
    "당신은 접수 담당자입니다. 요청을 분석해 적절한 전문가에게 연결합니다.\n"
    "- 기술 문제 → handoff_to_tech_support 호출\n"
    "- 결제 문제 → handoff_to_billing 호출"
), require_per_service_call_history_persistence=True)

workflow = (
    HandoffBuilder(name="고객_지원", participants=[triage, tech, billing])
    .with_start_agent(triage)                 # 시작(접수) 에이전트
    .add_handoff(triage, [tech, billing])     # 위임 경로 제한 (생략 시 mesh)
    .with_autonomous_mode()                   # 사용자 개입 없이 자동 진행
    .build()
)
result = await workflow.run("결제 오류가 발생했어요.")
for output in result.get_outputs():
    print(output)
```

- `HandoffBuilder(name=..., participants=[...])` — 빌더 생성(키워드 인자)
- `.with_start_agent(agent)` — 시작(접수) 에이전트 지정
- `.add_handoff(from, [to...])` — 특정 위임 경로만 허용(생략 시 기본 mesh)
- `.with_autonomous_mode()` — 사용자 입력 없이 자동 진행
- `.with_termination_condition(fn)` — 종료 조건 지정
- `.build()` — `Workflow` 생성

## 8. Magentic 워크플로우 (매니저 주도 동적 협업)

**매니저 에이전트가 작업을 계획·분해하고**, 전문가 에이전트들에게 동적으로 위임·취합한다.
복잡한 다단계 과제(리서치+코딩+검증 등)에 적합하다(Magentic-One 계열).

```python
from agent_framework.orchestrations import MagenticBuilder

manager = Agent(client=client, name="manager",
                instructions="작업을 단계로 분해하고 진행을 점검하며 전문가에게 위임합니다. 한국어로.")
researcher = Agent(client=client, name="researcher", instructions="자료를 조사합니다. 한국어로.")
coder = Agent(client=client, name="coder", instructions="코드를 작성·수정합니다. 한국어로.")

workflow = (
    MagenticBuilder(
        participants=[researcher, coder],
        manager_agent=manager,     # 계획·조율을 담당하는 매니저
        max_round_count=10,        # 라운드 상한 (무한 루프 방지)
    )
    # .with_plan_review()          # (선택) 사람이 계획을 검토·승인하는 HITL
    .build()
)
result = await workflow.run("주제를 조사한 뒤 예제 코드를 작성하고 검증해줘.")
for output in result.get_outputs():
    print(output)
```

- 검증된 생성자 인자: `participants`, `manager_agent`(또는 `manager`), `max_round_count`,
  `max_stall_count`(기본 3), `enable_plan_review`.
- HITL이 필요하면 `.with_plan_review()` 또는 `enable_plan_review=True`로 계획 검토 단계를 켠다.

> **오케스트레이션 선택 기준**
> - 정해진 순서: **Sequential** · 병렬 검토: **Concurrent**
> - 자유 토론(발화자 제어): **GroupChat** · 역할 위임(접수→전문가): **Handoff**
> - 동적 계획·분해가 필요한 복잡 과제: **Magentic**
> - 조건 분기/팬아웃이 있는 명시적 그래프: **WorkflowBuilder**(9절)

## 9. WorkflowBuilder — 조건부 라우팅 그래프

선언적이지만 **조건부 분기(switch-case)** 와 **팬아웃/팬인**이 필요한 흐름에 사용한다.
`Agent`를 노드로 직접 전달할 수 있다.

```python
from agent_framework import WorkflowBuilder, Case, Default

workflow = (
    WorkflowBuilder(start_executor=analyzer_agent)
    .add_switch_case_edge_group(
        analyzer_agent,
        [
            Case(condition=lambda msg: "기술" in str(msg), target=tech_writer_agent),
            Default(target=general_writer_agent),
        ],
    )
    .add_edge(tech_writer_agent, editor_agent)
    .add_edge(general_writer_agent, editor_agent)
    .build()
)
result = await workflow.run("Kubernetes 비용 최적화 전략")
for output in result.get_outputs():
    print(output)
```

- `WorkflowBuilder(start_executor=...)` — 빌더 생성(시작 노드, 키워드 인자)
- `.add_edge(source, target)` — 단순 순차 엣지
- `.add_switch_case_edge_group(source, [Case..., Default])` — 조건부 분기(순서대로 평가, 첫 일치)
- `.add_fan_out_edges(source, [t1, t2])` — 팬아웃(같은 메시지를 병렬 전송)
- `Case(condition=lambda msg: ..., target=agent)` / `Default(target=agent)` — 분기 케이스 / 기본
- `.build()` — `Workflow` 생성

## 10. 에이전트 합성 — Agent as Tool

에이전트를 **다른 에이전트의 도구**로 노출해 계층형 구성을 만든다.

```python
research_tool = researcher_agent.as_tool(
    name="research",
    description="주제를 조사해 핵심 사실을 정리합니다.",
)
# FunctionTool을 상위 에이전트의 tools=에 전달
supervisor = Agent(client=client, name="supervisor",
                   instructions="필요하면 research 도구로 조사한 뒤 종합합니다.",
                   tools=research_tool)
result = await supervisor.run("최신 AKS 비용 절감 방법을 조사해 정리해줘.")
```

- `agent.as_tool(*, name=..., description=..., arg_name="task", approval_mode="never_require")`
  → `FunctionTool`. 다른 에이전트의 `tools=`로 넘긴다.
- 에이전트를 MCP 서버로 노출하려면 `agent.as_mcp_server()`를 사용한다.

## 11. (선택) Python 제어 흐름 커스텀 워크플로우

SDK 빌더 없이 일반 Python 흐름으로 연결해도 된다(간단한 라우팅에 적합).

```python
analysis = await agents["topic_analyzer"].run(input_topic)
route = "tech_writer" if "기술" in str(analysis) else "general_writer"
draft = await agents[route].run(f"...{analysis}...")
final = await agents["editor"].run(f"...{draft}...")
print(final)
```

- 분기가 복잡해지면 9절의 `WorkflowBuilder`로 전환한다.

## 12. MCP 도구 연동 (외부 시스템 호출)

에이전트가 외부 MCP 서버의 도구를 런타임에 호출하게 한다. `tools=` 인자로 전달한다.

```python
from agent_framework import Agent, MCPStreamableHTTPTool

learn_mcp = MCPStreamableHTTPTool(
    name="MicrosoftLearn",
    url="https://learn.microsoft.com/api/mcp",
    description="Microsoft/Azure 공식 문서·코드 샘플 검색",
    # 인증이 필요하면 런타임 kwargs를 받는 header_provider로 헤더를 동적 제공
    # header_provider=lambda _: {"Authorization": f"Bearer {token}"},
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

- `MCPStreamableHTTPTool` — Streamable HTTP 원격 서버
- `MCPStdioTool` — 로컬 프로세스(stdio) 서버
- `MCPWebsocketTool` — WebSocket 서버

- 반드시 `async with mcp_tool:` 컨텍스트 안에서 에이전트를 생성·실행한다.
- 인증 헤더는 `headers=`가 아니라 **`header_provider`**로 전달한다. MAF 1.8.1의 콜백은
  런타임 키워드 인자 딕셔너리 하나를 받으므로 `lambda _: {...}` 형태여야 한다.
- 여러 도구는 `tools=[tool_a, tool_b]` 리스트로 전달한다.

## 13. RAG (검색 증강 생성)

질문 관련 문서를 먼저 검색해 컨텍스트로 주입한 뒤 답하게 한다: 검색 → 증강 → 생성.

### 13.1 코드 직접 방식 — 하이브리드 검색 (`src/06_rag_agent.py`)

```python
docs = retrieve(question, top_k=2)          # 1) 검색 (Azure AI Search 하이브리드: BM25+벡터)
context = build_context(docs)
augmented = (                               # 2) 증강 (프롬프트에 주입)
    f"다음 참고 문서를 바탕으로 답하세요.\n\n--- 참고 문서 ---\n{context}\n\n"
    f"--- 질문 ---\n{question}"
)
agent = Agent(client=client, name="RAG_어시스턴트",
              instructions="제공된 문서 안의 정보만 근거로 답하고, 없으면 모른다고 한다.")
result = await agent.run(augmented)          # 3) 생성
```

### 13.2 컨텍스트 프로바이더 방식 — Foundry IQ agentic (`src/06_rag_agent_foundry_iq.py`)

검색 단계를 **컨텍스트 프로바이더**에 위임한다. 에이전트가 실행될 때 프로바이더가
질의 계획 기반 멀티쿼리(agentic) 검색으로 컨텍스트를 자동 주입한다.

```python
from agent_framework.azure import AzureAISearchContextProvider
from azure.identity.aio import AzureCliCredential as AioAzureCliCredential

aio_credential = AioAzureCliCredential()
try:
    async with AzureAISearchContextProvider(
        endpoint=search_endpoint,
        index_name=index_name,
        mode="agentic",
        model=chat_model_deployment,               # 질의 계획용 채팅 모델
        azure_openai_resource_url=aoai_resource_url,
        credential=aio_credential,
        retrieval_reasoning_effort="low",          # minimal은 LLM 질의 계획을 건너뜀
    ) as provider:
        agent = Agent(
            client=client,
            name="RAG_어시스턴트",
            instructions="제공된 컨텍스트만 근거로 답하고 출처를 표시한다.",
            context_providers=[provider],          # 수동 검색 불필요
        )
        result = await agent.run(question)
finally:
    await aio_credential.close()
```

- 정확도를 좌우하는 두 축: **(1) 검색 품질**, **(2) "문서 밖 추측 금지" 지시문**.
- 13.1은 `SEARCH_SERVICE_ENDPOINT`·`SEARCH_INDEX_NAME`이 필요하다(인덱스 없으면 자동 생성).
- 13.2는 인덱스에 **기본 semantic 구성**이 있어야 하며, agentic 모드에서는 질의 계획용
  채팅 모델·Azure OpenAI 리소스 URL·비동기 자격 증명이 필요하다.
- 멀티쿼리 질의 계획은 `retrieval_reasoning_effort="low"` 또는 `"medium"`에서 동작한다.
  `"minimal"`은 LLM 질의 계획을 건너뛰고 전달된 검색 의도를 그대로 실행한다.
- 벡터 검색까지 사용하려면 인덱스 벡터 프로필에, 문서 임베딩과 같은 모델을 쓰는 쿼리
  벡터라이저가 연결되어야 한다.
- 이 provider 버전은 `model` 값을 지식 베이스의 배포 이름과 모델 이름에 모두 사용하므로,
  질의 계획 모델 배포 이름을 실제 모델 이름(예: `gpt-5.4`)과 같게 만든다.

## 14. 트러블슈팅

- `PROJECT_ENDPOINT 환경 변수를 설정해주세요` → 루트 `.env` 작성 + `load_dotenv` 경로 확인
- 인증 실패 → `az login` 재실행, `az account set`으로 구독 선택
- `ImportError: cannot import name 'ChatAgent'` → 이 버전엔 `ChatAgent`가 없음, `from agent_framework import Agent` 사용
- `Agent` has no attribute `run_stream` → 스트리밍은 `agent.run(msg, stream=True)`(별도 `run_stream` 없음)
- `400 Invalid 'tools[0].name'` (handoff) → Agent `name`에 한글/공백 사용, handoff 도구명은 ASCII(`^[a-zA-Z0-9_.-]+$`)만
- Handoff `build()`가 `ValueError`(persistence) → 일부 Agent에 `require_per_service_call_history_persistence=True` 누락
- 의도치 않은 handoff 경로 → 기본 mesh 적용, `add_handoff(from, [to...])`로 경로 제한
- GroupChat이 끝나지 않음 → `max_rounds` 또는 `with_termination_condition` 미설정
- GroupChat 결과가 종료 메시지만 나옴 → `get_outputs()`는 종료 메시지만, 토론은 이벤트의 `AgentExecutorResponse`에서 추출
- Magentic이 멈추거나 루프 → `max_round_count`/`max_stall_count`로 상한 지정
- `WorkflowBuilder` 분기가 항상 첫 케이스 → 조건은 순서대로 평가·첫 `True`에서 멈춤, 좁은 조건부터 배치
- MCP 도구를 호출하지 않음 → `tools=` 누락, 또는 `async with mcp_tool:` 밖에서 실행
- RAG가 엉뚱한 답 → 검색 결과 빈약 또는 "문서 밖 추측 금지" 지시문 누락
- `ImportError: agent_framework...` → 가상환경 활성화 후 `pip install -r requirements.txt` 실행
- 설치 후 MAF API 불일치 → 프리릴리스를 개별 업그레이드하지 말고 상단 호환 매트릭스로 재설치

## 15. 참고 — 예제 매핑 / 새 예제 규칙

- 단일 에이전트 — `src/01_single_agent.py`
- Sequential — `src/02_sequential_workflow.py`
- GroupChat — `src/03_group_chat.py`
- Concurrent — `src/04_concurrent_workflow.py`
- MCP 도구 연동 — `src/05_mcp_agent.py`
- RAG(하이브리드 / Foundry IQ) — `src/06_rag_agent.py` · `src/06_rag_agent_foundry_iq.py`
- (심화) Hosted Agent 배포 — `src/hosted_agents/`

- 새 예제는 `src/`에 **`NN_<name>.py`** 규칙으로 추가하고, 스트리밍은 `_streaming.py` 헬퍼를 쓴다.
- 원격 반영은 PR 기반으로만 한다(`AGENTS.md` 준수).
- 공식 문서: <https://learn.microsoft.com/agent-framework/> · 샘플:
  <https://github.com/microsoft/agent-framework/tree/main/python/samples>
