"""
[SDK v2] 실습 2: 순차(Sequential) 워크플로우

에이전트를 **Foundry Agent SDK v2**로 생성하고, **MAF ``SequentialBuilder``**로
순차 파이프라인을 구성해 실행합니다.

워크플로우: [분석가] → [작가] → [편집자]
  - 분석가: 주제를 분석해 핵심 논점을 정리합니다.
  - 작가: 분석을 바탕으로 글 초안을 작성합니다.
  - 편집자: 초안을 다듬어 최종본을 만듭니다.

루트의 [`src/02_sequential_workflow.py`](../02_sequential_workflow.py)도 같은 순차
패턴이지만, 그쪽은 에이전트를 MAF ``FoundryChatClient``로 만든다는 점이 다릅니다.
이 예제는 동일한 워크플로우를 **SDK v2로 생성한 서버 측 에이전트**로 구성합니다.
"""

import asyncio
import os
import sys

from dotenv import load_dotenv

# 공용 스트리밍 헬퍼(src/_streaming.py)와 프로젝트 루트(.env)를 참조하기 위한 경로 설정
_SRC_DIR = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, _SRC_DIR)
load_dotenv(dotenv_path=os.path.join(_SRC_DIR, "..", ".env"))

from agent_framework.orchestrations import SequentialBuilder
from azure.identity import AzureCliCredential

from _foundry_agents import FoundryAgentFactory
from _streaming import stream_workflow


async def main():
    """SDK v2 에이전트들을 MAF 순차 워크플로우로 실행하는 메인 함수"""

    print("=== [SDK v2] 순차 워크플로우 실행 ===\n")

    project_endpoint = os.getenv("PROJECT_ENDPOINT")
    model = os.getenv("MODEL_DEPLOYMENT_NAME", "gpt-5.4")

    if not project_endpoint:
        print("오류: PROJECT_ENDPOINT 환경 변수를 설정해주세요.")
        sys.exit(1)

    # ── 1단계: Foundry Agent SDK v2로 서버 측 에이전트 생성 ──
    factory = FoundryAgentFactory(project_endpoint, model, AzureCliCredential())

    try:
        analyzer = factory.create(
            "analyzer",
            instructions=(
                "당신은 콘텐츠 주제 분석가입니다. "
                "주어진 주제의 핵심 논점 3가지를 뽑아 간결히 정리합니다. "
                "한국어로 작성합니다."
            ),
        )
        writer = factory.create(
            "writer",
            instructions=(
                "당신은 기술 콘텐츠 작가입니다. "
                "앞 단계의 분석을 바탕으로 400자 이내의 글 초안을 작성합니다. "
                "한국어로 작성합니다."
            ),
        )
        editor = factory.create(
            "editor",
            instructions=(
                "당신은 시니어 편집자입니다. "
                "앞 단계의 초안을 검토해 논리적 흐름과 가독성을 개선한 최종본을 작성합니다. "
                "한국어로 작성합니다."
            ),
        )

        # 표시 이름 매핑(executor_id → 한국어 라벨)
        name_map = {
            analyzer.name: "분석가",
            writer.name: "작가",
            editor.name: "편집자",
        }

        # ── 2단계: Microsoft Agent Framework로 순차 워크플로우 구성·실행 ──
        await factory.enable_tracing()
        workflow = SequentialBuilder(participants=[analyzer, writer, editor]).build()

        topic = "Kubernetes 클러스터 비용 최적화 전략"
        print(f"입력 주제: {topic}\n")
        print("=" * 50)
        print("\n[순차 파이프라인 결과]")
        await stream_workflow(workflow, topic, name_map=name_map)

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
