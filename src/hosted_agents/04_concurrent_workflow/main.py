"""[Hosted Agent] 실습 4: 동시(Concurrent) 워크플로우를 Foundry Hosted Agent로 배포

기존 ``src/04_concurrent_workflow.py``의 병렬 검토(보안·성능·UX 리뷰어)를
그대로 가져와, ``Workflow.as_agent()``로 감싼 뒤 Hosted Agent로 호스팅합니다.
"""

import os

from agent_framework import Agent
from agent_framework.orchestrations import ConcurrentBuilder
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
    """동시 워크플로우를 만들어 Responses 프로토콜로 호스팅하는 메인 함수"""

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

    # ── 2단계: 관점별 리뷰어 에이전트 생성 ──
    # 대화 이력은 호스팅 인프라가 관리하므로 store=False를 지정합니다.
    security_agent = Agent(
        client=client,
        name="보안 리뷰어",
        instructions=(
            "당신은 보안 검토 전문가입니다. "
            "설계안의 보안 위험과 완화 방안을 핵심만 짚어 평가합니다. "
            "한국어로 작성합니다."
        ),
        default_options={"store": False},
    )

    performance_agent = Agent(
        client=client,
        name="성능 리뷰어",
        instructions=(
            "당신은 성능 검토 전문가입니다. "
            "설계안의 성능 병목과 확장성 개선점을 핵심만 짚어 평가합니다. "
            "한국어로 작성합니다."
        ),
        default_options={"store": False},
    )

    ux_agent = Agent(
        client=client,
        name="UX 리뷰어",
        instructions=(
            "당신은 UX 검토 전문가입니다. "
            "설계안의 사용성과 접근성 관점 개선점을 핵심만 짚어 평가합니다. "
            "한국어로 작성합니다."
        ),
        default_options={"store": False},
    )

    # ── 3단계: 동시 워크플로우 구성 후 단일 에이전트로 변환 ──
    workflow_agent = (
        ConcurrentBuilder(participants=[security_agent, performance_agent, ux_agent])
        .build()
        .as_agent()
    )

    # ── 4단계: Responses 프로토콜 서버로 호스팅 ──
    server = ResponsesHostServer(workflow_agent)
    server.run()


if __name__ == "__main__":
    main()
