"""[Hosted Agent] 실습 6 (변형): Foundry IQ RAG 에이전트를 Hosted Agent로 배포

기존 ``src/hosted_agents/06_rag_agent/``는 하이브리드 검색을 **함수 도구**로 노출해
에이전트가 직접 검색합니다. 이 변형은 검색을 **Foundry IQ**(지식 베이스 + agentic
retrieval)에 위임합니다. ``AzureAISearchContextProvider``(agentic 모드)를 컨텍스트
프로바이더로 연결하면, 에이전트는 질문을 받을 때마다 지식 베이스에 멀티홉 검색을
수행하고 그 결과를 컨텍스트로 받아 근거 기반으로 답변합니다.

전제 — 지식 베이스 사전 생성:
  이 호스팅 예제는 **이미 생성된 Foundry IQ 지식 베이스**(기본
  ``maf-lab-knowledge-iq-v1-kb``)에 연결만 합니다. 저장소 루트에서
  ``src/06_rag_agent_foundry_iq.py``를 한 번 실행하면 인덱스 시드 + 지식 베이스
  생성이 끝납니다(자동 생성에 필요한 컨트롤플레인 권한은 콘솔 실행 사용자에게만
  요구되고, 호스팅 인스턴스에는 검색(데이터 리더) 권한만 있으면 됩니다).
"""

import os

from agent_framework import Agent
from agent_framework.azure import AzureAISearchContextProvider
from agent_framework.foundry import FoundryChatClient
from azure.identity import DefaultAzureCredential
from azure.identity.aio import DefaultAzureCredential as AioDefaultAzureCredential
from dotenv import load_dotenv

from agent_framework_foundry_hosting import ResponsesHostServer

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
SEARCH_ENDPOINT = os.getenv("SEARCH_SERVICE_ENDPOINT")
# 기존 지식 베이스 이름. 콘솔 예제가 만든 ``<index>-kb`` 규칙을 따릅니다.
KNOWLEDGE_BASE_NAME = os.getenv("SEARCH_KNOWLEDGE_BASE_NAME", "maf-lab-knowledge-iq-v1-kb")
REASONING_EFFORT = os.getenv("FOUNDRY_IQ_REASONING_EFFORT", "minimal")


def main():
    """Foundry IQ 컨텍스트 프로바이더를 가진 에이전트를 Responses 프로토콜로 호스팅"""

    if not PROJECT_ENDPOINT:
        raise SystemExit(
            "오류: FOUNDRY_PROJECT_ENDPOINT(또는 PROJECT_ENDPOINT) 환경 변수를 설정해주세요."
        )
    if not SEARCH_ENDPOINT:
        raise SystemExit("오류: SEARCH_SERVICE_ENDPOINT 환경 변수를 설정해주세요.")

    # ── 1단계: 자격 증명 준비 ──
    # FoundryChatClient는 동기, 컨텍스트 프로바이더(비동기 Search 클라이언트)는
    # 비동기 자격 증명을 사용합니다. 컨테이너에서는 전용 관리 ID, 로컬에서는
    # 로그인 세션으로 인증됩니다.
    credential = DefaultAzureCredential()
    aio_credential = AioDefaultAzureCredential()

    # ── 2단계: Foundry IQ agentic 컨텍스트 프로바이더 (기존 지식 베이스에 연결) ──
    # 기존 지식 베이스에 연결만 하므로 검색(데이터 리더) 권한만 필요합니다.
    # 프로바이더의 비동기 클라이언트는 프로세스 수명 동안 유지됩니다.
    provider = AzureAISearchContextProvider(
        endpoint=SEARCH_ENDPOINT,
        knowledge_base_name=KNOWLEDGE_BASE_NAME,
        mode="agentic",
        credential=aio_credential,
        retrieval_reasoning_effort=REASONING_EFFORT,
    )

    # ── 3단계: RAG 에이전트 생성 ──
    # 대화 이력은 호스팅 인프라가 관리하므로 store=False를 지정합니다.
    agent = Agent(
        client=FoundryChatClient(
            project_endpoint=PROJECT_ENDPOINT,
            model=MODEL,
            credential=credential,
        ),
        name="고객지원_RAG_어시스턴트",
        instructions=(
            "당신은 고객 지원 어시스턴트입니다. "
            "반드시 제공된 검색 컨텍스트 안의 정보만 근거로 한국어로 답변하고, "
            "컨텍스트에 없는 내용은 추측하지 말고 '관련 정보를 찾을 수 없습니다'라고 답하세요. "
            "답변 끝에 근거가 된 문서 제목을 [출처: ...] 형식으로 표시하세요."
        ),
        context_providers=[provider],
        default_options={"store": False},
    )

    # ── 4단계: Responses 프로토콜 서버로 호스팅 ──
    server = ResponsesHostServer(agent)
    server.run()


if __name__ == "__main__":
    main()
