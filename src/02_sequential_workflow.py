"""
실습 2: 순차(Sequential) 워크플로우
에이전트를 순차적으로 연결해 콘텐츠 제작 파이프라인을 구축합니다.
분석가 → 작가 → 편집자가 차례로 작업을 이어받습니다.

워크플로우: [분석가] → [작가] → [편집자]
  - 분석가: 주제를 분석해 핵심 논점을 정리합니다.
  - 작가: 분석을 바탕으로 글 초안을 작성합니다.
  - 편집자: 초안을 다듬어 최종본을 만듭니다.
"""

import asyncio
import os
import sys

from dotenv import load_dotenv

# 프로젝트 루트의 .env 파일 로드
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", ".env"))

from agent_framework import Agent
from agent_framework.orchestrations import SequentialBuilder
from agent_framework.foundry import FoundryChatClient
from azure.identity import AzureCliCredential

from _streaming import stream_workflow


async def main():
    """순차 워크플로우를 구성하고 실행하는 메인 함수"""

    print("=== 순차 워크플로우 실행 ===\n")

    # ── 1단계: Foundry Chat 클라이언트 설정 ──
    project_endpoint = os.getenv("PROJECT_ENDPOINT")
    model = os.getenv("MODEL_DEPLOYMENT_NAME") or "gpt-5.4"

    if not project_endpoint:
        print("오류: PROJECT_ENDPOINT 환경 변수를 설정해주세요.")
        sys.exit(1)

    topic = "Kubernetes 클러스터 비용 최적화 전략"
    print(f"입력 주제: {topic}\n")
    print("=" * 50)

    try:
        # ── 2단계: 단계별 에이전트 생성 ──
        # 각 에이전트는 파이프라인의 한 단계를 담당합니다
        client = FoundryChatClient(
            project_endpoint=project_endpoint,
            model=model,
            credential=AzureCliCredential(),
        )

        # 분석가 에이전트 - 주제의 핵심 논점을 정리합니다
        analyzer_agent = Agent(
            client=client,
            name="분석가",
            instructions=(
                "당신은 콘텐츠 주제 분석가입니다. "
                "주어진 주제의 핵심 논점 3가지를 뽑아 간결히 정리합니다. "
                "한국어로 작성합니다."
            ),
        )

        # 작가 에이전트 - 분석을 바탕으로 초안을 작성합니다
        writer_agent = Agent(
            client=client,
            name="작가",
            instructions=(
                "당신은 기술 콘텐츠 작가입니다. "
                "앞 단계의 분석을 바탕으로 400자 이내의 글 초안을 작성합니다. "
                "한국어로 작성합니다."
            ),
        )

        # 편집자 에이전트 - 초안을 다듬어 최종본을 만듭니다
        editor_agent = Agent(
            client=client,
            name="편집자",
            instructions=(
                "당신은 시니어 편집자입니다. "
                "앞 단계의 초안을 검토해 논리적 흐름과 가독성을 개선한 최종본을 작성합니다. "
                "한국어로 작성합니다."
            ),
        )

        # ── 3단계: 순차 워크플로우 구성 ──
        # SequentialBuilder가 참여자 순서대로 출력을 다음 단계로 전달합니다
        workflow = SequentialBuilder(
            participants=[analyzer_agent, writer_agent, editor_agent]
        ).build()

        # ── 4단계: 파이프라인 결과 스트리밍 출력 ──
        print("\n[순차 파이프라인 결과]")
        await stream_workflow(workflow, topic)

    except Exception as e:
        print(f"순차 워크플로우 실행 중 오류 발생: {e}")
        sys.exit(1)

    print("\n=== 실행 완료 ===")


if __name__ == "__main__":
    asyncio.run(main())
