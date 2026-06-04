"""스트리밍 출력 공용 헬퍼.

에이전트·워크플로우 응답을 토큰(청크) 단위로 실시간 출력해, 답변이 생성되는
과정을 콘솔에서 바로 확인할 수 있게 합니다. 모든 예제(01~06)가 공유합니다.
"""

from typing import Any

from agent_framework import AgentExecutorResponse, AgentResponseUpdate


async def stream_agent(
    agent: Any,
    prompt: str,
    *,
    label: str | None = "에이전트 응답",
    **run_kwargs: Any,
) -> str:
    """에이전트 응답을 토큰 단위로 출력하고, 누적된 전체 텍스트를 반환합니다.

    Args:
        agent: 실행할 에이전트.
        prompt: 에이전트에 전달할 입력 메시지.
        label: 출력 앞에 붙일 머리말. None이면 머리말을 생략합니다.
        **run_kwargs: ``agent.run``에 그대로 전달할 추가 인자(예: tools).

    Returns:
        스트리밍으로 받은 전체 응답 텍스트(다음 단계 입력 등으로 재사용).
    """
    if label:
        print(f"{label}:")
    chunks = []
    async for update in agent.run(prompt, stream=True, **run_kwargs):
        text = getattr(update, "text", "") or ""
        if text:
            chunks.append(text)
            print(text, end="", flush=True)
    print()
    return "".join(chunks)


def _is_orchestrator(speaker: str | None) -> bool:
    """발화자 id가 내부 오케스트레이터(중계/종료용)인지 판별합니다."""
    return bool(speaker) and "orchestrator" in speaker


async def stream_workflow(
    workflow: Any,
    message: str,
    *,
    name_map: dict[str, str] | None = None,
) -> Any:
    """워크플로우를 스트리밍 실행하며 발화자별 응답을 실시간 출력합니다.

    오케스트레이션 종류에 따라 이벤트 형태가 다릅니다.
      - Handoff: 발화자별로 **토큰 단위 갱신**(AgentResponseUpdate)이 흘러옵니다.
        → 토큰을 실시간으로 이어 붙여 출력합니다.
      - GroupChat / Sequential / Concurrent: 참여자는 내부에서 실행되고 **완성된 응답**
        (AgentExecutorResponse)만 이벤트로 노출됩니다. → 완성된 발언을 발화 순서대로
        블록 출력합니다.
    두 경우 모두 내부 오케스트레이터의 중계·종료 메시지는 생략하고, 토큰으로 이미
    출력한 발화자의 완성 이벤트는 중복 출력하지 않습니다.

    Args:
        workflow: 실행할 워크플로우.
        message: 워크플로우에 전달할 입력 메시지.
        name_map: executor_id → 표시 이름 매핑(선택). 없으면 executor_id를 그대로 사용.

    Returns:
        최종 ``WorkflowRunResult``.
    """
    name_map = name_map or {}
    current_speaker = None
    streamed = set()          # 토큰으로 이미 출력한 발화자 (완성 이벤트 중복 방지)
    printed_blocks = set()    # 블록으로 출력한 (발화자, 텍스트) 중복 방지

    stream = workflow.run(message, stream=True)
    async for event in stream:
        data = getattr(event, "data", None)

        # 1) 토큰 단위 스트리밍 (Handoff 등)
        if isinstance(data, AgentResponseUpdate):
            speaker = getattr(event, "executor_id", None)
            text = getattr(data, "text", "") or ""
            if not text or _is_orchestrator(speaker):
                continue
            if speaker != current_speaker:
                current_speaker = speaker
                print(f"\n\n[{name_map.get(speaker, speaker)}]")
            print(text, end="", flush=True)
            streamed.add(speaker)
            continue

        # 2) 완성된 응답 (Sequential / GroupChat / Concurrent 참여자 등)
        items = data if isinstance(data, list) else [data]
        for item in items:
            if not isinstance(item, AgentExecutorResponse):
                continue
            speaker = getattr(item, "executor_id", getattr(event, "executor_id", None))
            if _is_orchestrator(speaker) or speaker in streamed:
                continue
            text = str(item.agent_response).strip()
            key = (speaker, text)
            if not text or key in printed_blocks:
                continue
            printed_blocks.add(key)
            current_speaker = None  # 이후 토큰 스트림이 다시 머리말을 출력하도록 초기화
            print(f"\n\n[{name_map.get(speaker, speaker)}]\n{text}")

    print()
    return await stream.get_final_response()

