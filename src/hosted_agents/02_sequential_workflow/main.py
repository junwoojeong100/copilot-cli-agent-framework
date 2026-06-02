"""[Hosted Agent] 실습 2: 순차 워크플로우를 Foundry Hosted Agent로 배포

기존 ``src/02_sequential_workflow.py``의 순차 파이프라인(분석가 → 작가 → 편집자)을
그대로 가져와, ``Workflow.as_agent()``로 단일 에이전트처럼 감싼 뒤
Microsoft Foundry **Hosted Agent**로 호스팅합니다.

핵심 교훈:
  MAF 워크플로우는 Foundry Agent SDK v2로 재작성하지 않고도
  ``.as_agent()`` 한 줄로 Hosted Agent가 되어, 관리형 인프라와
  자동 trace/monitoring을 그대로 받습니다.
"""

import os

from agent_framework import Agent
from agent_framework.orchestrations import SequentialBuilder
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
    """순차 워크플로우를 만들어 Responses 프로토콜로 호스팅하는 메인 함수"""

    if not PROJECT_ENDPOINT:
        raise SystemExit(
            "오류: FOUNDRY_PROJECT_ENDPOINT(또는 PROJECT_ENDPOINT) 환경 변수를 설정해주세요."
        )

    # ── 1단계: Foundry Chat 클라이언트 설정 ──
    # 컨테이너에서는 전용 관리 ID, 로컬에서는 az login 세션으로 인증됩니다.
    client = FoundryChatClient(
        project_endpoint=PROJECT_ENDPOINT,
        model=MODEL,
        credential=DefaultAzureCredential(),
    )

    # ── 2단계: 단계별 에이전트 생성 ──
    # 대화 이력은 호스팅 인프라가 관리하므로 각 에이전트에 store=False를 지정합니다.
    analyzer_agent = Agent(
        client=client,
        name="분석가",
        instructions=(
            "당신은 콘텐츠 주제 분석가입니다. "
            "주어진 주제의 핵심 논점 3가지를 뽑아 간결히 정리합니다. "
            "한국어로 작성합니다."
        ),
        default_options={"store": False},
    )

    writer_agent = Agent(
        client=client,
        name="작가",
        instructions=(
            "당신은 기술 콘텐츠 작가입니다. "
            "앞 단계의 분석을 바탕으로 400자 이내의 글 초안을 작성합니다. "
            "한국어로 작성합니다."
        ),
        default_options={"store": False},
    )

    editor_agent = Agent(
        client=client,
        name="편집자",
        instructions=(
            "당신은 시니어 편집자입니다. "
            "앞 단계의 초안을 검토해 논리적 흐름과 가독성을 개선한 최종본을 작성합니다. "
            "한국어로 작성합니다."
        ),
        default_options={"store": False},
    )

    # ── 3단계: 순차 워크플로우 구성 후 단일 에이전트로 변환 ──
    # SequentialBuilder로 만든 Workflow를 .as_agent()로 감싸면
    # ResponsesHostServer가 일반 에이전트처럼 호스팅할 수 있습니다.
    workflow_agent = (
        SequentialBuilder(participants=[analyzer_agent, writer_agent, editor_agent])
        .build()
        .as_agent()
    )

    # ── 4단계: Responses 프로토콜 서버로 호스팅 ──
    # server.run()은 동기 호출입니다. /responses 엔드포인트가 8088 포트에서 열립니다.
    server = ResponsesHostServer(workflow_agent)
    server.run()


if __name__ == "__main__":
    main()
