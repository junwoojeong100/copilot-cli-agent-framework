"""애플리케이션 추적(Tracing)·모니터링 설정 헬퍼.

Microsoft Agent Framework의 OpenTelemetry 계측을 켜고, 수집된 트레이스·메트릭·
로그를 Azure Monitor(Application Insights)로 전송합니다.

환경변수 ``APPLICATIONINSIGHTS_CONNECTION_STRING``이 설정돼 있을 때만 활성화되며,
없으면 조용히 건너뛰어 예제가 그대로 동작하도록 합니다. 따라서 모든 예제의
``main()`` 시작 부분에서 부담 없이 호출할 수 있습니다.
"""

from __future__ import annotations

import os

# 중복 초기화 방지(여러 번 호출돼도 한 번만 설정)
_CONFIGURED = False


def setup_observability(*, enable_sensitive_data: bool = True) -> bool:
    """추적·모니터링을 활성화한다.

    ``APPLICATIONINSIGHTS_CONNECTION_STRING`` 환경변수가 있으면 Azure Monitor
    익스포터를 전역 OpenTelemetry 프로바이더에 등록하고, Agent Framework 계측을
    켜서 에이전트·모델·도구 호출이 트레이스로 기록되도록 합니다.

    Args:
        enable_sensitive_data: 프롬프트·응답 등 메시지 본문을 트레이스에 포함할지
            여부. 개발·실습에는 편리하지만, 운영 환경에서는 민감정보 노출을 막기
            위해 ``False``를 권장합니다.

    Returns:
        활성화되면 ``True``, connection string이 없어 건너뛰면 ``False``.
    """
    global _CONFIGURED
    if _CONFIGURED:
        return True

    connection_string = os.getenv("APPLICATIONINSIGHTS_CONNECTION_STRING")
    if not connection_string:
        return False

    # Azure Monitor(Application Insights) OTel 익스포터를 전역 프로바이더에 등록
    from azure.monitor.opentelemetry import configure_azure_monitor

    configure_azure_monitor(connection_string=connection_string)

    # Agent Framework 계측 활성화 → 에이전트·모델·도구 호출이 트레이스로 기록됨
    from agent_framework.observability import enable_instrumentation

    enable_instrumentation(enable_sensitive_data=enable_sensitive_data)

    _CONFIGURED = True
    return True
