"""[Hosted Agent] 실습 6: RAG 에이전트를 Foundry Hosted Agent로 배포

기존 ``src/06_rag_agent.py``의 RAG(검색 증강 생성) 로직을 Hosted Agent로 호스팅합니다.

기존 예제는 "검색 → 증강 → 생성"을 한 번에 수행하지만, 호스팅 환경에서는
대화형으로 동작해야 하므로 **하이브리드 검색을 함수 도구(tool)로 노출**합니다.
에이전트(LLM)는 질문을 받으면 스스로 ``search_knowledge_base`` 도구를 호출해
관련 문서를 검색(Retrieval)하고, 그 내용을 컨텍스트로 받아(Augmentation)
근거 기반으로 답변(Generation)합니다.

전제: 검색 인덱스가 이미 시드되어 있어야 합니다.
      저장소의 ``src/06_rag_agent.py`` 를 한 번 실행하면 동일한 인덱스
      (기본값 ``maf-lab-knowledge-v1``)가 생성·시드됩니다.
"""

import os
from typing import Annotated

from agent_framework import Agent
from agent_framework.foundry import FoundryChatClient
from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from azure.search.documents import SearchClient
from azure.search.documents.models import VectorizedQuery
from openai import AzureOpenAI

from agent_framework_foundry_hosting import ResponsesHostServer
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
SEARCH_ENDPOINT = os.getenv("SEARCH_SERVICE_ENDPOINT")
INDEX_NAME = os.getenv("SEARCH_INDEX_NAME", "maf-lab-knowledge-v1")
AOAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
EMBEDDING_DEPLOYMENT = os.getenv("EMBEDDING_DEPLOYMENT_NAME", "text-embedding-3-large")
AOAI_API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION", "2024-10-21")


def make_embedder(endpoint: str, deployment: str, api_version: str, credential):
    """Azure OpenAI 임베딩 호출 함수를 생성합니다 (키리스 AAD 인증).

    Args:
        endpoint: Azure OpenAI 엔드포인트.
        deployment: 임베딩 모델 배포 이름.
        api_version: Azure OpenAI API 버전.
        credential: 토큰 자격 증명.

    Returns:
        텍스트 리스트를 임베딩 벡터 리스트로 변환하는 함수.
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
        response = client.embeddings.create(model=deployment, input=texts)
        return [item.embedding for item in response.data]

    return embed


def main():
    """RAG 검색 도구를 가진 에이전트를 Responses 프로토콜로 호스팅하는 메인 함수"""

    if not PROJECT_ENDPOINT:
        raise SystemExit(
            "오류: FOUNDRY_PROJECT_ENDPOINT(또는 PROJECT_ENDPOINT) 환경 변수를 설정해주세요."
        )
    if not SEARCH_ENDPOINT:
        raise SystemExit("오류: SEARCH_SERVICE_ENDPOINT 환경 변수를 설정해주세요.")
    if not AOAI_ENDPOINT:
        raise SystemExit("오류: AZURE_OPENAI_ENDPOINT 환경 변수를 설정해주세요.")

    # ── 1단계: 공용 자격 증명 + 검색/임베딩 클라이언트 준비 ──
    # 컨테이너에서는 전용 관리 ID, 로컬에서는 az login 세션으로 인증됩니다.
    credential = DefaultAzureCredential()
    embed = make_embedder(AOAI_ENDPOINT, EMBEDDING_DEPLOYMENT, AOAI_API_VERSION, credential)
    search_client = SearchClient(
        endpoint=SEARCH_ENDPOINT, index_name=INDEX_NAME, credential=credential
    )

    # ── 2단계: 하이브리드 검색을 함수 도구로 정의 ──
    # 에이전트가 필요하다고 판단하면 이 도구를 스스로 호출합니다.
    def search_knowledge_base(
        query: Annotated[str, "지식 베이스에서 찾을 검색어/질문"],
    ) -> str:
        """지식 베이스에서 질문과 관련된 문서를 하이브리드(키워드+벡터) 검색합니다.

        Args:
            query: 사용자 질문 또는 검색어.

        Returns:
            관련 문서들을 합친 컨텍스트 문자열(제목 + 본문). 없으면 안내 문구.
        """
        query_vector = embed([query])[0]
        vector_query = VectorizedQuery(
            vector=query_vector, k=5, fields="content_vector"
        )
        results = search_client.search(
            search_text=query,
            vector_queries=[vector_query],
            select=["id", "title", "content"],
            top=3,
        )
        blocks = [f"[{r['title']}]\n{r['content']}" for r in results]
        return "\n\n".join(blocks) if blocks else "(관련 문서를 찾지 못했습니다.)"

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
            "사용자 질문에 답하기 전에 반드시 search_knowledge_base 도구로 관련 문서를 검색하세요. "
            "검색된 '참고 문서' 안의 정보만 근거로 한국어로 답변하고, "
            "문서에 없는 내용은 추측하지 말고 '관련 정보를 찾을 수 없습니다'라고 답하세요. "
            "답변 끝에 근거가 된 문서 제목을 [출처: ...] 형식으로 표시하세요."
        ),
        tools=[search_knowledge_base],
        default_options={"store": False},
    )

    # ── 4단계: Responses 프로토콜 서버로 호스팅 ──
    server = ResponsesHostServer(agent)
    server.run()


if __name__ == "__main__":
    main()
