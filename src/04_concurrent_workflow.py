"""
실습 4: 동시(Concurrent) 워크플로우
여러 전문가 에이전트가 같은 입력을 동시에 검토하는 패턴입니다.
보안, 성능, UX 리뷰어가 하나의 설계안을 각자 관점에서 병렬 평가합니다.

워크플로우: [설계안] → [보안 리뷰어] · [성능 리뷰어] · [UX 리뷰어] (동시)
"""

import asyncio
import os
import sys

from dotenv import load_dotenv

# 프로젝트 루트의 .env 파일 로드
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", ".env"))

from agent_framework import Agent
from agent_framework.orchestrations import ConcurrentBuilder
from agent_framework.foundry import FoundryChatClient
from azure.identity import AzureCliCredential

from _streaming import stream_workflow


async def main():
    """동시 워크플로우를 구성하고 실행하는 메인 함수"""

    print("=== 동시 워크플로우 실행 ===\n")

    # ── 1단계: Foundry Chat 클라이언트 설정 ──
    project_endpoint = os.getenv("PROJECT_ENDPOINT")
    model = os.getenv("MODEL_DEPLOYMENT_NAME") or "gpt-5.4"

    if not project_endpoint:
        print("오류: PROJECT_ENDPOINT 환경 변수를 설정해주세요.")
        sys.exit(1)

    design = (
        "신규 모바일 앱에 로그인 없이 게스트 결제를 허용하고, "
        "추천 데이터를 단말에 캐시하는 설계안을 검토해 주세요."
    )
    print(f"검토 대상 설계안: {design}\n")
    print("=" * 50)

    try:
        # ── 2단계: 관점별 리뷰어 에이전트 생성 ──
        # 각 에이전트는 같은 입력을 서로 다른 관점에서 평가합니다
        client = FoundryChatClient(
            project_endpoint=project_endpoint,
            model=model,
            credential=AzureCliCredential(),
        )

        # 보안 리뷰어 - 보안 위험과 완화 방안을 평가합니다
        security_agent = Agent(
            client=client,
            name="보안 리뷰어",
            instructions=(
                "당신은 보안 검토 전문가입니다. "
                "설계안의 보안 위험과 완화 방안을 핵심만 짚어 평가합니다. "
                "한국어로 작성합니다."
            ),
        )

        # 성능 리뷰어 - 성능 병목과 확장성을 평가합니다
        performance_agent = Agent(
            client=client,
            name="성능 리뷰어",
            instructions=(
                "당신은 성능 검토 전문가입니다. "
                "설계안의 성능 병목과 확장성 개선점을 핵심만 짚어 평가합니다. "
                "한국어로 작성합니다."
            ),
        )

        # UX 리뷰어 - 사용성과 접근성을 평가합니다
        ux_agent = Agent(
            client=client,
            name="UX 리뷰어",
            instructions=(
                "당신은 UX 검토 전문가입니다. "
                "설계안의 사용성과 접근성 관점 개선점을 핵심만 짚어 평가합니다. "
                "한국어로 작성합니다."
            ),
        )

        # ── 3단계: 동시 워크플로우 구성 ──
        # ConcurrentBuilder가 모든 참여자에게 같은 입력을 병렬로 전달합니다
        workflow = ConcurrentBuilder(
            participants=[security_agent, performance_agent, ux_agent]
        ).build()

        # ── 4단계: 동시 리뷰 결과 스트리밍 출력 ──
        print("\n[동시 리뷰 결과]")
        await stream_workflow(workflow, design)

    except Exception as e:
        print(f"동시 워크플로우 실행 중 오류 발생: {e}")
        sys.exit(1)

    print("\n=== 실행 완료 ===")


if __name__ == "__main__":
    asyncio.run(main())
