"""
[SDK v2] 실습 3: GroupChat 워크플로우

에이전트를 **Foundry Agent SDK v2**로 생성하고, **MAF ``GroupChatBuilder``**로
여러 에이전트가 하나의 주제를 협업 토론하게 합니다.
기획자, 개발자, 디자이너가 모바일 앱 신규 기능을 함께 기획합니다.

기존 ``src/03_group_chat.py``와 토론 구조는 같지만, 참여 에이전트를 MAF
FoundryChatClient가 아니라 SDK v2로 생성한 영속 에이전트로 구성합니다.
"""

import asyncio
import os
import sys

from dotenv import load_dotenv

# 공용 스트리밍 헬퍼(src/_streaming.py)와 프로젝트 루트(.env)를 참조하기 위한 경로 설정
_SRC_DIR = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, _SRC_DIR)
load_dotenv(dotenv_path=os.path.join(_SRC_DIR, "..", ".env"))

from agent_framework.orchestrations import GroupChatBuilder, GroupChatState
from azure.identity import AzureCliCredential

from _foundry_agents import FoundryAgentFactory
from _streaming import stream_workflow


async def main():
    """SDK v2 에이전트들을 MAF GroupChat 워크플로우로 실행하는 메인 함수"""

    print("=== [SDK v2] GroupChat 워크플로우 실행 ===\n")

    project_endpoint = os.getenv("PROJECT_ENDPOINT")
    model = os.getenv("MODEL_DEPLOYMENT_NAME", "gpt-5.4")

    if not project_endpoint:
        print("오류: PROJECT_ENDPOINT 환경 변수를 설정해주세요.")
        sys.exit(1)

    # ── 1단계: Foundry Agent SDK v2로 서버 측 에이전트 생성 ──
    factory = FoundryAgentFactory(project_endpoint, model, AzureCliCredential())

    try:
        planner = factory.create(
            "planner",
            instructions=(
                "당신은 시니어 프로덕트 매니저입니다. "
                "비즈니스 가치와 사용자 요구사항을 기반으로 기능을 기획합니다. "
                "다른 팀원의 의견을 경청하고 실현 가능한 방향으로 조율합니다. "
                "답변은 간결하게 핵심만 전달합니다. 한국어로 대화합니다."
            ),
        )
        developer = factory.create(
            "developer",
            instructions=(
                "당신은 시니어 풀스택 개발자입니다. "
                "기술적 실현 가능성과 아키텍처, Azure 활용 방안을 평가합니다. "
                "기획자·디자이너 제안에 기술적 피드백을 제공합니다. "
                "답변은 간결하게 핵심만 전달합니다. 한국어로 대화합니다."
            ),
        )
        designer = factory.create(
            "designer",
            instructions=(
                "당신은 시니어 UX/UI 디자이너입니다. "
                "사용자 경험, 인터페이스, 접근성 관점에서 의견을 제시합니다. "
                "기획자·개발자 제안에 UX 관점의 피드백을 제공합니다. "
                "답변은 간결하게 핵심만 전달합니다. 한국어로 대화합니다."
            ),
        )

        # 라운드 로빈 발화 순서(참여자 식별자 = 에이전트 이름) 및 표시 라벨
        speakers = [planner.name, developer.name, designer.name]
        name_map = {
            planner.name: "기획자",
            developer.name: "개발자",
            designer.name: "디자이너",
        }

        def select_next_speaker(state: GroupChatState) -> str:
            """라운드 로빈 방식으로 다음 발화자를 선택합니다."""
            return speakers[state.current_round % len(speakers)]

        # ── 2단계: Microsoft Agent Framework로 GroupChat 워크플로우 구성·실행 ──
        await factory.enable_tracing()
        workflow = GroupChatBuilder(
            participants=[planner, developer, designer],
            selection_func=select_next_speaker,
            max_rounds=6,  # 무한 토론 방지
        ).build()

        topic = "모바일 앱 신규 기능 기획: AI 기반 개인화 추천 시스템을 도입하려고 합니다."
        print(f"주제: {topic}\n")
        print("=" * 50)
        print("\n[GroupChat 토론 결과]")
        await stream_workflow(workflow, topic, name_map=name_map)

    except Exception as e:
        print(f"GroupChat 실행 중 오류 발생: {e}")
        sys.exit(1)
    finally:
        # ── 3단계: 생성한 서버 측 에이전트 정리 + 추적 플러시 ──
        factory.cleanup()
        factory.flush_tracing()

    print("\n=== 실행 완료 ===")


if __name__ == "__main__":
    asyncio.run(main())
