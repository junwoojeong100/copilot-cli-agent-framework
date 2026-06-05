"""[SDK v2] 실습 6 (변형): RAG 에이전트 — Foundry IQ + agentic retrieval

검색은 **Foundry IQ**(지식 베이스 + agentic retrieval)에 위임하고, 생성(Generation)은
**Foundry Agent SDK v2**로 만든 에이전트가 담당합니다. 즉, SDK v2 ``FoundryAgent``에
``AzureAISearchContextProvider``(agentic 모드)를 컨텍스트 프로바이더로 연결합니다.

  [질문] → [Foundry IQ agentic 검색] → [컨텍스트 자동 주입]
        → [SDK v2 에이전트가 근거 기반 답변]

기존 ``src/foundry_sdk_v2/06_rag_agent.py``(하이브리드 검색 + SDK v2 생성)는 그대로
두고, 이 변형은 검색을 Foundry IQ에 맡긴다는 점이 다릅니다. 인덱스·시드 헬퍼는
저장소 공용 모듈 ``src/_rag_iq.py``를 사용합니다.

필요 리소스: Azure AI Search(**semantic ranker 활성화 + agentic 지원 리전**),
Azure OpenAI 임베딩 배포, Foundry 프로젝트+모델. 인증은 전부 키리스입니다.
"""

import asyncio
import os
import sys

from dotenv import load_dotenv

# 공용 헬퍼(src/_rag_iq.py, src/_streaming.py)와 프로젝트 루트(.env)를 참조하기 위한 경로 설정
_SRC_DIR = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, _SRC_DIR)
load_dotenv(dotenv_path=os.path.join(_SRC_DIR, "..", ".env"))

from azure.identity import AzureCliCredential
from azure.identity.aio import AzureCliCredential as AioAzureCliCredential

from _foundry_agents import FoundryAgentFactory
from _rag_iq import build_agentic_provider, resolve_iq_env, seed_iq_index
from _streaming import stream_agent


async def main():
    """Foundry IQ 검색 + SDK v2 에이전트 생성으로 RAG를 실행하는 메인 함수"""

    print("=== [SDK v2] RAG 에이전트 (Foundry IQ · agentic retrieval) 실행 ===\n")

    cfg = resolve_iq_env()
    if not cfg["project_endpoint"]:
        print("오류: PROJECT_ENDPOINT 환경 변수를 설정해주세요.")
        sys.exit(1)
    if not cfg["search_endpoint"]:
        print("오류: SEARCH_SERVICE_ENDPOINT 환경 변수를 설정해주세요.")
        sys.exit(1)
    if not cfg["aoai_endpoint"]:
        print("오류: AZURE_OPENAI_ENDPOINT 환경 변수를 설정해주세요.")
        sys.exit(1)

    # SDK v2/시드용 동기 자격 증명과, 컨텍스트 프로바이더용 비동기 자격 증명을 분리합니다.
    credential = AzureCliCredential()
    aio_credential = AioAzureCliCredential()
    factory = FoundryAgentFactory(cfg["project_endpoint"], cfg["model"], credential)

    try:
        # ── 1단계: Foundry IQ 인덱스 생성 + 지식 베이스 시드(공용 헬퍼) ──
        print("[1단계] Foundry IQ 인덱스 생성/시드...")
        seed_iq_index(
            search_endpoint=cfg["search_endpoint"],
            index_name=cfg["index_name"],
            aoai_endpoint=cfg["aoai_endpoint"],
            embedding_deployment=cfg["embedding_deployment"],
            aoai_api_version=cfg["aoai_api_version"],
            credential=credential,
        )

        # ── 2단계: agentic 컨텍스트 프로바이더 + SDK v2 생성 에이전트 ──
        print("\n[2단계] Foundry IQ 지식 베이스 연결 + SDK v2 에이전트 생성...")
        async with build_agentic_provider(
            search_endpoint=cfg["search_endpoint"],
            index_name=cfg["index_name"],
            azure_openai_resource_url=cfg["aoai_resource_url"],
            query_planning_model=cfg["model"],
            credential=aio_credential,
            retrieval_reasoning_effort=cfg["reasoning_effort"],
        ) as provider:
            agent = factory.create(
                "support-rag-iq",
                instructions=(
                    "당신은 고객 지원 어시스턴트입니다. "
                    "반드시 제공된 검색 컨텍스트 안의 정보만 근거로 한국어로 답변하세요. "
                    "컨텍스트에 없는 내용은 추측하지 말고 '관련 정보를 찾을 수 없습니다'라고 답하세요. "
                    "답변 끝에 근거가 된 문서 제목을 [출처: ...] 형식으로 표시하세요."
                ),
                context_providers=[provider],
            )

            # ── 3단계: Microsoft Agent Framework로 생성 단계 실행(스트리밍) ──
            await factory.enable_tracing()
            question = "Pro 요금제는 얼마이고 기술 지원은 얼마나 빨리 받을 수 있나요?"
            print(f"\n[3단계] 질문: {question}")
            print("\n[4단계] 에이전트가 검색 후 답변 생성 중...")
            await stream_agent(agent, question, label="\n에이전트 응답")

    except Exception as e:
        print(f"RAG 실행 중 오류 발생: {e}")
        sys.exit(1)
    finally:
        # ── 4단계: 생성한 서버 측 에이전트 정리 + 추적 플러시 + 자격 증명 종료 ──
        factory.cleanup()
        factory.flush_tracing()
        await aio_credential.close()

    print("\n=== 실행 완료 ===")


if __name__ == "__main__":
    asyncio.run(main())
