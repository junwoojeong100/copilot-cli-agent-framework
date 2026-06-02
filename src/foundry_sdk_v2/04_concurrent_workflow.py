"""
[SDK v2] 실습 4: 동시(Concurrent) 워크플로우

에이전트를 **Foundry Agent SDK v2**로 생성하고, **MAF ``ConcurrentBuilder``**로
여러 전문가가 같은 입력을 동시에 검토하게 합니다.
보안, 성능, UX 리뷰어가 하나의 설계안을 각자 관점에서 병렬 평가합니다.

루트의 [`src/04_concurrent_workflow.py`](../04_concurrent_workflow.py)도 같은 동시
패턴이지만, 그쪽은 에이전트를 MAF ``FoundryChatClient``로 만듭니다. 이 예제는 SDK v2로
만든 에이전트가 Handoff를 제외한 MAF 오케스트레이션 전반과 호환됨을 보여 줍니다.
"""

import asyncio
import os
import sys

from dotenv import load_dotenv

# 공용 스트리밍 헬퍼(src/_streaming.py)와 프로젝트 루트(.env)를 참조하기 위한 경로 설정
_SRC_DIR = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, _SRC_DIR)
load_dotenv(dotenv_path=os.path.join(_SRC_DIR, "..", ".env"))

from agent_framework.orchestrations import ConcurrentBuilder
from azure.identity import AzureCliCredential

from _foundry_agents import FoundryAgentFactory
from _streaming import stream_workflow


async def main():
    """SDK v2 에이전트들을 MAF 동시 워크플로우로 실행하는 메인 함수"""

    print("=== [SDK v2] 동시 워크플로우 실행 ===\n")

    project_endpoint = os.getenv("PROJECT_ENDPOINT")
    model = os.getenv("MODEL_DEPLOYMENT_NAME", "gpt-5.4")

    if not project_endpoint:
        print("오류: PROJECT_ENDPOINT 환경 변수를 설정해주세요.")
        sys.exit(1)

    # ── 1단계: Foundry Agent SDK v2로 서버 측 에이전트 생성 ──
    factory = FoundryAgentFactory(project_endpoint, model, AzureCliCredential())

    try:
        security = factory.create(
            "security",
            instructions=(
                "당신은 보안 검토 전문가입니다. "
                "설계안의 보안 위험과 완화 방안을 핵심만 짚어 평가합니다. "
                "한국어로 작성합니다."
            ),
        )
        performance = factory.create(
            "performance",
            instructions=(
                "당신은 성능 검토 전문가입니다. "
                "설계안의 성능 병목과 확장성 개선점을 핵심만 짚어 평가합니다. "
                "한국어로 작성합니다."
            ),
        )
        ux = factory.create(
            "ux",
            instructions=(
                "당신은 UX 검토 전문가입니다. "
                "설계안의 사용성과 접근성 관점 개선점을 핵심만 짚어 평가합니다. "
                "한국어로 작성합니다."
            ),
        )

        name_map = {
            security.name: "보안 리뷰어",
            performance.name: "성능 리뷰어",
            ux.name: "UX 리뷰어",
        }

        # ── 2단계: Microsoft Agent Framework로 동시 워크플로우 구성·실행 ──
        await factory.enable_tracing()
        workflow = ConcurrentBuilder(
            participants=[security, performance, ux]
        ).build()

        design = (
            "신규 모바일 앱에 로그인 없이 게스트 결제를 허용하고, "
            "추천 데이터를 단말에 캐시하는 설계안을 검토해 주세요."
        )
        print(f"검토 대상 설계안: {design}\n")
        print("=" * 50)
        print("\n[동시 리뷰 결과]")
        await stream_workflow(workflow, design, name_map=name_map)

    except Exception as e:
        print(f"워크플로우 실행 중 오류 발생: {e}")
        sys.exit(1)
    finally:
        # ── 3단계: 생성한 서버 측 에이전트 정리 + 추적 플러시 ──
        factory.cleanup()
        factory.flush_tracing()

    print("\n=== 실행 완료 ===")


if __name__ == "__main__":
    asyncio.run(main())
