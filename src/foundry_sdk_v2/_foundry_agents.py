"""Foundry Agent SDK v2 에이전트 수명주기 헬퍼.

이 모듈은 **Microsoft Foundry Agent SDK v2**(``azure-ai-projects``)로 서버 측
영속(persistent) 에이전트를 생성하고, 이를 **Microsoft Agent Framework(MAF)**
워크플로우에서 바로 사용할 수 있는 ``FoundryAgent``로 감싸 줍니다.

설계 핵심 — 역할 분리:
  - 에이전트 "생성"은 Foundry Agent SDK v2(``AIProjectClient``)가 담당합니다.
  - 에이전트 "오케스트레이션"은 MAF 빌더(Sequential/GroupChat/Concurrent)가 담당합니다.

실행마다 고유한 이름으로 에이전트를 만들고, 끝나면 ``cleanup()``으로 모두
삭제(베스트 에포트)하여 Foundry 프로젝트에 에이전트가 누적되지 않게 합니다.
"""

import uuid

from agent_framework.foundry import FoundryAgent
from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import PromptAgentDefinition


class FoundryAgentFactory:
    """SDK v2로 영속 에이전트를 생성하고 MAF ``FoundryAgent``로 감싸는 팩토리.

    같은 실행 안에서 생성한 에이전트 이름을 추적해 두었다가 ``cleanup()``으로
    한 번에 삭제합니다. 이름 충돌을 막기 위해 실행마다 고유 접미사를 붙입니다.
    """

    def __init__(self, project_endpoint: str, model: str, credential):
        """팩토리를 초기화합니다.

        Args:
            project_endpoint: Foundry 프로젝트 엔드포인트(``PROJECT_ENDPOINT``).
            model: 에이전트가 사용할 배포 모델 이름.
            credential: 키리스 인증용 자격 증명(``AzureCliCredential``).
        """
        self._endpoint = project_endpoint
        self._model = model
        self._credential = credential
        self._client = AIProjectClient(endpoint=project_endpoint, credential=credential)
        # 실행마다 고유 → 동시 실행/재실행 시 이름 충돌 및 오삭제 방지
        self._run_id = uuid.uuid4().hex[:8]
        self._created: list[str] = []

    def create(self, slug: str, instructions: str, *, tools=None) -> FoundryAgent:
        """SDK v2로 에이전트를 생성하고 MAF ``FoundryAgent``로 감싸 반환합니다.

        Args:
            slug: 에이전트 식별 슬러그(영문, 예: ``"analyzer"``).
            instructions: 에이전트 역할 지시사항(한국어).
            tools: 에이전트에 부여할 도구 목록(선택).

        Returns:
            MAF 워크플로우에 바로 넣을 수 있는 ``FoundryAgent`` 인스턴스.
        """
        agent_name = f"maf-sdkv2-{slug}-{self._run_id}"

        # 1단계: Foundry Agent SDK v2로 서버 측 에이전트(버전) 생성
        version = self._client.agents.create_version(
            agent_name=agent_name,
            definition=PromptAgentDefinition(
                model=self._model,
                instructions=instructions,
                tools=tools,
            ),
        )
        self._created.append(agent_name)

        # 2단계: 생성한 영속 에이전트를 MAF FoundryAgent로 래핑
        return FoundryAgent(
            project_endpoint=self._endpoint,
            agent_name=agent_name,
            agent_version=str(version.version),
            credential=self._credential,
        )

    def cleanup(self) -> None:
        """이 실행에서 생성한 에이전트를 모두 삭제합니다(베스트 에포트).

        정리 중 오류는 출력만 하고 무시하여, 본 실행에서 발생한 실제 오류를
        가리지 않도록 합니다.
        """
        for name in self._created:
            try:
                self._client.agents.delete(name)
            except Exception as exc:  # 정리 실패가 본 오류를 덮지 않도록
                print(f"  (정리 경고) 에이전트 '{name}' 삭제 실패: {exc}")
        self._created.clear()
        try:
            self._client.close()
        except Exception:
            pass
