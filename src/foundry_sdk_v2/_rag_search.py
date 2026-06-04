"""RAG 검색 헬퍼 — Azure AI Search 하이브리드 검색.

이 모듈은 루트의 ``src/06_rag_agent.py``에 있는 검색(Retrieval) 로직을 그대로
미러링한 것입니다. 루트 예제는 스크립트 형태이고 파일명이 숫자로 시작해 모듈로
임포트할 수 없으므로, SDK v2 RAG 예제가 자급자족하도록 검색 헬퍼만 따로 모았습니다.

생성(Generation) 단계만 Foundry Agent SDK v2 에이전트로 바뀌고, 검색·증강 로직은
기존 예제와 동일합니다. 인증은 전부 키리스(AzureCliCredential / Entra ID)입니다.

.. note::
    코드 중복 동기화 주의:
    ``make_embedder``, ``ensure_index``, ``seed_documents``, ``retrieve``,
    ``build_context`` 함수의 로직을 변경할 때는 ``src/06_rag_agent.py``와
    이 파일을 함께 수정하여 두 구현이 일치하도록 유지하세요.
"""

import time

from azure.core.credentials import TokenCredential
from azure.identity import get_bearer_token_provider
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
        endpoint: Azure OpenAI 엔드포인트.
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
    """인덱스가 없으면 하이브리드 검색용 스키마로 생성합니다 (멱등)."""
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


def seed_documents(search_client: SearchClient, embed) -> None:
    """지식 베이스 문서를 임베딩하여 인덱스에 업로드합니다 (멱등 upsert)."""
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

    # 인덱싱 반영 대기 (최대 30초)
    target = len(KNOWLEDGE_BASE)
    for _ in range(30):
        if search_client.get_document_count() >= target:
            break
        time.sleep(1)
    print(f"  → 문서 {target}건 임베딩·업로드 완료")


def retrieve(search_client: SearchClient, embed, query: str, top_k: int = 2) -> list:
    """하이브리드(키워드 + 벡터) 검색으로 관련 문서를 찾습니다."""
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
