"""
실습 5: MCP 도구를 사용하는 에이전트
Model Context Protocol(MCP) 서버를 에이전트의 "도구"로 연결하여,
에이전트가 외부 시스템의 기능을 실시간으로 호출하도록 만듭니다.

이 예제는 인증이 필요 없는 공개 MCP 서버인 **Microsoft Learn MCP**
(https://learn.microsoft.com/api/mcp)에 연결하여, 에이전트가 공식 문서를
검색해 답변하도록 합니다.

  [사용자 질문] → [에이전트] → (MCP 도구로 Learn 문서 검색) → [근거 기반 답변]
"""

import asyncio
import os
import sys

from dotenv import load_dotenv

# 프로젝트 루트의 .env 파일 로드
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", ".env"))

from agent_framework import Agent, MCPStreamableHTTPTool
from agent_framework.foundry import FoundryChatClient
from azure.identity import AzureCliCredential

from _streaming import stream_agent


async def main():
    """MCP 도구를 연결한 에이전트를 실행하는 메인 함수"""

    print("=== MCP 도구 연동 에이전트 실행 ===\n")

    # ── 1단계: Foundry Chat 클라이언트 설정 ──
    project_endpoint = os.getenv("PROJECT_ENDPOINT")
    model = os.getenv("MODEL_DEPLOYMENT_NAME") or "gpt-5.4"

    if not project_endpoint:
        print("오류: PROJECT_ENDPOINT 환경 변수를 설정해주세요.")
        sys.exit(1)

    question = (
        "Microsoft Agent Framework에서 여러 에이전트를 협업시키는 "
        "Handoff 방식이 무엇인지 공식 문서를 근거로 설명해줘."
    )
    print(f"질문: {question}\n")

    try:
        client = FoundryChatClient(
            project_endpoint=project_endpoint,
            model=model,
            credential=AzureCliCredential(),
        )

        # ── 2단계: MCP 도구 정의 ──
        # MCPStreamableHTTPTool은 HTTP(SSE) 기반 MCP 서버에 연결합니다.
        # Microsoft Learn MCP는 공개 서버라 별도 인증 헤더가 필요 없습니다.
        # 인증이 필요한 서버라면 headers={"Authorization": "Bearer ..."}를 추가합니다.
        learn_mcp = MCPStreamableHTTPTool(
            name="MicrosoftLearn",
            url="https://learn.microsoft.com/api/mcp",
            description="Microsoft/Azure 공식 문서·코드 샘플 검색 도구",
        )

        # ── 3단계: MCP 서버에 연결한 상태에서 에이전트 실행 ──
        # async with 블록 안에서만 MCP 세션이 활성화됩니다.
        # 블록에 들어가면 connect()로 서버의 도구 목록을 불러오고,
        # 블록을 나가면 close()로 연결을 정리합니다.
        async with learn_mcp:
            # tools= 인자로 MCP 도구를 에이전트에 연결합니다.
            # 에이전트(LLM)는 필요하다고 판단하면 스스로 검색 도구를 호출합니다.
            agent = Agent(
                client=client,
                name="문서_리서치_어시스턴트",
                instructions=(
                    "당신은 Microsoft 기술 문서 리서치 어시스턴트입니다. "
                    "질문에 답하기 전에 MicrosoftLearn 도구로 공식 문서를 검색하여 "
                    "근거를 확보한 뒤, 출처를 함께 제시하며 한국어로 답변합니다. "
                    "추측하지 말고 검색 결과에 기반해 답변하세요."
                ),
                tools=learn_mcp,
            )

            await stream_agent(agent, question, label="에이전트 응답")

    except Exception as e:
        print(f"에이전트 실행 중 오류 발생: {e}")
        sys.exit(1)

    print("\n=== 실행 완료 ===")


if __name__ == "__main__":
    asyncio.run(main())
