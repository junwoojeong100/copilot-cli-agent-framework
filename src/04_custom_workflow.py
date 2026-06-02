"""
실습 4: 커스텀 순차 워크플로우
에이전트를 순차적으로 연결하고, 조건부 라우팅을 포함한
콘텐츠 제작 파이프라인을 구축합니다.

워크플로우:
  [주제 분석] → 기술 주제? → [기술 작가] → [편집자] → [최종 출력]
                일반 주제? → [일반 작가] → [편집자] → [최종 출력]
"""

import asyncio
import os
import sys

from dotenv import load_dotenv

# 프로젝트 루트의 .env 파일 로드
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", ".env"))

from agent_framework import Agent
from agent_framework.foundry import FoundryChatClient
from azure.identity import AzureCliCredential


def create_agents(client: FoundryChatClient) -> dict:
    """파이프라인에 필요한 에이전트들을 생성합니다.

    Args:
        client: Foundry Chat 클라이언트.

    Returns:
        에이전트 이름(키) → Agent 인스턴스(값) 딕셔너리.
    """

    agents = {}

    # 주제 분석 에이전트 - 입력 주제의 카테고리를 판별합니다
    agents["topic_analyzer"] = Agent(
        client=client,
        name="주제_분석",
        instructions=(
            "당신은 콘텐츠 주제 분석 전문가입니다. "
            "주어진 주제를 분석하여 '기술' 또는 '일반' 카테고리로 분류합니다.\n"
            "판단 기준:\n"
            "- 기술: 프로그래밍, 클라우드, AI/ML, DevOps, 보안, 데이터베이스 등\n"
            "- 일반: 비즈니스, 마케팅, 라이프스타일, 교육 등\n\n"
            "반드시 첫 줄에 '카테고리: 기술' 또는 '카테고리: 일반'으로 시작하고, "
            "그 다음에 주제 분석 요약을 작성합니다. 한국어로 답변합니다."
        ),
    )

    # 기술 작가 에이전트 - 기술 주제에 특화된 글을 작성합니다
    agents["tech_writer"] = Agent(
        client=client,
        name="기술_작가",
        instructions=(
            "당신은 기술 콘텐츠 전문 작가입니다. "
            "기술 주제에 대해 정확하고 깊이 있는 글을 작성합니다. "
            "코드 예제, 아키텍처 다이어그램 설명, 모범 사례를 포함합니다. "
            "전문 용어를 사용하되 이해하기 쉽게 설명합니다. "
            "한국어로 작성합니다."
        ),
    )

    # 일반 작가 에이전트 - 일반 주제에 대해 읽기 쉬운 글을 작성합니다
    agents["general_writer"] = Agent(
        client=client,
        name="일반_작가",
        instructions=(
            "당신은 일반 콘텐츠 작가입니다. "
            "일반 주제에 대해 대중이 이해하기 쉬운 글을 작성합니다. "
            "스토리텔링 기법을 활용하고, 실생활 예시를 포함합니다. "
            "전문 용어 사용을 최소화하고 누구나 읽을 수 있도록 작성합니다. "
            "한국어로 작성합니다."
        ),
    )

    # 편집자 에이전트 - 작성된 글을 검토하고 개선합니다
    agents["editor"] = Agent(
        client=client,
        name="편집자",
        instructions=(
            "당신은 시니어 편집자입니다. "
            "이전 작가가 작성한 초안을 검토하고 개선합니다.\n"
            "검토 항목: 논리적 흐름, 문법, 가독성, 정확성\n"
            "개선된 최종 버전을 출력합니다. "
            "한국어로 작성합니다."
        ),
    )

    return agents


def route_by_category(analysis_result: str) -> str:
    """주제 분석 결과에서 카테고리를 추출하여 라우팅 경로를 결정합니다.

    Args:
        analysis_result: 주제 분석 에이전트의 응답 텍스트.

    Returns:
        라우팅할 작가 에이전트 키 ("tech_writer" 또는 "general_writer").
    """
    first_line = str(analysis_result).split("\n")[0]
    if "기술" in first_line:
        return "tech_writer"
    return "general_writer"


async def main():
    """커스텀 순차 워크플로우를 구성하고 실행하는 메인 함수"""

    print("=== 커스텀 순차 워크플로우 실행 ===\n")

    # ── 1단계: Foundry Chat 클라이언트 설정 ──
    project_endpoint = os.getenv("PROJECT_ENDPOINT")
    model = os.getenv("MODEL_DEPLOYMENT_NAME", "gpt-5.4")

    if not project_endpoint:
        print("오류: PROJECT_ENDPOINT 환경 변수를 설정해주세요.")
        sys.exit(1)

    client = FoundryChatClient(
        project_endpoint=project_endpoint,
        model=model,
        credential=AzureCliCredential(),
    )

    # ── 2단계: 에이전트 생성 ──
    agents = create_agents(client)

    # ── 3단계: 파이프라인 실행 ──
    input_topic = "Kubernetes 클러스터 최적화 전략"
    print(f"입력 주제: {input_topic}\n")
    print("=" * 50)

    try:
        # 3-1. 주제 분석
        print("\n[1단계] 주제 분석 중...")
        analysis = await agents["topic_analyzer"].run(input_topic)
        route = route_by_category(str(analysis))
        category_label = "기술" if route == "tech_writer" else "일반"
        print(f"  → 분석 결과: {category_label} 주제")

        # 3-2. 조건부 라우팅: 카테고리에 따라 적절한 작가 선택
        writer_name = "기술 작가" if route == "tech_writer" else "일반 작가"
        print(f"\n[2단계] {writer_name}가 초안 작성 중...")
        writer_prompt = (
            f"다음 주제 분석을 참고하여 글을 작성하세요:\n\n"
            f"--- 주제 분석 ---\n{analysis}\n\n"
            f"--- 요청 ---\n'{input_topic}' 주제로 500자 이내의 글을 작성하세요."
        )
        draft = await agents[route].run(writer_prompt)
        print("  → 초안 작성 완료")

        # 3-3. 편집자 검토
        print("\n[3단계] 편집자가 검토 및 개선 중...")
        editor_prompt = (
            f"다음 초안을 검토하고 개선된 최종 버전을 작성하세요:\n\n"
            f"--- 초안 ---\n{draft}"
        )
        final_content = await agents["editor"].run(editor_prompt)
        print("  → 최종 편집 완료")

        # ── 4단계: 최종 결과 출력 ──
        print("\n" + "=" * 50)
        print("\n=== 최종 콘텐츠 ===\n")
        print(final_content)

    except Exception as e:
        print(f"워크플로우 실행 중 오류 발생: {e}")
        sys.exit(1)

    print("\n=== 실행 완료 ===")


if __name__ == "__main__":
    asyncio.run(main())
