"""
실습 3: GroupChat 워크플로우
여러 에이전트가 하나의 주제에 대해 협업 토론하는 GroupChat 패턴입니다.
기획자, 개발자, 디자이너가 모바일 앱 신규 기능을 함께 기획합니다.
"""

import asyncio
import os
import sys

from dotenv import load_dotenv

# 프로젝트 루트의 .env 파일 로드
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", ".env"))

from agent_framework import Agent, AgentExecutorResponse
from agent_framework.orchestrations import GroupChatBuilder, GroupChatState
from agent_framework.foundry import FoundryChatClient
from azure.identity import AzureCliCredential


def print_transcript(result) -> None:
    """GroupChat 실행 결과(이벤트 목록)에서 각 참여자의 발언을 순서대로 출력합니다.

    GroupChat의 최종 산출물(get_outputs)은 오케스트레이터의 종료 메시지뿐이라,
    실제 토론 내용은 이벤트 스트림의 AgentExecutorResponse에서 추출합니다.
    """
    last = None
    for event in result:
        data = getattr(event, "data", None)
        items = data if isinstance(data, list) else [data]
        for item in items:
            if isinstance(item, AgentExecutorResponse):
                speaker = getattr(item, "executor_id", "?")
                text = str(item.agent_response).strip()
                if (speaker, text) != last:  # 연속 중복 이벤트 제거
                    last = (speaker, text)
                    print(f"\n[{speaker}]\n{text}")


def select_next_speaker(state: GroupChatState) -> str:
    """라운드 로빈 방식으로 다음 발화자를 선택합니다.

    Args:
        state: 현재 GroupChat 상태.
            - state.current_round: 현재 라운드 인덱스 (0부터 시작)
            - state.participants: 참여자 이름 → 설명 딕셔너리
            - state.conversation: 전체 대화 이력

    Returns:
        다음 발화자 에이전트 이름.
    """
    speakers = ["기획자", "개발자", "디자이너"]
    idx = state.current_round % len(speakers)
    return speakers[idx]


async def main():
    """GroupChat 워크플로우를 구성하고 실행하는 메인 함수"""

    print("=== GroupChat 워크플로우 실행 ===\n")

    # ── 1단계: Foundry Chat 클라이언트 설정 ──
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

    # ── 2단계: 역할별 에이전트 생성 ──
    # 각 에이전트는 프로젝트에서 고유한 역할과 관점을 가집니다

    # 기획자 에이전트 - 비즈니스 관점에서 기능을 정의합니다
    planner_agent = Agent(
        client=client,
        name="기획자",
        instructions=(
            "당신은 시니어 프로덕트 매니저입니다. "
            "비즈니스 가치, 사용자 요구사항, 시장 트렌드를 기반으로 기능을 기획합니다. "
            "다른 팀원의 의견을 경청하고, 실현 가능한 방향으로 조율합니다. "
            "답변은 간결하게 핵심만 전달합니다. 한국어로 대화합니다."
        ),
    )

    # 개발자 에이전트 - 기술적 실현 가능성을 평가합니다
    developer_agent = Agent(
        client=client,
        name="개발자",
        instructions=(
            "당신은 시니어 풀스택 개발자입니다. "
            "기술적 실현 가능성, 아키텍처 설계, 개발 일정을 평가합니다. "
            "Azure 클라우드 서비스와 AI 기술 활용 방안을 제시합니다. "
            "기획자와 디자이너의 제안에 대해 기술적 피드백을 제공합니다. "
            "답변은 간결하게 핵심만 전달합니다. 한국어로 대화합니다."
        ),
    )

    # 디자이너 에이전트 - 사용자 경험(UX)을 설계합니다
    designer_agent = Agent(
        client=client,
        name="디자이너",
        instructions=(
            "당신은 시니어 UX/UI 디자이너입니다. "
            "사용자 경험, 인터페이스 디자인, 접근성을 중심으로 의견을 제시합니다. "
            "사용자 리서치 결과와 디자인 트렌드를 근거로 제안합니다. "
            "기획자와 개발자의 제안에 대해 UX 관점의 피드백을 제공합니다. "
            "답변은 간결하게 핵심만 전달합니다. 한국어로 대화합니다."
        ),
    )

    # ── 3단계: GroupChat 워크플로우 구성 ──
    # GroupChatBuilder를 사용하여 다중 에이전트 토론을 설정합니다
    workflow = GroupChatBuilder(
        participants=[planner_agent, developer_agent, designer_agent],
        selection_func=select_next_speaker,
        max_rounds=6,  # 무한 토론 방지를 위한 최대 라운드
    ).build()

    # ── 4단계: GroupChat 실행 ──
    # 토론 주제를 전달하여 협업 토론을 시작합니다
    topic = "모바일 앱 신규 기능 기획: AI 기반 개인화 추천 시스템을 도입하려고 합니다."
    print(f"주제: {topic}\n")
    print("=" * 50)

    try:
        result = await workflow.run(topic)

        # ── 5단계: 토론 결과 출력 ──
        # 이벤트 스트림에서 각 참여자의 발언을 순서대로 추출해 출력합니다.
        print("\n[GroupChat 토론 결과]")
        print_transcript(result)

    except Exception as e:
        print(f"GroupChat 실행 중 오류 발생: {e}")
        sys.exit(1)

    print("\n=== 실행 완료 ===")


if __name__ == "__main__":
    asyncio.run(main())
