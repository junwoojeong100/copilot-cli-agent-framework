"""
[SDK v2] 실습 6: RAG (검색 증강 생성) 에이전트

검색(Retrieval)·증강(Augmentation)은 Azure AI Search 하이브리드 검색으로 하고,
생성(Generation)은 **Foundry Agent SDK v2**로 만든 에이전트가 담당합니다.
검색·증강 로직은 기존 ``src/06_rag_agent.py``와 동일하며(헬퍼 ``_rag_search.py``),
생성 단계의 에이전트만 SDK v2로 생성한다는 점이 다릅니다.

  [질문] → [1.검색: Azure AI Search 하이브리드] → [2.증강: 컨텍스트 주입]
        → [3.생성: SDK v2 에이전트가 근거 기반 답변]

필요 리소스: Azure AI Search 서비스, Azure OpenAI 임베딩 배포, Foundry 프로젝트+모델.
인증은 전부 키리스(AzureCliCredential / Entra ID)로 동작합니다.

> v2 네이티브 대안: ``azure.ai.projects.models.AzureAISearchTool``로 검색을 서버 측
> 도구로 둘 수도 있습니다(프로젝트에 Search 연결 + 인덱스 등록 필요). 이 예제는
> 견고함과 키리스 일관성을 위해 Python 검색 + SDK v2 생성 방식을 사용합니다.
"""

import asyncio
import os
import sys

from dotenv import load_dotenv

# 공용 스트리밍 헬퍼(src/_streaming.py)와 프로젝트 루트(.env)를 참조하기 위한 경로 설정
_SRC_DIR = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, _SRC_DIR)
load_dotenv(dotenv_path=os.path.join(_SRC_DIR, "..", ".env"))

from azure.identity import AzureCliCredential
from azure.search.documents import SearchClient
from azure.search.documents.indexes import SearchIndexClient

from _foundry_agents import FoundryAgentFactory
from _rag_search import (
    build_context,
    ensure_index,
    make_embedder,
    retrieve,
    seed_documents,
)
from _streaming import stream_agent


async def main():
    """Azure AI Search 검색 + SDK v2 에이전트 생성으로 RAG를 실행하는 메인 함수"""

    print("=== [SDK v2] RAG 에이전트 (Azure AI Search) 실행 ===\n")

    project_endpoint = os.getenv("PROJECT_ENDPOINT")
    model = os.getenv("MODEL_DEPLOYMENT_NAME", "gpt-5.4")
    search_endpoint = os.getenv("SEARCH_SERVICE_ENDPOINT")
    index_name = os.getenv("SEARCH_INDEX_NAME", "maf-lab-knowledge-v1")
    aoai_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
    embedding_deployment = os.getenv("EMBEDDING_DEPLOYMENT_NAME", "text-embedding-3-large")
    aoai_api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2024-10-21")

    if not project_endpoint:
        print("오류: PROJECT_ENDPOINT 환경 변수를 설정해주세요.")
        sys.exit(1)
    if not search_endpoint:
        print("오류: SEARCH_SERVICE_ENDPOINT 환경 변수를 설정해주세요.")
        sys.exit(1)
    if not aoai_endpoint:
        print("오류: AZURE_OPENAI_ENDPOINT 환경 변수를 설정해주세요.")
        sys.exit(1)

    # 모든 Azure 서비스에서 동일한 자격 증명을 재사용합니다 (키리스).
    credential = AzureCliCredential()
    factory = FoundryAgentFactory(project_endpoint, model, credential)

    try:
        # ── 1단계: 검색·증강 준비 (기존 06과 동일) ──
        print("[1단계] 임베딩 클라이언트 준비 및 차원 확인...")
        embed = make_embedder(aoai_endpoint, embedding_deployment, aoai_api_version, credential)
        dim = len(embed(["차원 확인"])[0])
        print(f"  → 임베딩 차원: {dim}")

        print("\n[2단계] Azure AI Search 인덱스 확인/생성...")
        index_client = SearchIndexClient(endpoint=search_endpoint, credential=credential)
        ensure_index(index_client, index_name, dim)

        print("\n[3단계] 지식 베이스 임베딩 및 업로드...")
        search_client = SearchClient(endpoint=search_endpoint, index_name=index_name, credential=credential)
        seed_documents(search_client, embed)

        question = "Pro 요금제는 얼마이고 기술 지원은 얼마나 빨리 받을 수 있나요?"
        print(f"\n[4단계] 하이브리드 검색 — 질문: {question}")
        docs = retrieve(search_client, embed, question, top_k=2)
        print("  → 검색된 문서:")
        for doc in docs:
            print(f"     - {doc['title']} ({doc['id']}, score={doc['score']:.3f})")
        context = build_context(docs)

        augmented_prompt = (
            f"다음 참고 문서를 바탕으로 질문에 답하세요.\n\n"
            f"--- 참고 문서 ---\n{context}\n\n"
            f"--- 질문 ---\n{question}"
        )

        # ── 2단계: Foundry Agent SDK v2로 생성 에이전트 생성 ──
        agent = factory.create(
            "support-rag",
            instructions=(
                "당신은 고객 지원 어시스턴트입니다. "
                "반드시 제공된 '참고 문서' 안의 정보만 근거로 한국어로 답변하세요. "
                "문서에 없는 내용은 추측하지 말고 '관련 정보를 찾을 수 없습니다'라고 답하세요. "
                "답변 끝에 근거가 된 문서 제목을 [출처: ...] 형식으로 표시하세요."
            ),
        )

        # ── 3단계: Microsoft Agent Framework로 생성 단계 실행(스트리밍) ──
        await factory.enable_tracing()
        print("\n[5단계] 에이전트가 답변 생성 중...")
        await stream_agent(agent, augmented_prompt, label="\n에이전트 응답")

    except Exception as e:
        print(f"RAG 실행 중 오류 발생: {e}")
        sys.exit(1)
    finally:
        # ── 4단계: 생성한 서버 측 에이전트 정리 + 추적 플러시 ──
        factory.cleanup()
        factory.flush_tracing()

    print("\n=== 실행 완료 ===")


if __name__ == "__main__":
    asyncio.run(main())
