"""Foundry IQ RAG 공용 헬퍼 — 지식 베이스 + agentic retrieval.

기존 ``src/06_rag_agent.py``(Azure AI Search 하이브리드 검색)는 검색·증강을 Python
코드로 직접 수행합니다. 이 모듈은 그 대신 **Foundry IQ**(지식 베이스 + agentic
retrieval)에 검색을 위임하는 변형 예제들이 공유하는 헬퍼를 모았습니다.

핵심 차이:
  - 인덱스를 **기본 semantic 구성**과 함께 생성합니다(agentic retrieval 필수 요건).
  - 검색 단계는 ``agent_framework.azure.AzureAISearchContextProvider``(agentic 모드)가
    담당합니다. 이 프로바이더는 인덱스로부터 지식 소스(``<index>-source``)와 지식
    베이스(``<index>-kb``)를 자동 생성하고, 멀티홉 검색 결과를 에이전트 세션
    컨텍스트에 주입(``before_run`` 훅)합니다.

지식 베이스(Foundry IQ)·인덱스는 기존 하이브리드 예제와 충돌하지 않도록 **별도
인덱스 이름**(기본 ``maf-lab-knowledge-iq-v1``)을 사용합니다.

.. note::
    지식 베이스의 ``model``에는 **임베딩이 아니라 채팅 모델 배포 이름**(예:
    ``gpt-5.4``)을 전달해야 합니다. 지식 베이스 모델은 질의 계획(query planning)에
    쓰이며 gpt-4o / gpt-4.1 / gpt-5.x 계열만 허용됩니다. 문서 임베딩은 별도의 임베딩
    배포(``EMBEDDING_DEPLOYMENT_NAME``)로 시드 단계에서 수행합니다.
"""

import os
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
    SemanticConfiguration,
    SemanticField,
    SemanticPrioritizedFields,
    SemanticSearch,
    SimpleField,
    VectorSearch,
    VectorSearchAlgorithmMetric,
    VectorSearchProfile,
)
from openai import AzureOpenAI

# agentic retrieval에 필요한 기본 semantic 구성 이름
SEMANTIC_CONFIG_NAME = "maf-lab-semantic"


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


def ensure_index_semantic(index_client: SearchIndexClient, index_name: str, dim: int) -> None:
    """agentic retrieval용 인덱스를 생성합니다 — 벡터 + **기본 semantic 구성**(멱등).

    하이브리드 예제의 ``ensure_index``와 달리, Foundry IQ agentic retrieval이 요구하는
    **기본 semantic 구성**을 함께 만듭니다. semantic 구성이 없으면 지식 소스 생성·검색이
    실패합니다.

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

    # agentic retrieval은 semantic 랭킹을 사용하므로 기본 semantic 구성이 필요합니다.
    semantic_search = SemanticSearch(
        default_configuration_name=SEMANTIC_CONFIG_NAME,
        configurations=[
            SemanticConfiguration(
                name=SEMANTIC_CONFIG_NAME,
                prioritized_fields=SemanticPrioritizedFields(
                    title_field=SemanticField(field_name="title"),
                    content_fields=[SemanticField(field_name="content")],
                ),
            )
        ],
    )

    index = SearchIndex(
        name=index_name,
        fields=fields,
        vector_search=vector_search,
        semantic_search=semantic_search,
    )
    index_client.create_index(index)
    print(f"  → 인덱스 생성 완료: {index_name} (벡터 차원 {dim}, 코사인, semantic 구성 포함)")


def seed_documents(search_client: SearchClient, embed) -> None:
    """지식 베이스 문서를 임베딩하여 인덱스에 업로드합니다 (멱등 upsert).

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

    # 인덱싱 반영 대기 (최대 30초)
    target = len(KNOWLEDGE_BASE)
    for _ in range(30):
        if search_client.get_document_count() >= target:
            break
        time.sleep(1)
    print(f"  → 문서 {target}건 임베딩·업로드 완료")


def seed_iq_index(
    search_endpoint: str,
    index_name: str,
    aoai_endpoint: str,
    embedding_deployment: str,
    aoai_api_version: str,
    credential: TokenCredential,
) -> int:
    """Foundry IQ용 인덱스를 생성하고 지식 베이스를 시드합니다(멱등).

    Args:
        search_endpoint: Azure AI Search 엔드포인트.
        index_name: Foundry IQ 인덱스 이름.
        aoai_endpoint: 임베딩 호출용 Azure OpenAI 엔드포인트.
        embedding_deployment: 임베딩 모델 배포 이름.
        aoai_api_version: Azure OpenAI API 버전.
        credential: 동기 토큰 자격 증명(AzureCliCredential 등).

    Returns:
        임베딩 벡터 차원(인덱스 생성에 사용한 값).
    """
    embed = make_embedder(aoai_endpoint, embedding_deployment, aoai_api_version, credential)
    dim = len(embed(["차원 확인"])[0])
    print(f"  → 임베딩 차원: {dim}")

    index_client = SearchIndexClient(endpoint=search_endpoint, credential=credential)
    ensure_index_semantic(index_client, index_name, dim)

    search_client = SearchClient(endpoint=search_endpoint, index_name=index_name, credential=credential)
    seed_documents(search_client, embed)
    return dim


def build_agentic_provider(
    *,
    search_endpoint: str,
    index_name: str,
    azure_openai_resource_url: str,
    query_planning_model: str,
    credential,
    retrieval_reasoning_effort: str = "minimal",
):
    """인덱스 기반 Foundry IQ agentic 컨텍스트 프로바이더를 생성합니다.

    인덱스로부터 지식 소스·지식 베이스를 자동 생성(create-or-update, 멱등)하고,
    멀티홉 agentic 검색 결과를 에이전트 세션 컨텍스트에 주입합니다.

    Args:
        search_endpoint: Azure AI Search 엔드포인트.
        index_name: Foundry IQ 인덱스 이름(``<index>-kb`` 지식 베이스가 자동 생성됨).
        azure_openai_resource_url: 지식 베이스 모델이 사용할 Azure OpenAI 리소스 URL.
        query_planning_model: 지식 베이스의 질의 계획에 사용할 **채팅 모델 배포 이름**
            (예: ``gpt-5.4``). 지식 베이스 모델은 임베딩이 아니라 채팅 모델이어야
            합니다(gpt-4o / gpt-4.1 / gpt-5.x 계열).
        credential: 비동기 자격 증명(``azure.identity.aio.AzureCliCredential`` 등).
            프로바이더 내부가 비동기 Search 클라이언트를 사용하므로 비동기 자격 증명이
            필요합니다.
        retrieval_reasoning_effort: 질의 계획 추론 강도(minimal/low/medium).

    Returns:
        ``AzureAISearchContextProvider`` 인스턴스(에이전트의 ``context_providers``에 전달).
    """
    from agent_framework.azure import AzureAISearchContextProvider

    return AzureAISearchContextProvider(
        endpoint=search_endpoint,
        index_name=index_name,
        mode="agentic",
        model=query_planning_model,
        azure_openai_resource_url=azure_openai_resource_url,
        credential=credential,
        retrieval_reasoning_effort=retrieval_reasoning_effort,
    )


def resolve_iq_env() -> dict:
    """Foundry IQ 예제 공통 환경 변수를 읽어 반환합니다.

    Returns:
        설정 값 딕셔너리. 누락 시 값이 ``None``일 수 있으므로 호출 측에서 검증하세요.
    """
    return {
        "project_endpoint": os.getenv("PROJECT_ENDPOINT"),
        "model": os.getenv("MODEL_DEPLOYMENT_NAME") or "gpt-5.4",
        "search_endpoint": os.getenv("SEARCH_SERVICE_ENDPOINT"),
        "index_name": os.getenv("SEARCH_INDEX_NAME_IQ", "maf-lab-knowledge-iq-v1"),
        "aoai_endpoint": os.getenv("AZURE_OPENAI_ENDPOINT"),
        # 일부 환경에서 agentic 벡터화는 .openai.azure.com 형식을 요구할 수 있어 분리 가능
        "aoai_resource_url": os.getenv("AZURE_OPENAI_RESOURCE_URL") or os.getenv("AZURE_OPENAI_ENDPOINT"),
        "embedding_deployment": os.getenv("EMBEDDING_DEPLOYMENT_NAME") or "text-embedding-3-large",
        "aoai_api_version": os.getenv("AZURE_OPENAI_API_VERSION", "2024-10-21"),
        "reasoning_effort": os.getenv("FOUNDRY_IQ_REASONING_EFFORT", "minimal"),
    }
