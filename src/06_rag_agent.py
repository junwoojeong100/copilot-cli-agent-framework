"""
실습 6: RAG (검색 증강 생성) 에이전트 — Azure AI Search 하이브리드 검색
지식 베이스를 Azure AI Search 인덱스에 저장하고, 질문과 관련된 문서를
하이브리드(키워드 + 벡터) 검색으로 찾은 뒤(Retrieval), 그 내용을 컨텍스트로
주입하여(Augmentation) 에이전트가 근거 기반으로 답변(Generation)하게 합니다.

  [질문] → [1.검색: Azure AI Search 하이브리드] → [2.증강: 컨텍스트 주입] → [3.생성: 에이전트 답변]

이 예제는 처음 실행 시 인덱스를 자동으로 생성하고 문서를 임베딩하여 업로드합니다
(자체 완결·멱등). 인증은 전부 키리스(AzureCliCredential / Entra ID)로 동작합니다.

필요 리소스:
  - Azure AI Search 서비스 (RBAC: Search Service Contributor + Index Data Contributor/Reader)
  - Azure OpenAI 임베딩 배포 (예: text-embedding-3-large)
  - Microsoft Foundry 프로젝트 + 채팅 모델 (응답 생성)
"""

import asyncio
import os
import sys

from dotenv import load_dotenv

# 프로젝트 루트의 .env 파일 로드
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", ".env"))

from agent_framework import Agent
from agent_framework.foundry import FoundryChatClient
from azure.core.credentials import TokenCredential
from azure.identity import AzureCliCredential, get_bearer_token_provider
from azure.search.documents import SearchClient
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import (
    HnswAlgorithmConfiguration,
    HnswParameters,
    SearchableField,
    SearchField,
    SearchFieldDataType,
    SearchIndex,
    SimpleField,
    VectorSearch,
    VectorSearchAlgorithmMetric,
    VectorSearchProfile,
)
from azure.search.documents.models import VectorizedQuery
from openai import AzureOpenAI

from _streaming import stream_agent


# ── 지식 베이스 ──
# 실제로는 사내 위키, 제품 매뉴얼, FAQ 등을 청크로 나눠 저장합니다.
KNOWLEDGE_BASE = [
    {
        "id": "doc-1",
        "title": "환불 정책",
        "content": (
            "제품 구매 후 14일 이내에는 전액 환불이 가능합니다. "
            "단, 디지털 제품은 다운로드 또는 라이선스 활성화 이전에만 환불됩니다. "
            "환불 요청은 고객센터 또는 마이페이지에서 접수할 수 있으며, "
            "처리에는 영업일 기준 3~5일이 소요됩니다."
        ),
    },
    {
        "id": "doc-2",
        "title": "구독 요금제",
        "content": (
            "Basic 요금제는 월 9,900원으로 사용자 3명까지 지원합니다. "
            "Pro 요금제는 월 29,900원으로 사용자 무제한과 우선 기술 지원을 제공합니다. "
            "연간 결제 시 두 달치 요금이 할인됩니다."
        ),
    },
    {
        "id": "doc-3",
        "title": "기술 지원 SLA",
        "content": (
            "Pro 요금제 고객은 24시간 이내 1차 응답을 보장받습니다. "
            "Basic 요금제는 영업일 기준 48시간 이내 응답을 제공합니다. "
            "장애 등급이 Critical인 경우 요금제와 무관하게 4시간 이내 대응합니다."
        ),
    },
    {
        "id": "doc-4",
        "title": "계정 보안",
        "content": (
            "모든 계정은 2단계 인증(2FA)을 설정할 수 있습니다. "
            "비밀번호는 최소 12자 이상이어야 하며 90일마다 변경을 권장합니다. "
            "의심스러운 로그인 시도는 이메일로 즉시 알림이 발송됩니다."
        ),
    },
]


def make_embedder(endpoint: str, deployment: str, api_version: str, credential: TokenCredential):
    """Azure OpenAI 임베딩 호출 함수를 생성합니다 (키리스 AAD 인증).

    Args:
        endpoint: Azure OpenAI 엔드포인트 (예: https://<resource>.cognitiveservices.azure.com/).
        deployment: 임베딩 모델 배포 이름 (예: text-embedding-3-large).
        api_version: Azure OpenAI API 버전.
        credential: AzureCliCredential 등 토큰 자격 증명.

    Returns:
        텍스트 리스트를 받아 임베딩 벡터 리스트를 반환하는 함수.
    """
    token_provider = get_bearer_token_provider(
        credential, "https://cognitiveservices.azure.com/.default"
    )
    client = AzureOpenAI(
        azure_endpoint=endpoint,
        azure_ad_token_provider=token_provider,
        api_version=api_version,
    )

    def embed(texts: list[str]) -> list[list[float]]:
        """텍스트 리스트를 임베딩 벡터 리스트로 변환합니다."""
        response = client.embeddings.create(model=deployment, input=texts)
        return [item.embedding for item in response.data]

    return embed


def ensure_index(index_client: SearchIndexClient, index_name: str, dim: int) -> None:
    """인덱스가 없으면 하이브리드 검색용 스키마로 생성합니다 (멱등).

    Args:
        index_client: Azure AI Search 인덱스 관리 클라이언트.
        index_name: 생성/확인할 인덱스 이름.
        dim: 벡터 필드 차원 (임베딩 모델 출력 차원).
    """
    existing = list(index_client.list_index_names())
    if index_name in existing:
        print(f"  → 기존 인덱스 사용: {index_name}")
        return

    # 한국어 키워드 검색 품질을 위해 ko.microsoft 분석기를 사용합니다.
    fields = [
        SimpleField(name="id", type=SearchFieldDataType.String, key=True),
        SearchableField(name="title", type=SearchFieldDataType.String, analyzer_name="ko.microsoft"),
        SearchableField(name="content", type=SearchFieldDataType.String, analyzer_name="ko.microsoft"),
        SearchField(
            name="content_vector",
            type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
            searchable=True,
            vector_search_dimensions=dim,
            vector_search_profile_name="vprofile",
        ),
    ]

    # OpenAI 임베딩은 코사인 유사도와 함께 사용하는 것이 일반적입니다.
    vector_search = VectorSearch(
        algorithms=[
            HnswAlgorithmConfiguration(
                name="hnsw",
                parameters=HnswParameters(metric=VectorSearchAlgorithmMetric.COSINE),
            )
        ],
        profiles=[VectorSearchProfile(name="vprofile", algorithm_configuration_name="hnsw")],
    )

    index = SearchIndex(name=index_name, fields=fields, vector_search=vector_search)
    index_client.create_index(index)
    print(f"  → 인덱스 생성 완료: {index_name} (벡터 차원 {dim}, 코사인)")


async def seed_documents(search_client: SearchClient, embed) -> None:
    """지식 베이스 문서를 임베딩하여 인덱스에 업로드합니다 (멱등 upsert).

    문서가 4건뿐이라 매 실행 시 새로 임베딩하여 덮어씁니다(내용 변경 자동 반영).
    업로드 후에는 인덱싱이 반영될 때까지 문서 수를 폴링합니다
    (Azure AI Search는 최종 일관성이라 업로드 직후 검색이 비어 있을 수 있습니다).

    Args:
        search_client: 대상 인덱스의 SearchClient.
        embed: 텍스트 리스트를 임베딩 벡터로 변환하는 함수.
    """
    vectors = embed([doc["content"] for doc in KNOWLEDGE_BASE])
    documents = [
        {
            "id": doc["id"],
            "title": doc["title"],
            "content": doc["content"],
            "content_vector": vector,
        }
        for doc, vector in zip(KNOWLEDGE_BASE, vectors)
    ]

    results = search_client.merge_or_upload_documents(documents=documents)
    failed = [r for r in results if not r.succeeded]
    if failed:
        raise RuntimeError(f"문서 업로드 실패: {[r.key for r in failed]}")

    # 인덱싱 반영 대기 (최대 30초).
    # embed/merge_or_upload/get_document_count는 동기 Azure SDK 호출이며,
    # sleep만 비동기화하여 이벤트 루프 블로킹을 최소화합니다.
    target = len(KNOWLEDGE_BASE)
    for _ in range(30):
        if search_client.get_document_count() >= target:
            break
        await asyncio.sleep(1)
    print(f"  → 문서 {target}건 임베딩·업로드 완료")


def retrieve(search_client: SearchClient, embed, query: str, top_k: int = 2) -> list:
    """하이브리드(키워드 + 벡터) 검색으로 관련 문서를 찾습니다.

    Args:
        search_client: 검색 대상 인덱스의 SearchClient.
        embed: 질문을 임베딩 벡터로 변환하는 함수.
        query: 사용자 질문.
        top_k: 반환할 상위 문서 수.

    Returns:
        관련도 높은 순으로 정렬된 문서 리스트(id/title/content/score).
    """
    query_vector = embed([query])[0]
    vector_query = VectorizedQuery(
        vector=query_vector,
        k=max(5, top_k),  # 하이브리드 융합용 후보 풀은 넉넉히
        fields="content_vector",
    )

    results = search_client.search(
        search_text=query,  # 키워드(BM25) 검색
        vector_queries=[vector_query],  # 벡터 검색 → 하이브리드 융합(RRF)
        select=["id", "title", "content"],
        top=top_k,
    )

    docs = []
    for result in results:
        docs.append(
            {
                "id": result["id"],
                "title": result["title"],
                "content": result["content"],
                "score": result.get("@search.score"),
            }
        )
    return docs


def build_context(docs: list) -> str:
    """검색된 문서들을 프롬프트에 넣을 컨텍스트 문자열로 만듭니다."""
    if not docs:
        return "(관련 문서를 찾지 못했습니다.)"
    blocks = [f"[{doc['title']}]\n{doc['content']}" for doc in docs]
    return "\n\n".join(blocks)


async def main():
    """Azure AI Search 기반 RAG 파이프라인을 구성하고 실행하는 메인 함수"""

    print("=== RAG 에이전트 (Azure AI Search) 실행 ===\n")

    # ── 1단계: 환경 변수 확인 ──
    project_endpoint = os.getenv("PROJECT_ENDPOINT")
    model = os.getenv("MODEL_DEPLOYMENT_NAME") or "gpt-5.4"
    search_endpoint = os.getenv("SEARCH_SERVICE_ENDPOINT")
    index_name = os.getenv("SEARCH_INDEX_NAME", "maf-lab-knowledge-v1")
    aoai_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
    embedding_deployment = os.getenv("EMBEDDING_DEPLOYMENT_NAME") or "text-embedding-3-large"
    aoai_api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2024-10-21")

    if not project_endpoint:
        print("오류: PROJECT_ENDPOINT 환경 변수를 설정해주세요.")
        sys.exit(1)
    if not search_endpoint:
        print("오류: SEARCH_SERVICE_ENDPOINT 환경 변수를 설정해주세요.")
        print("      (예: https://<your-search>.search.windows.net)")
        sys.exit(1)
    if not aoai_endpoint:
        print("오류: AZURE_OPENAI_ENDPOINT 환경 변수를 설정해주세요.")
        print("      (임베딩 호출용 Azure OpenAI 엔드포인트)")
        sys.exit(1)

    # 모든 Azure 서비스에서 동일한 자격 증명을 재사용합니다 (키리스).
    credential = AzureCliCredential()

    try:
        # ── 2단계: 임베딩 함수 준비 및 벡터 차원 확인 ──
        print("[1단계] 임베딩 클라이언트 준비 및 차원 확인...")
        embed = make_embedder(aoai_endpoint, embedding_deployment, aoai_api_version, credential)
        dim = len(embed(["차원 확인"])[0])  # 모델 실제 출력 차원을 동적으로 사용
        print(f"  → 임베딩 차원: {dim}")

        # ── 3단계: 인덱스 확인/생성 ──
        print("\n[2단계] Azure AI Search 인덱스 확인/생성...")
        index_client = SearchIndexClient(endpoint=search_endpoint, credential=credential)
        ensure_index(index_client, index_name, dim)

        # ── 4단계: 문서 임베딩 및 업로드 ──
        print("\n[3단계] 지식 베이스 임베딩 및 업로드...")
        search_client = SearchClient(endpoint=search_endpoint, index_name=index_name, credential=credential)
        await seed_documents(search_client, embed)

        # ── 5단계: 검색(Retrieval) ──
        question = "Pro 요금제는 얼마이고 기술 지원은 얼마나 빨리 받을 수 있나요?"
        print(f"\n[4단계] 하이브리드 검색 — 질문: {question}")
        docs = retrieve(search_client, embed, question, top_k=2)
        print("  → 검색된 문서:")
        for doc in docs:
            print(f"     - {doc['title']} ({doc['id']}, score={doc['score']:.3f})")
        context = build_context(docs)

        # ── 6단계: 증강(Augmentation) — 검색 결과를 프롬프트에 주입 ──
        augmented_prompt = (
            f"다음 참고 문서를 바탕으로 질문에 답하세요.\n\n"
            f"--- 참고 문서 ---\n{context}\n\n"
            f"--- 질문 ---\n{question}"
        )

        # ── 7단계: 생성(Generation) ──
        # 핵심: 검색된 컨텍스트 안에서만 답하도록 지시하여 환각(hallucination)을 줄입니다.
        agent = Agent(
            client=FoundryChatClient(
                project_endpoint=project_endpoint,
                model=model,
                credential=credential,
            ),
            name="고객지원_RAG_어시스턴트",
            instructions=(
                "당신은 고객 지원 어시스턴트입니다. "
                "반드시 제공된 '참고 문서' 안의 정보만 근거로 한국어로 답변하세요. "
                "문서에 없는 내용은 추측하지 말고 '관련 정보를 찾을 수 없습니다'라고 답하세요. "
                "답변 끝에 근거가 된 문서 제목을 [출처: ...] 형식으로 표시하세요."
            ),
        )

        print("\n[5단계] 에이전트가 답변 생성 중...")
        await stream_agent(agent, augmented_prompt, label="\n에이전트 응답")

    except Exception as e:
        print(f"RAG 실행 중 오류 발생: {e}")
        sys.exit(1)

    print("\n=== 실행 완료 ===")


if __name__ == "__main__":
    asyncio.run(main())
