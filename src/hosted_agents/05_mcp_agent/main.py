"""[Hosted Agent] 실습 5: MCP 도구 연동 에이전트를 Foundry Hosted Agent로 배포

기존 ``src/05_mcp_agent.py``의 MCP 도구 연동 에이전트를 Hosted Agent로 호스팅합니다.

호스팅 환경에서는 ``async with`` 로 클라이언트 측 MCP 세션을 직접 관리하는 대신,
``client.get_mcp_tool(...)`` 로 **서버 측 MCP 도구**를 등록합니다.
Foundry 게이트웨이가 MCP 서버 호출과 도구 수명주기를 대신 관리합니다.

이 예제는 인증이 필요 없는 공개 MCP 서버인 **Microsoft Learn MCP**
(https://learn.microsoft.com/api/mcp)에 연결합니다.
"""

import os

from agent_framework import Agent
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


def main():
    """MCP 도구를 연결한 에이전트를 Responses 프로토콜로 호스팅하는 메인 함수"""

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

    # ── 2단계: 서버 측 MCP 도구 등록 ──
    # get_mcp_tool은 게이트웨이가 직접 호출하는 원격 MCP 도구를 등록합니다.
    # 공개 서버라 인증 헤더가 필요 없습니다(인증이 필요하면 headers= 추가).
    # approval_mode="never_require"로 매 호출 승인 없이 자동 사용하게 합니다.
    learn_mcp = client.get_mcp_tool(
        name="MicrosoftLearn",
        url="https://learn.microsoft.com/api/mcp",
        description="Microsoft/Azure 공식 문서·코드 샘플 검색 도구",
        approval_mode="never_require",
    )

    # ── 3단계: 에이전트 생성 ──
    # 대화 이력은 호스팅 인프라가 관리하므로 store=False를 지정합니다.
    agent = Agent(
        client=client,
        name="문서_리서치_어시스턴트",
        instructions=(
            "당신은 Microsoft 기술 문서 리서치 어시스턴트입니다. "
            "질문에 답하기 전에 MicrosoftLearn 도구로 공식 문서를 검색하여 "
            "근거를 확보한 뒤, 출처를 함께 제시하며 한국어로 답변합니다. "
            "추측하지 말고 검색 결과에 기반해 답변하세요."
        ),
        tools=[learn_mcp],
        default_options={"store": False},
    )

    # ── 4단계: Responses 프로토콜 서버로 호스팅 ──
    server = ResponsesHostServer(agent)
    server.run()


if __name__ == "__main__":
    main()
