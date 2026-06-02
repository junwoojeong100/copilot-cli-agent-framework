"""
[SDK v2] 실습 5: MCP 도구 연동 에이전트 (서버 측 도구)

에이전트를 **Foundry Agent SDK v2**로 생성하면서, ``PromptAgentDefinition``에
**서버 측 MCP 도구**(``MCPTool``)를 부여합니다. 기존 ``src/05_mcp_agent.py``는 MAF의
클라이언트 측 ``MCPStreamableHTTPTool``을 ``agent.run(tools=...)``로 주입하지만,
이 예제는 **Foundry 서버가 직접 MCP 서버를 호출**합니다(로컬 함수 호출 불필요).

인증이 필요 없는 공개 서버인 **Microsoft Learn MCP**(https://learn.microsoft.com/api/mcp)에
연결해, 에이전트가 공식 문서를 검색해 근거 기반으로 답변하게 합니다.
"""

import asyncio
import os
import sys

from dotenv import load_dotenv

# 공용 스트리밍 헬퍼(src/_streaming.py)와 프로젝트 루트(.env)를 참조하기 위한 경로 설정
_SRC_DIR = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, _SRC_DIR)
load_dotenv(dotenv_path=os.path.join(_SRC_DIR, "..", ".env"))

from azure.ai.projects.models import MCPTool
from azure.identity import AzureCliCredential

from _foundry_agents import FoundryAgentFactory
from _streaming import stream_agent


async def main():
    """서버 측 MCP 도구를 가진 SDK v2 에이전트를 MAF로 실행하는 메인 함수"""

    print("=== [SDK v2] MCP 도구 연동 에이전트 실행 ===\n")

    project_endpoint = os.getenv("PROJECT_ENDPOINT")
    model = os.getenv("MODEL_DEPLOYMENT_NAME", "gpt-5.4")

    if not project_endpoint:
        print("오류: PROJECT_ENDPOINT 환경 변수를 설정해주세요.")
        sys.exit(1)

    # ── 1단계: Foundry Agent SDK v2로 서버 측 MCP 도구를 가진 에이전트 생성 ──
    # require_approval="never": 공개 읽기 전용 서버라 호출마다 승인받지 않습니다.
    learn_mcp = MCPTool(
        server_label="MicrosoftLearn",
        server_url="https://learn.microsoft.com/api/mcp",
        require_approval="never",
    )

    factory = FoundryAgentFactory(project_endpoint, model, AzureCliCredential())

    try:
        agent = factory.create(
            "docs-researcher",
            instructions=(
                "당신은 Microsoft 기술 문서 리서치 어시스턴트입니다. "
                "질문에 답하기 전에 반드시 MicrosoftLearn MCP 도구로 공식 문서를 검색해 "
                "근거를 확보한 뒤, 한국어로 답변하고 끝에 참고한 문서의 출처(제목/URL)를 "
                "[출처: ...] 형식으로 제시하세요. 추측하지 말고 검색 결과에 기반하세요."
            ),
            tools=[learn_mcp],
        )

        # ── 2단계: Microsoft Agent Framework로 에이전트 실행(스트리밍) ──
        await factory.enable_tracing()
        question = (
            "Microsoft Agent Framework에서 여러 에이전트를 협업시키는 "
            "Handoff 방식이 무엇인지 공식 문서를 근거로 설명해줘."
        )
        print(f"질문: {question}\n")
        answer = await stream_agent(agent, question, label="에이전트 응답")

        # 근거(출처) 표기 여부를 가볍게 점검 — 서버 측 MCP 호출이 일어났는지 확인용
        if "출처" not in answer:
            print(
                "\n⚠ 응답에 출처 표기가 없습니다. 모델이 MCP 도구를 호출하지 않았을 수 있습니다.\n"
                "  (대안) 클라이언트 측 MCP 예제 src/05_mcp_agent.py를 참고하세요."
            )

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
