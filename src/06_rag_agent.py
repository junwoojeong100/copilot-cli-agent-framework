"""
실습 6: RAG (검색 증강 생성) 에이전트
지식 베이스에서 질문과 관련된 문서를 먼저 검색(Retrieval)하고,
그 내용을 컨텍스트로 주입하여 에이전트가 근거 기반으로 답변(Generation)하게 합니다.

  [질문] → [1.검색: 관련 문서 추출] → [2.증강: 컨텍스트 주입] → [3.생성: 에이전트 답변]

이 예제는 외부 인프라 없이 바로 실행되도록 **인메모리 지식 베이스 + 키워드 검색**을
사용합니다. 운영 환경에서는 이 검색 단계를 Azure AI Search(Foundry IQ)나
벡터 데이터베이스로 교체하면 됩니다 (가이드의 'RAG 확장' 절 참고).
"""

import asyncio
import os
import re
import sys

from dotenv import load_dotenv

# 프로젝트 루트의 .env 파일 로드
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", ".env"))

from agent_framework import Agent
from agent_framework.foundry import FoundryChatClient
from azure.identity import AzureCliCredential


# ── 인메모리 지식 베이스 ──
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


def tokenize(text: str) -> set:
    """텍스트를 소문자 단어 집합으로 변환합니다 (간단한 토크나이저)."""
    return set(re.findall(r"[0-9A-Za-z가-힣]+", text.lower()))


def retrieve(query: str, top_k: int = 2) -> list:
    """질문과 가장 관련 있는 문서를 키워드 겹침 점수로 검색합니다.

    Args:
        query: 사용자 질문.
        top_k: 반환할 상위 문서 수.

    Returns:
        점수가 높은 순으로 정렬된 문서 리스트.
    """
    query_tokens = tokenize(query)
    scored = []
    for doc in KNOWLEDGE_BASE:
        doc_tokens = tokenize(doc["title"] + " " + doc["content"])
        # 질문 단어와 문서 단어의 겹침 개수를 관련도 점수로 사용
        score = len(query_tokens & doc_tokens)
        if score > 0:
            scored.append((score, doc))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [doc for _, doc in scored[:top_k]]


def build_context(docs: list) -> str:
    """검색된 문서들을 프롬프트에 넣을 컨텍스트 문자열로 만듭니다."""
    if not docs:
        return "(관련 문서를 찾지 못했습니다.)"
    blocks = [f"[{doc['title']}]\n{doc['content']}" for doc in docs]
    return "\n\n".join(blocks)


async def main():
    """RAG 파이프라인을 구성하고 실행하는 메인 함수"""

    print("=== RAG 에이전트 실행 ===\n")

    # ── 1단계: Foundry Chat 클라이언트 설정 ──
    project_endpoint = os.getenv("PROJECT_ENDPOINT")
    model = os.getenv("MODEL_DEPLOYMENT_NAME", "gpt-4o")

    if not project_endpoint:
        print("오류: PROJECT_ENDPOINT 환경 변수를 설정해주세요.")
        sys.exit(1)

    client = FoundryChatClient(
        project_endpoint=project_endpoint,
        model=model,
        credential=AzureCliCredential(),
    )

    # ── 2단계: 에이전트 생성 ──
    # 핵심: 지식 베이스의 컨텍스트 안에서만 답하도록 지시하여 환각(hallucination)을 줄입니다.
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

    question = "Pro 요금제는 얼마이고 기술 지원은 얼마나 빨리 받을 수 있나요?"
    print(f"질문: {question}\n")

    try:
        # ── 3단계: 검색(Retrieval) ──
        docs = retrieve(question, top_k=2)
        print("검색된 문서:")
        for doc in docs:
            print(f"  - {doc['title']} ({doc['id']})")
        context = build_context(docs)

        # ── 4단계: 증강(Augmentation) — 검색 결과를 프롬프트에 주입 ──
        augmented_prompt = (
            f"다음 참고 문서를 바탕으로 질문에 답하세요.\n\n"
            f"--- 참고 문서 ---\n{context}\n\n"
            f"--- 질문 ---\n{question}"
        )

        # ── 5단계: 생성(Generation) ──
        print("\n에이전트가 답변 생성 중...")
        result = await agent.run(augmented_prompt)

        print("\n에이전트 응답:")
        print(result)

    except Exception as e:
        print(f"RAG 실행 중 오류 발생: {e}")
        sys.exit(1)

    print("\n=== 실행 완료 ===")


if __name__ == "__main__":
    asyncio.run(main())
