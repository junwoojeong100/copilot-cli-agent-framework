"""[Hosted Agent] 실습 1: 단일 에이전트를 Foundry Hosted Agent로 배포

기존 ``src/01_single_agent.py``의 단일 에이전트를 그대로 가져와,
Microsoft Foundry의 **Hosted Agent**(관리형 컨테이너)로 호스팅합니다.

기존 예제와의 차이:
  - 기존: ``asyncio.run(main())`` 으로 질문 1건 처리 후 종료
  - 호스팅: ``server.run()`` 으로 ``/responses`` HTTP 엔드포인트를 띄워
            Foundry 게이트웨이의 요청을 계속 처리합니다.

이렇게 배포하면 Foundry Agent SDK v2로 재작성하지 않고도
관리형 인프라(스케일링·세션 관리)와 자동 trace/monitoring을 그대로 받습니다.
"""

import os

from agent_framework import Agent
from agent_framework.foundry import FoundryChatClient
from agent_framework_foundry_hosting import ResponsesHostServer
from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv

# 로컬 테스트 시 같은 폴더의 .env를 로드합니다.
# (Foundry에 배포되면 런타임이 환경 변수를 자동 주입하므로 .env가 없어도 됩니다.)
load_dotenv()

# ── 환경 변수 ──
# Foundry 호스팅 런타임이 주입하는 표준 이름을 먼저 사용하고,
# 로컬에서는 이 저장소의 기존 .env 이름(PROJECT_ENDPOINT/MODEL_DEPLOYMENT_NAME)으로 폴백합니다.
PROJECT_ENDPOINT = os.getenv("FOUNDRY_PROJECT_ENDPOINT") or os.getenv("PROJECT_ENDPOINT")
MODEL = (
    os.getenv("AZURE_AI_MODEL_DEPLOYMENT_NAME")
    or os.getenv("MODEL_DEPLOYMENT_NAME")
    or "gpt-5.4"
)


def main():
    """단일 에이전트를 만들어 Responses 프로토콜로 호스팅하는 메인 함수"""

    if not PROJECT_ENDPOINT:
        raise SystemExit(
            "오류: FOUNDRY_PROJECT_ENDPOINT(또는 PROJECT_ENDPOINT) 환경 변수를 설정해주세요."
        )

    # ── 1단계: Foundry Chat 클라이언트 설정 ──
    # 컨테이너 안에서는 전용 관리 ID로 인증되므로 DefaultAzureCredential을 사용합니다.
    # (로컬에서는 az login 세션을 자동으로 사용합니다.)
    client = FoundryChatClient(
        project_endpoint=PROJECT_ENDPOINT,
        model=MODEL,
        credential=DefaultAzureCredential(),
    )

    # ── 2단계: 에이전트 생성 ──
    # 대화 이력은 호스팅 인프라가 관리하므로 store=False로 중복 저장을 막습니다.
    agent = Agent(
        client=client,
        name="기술_어시스턴트",
        instructions=(
            "당신은 Microsoft 기술 전문 어시스턴트입니다. "
            "사용자의 기술 질문에 대해 정확하고 이해하기 쉽게 한국어로 답변합니다. "
            "답변은 간결하면서도 핵심을 포함해야 합니다."
        ),
        default_options={"store": False},
    )

    # ── 3단계: Responses 프로토콜 서버로 호스팅 ──
    # server.run()은 동기 호출입니다(asyncio.run으로 감싸지 않습니다).
    # /responses 엔드포인트가 8088 포트에서 열립니다.
    server = ResponsesHostServer(agent)
    server.run()


if __name__ == "__main__":
    main()
