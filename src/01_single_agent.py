"""
실습 1: 단일 에이전트 기본
Microsoft Agent Framework를 사용한 가장 기본적인 에이전트 실행 예제입니다.
Microsoft Foundry와 연동하여 단일 에이전트가 사용자 질문에 응답합니다.
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

from _streaming import stream_agent


async def main():
    """단일 에이전트를 생성하고 실행하는 메인 함수"""

    print("=== 단일 에이전트 실행 ===\n")

    # ── 1단계: Foundry Chat 클라이언트 설정 ──
    # 환경 변수에서 프로젝트 엔드포인트와 모델 이름을 가져옵니다
    project_endpoint = os.getenv("PROJECT_ENDPOINT")
    model = os.getenv("MODEL_DEPLOYMENT_NAME")

    if not project_endpoint:
        print("오류: PROJECT_ENDPOINT 환경 변수를 설정해주세요.")
        sys.exit(1)
    if not model:
        print("오류: MODEL_DEPLOYMENT_NAME 환경 변수를 설정해주세요.")
        sys.exit(1)

    # FoundryChatClient는 Microsoft Foundry 프로젝트에 연결합니다
    try:
        client = FoundryChatClient(
            project_endpoint=project_endpoint,
            model=model,
            credential=AzureCliCredential(),
        )
    except Exception as e:
        print(f"오류: Azure 클라이언트 초기화에 실패했습니다. `az login` 상태를 확인해주세요.\n상세: {e}")
        sys.exit(1)

    # ── 2단계: 에이전트 생성 ──
    # 에이전트에게 역할과 지시사항을 부여합니다
    agent = Agent(
        client=client,
        name="기술_어시스턴트",
        instructions=(
            "당신은 Microsoft 기술 전문 어시스턴트입니다. "
            "사용자의 기술 질문에 대해 정확하고 이해하기 쉽게 한국어로 답변합니다. "
            "답변은 간결하면서도 핵심을 포함해야 합니다."
        ),
    )

    # ── 3단계: 에이전트 실행 ──
    # 질문을 전달하고 에이전트의 응답을 받습니다
    question = "Microsoft Agent Framework가 무엇인가요?"
    print(f"질문: {question}\n")

    try:
        # ── 4단계: 결과 출력 (스트리밍) ──
        # stream=True로 응답을 토큰 단위로 받아 생성 과정을 실시간 출력합니다.
        await stream_agent(agent, question, label="에이전트 응답")

    except Exception as e:
        print(f"에이전트 실행 중 오류 발생: {e}")
        sys.exit(1)

    print("\n=== 실행 완료 ===")


if __name__ == "__main__":
    asyncio.run(main())
