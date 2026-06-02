"""
[SDK v2] 실습 1: 단일 에이전트 기본

에이전트를 **Microsoft Foundry Agent SDK v2**로 생성하고,
**Microsoft Agent Framework(MAF)**로 실행하는 가장 기본적인 예제입니다.
기존 ``src/01_single_agent.py``는 MAF FoundryChatClient(모델 채팅)로 에이전트를
구성하지만, 이 예제는 SDK v2로 만든 서버 측 영속 에이전트를 사용합니다.
"""

import asyncio
import os
import sys

from dotenv import load_dotenv

# 공용 스트리밍 헬퍼(src/_streaming.py)와 프로젝트 루트(.env)를 참조하기 위한 경로 설정
_SRC_DIR = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, _SRC_DIR)
load_dotenv(dotenv_path=os.path.join(_SRC_DIR, "..", ".env"))

from azure.identity import AzureCliCredential

from _foundry_agents import FoundryAgentFactory
from _streaming import stream_agent


async def main():
    """SDK v2 단일 에이전트를 생성하고 MAF로 실행하는 메인 함수"""

    print("=== [SDK v2] 단일 에이전트 실행 ===\n")

    project_endpoint = os.getenv("PROJECT_ENDPOINT")
    model = os.getenv("MODEL_DEPLOYMENT_NAME", "gpt-5.4")

    if not project_endpoint:
        print("오류: PROJECT_ENDPOINT 환경 변수를 설정해주세요.")
        sys.exit(1)

    # ── 1단계: Foundry Agent SDK v2로 서버 측 에이전트 생성 ──
    factory = FoundryAgentFactory(project_endpoint, model, AzureCliCredential())

    try:
        agent = factory.create(
            "assistant",
            instructions=(
                "당신은 Microsoft 기술 전문 어시스턴트입니다. "
                "사용자의 기술 질문에 대해 정확하고 이해하기 쉽게 한국어로 답변합니다. "
                "답변은 간결하면서도 핵심을 포함해야 합니다."
            ),
        )

        # ── 2단계: Microsoft Agent Framework로 에이전트 실행(스트리밍) ──
        await factory.enable_tracing()
        question = "Microsoft Agent Framework가 무엇인가요?"
        print(f"질문: {question}\n")
        await stream_agent(agent, question, label="에이전트 응답")

    except Exception as e:
        print(f"에이전트 실행 중 오류 발생: {e}")
        sys.exit(1)
    finally:
        # ── 3단계: 생성한 서버 측 에이전트 정리 + 추적 플러시 ──
        factory.cleanup()
        factory.flush_tracing()

    print("\n=== 실행 완료 ===")


if __name__ == "__main__":
    asyncio.run(main())
