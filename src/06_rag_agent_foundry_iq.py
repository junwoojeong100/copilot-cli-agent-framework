"""실습 6 (변형): RAG 에이전트 — Foundry IQ 지식 베이스 + agentic retrieval

기존 ``src/06_rag_agent.py``는 검색·증강을 Python 코드로 직접 수행합니다(하이브리드
검색). 이 변형은 동일한 지식 베이스를 **Foundry IQ**(지식 베이스 + agentic retrieval)에
올리고, 검색 단계를 ``AzureAISearchContextProvider``(agentic 모드)에 위임합니다.

  [질문] → [Foundry IQ agentic 검색(멀티홉)] → [컨텍스트 자동 주입] → [에이전트 답변]

핵심 차이(기존 06 대비):
  - 인덱스를 **기본 semantic 구성**과 함께 생성합니다(agentic retrieval 필수).
  - 검색·증강을 직접 코딩하지 않고, 컨텍스트 프로바이더가 ``before_run`` 훅에서
    멀티홉 검색을 수행하고 결과를 세션 컨텍스트에 주입합니다.
  - 프로바이더는 인덱스로부터 지식 소스/지식 베이스(``<index>-kb``)를 자동 생성합니다.

필요 리소스:
  - Azure AI Search 서비스 (**semantic ranker 활성화** + **agentic retrieval 지원 리전**)
  - Azure OpenAI 임베딩 배포 (예: text-embedding-3-large)
  - Microsoft Foundry 프로젝트 + 채팅 모델 (응답 생성)
인증은 전부 키리스(AzureCliCredential / Entra ID)로 동작합니다.
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
from azure.identity.aio import AzureCliCredential as AioAzureCliCredential

from _rag_iq import build_agentic_provider, resolve_iq_env, seed_iq_index
from _streaming import stream_agent


async def main():
    """Foundry IQ agentic retrieval 기반 RAG 파이프라인을 구성·실행하는 메인 함수"""

    print("=== RAG 에이전트 (Foundry IQ · agentic retrieval) 실행 ===\n")

    cfg = resolve_iq_env()
    if not cfg["project_endpoint"]:
        print("오류: PROJECT_ENDPOINT 환경 변수를 설정해주세요.")
        sys.exit(1)
    if not cfg["search_endpoint"]:
        print("오류: SEARCH_SERVICE_ENDPOINT 환경 변수를 설정해주세요.")
        print("      (예: https://<your-search>.search.windows.net)")
        sys.exit(1)
    if not cfg["aoai_endpoint"]:
        print("오류: AZURE_OPENAI_ENDPOINT 환경 변수를 설정해주세요.")
        print("      (임베딩·벡터화용 Azure OpenAI 엔드포인트)")
        sys.exit(1)

    # FoundryChatClient·시드용 동기 자격 증명과, 컨텍스트 프로바이더(비동기 Search
    # 클라이언트 사용)용 비동기 자격 증명을 따로 둡니다.
    credential = AzureCliCredential()
    aio_credential = AioAzureCliCredential()

    try:
        # ── 1단계: Foundry IQ 인덱스 생성 + 지식 베이스 시드(기본 semantic 구성 포함) ──
        print("[1단계] Foundry IQ 인덱스 생성/시드...")
        seed_iq_index(
            search_endpoint=cfg["search_endpoint"],
            index_name=cfg["index_name"],
            aoai_endpoint=cfg["aoai_endpoint"],
            embedding_deployment=cfg["embedding_deployment"],
            aoai_api_version=cfg["aoai_api_version"],
            credential=credential,
        )

        # ── 2단계: agentic 컨텍스트 프로바이더 구성 ──
        # 인덱스로부터 지식 소스·지식 베이스를 자동 생성하고, 검색 결과를 주입합니다.
        print("\n[2단계] Foundry IQ 지식 베이스 연결(없으면 자동 생성)...")
        async with build_agentic_provider(
            search_endpoint=cfg["search_endpoint"],
            index_name=cfg["index_name"],
            azure_openai_resource_url=cfg["aoai_resource_url"],
            query_planning_model=cfg["model"],
            credential=aio_credential,
            retrieval_reasoning_effort=cfg["reasoning_effort"],
        ) as provider:
            # ── 3단계: 검색을 프로바이더에 위임하는 RAG 에이전트 생성 ──
            agent = Agent(
                client=FoundryChatClient(
                    project_endpoint=cfg["project_endpoint"],
                    model=cfg["model"],
                    credential=credential,
                ),
                name="고객지원_RAG_어시스턴트",
                instructions=(
                    "당신은 고객 지원 어시스턴트입니다. "
                    "반드시 제공된 검색 컨텍스트 안의 정보만 근거로 한국어로 답변하세요. "
                    "컨텍스트에 없는 내용은 추측하지 말고 '관련 정보를 찾을 수 없습니다'라고 답하세요. "
                    "답변 끝에 근거가 된 문서 제목을 [출처: ...] 형식으로 표시하세요."
                ),
                context_providers=[provider],
            )

            # ── 4단계: 질문 → agentic 검색 자동 수행 → 근거 기반 생성 ──
            question = "Pro 요금제는 얼마이고 기술 지원은 얼마나 빨리 받을 수 있나요?"
            print(f"\n[3단계] 질문: {question}")
            print("\n[4단계] 에이전트가 검색 후 답변 생성 중...")
            await stream_agent(agent, question, label="\n에이전트 응답")

    except Exception as e:
        print(f"RAG 실행 중 오류 발생: {e}")
        sys.exit(1)
    finally:
        await aio_credential.close()

    print("\n=== 실행 완료 ===")


if __name__ == "__main__":
    asyncio.run(main())
