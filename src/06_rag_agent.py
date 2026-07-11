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
import math
import os
import sys
from collections.abc import Callable
from typing import TypedDict

from dotenv import load_dotenv

# 프로젝트 루트의 .env 파일 로드
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", ".env"))

from agent_framework import Agent
from agent_framework.foundry import FoundryChatClient
from azure.core.credentials import TokenCredential
from azure.core.exceptions import ResourceNotFoundError
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

from ._streaming import stream_agent


class RetrievedDocument(TypedDict):
    """검색 결과 문서 형식."""

    id: str
    title: str
    content: str
    score: float | None


class IndexedDocument(TypedDict):
    """인덱스에 업로드하는 문서 형식."""

    id: str
    title: str
    content: str
    content_vector: list[float]


Embedder = Callable[[list[str]], list[list[float]]]


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


def _validate_index(index: SearchIndex, index_name: str, dim: int) -> None:
    """기존 인덱스가 이 예제의 스키마와 호환되는지 확인합니다.

    Args:
        index: Azure AI Search에서 읽은 기존 인덱스.
        index_name: 검증할 인덱스 이름.
        dim: 현재 임베딩 모델의 벡터 차원.

    Raises:
        RuntimeError: 필수 필드나 벡터 설정이 호환되지 않을 때.
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

    if errors:
        details = "; ".join(errors)
        raise RuntimeError(
            f"기존 인덱스 '{index_name}'가 예제 스키마와 호환되지 않습니다: {details}. "
            "SEARCH_INDEX_NAME을 새 이름으로 바꾸거나 기존 인덱스를 정리한 뒤 다시 실행하세요."
        )


def ensure_index(index_client: SearchIndexClient, index_name: str, dim: int) -> None:
    """인덱스가 없으면 하이브리드 검색용 스키마로 생성합니다 (멱등).

    Args:
        index_client: Azure AI Search 인덱스 관리 클라이언트.
        index_name: 생성/확인할 인덱스 이름.
        dim: 벡터 필드 차원 (임베딩 모델 출력 차원).
    """
    try:
        existing_index = index_client.get_index(index_name)
    except ResourceNotFoundError:
        existing_index = None

    if existing_index is not None:
        _validate_index(existing_index, index_name, dim)
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
        profiles=[VectorSearchProfile(name="vprofile", algorithm_configuration_name="hnsw")],
    )

    index = SearchIndex(name=index_name, fields=fields, vector_search=vector_search)
    index_client.create_index(index)
    print(f"  → 인덱스 생성 완료: {index_name} (벡터 차원 {dim}, 코사인)")


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


async def seed_documents(search_client: SearchClient, embed: Embedder) -> None:
    """지식 베이스 문서를 임베딩하여 인덱스에 업로드합니다 (멱등 upsert).

    문서가 4건뿐이라 매 실행 시 새로 임베딩하여 덮어씁니다(내용 변경 자동 반영).
    업로드 후에는 인덱싱이 반영될 때까지 문서 내용을 폴링합니다
    (Azure AI Search는 최종 일관성이라 업로드 직후 검색이 비어 있을 수 있습니다).

    Args:
        search_client: 대상 인덱스의 SearchClient.
        embed: 텍스트 리스트를 임베딩 벡터로 변환하는 함수.
    """
    vectors = await asyncio.to_thread(embed, [doc["content"] for doc in KNOWLEDGE_BASE])
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

    results = await asyncio.to_thread(
        search_client.merge_or_upload_documents,
        documents=documents,
    )
    failed = [r for r in results if not r.succeeded]
    if failed:
        raise RuntimeError(f"문서 업로드 실패: {[r.key for r in failed]}")

    # 문서 수만 확인하면 기존 문서의 업데이트 반영 여부를 놓칠 수 있으므로
    # 키 조회 결과의 제목·본문·벡터가 최신 값인지 최대 30초 동안 확인합니다.
    for _ in range(30):
        if await asyncio.to_thread(_documents_are_indexed, search_client, documents):
            print(f"  → 문서 {len(KNOWLEDGE_BASE)}건 임베딩·업로드 완료")
            return
        await asyncio.sleep(1)
    raise TimeoutError("문서 업로드 후 30초 안에 최신 인덱싱 결과를 확인하지 못했습니다.")


def retrieve(
    search_client: SearchClient,
    embed: Embedder,
    query: str,
    top_k: int = 2,
) -> list[RetrievedDocument]:
    """하이브리드(키워드 + 벡터) 검색으로 관련 문서를 찾습니다.

    Args:
        search_client: 검색 대상 인덱스의 SearchClient.
        embed: 질문을 임베딩 벡터로 변환하는 함수.
        query: 사용자 질문.
        top_k: 반환할 상위 문서 수.

    Returns:
        관련도 높은 순으로 정렬된 문서 리스트(id/title/content/score).
    """
    query_vectors = embed([query])
    if not query_vectors or not query_vectors[0]:
        raise RuntimeError("질문 임베딩 모델이 빈 벡터를 반환했습니다.")
    query_vector = query_vectors[0]
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

    docs: list[RetrievedDocument] = []
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


def build_context(docs: list[RetrievedDocument]) -> str:
    """검색된 문서를 프롬프트에 넣을 컨텍스트 문자열로 만듭니다.

    Args:
        docs: 검색된 문서 목록.

    Returns:
        제목과 본문을 결합한 컨텍스트 문자열.
    """
    if not docs:
        return "(관련 문서를 찾지 못했습니다.)"
    blocks = [f"[{doc['title']}]\n{doc['content']}" for doc in docs]
    return "\n\n".join(blocks)


async def main() -> None:
    """Azure AI Search 기반 RAG 파이프라인을 구성하고 실행하는 메인 함수"""

    print("=== RAG 에이전트 (Azure AI Search) 실행 ===\n")

    # ── 1단계: 환경 변수 확인 ──
    project_endpoint = os.getenv("PROJECT_ENDPOINT")
    model = os.getenv("MODEL_DEPLOYMENT_NAME") or "gpt-5.4"
    search_endpoint = os.getenv("SEARCH_SERVICE_ENDPOINT")
    index_name = os.getenv("SEARCH_INDEX_NAME", "maf-lab-knowledge-v2")
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
        dimension_probe = await asyncio.to_thread(embed, ["차원 확인"])
        if not dimension_probe or not dimension_probe[0]:
            raise RuntimeError("임베딩 모델이 빈 벡터를 반환했습니다.")
        dim = len(dimension_probe[0])
        print(f"  → 임베딩 차원: {dim}")

        # ── 3단계: 인덱스 확인/생성 ──
        print("\n[2단계] Azure AI Search 인덱스 확인/생성...")
        index_client = SearchIndexClient(endpoint=search_endpoint, credential=credential)
        await asyncio.to_thread(ensure_index, index_client, index_name, dim)

        # ── 4단계: 문서 임베딩 및 업로드 ──
        print("\n[3단계] 지식 베이스 임베딩 및 업로드...")
        search_client = SearchClient(
            endpoint=search_endpoint,
            index_name=index_name,
            credential=credential,
        )
        await seed_documents(search_client, embed)

        # ── 5단계: 검색(Retrieval) ──
        question = "Pro 요금제는 얼마이고 기술 지원은 얼마나 빨리 받을 수 있나요?"
        print(f"\n[4단계] 하이브리드 검색 — 질문: {question}")
        docs = await asyncio.to_thread(retrieve, search_client, embed, question, 2)
        print("  → 검색된 문서:")
        for doc in docs:
            score = f"{doc['score']:.3f}" if doc["score"] is not None else "n/a"
            print(f"     - {doc['title']} ({doc['id']}, score={score})")
        context = build_context(docs)

        # ── 6단계: 증강(Augmentation) — 검색 결과를 프롬프트에 주입 ──
        augmented_prompt = (
            f"다음 참고 문서를 바탕으로 질문에 답하세요.\n\n"
            f"--- 참고 문서 ---\n{context}\n\n"
            f"--- 질문 ---\n{question}"
        )

        # ── 7단계: 생성(Generation) ──
        # 핵심: 검색된 컨텍스트 안에서만 답하도록 지시하여 환각(hallucination)을 줄입니다.
        client = FoundryChatClient(
            project_endpoint=project_endpoint,
            model=model,
            credential=credential,
        )
        agent = Agent(
            client=client,
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
    finally:
        credential.close()

    print("\n=== 실행 완료 ===")


if __name__ == "__main__":
    asyncio.run(main())
