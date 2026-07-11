"""Foundry IQ RAG 공용 헬퍼 — 지식 베이스 + agentic retrieval.

기존 ``src/06_rag_agent.py``(Azure AI Search 하이브리드 검색)는 검색·증강을 Python
코드로 직접 수행합니다. 이 모듈은 그 대신 **Foundry IQ**(지식 베이스 + agentic
retrieval)에 검색을 위임하는 변형 예제들이 공유하는 헬퍼를 모았습니다.

핵심 차이:
  - 인덱스를 **기본 semantic 구성 + 쿼리 벡터라이저**와 함께 생성합니다.
  - 검색 단계는 ``agent_framework.azure.AzureAISearchContextProvider``(agentic 모드)가
    담당합니다. 이 프로바이더는 인덱스로부터 지식 소스(``<index>-source``)와 지식
    베이스(``<index>-kb``)를 자동 생성하고, 질의 계획 기반 멀티쿼리 검색 결과를
    에이전트 세션 컨텍스트에 주입(``before_run`` 훅)합니다.

지식 베이스(Foundry IQ)·인덱스는 기존 하이브리드 예제와 충돌하지 않도록 **별도
인덱스 이름**(기본 ``maf-lab-knowledge-iq-v3``)을 사용합니다.

.. note::
    지식 베이스의 ``model``에는 **임베딩이 아니라 채팅 모델 배포 이름**(예:
    ``gpt-5.4``)을 전달해야 합니다. 지식 베이스 모델은 질의 계획(query planning)에
    쓰이며 gpt-4o / gpt-4.1 / gpt-5.x 계열만 허용됩니다. 문서 임베딩은 별도의 임베딩
    배포(``EMBEDDING_DEPLOYMENT_NAME``)로 시드 단계에서 수행합니다.
"""

import math
import os
import time
from collections.abc import Callable
from typing import Literal, TypedDict, cast

from agent_framework.azure import AzureAISearchContextProvider
from azure.core.credentials import TokenCredential
from azure.core.credentials_async import AsyncTokenCredential
from azure.core.exceptions import ResourceNotFoundError
from azure.identity import get_bearer_token_provider
from azure.search.documents import SearchClient
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import (
    AzureOpenAIVectorizer,
    AzureOpenAIVectorizerParameters,
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
VECTORIZER_NAME = "maf-lab-aoai-vectorizer"
ReasoningEffort = Literal["minimal", "low", "medium"]
Embedder = Callable[[list[str]], list[list[float]]]


class IQConfig(TypedDict):
    """Foundry IQ 예제 환경 변수 형식."""

    project_endpoint: str | None
    model: str
    search_endpoint: str | None
    index_name: str
    aoai_endpoint: str | None
    aoai_resource_url: str | None
    embedding_deployment: str
    embedding_model: str
    aoai_api_version: str
    reasoning_effort: ReasoningEffort


class IndexedDocument(TypedDict):
    """인덱스에 업로드하는 문서 형식."""

    id: str
    title: str
    content: str
    content_vector: list[float]


def _vectors_match(actual: object, expected: list[float]) -> bool:
    """Search의 단정밀도 벡터가 업로드 값과 같은지 허용 오차로 비교합니다.

    Args:
        actual: Search에서 조회한 벡터 값.
        expected: 업로드한 임베딩 벡터.

    Returns:
        차원과 각 원소가 단정밀도 저장 오차 안에서 같으면 True.
    """
    if not isinstance(actual, list) or len(actual) != len(expected):
        return False
    if not all(isinstance(value, (int, float)) for value in actual):
        return False
    return all(
        math.isclose(float(current), target, rel_tol=1e-6, abs_tol=1e-7)
        for current, target in zip(actual, expected, strict=True)
    )


# ── 지식 베이스 ──
# 실제로는 사내 위키, 제품 매뉴얼, FAQ 등을 청크로 나눠 저장합니다.
KNOWLEDGE_BASE: list[dict[str, str]] = [
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


def make_embedder(
    endpoint: str,
    deployment: str,
    api_version: str,
    credential: TokenCredential,
) -> Embedder:
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


def _normalize_resource_url(value: str | None) -> str:
    """리소스 URL을 비교 가능한 형식으로 정규화합니다."""
    return (value or "").rstrip("/").lower()


def _validate_index(
    index: SearchIndex,
    index_name: str,
    dim: int,
    embedding_resource_url: str,
    embedding_deployment: str,
    embedding_model: str,
) -> None:
    """기존 인덱스가 Foundry IQ 예제 스키마와 호환되는지 확인합니다.

    Args:
        index: Azure AI Search에서 읽은 기존 인덱스.
        index_name: 검증할 인덱스 이름.
        dim: 현재 임베딩 모델의 벡터 차원.
        embedding_resource_url: 쿼리 벡터라이저가 사용할 Azure OpenAI 리소스 URL.
        embedding_deployment: 쿼리 벡터라이저의 임베딩 배포 이름.
        embedding_model: 쿼리 벡터라이저의 실제 임베딩 모델 이름.

    Raises:
        RuntimeError: 벡터 또는 semantic 구성이 호환되지 않을 때.
    """
    fields = {field.name: field for field in index.fields}
    required_fields = {"id", "title", "content", "content_vector"}
    errors = []

    missing = sorted(required_fields - fields.keys())
    if missing:
        errors.append(f"필수 필드 누락: {', '.join(missing)}")
    else:
        id_field = fields["id"]
        if (
            id_field.type != SearchFieldDataType.String
            or id_field.key is not True
            or id_field.hidden is not False
        ):
            errors.append("id 필드가 조회 가능한 문자열 키가 아님")

        for field_name in ("title", "content"):
            text_field = fields[field_name]
            if (
                text_field.type != SearchFieldDataType.String
                or text_field.searchable is not True
                or text_field.analyzer_name != "ko.microsoft"
                or text_field.hidden is not False
            ):
                errors.append(
                    f"{field_name} 필드가 조회 가능한 ko.microsoft 검색 문자열 구성이 아님"
                )

        vector_field = fields["content_vector"]
        expected_vector_type = SearchFieldDataType.Collection(SearchFieldDataType.Single)
        if vector_field.type != expected_vector_type or vector_field.searchable is not True:
            errors.append("content_vector가 검색 가능한 단정밀도 벡터 필드가 아님")
        if vector_field.vector_search_dimensions != dim:
            errors.append(
                "content_vector 차원 불일치 "
                f"(인덱스={vector_field.vector_search_dimensions}, 모델={dim})"
            )
        if vector_field.vector_search_profile_name != "vprofile":
            errors.append("content_vector의 벡터 프로필이 vprofile이 아님")
        if vector_field.hidden is not False or vector_field.stored is False:
            errors.append("content_vector가 인덱싱 반영 검증을 위해 조회 가능하게 저장되지 않음")

        vector_search = index.vector_search
        profiles = {
            profile.name: profile for profile in (vector_search.profiles or [])
        } if vector_search else {}
        algorithms = {
            algorithm.name: algorithm for algorithm in (vector_search.algorithms or [])
        } if vector_search else {}
        profile = profiles.get("vprofile")
        algorithm = (
            algorithms.get(profile.algorithm_configuration_name)
            if profile and profile.algorithm_configuration_name
            else None
        )
        metric = getattr(getattr(algorithm, "parameters", None), "metric", None)
        if algorithm is None or metric != VectorSearchAlgorithmMetric.COSINE:
            errors.append("vprofile이 코사인 벡터 검색 알고리즘을 참조하지 않음")
        if profile is None or profile.vectorizer_name != VECTORIZER_NAME:
            errors.append(f"vprofile이 쿼리 벡터라이저 '{VECTORIZER_NAME}'를 참조하지 않음")

        vectorizers = {
            vectorizer.vectorizer_name: vectorizer
            for vectorizer in (vector_search.vectorizers or [])
        } if vector_search else {}
        vectorizer = vectorizers.get(VECTORIZER_NAME)
        parameters = getattr(vectorizer, "parameters", None)
        if vectorizer is None or parameters is None:
            errors.append(f"Azure OpenAI 쿼리 벡터라이저 '{VECTORIZER_NAME}' 누락")
        else:
            if (
                _normalize_resource_url(parameters.resource_url)
                != _normalize_resource_url(embedding_resource_url)
            ):
                errors.append(f"벡터라이저 '{VECTORIZER_NAME}'의 Azure OpenAI 리소스 URL 불일치")
            if parameters.deployment_name != embedding_deployment:
                errors.append(f"벡터라이저 '{VECTORIZER_NAME}'의 임베딩 배포 이름 불일치")
            actual_model_name = getattr(parameters.model_name, "value", parameters.model_name)
            if actual_model_name != embedding_model:
                errors.append(f"벡터라이저 '{VECTORIZER_NAME}'의 임베딩 모델 이름 불일치")

    semantic_search = index.semantic_search
    configurations = (semantic_search.configurations or []) if semantic_search else []
    semantic_configuration = next(
        (config for config in configurations if config.name == SEMANTIC_CONFIG_NAME),
        None,
    )
    if (
        semantic_search is None
        or semantic_search.default_configuration_name != SEMANTIC_CONFIG_NAME
        or semantic_configuration is None
    ):
        errors.append(f"기본 semantic 구성 '{SEMANTIC_CONFIG_NAME}' 누락")
    else:
        prioritized_fields = semantic_configuration.prioritized_fields
        title_field = prioritized_fields.title_field if prioritized_fields else None
        content_fields = prioritized_fields.content_fields if prioritized_fields else []
        if (
            title_field is None
            or title_field.field_name != "title"
            or "content" not in {field.field_name for field in content_fields or []}
        ):
            errors.append(f"semantic 구성 '{SEMANTIC_CONFIG_NAME}'의 우선 필드가 올바르지 않음")

    if errors:
        details = "; ".join(errors)
        raise RuntimeError(
            f"기존 인덱스 '{index_name}'가 Foundry IQ 예제와 호환되지 않습니다: {details}. "
            "SEARCH_INDEX_NAME_IQ를 새 이름으로 바꾸거나 기존 인덱스를 정리한 뒤 다시 실행하세요."
        )


def ensure_index_semantic(
    index_client: SearchIndexClient,
    index_name: str,
    dim: int,
    embedding_resource_url: str,
    embedding_deployment: str,
    embedding_model: str,
) -> None:
    """agentic retrieval용 인덱스를 생성합니다 — 벡터라이저 + semantic 구성(멱등).

    하이브리드 예제의 ``ensure_index``와 달리, Foundry IQ agentic retrieval이 요구하는
    **기본 semantic 구성**과 쿼리 시점 Azure OpenAI 벡터라이저를 함께 만듭니다.
    벡터라이저가 없으면 저장된 벡터 필드는 agentic 검색의 벡터 쿼리에 사용되지 않습니다.

    Args:
        index_client: Azure AI Search 인덱스 관리 클라이언트.
        index_name: 생성/확인할 인덱스 이름.
        dim: 벡터 필드 차원 (임베딩 모델 출력 차원).
        embedding_resource_url: 쿼리 벡터라이저가 사용할 Azure OpenAI 리소스 URL.
        embedding_deployment: 쿼리 벡터라이저의 임베딩 배포 이름.
        embedding_model: 쿼리 벡터라이저의 실제 임베딩 모델 이름.
    """
    try:
        existing_index = index_client.get_index(index_name)
    except ResourceNotFoundError:
        existing_index = None

    if existing_index is not None:
        _validate_index(
            existing_index,
            index_name,
            dim,
            embedding_resource_url,
            embedding_deployment,
            embedding_model,
        )
        print(f"  → 기존 인덱스 사용: {index_name}")
        return

    # 한국어 키워드 검색 품질을 위해 ko.microsoft 분석기를 사용합니다.
    fields = [
        SimpleField(name="id", type=SearchFieldDataType.String, key=True),
        SearchableField(
            name="title",
            type=SearchFieldDataType.String,
            analyzer_name="ko.microsoft",
        ),
        SearchableField(
            name="content",
            type=SearchFieldDataType.String,
            analyzer_name="ko.microsoft",
        ),
        SearchField(
            name="content_vector",
            type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
            searchable=True,
            hidden=False,
            stored=True,
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
        profiles=[
            VectorSearchProfile(
                name="vprofile",
                algorithm_configuration_name="hnsw",
                vectorizer_name=VECTORIZER_NAME,
            )
        ],
        vectorizers=[
            AzureOpenAIVectorizer(
                vectorizer_name=VECTORIZER_NAME,
                parameters=AzureOpenAIVectorizerParameters(
                    resource_url=embedding_resource_url,
                    deployment_name=embedding_deployment,
                    model_name=embedding_model,
                ),
            )
        ],
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
    print(
        f"  → 인덱스 생성 완료: {index_name} "
        f"(벡터 차원 {dim}, 코사인, 쿼리 벡터라이저, semantic 구성 포함)"
    )


def _documents_are_indexed(
    search_client: SearchClient,
    expected_documents: list[IndexedDocument],
) -> bool:
    """업로드한 문서가 최신 내용으로 조회되는지 확인합니다.

    Args:
        search_client: 대상 인덱스의 SearchClient.
        expected_documents: 업로드한 최신 문서와 임베딩 벡터.

    Returns:
        모든 문서의 제목·본문·임베딩 벡터가 최신 값이면 True.
    """
    for expected in expected_documents:
        try:
            actual = search_client.get_document(
                key=expected["id"],
                selected_fields=["title", "content", "content_vector"],
            )
        except ResourceNotFoundError:
            return False
        if (
            actual.get("title") != expected["title"]
            or actual.get("content") != expected["content"]
            or not _vectors_match(actual.get("content_vector"), expected["content_vector"])
        ):
            return False
    return True


def seed_documents(search_client: SearchClient, embed: Embedder) -> None:
    """지식 베이스 문서를 임베딩하여 인덱스에 업로드합니다 (멱등 upsert).

    Args:
        search_client: 대상 인덱스의 SearchClient.
        embed: 텍스트 리스트를 임베딩 벡터로 변환하는 함수.
    """
    vectors = embed([doc["content"] for doc in KNOWLEDGE_BASE])
    if len(vectors) != len(KNOWLEDGE_BASE):
        raise RuntimeError(
            f"임베딩 결과 수가 문서 수와 다릅니다: {len(vectors)} != {len(KNOWLEDGE_BASE)}"
        )
    documents: list[IndexedDocument] = [
        {
            "id": doc["id"],
            "title": doc["title"],
            "content": doc["content"],
            "content_vector": vector,
        }
        for doc, vector in zip(KNOWLEDGE_BASE, vectors, strict=True)
    ]

    results = search_client.merge_or_upload_documents(documents=documents)
    failed = [r for r in results if not r.succeeded]
    if failed:
        raise RuntimeError(f"문서 업로드 실패: {[r.key for r in failed]}")

    # 문서 수뿐 아니라 최신 제목·본문·벡터가 조회되는지 최대 30초 동안 확인합니다.
    for _ in range(30):
        if _documents_are_indexed(search_client, documents):
            print(f"  → 문서 {len(KNOWLEDGE_BASE)}건 임베딩·업로드 완료")
            return
        time.sleep(1)
    raise TimeoutError("문서 업로드 후 30초 안에 최신 인덱싱 결과를 확인하지 못했습니다.")


def seed_iq_index(
    search_endpoint: str,
    index_name: str,
    aoai_endpoint: str,
    embedding_deployment: str,
    embedding_model: str,
    aoai_api_version: str,
    credential: TokenCredential,
) -> int:
    """Foundry IQ용 인덱스를 생성하고 지식 베이스를 시드합니다(멱등).

    Args:
        search_endpoint: Azure AI Search 엔드포인트.
        index_name: Foundry IQ 인덱스 이름.
        aoai_endpoint: 문서 임베딩과 Search 쿼리 벡터라이저용 Azure OpenAI 엔드포인트.
        embedding_deployment: 임베딩 모델 배포 이름.
        embedding_model: 배포의 실제 임베딩 모델 이름.
        aoai_api_version: Azure OpenAI API 버전.
        credential: 동기 토큰 자격 증명(AzureCliCredential 등).

    Returns:
        임베딩 벡터 차원(인덱스 생성에 사용한 값).
    """
    embed = make_embedder(aoai_endpoint, embedding_deployment, aoai_api_version, credential)
    dimension_probe = embed(["차원 확인"])
    if not dimension_probe or not dimension_probe[0]:
        raise RuntimeError("임베딩 모델이 빈 벡터를 반환했습니다.")
    dim = len(dimension_probe[0])
    print(f"  → 임베딩 차원: {dim}")

    index_client = SearchIndexClient(endpoint=search_endpoint, credential=credential)
    ensure_index_semantic(
        index_client,
        index_name,
        dim,
        aoai_endpoint,
        embedding_deployment,
        embedding_model,
    )

    search_client = SearchClient(
        endpoint=search_endpoint,
        index_name=index_name,
        credential=credential,
    )
    seed_documents(search_client, embed)
    return dim


def build_agentic_provider(
    *,
    search_endpoint: str,
    index_name: str,
    azure_openai_resource_url: str,
    query_planning_model: str,
    credential: AsyncTokenCredential,
    retrieval_reasoning_effort: ReasoningEffort = "low",
) -> AzureAISearchContextProvider:
    """인덱스 기반 Foundry IQ agentic 컨텍스트 프로바이더를 생성합니다.

    인덱스로부터 지식 소스·지식 베이스를 자동 생성(create-or-update, 멱등)하고,
    질의 계획 기반 멀티쿼리 검색 결과를 에이전트 세션 컨텍스트에 주입합니다.

    Args:
        search_endpoint: Azure AI Search 엔드포인트.
        index_name: Foundry IQ 인덱스 이름(``<index>-kb`` 지식 베이스가 자동 생성됨).
        azure_openai_resource_url: 지식 베이스 모델이 사용할 Azure OpenAI 리소스 URL.
        query_planning_model: 지식 베이스의 질의 계획에 사용할 **채팅 모델 배포 이름**
            (예: ``gpt-5.4``). 지식 베이스 모델은 임베딩이 아니라 채팅 모델이어야
            합니다(gpt-4o / gpt-4.1 / gpt-5.x 계열). 이 프로바이더 버전은 같은 값을
            지식 베이스의 배포 이름과 모델 이름에 모두 사용하므로 두 이름이 같아야 합니다.
        credential: 비동기 자격 증명(``azure.identity.aio.AzureCliCredential`` 등).
            프로바이더 내부가 비동기 Search 클라이언트를 사용하므로 비동기 자격 증명이
            필요합니다.
        retrieval_reasoning_effort: 질의 계획 추론 강도(minimal/low/medium). ``minimal``은
            LLM 질의 계획을 건너뛰므로 멀티쿼리 실습의 기본값은 ``low``입니다.

    Returns:
        ``AzureAISearchContextProvider`` 인스턴스(에이전트의 ``context_providers``에 전달).
    """
    return AzureAISearchContextProvider(
        endpoint=search_endpoint,
        index_name=index_name,
        mode="agentic",
        model=query_planning_model,
        azure_openai_resource_url=azure_openai_resource_url,
        credential=credential,
        retrieval_reasoning_effort=retrieval_reasoning_effort,
    )


def resolve_iq_env() -> IQConfig:
    """Foundry IQ 예제 공통 환경 변수를 읽어 반환합니다.

    Returns:
        설정 값 딕셔너리. 누락 시 값이 ``None``일 수 있으므로 호출 측에서 검증하세요.

    Raises:
        ValueError: 질의 계획 추론 강도 값이 허용 범위를 벗어날 때.
    """
    reasoning_effort = os.getenv("FOUNDRY_IQ_REASONING_EFFORT", "low")
    if reasoning_effort not in {"minimal", "low", "medium"}:
        raise ValueError(
            "FOUNDRY_IQ_REASONING_EFFORT는 minimal, low, medium 중 하나여야 합니다."
        )

    return {
        "project_endpoint": os.getenv("PROJECT_ENDPOINT"),
        "model": os.getenv("MODEL_DEPLOYMENT_NAME") or "gpt-5.4",
        "search_endpoint": os.getenv("SEARCH_SERVICE_ENDPOINT"),
        "index_name": os.getenv("SEARCH_INDEX_NAME_IQ", "maf-lab-knowledge-iq-v3"),
        "aoai_endpoint": os.getenv("AZURE_OPENAI_ENDPOINT"),
        # 모델 공급자 리소스 루트 URL이며, 미설정 시 임베딩 엔드포인트를 재사용
        "aoai_resource_url": os.getenv("AZURE_OPENAI_RESOURCE_URL")
        or os.getenv("AZURE_OPENAI_ENDPOINT"),
        "embedding_deployment": os.getenv("EMBEDDING_DEPLOYMENT_NAME") or "text-embedding-3-large",
        "embedding_model": os.getenv("EMBEDDING_MODEL_NAME") or "text-embedding-3-large",
        "aoai_api_version": os.getenv("AZURE_OPENAI_API_VERSION", "2024-10-21"),
        "reasoning_effort": cast(ReasoningEffort, reasoning_effort),
    }
