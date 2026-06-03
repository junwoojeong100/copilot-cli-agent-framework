"""[Hosted Agent] 실습 3: GroupChat 워크플로우를 Foundry Hosted Agent로 배포

기존 ``src/03_group_chat.py``의 다중 협업 토론(기획자·개발자·디자이너)을
그대로 가져와, ``Workflow.as_agent()``로 감싼 뒤 Hosted Agent로 호스팅합니다.

GroupChat 워크플로우 역시 ``.as_agent()`` 한 줄로 Hosted Agent가 되어,
관리형 인프라와 자동 trace/monitoring을 그대로 받습니다.
"""

import os

from agent_framework import Agent
from agent_framework.orchestrations import GroupChatBuilder, GroupChatState
from agent_framework.foundry import FoundryChatClient
from agent_framework_foundry_hosting import ResponsesHostServer
from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv

# 로컬 테스트 시 같은 폴더의 .env를 로드합니다.
# (Foundry에 배포되면 런타임이 환경 변수를 자동 주입합니다.)
load_dotenv()

# Foundry 호스팅 표준 env를 우선 사용하고, 로컬은 저장소 기존 이름으로 폴백합니다.
PROJECT_ENDPOINT = os.getenv("FOUNDRY_PROJECT_ENDPOINT") or os.getenv("PROJECT_ENDPOINT")
MODEL = (
    os.getenv("AZURE_AI_MODEL_DEPLOYMENT_NAME")
    or os.getenv("MODEL_DEPLOYMENT_NAME")
    or "gpt-5.4"
)


def select_next_speaker(state: GroupChatState) -> str:
    """라운드 로빈 방식으로 다음 발화자를 선택합니다.

    Args:
        state: 현재 GroupChat 상태(라운드 인덱스·참여자·대화 이력).

    Returns:
        다음 발화자 에이전트 이름.
    """
    speakers = ["기획자", "개발자", "디자이너"]
    return speakers[state.current_round % len(speakers)]


def main():
    """GroupChat 워크플로우를 만들어 Responses 프로토콜로 호스팅하는 메인 함수"""

    if not PROJECT_ENDPOINT:
        raise SystemExit(
            "오류: FOUNDRY_PROJECT_ENDPOINT(또는 PROJECT_ENDPOINT) 환경 변수를 설정해주세요."
        )

    # ── 1단계: Foundry Chat 클라이언트 설정 ──
    client = FoundryChatClient(
        project_endpoint=PROJECT_ENDPOINT,
        model=MODEL,
        credential=DefaultAzureCredential(),
    )

    # ── 2단계: 역할별 에이전트 생성 ──
    # 대화 이력은 호스팅 인프라가 관리하므로 store=False를 지정합니다.
    planner_agent = Agent(
        client=client,
        name="기획자",
        instructions=(
            "당신은 시니어 프로덕트 매니저입니다. "
            "비즈니스 가치, 사용자 요구사항, 시장 트렌드를 기반으로 기능을 기획합니다. "
            "다른 팀원의 의견을 경청하고, 실현 가능한 방향으로 조율합니다. "
            "각 발화는 반드시 3문장 이내로, 핵심 결정과 근거만 한국어로 전달합니다."
        ),
        default_options={"store": False},
    )

    developer_agent = Agent(
        client=client,
        name="개발자",
        instructions=(
            "당신은 시니어 풀스택 개발자입니다. "
            "기술적 실현 가능성, 아키텍처 설계, 개발 일정을 평가합니다. "
            "Azure 클라우드 서비스와 AI 기술 활용 방안을 제시합니다. "
            "기획자와 디자이너의 제안에 대해 기술적 피드백을 제공합니다. "
            "각 발화는 반드시 3문장 이내로, 핵심 결정과 근거만 한국어로 전달합니다."
        ),
        default_options={"store": False},
    )

    designer_agent = Agent(
        client=client,
        name="디자이너",
        instructions=(
            "당신은 시니어 UX/UI 디자이너입니다. "
            "사용자 경험, 인터페이스 디자인, 접근성을 중심으로 의견을 제시합니다. "
            "사용자 리서치 결과와 디자인 트렌드를 근거로 제안합니다. "
            "기획자와 개발자의 제안에 대해 UX 관점의 피드백을 제공합니다. "
            "각 발화는 반드시 3문장 이내로, 핵심 결정과 근거만 한국어로 전달합니다."
        ),
        default_options={"store": False},
    )

    # ── 3단계: GroupChat 워크플로우 구성 후 단일 에이전트로 변환 ──
    workflow_agent = (
        GroupChatBuilder(
            participants=[planner_agent, developer_agent, designer_agent],
            selection_func=select_next_speaker,
            max_rounds=3,  # Hosted /responses 단일 응답에 맞게 짧게 제한
        )
        .build()
        .as_agent()
    )

    # ── 4단계: Responses 프로토콜 서버로 호스팅 ──
    server = ResponsesHostServer(workflow_agent)
    server.run()


if __name__ == "__main__":
    main()
