"""Foundry Agent SDK v2 에이전트 수명주기 헬퍼.

이 모듈은 **Microsoft Foundry Agent SDK v2**(``azure-ai-projects``)로 서버 측
영속(persistent) 에이전트를 생성하고, 이를 **Microsoft Agent Framework(MAF)**
워크플로우에서 바로 사용할 수 있는 ``FoundryAgent``로 감싸 줍니다.

설계 핵심 — 역할 분리:
  - 에이전트 "생성"은 Foundry Agent SDK v2(``AIProjectClient``)가 담당합니다.
  - 에이전트 "오케스트레이션"은 MAF 빌더(Sequential/GroupChat/Concurrent)가 담당합니다.

실행마다 고유한 이름으로 에이전트를 만들고, 끝나면 ``cleanup()``으로 모두
삭제(베스트 에포트)하여 Foundry 프로젝트에 에이전트가 누적되지 않게 합니다.

또한 ``enable_tracing()``으로 Azure Monitor(Application Insights) 분산 추적을
켜서, 에이전트·워크플로우 실행 과정을 OpenTelemetry 스팬으로 수집할 수 있습니다.
"""

import os
import uuid

from agent_framework.foundry import FoundryAgent
from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import PromptAgentDefinition

# 프로세스 전역 추적 설정은 한 번만 수행합니다(스팬 중복 방지).
_TRACING_CONFIGURED = False


def _tracing_enabled_by_env() -> bool:
    """``ENABLE_TRACING`` 환경 변수로 추적 활성화 여부를 결정합니다(기본값 True)."""
    return os.getenv("ENABLE_TRACING", "true").strip().lower() not in ("false", "0", "no")


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
        self._agents: list[FoundryAgent] = []

    def create(self, slug: str, instructions: str, *, tools=None, context_providers=None) -> FoundryAgent:
        """SDK v2로 에이전트를 생성하고 MAF ``FoundryAgent``로 감싸 반환합니다.

        Args:
            slug: 에이전트 식별 슬러그(영문, 예: ``"analyzer"``).
            instructions: 에이전트 역할 지시사항(한국어).
            tools: 에이전트에 부여할 도구 목록(선택).
            context_providers: MAF 컨텍스트 프로바이더 목록(선택). 예: Foundry IQ
                agentic 검색 프로바이더. ``before_run`` 훅에서 검색 결과를 주입합니다.

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
        agent = FoundryAgent(
            project_endpoint=self._endpoint,
            agent_name=agent_name,
            agent_version=str(version.version),
            credential=self._credential,
            context_providers=context_providers,
        )
        self._agents.append(agent)
        return agent

    async def enable_tracing(self, *, enable_sensitive_data: bool = False) -> bool:
        """Azure Monitor(Application Insights) 분산 추적을 활성화합니다.

        Foundry 프로젝트에 연결된 Application Insights의 연결 문자열을 자동으로
        가져와 OpenTelemetry → Azure Monitor 파이프라인을 구성합니다. 전역 설정이라
        한 번만 호출하면 이후 모든 에이전트·워크플로우 실행이 추적됩니다.

        먼저 에이전트를 하나 이상 ``create()`` 한 뒤 호출해야 합니다.

        Args:
            enable_sensitive_data: 프롬프트·응답 등 민감 데이터까지 스팬에 기록할지
                여부. 개발/테스트 환경에서만 켜는 것을 권장합니다. 기본값 False.

        Returns:
            추적이 구성되면 True, 비활성화/미연결/패키지 누락이면 False.
        """
        global _TRACING_CONFIGURED

        if not _tracing_enabled_by_env():
            print("  (추적) ENABLE_TRACING=false → 추적 비활성화")
            return False
        if _TRACING_CONFIGURED:
            return True
        if not self._agents:
            print("  (추적) 활성화할 에이전트가 없습니다. create() 후 호출하세요.")
            return False

        try:
            # FoundryAgent.configure_azure_monitor: 프로젝트의 App Insights 연결
            # 문자열을 가져와 configure_azure_monitor()와 계측을 설정합니다.
            await self._agents[0].configure_azure_monitor(enable_sensitive_data=enable_sensitive_data)
        except ImportError:
            print(
                "  (추적) azure-monitor-opentelemetry 미설치 → 추적 건너뜀.\n"
                "         pip install -r requirements-foundry-sdk-v2.txt 로 설치하세요."
            )
            return False
        except Exception as exc:  # App Insights 미연결 등은 추적 없이 계속 진행
            print(f"  (추적) 설정 실패 → 추적 없이 계속: {exc}")
            return False

        _TRACING_CONFIGURED = True
        print("  ✓ Azure Monitor 추적 활성화 (Application Insights로 스팬 전송)")
        return True

    def flush_tracing(self, timeout_millis: int = 5000) -> None:
        """수집된 스팬을 Application Insights로 강제 전송합니다(베스트 에포트).

        예제는 실행 직후 종료되므로, 짧은 프로세스에서 스팬 유실을 막기 위해
        종료 전에 한 번 플러시합니다.
        """
        if not _TRACING_CONFIGURED:
            return
        try:
            from opentelemetry import trace

            provider = trace.get_tracer_provider()
            if hasattr(provider, "force_flush"):
                provider.force_flush(timeout_millis=timeout_millis)
        except Exception:
            pass

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
        self._agents.clear()
        try:
            self._client.close()
        except Exception:
            pass
