# (심화) Foundry Agent SDK v2 + MAF 오케스트레이션

> 에이전트 "생성"은 Microsoft Foundry Agent SDK v2가, "오케스트레이션"은 MAF 워크플로우 빌더가
> 맡는 분리 구조를 보여주는 심화 가이드입니다.

---

실습 01~06은 에이전트를 **MAF `FoundryChatClient`(모델 채팅)** 로 구성합니다. 이 심화
세트는 **에이전트 "생성"은 Microsoft Foundry Agent SDK v2(`azure-ai-projects`)** 가
맡고, **에이전트 "오케스트레이션"은 MAF 워크플로우 빌더**가 맡는 분리 구조를 보여
줍니다. 기존 소스(01~06)는 그대로 두고, 가이드·의존성도 분리했습니다.

> 위치: [`src/foundry_sdk_v2/`](../src/foundry_sdk_v2/) · 의존성: `requirements-foundry-sdk-v2.txt`

## 핵심 패턴 — 생성은 SDK v2, 실행은 MAF

```python
# 1단계: Foundry Agent SDK v2로 서버 측 영속 에이전트 생성
from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import PromptAgentDefinition

pc = AIProjectClient(endpoint=PROJECT_ENDPOINT, credential=AzureCliCredential())
version = pc.agents.create_version(
    agent_name="maf-sdkv2-analyzer-ab12cd34",
    definition=PromptAgentDefinition(model=MODEL, instructions="...", tools=None),
)

# 2단계: 생성한 영속 에이전트를 MAF FoundryAgent로 래핑
from agent_framework.foundry import FoundryAgent
analyzer = FoundryAgent(
    project_endpoint=PROJECT_ENDPOINT,
    agent_name="maf-sdkv2-analyzer-ab12cd34",
    agent_version=str(version.version),
    credential=AzureCliCredential(),
)

# 3단계: MAF 워크플로우 빌더로 오케스트레이션
from agent_framework.orchestrations import SequentialBuilder
workflow = SequentialBuilder(participants=[analyzer, writer, editor]).build()
```

생성·정리 로직은 [`src/foundry_sdk_v2/_foundry_agents.py`](../src/foundry_sdk_v2/_foundry_agents.py)의
`FoundryAgentFactory`로 모았습니다. 실행마다 고유 이름으로 에이전트를 만들고,
`finally`에서 `cleanup()`으로 삭제(베스트 에포트)해 프로젝트에 누적되지 않습니다.

## 예제 목록 / 실행

```bash
pip install -r requirements-foundry-sdk-v2.txt   # 최초 1회 (오버레이 설치)
cd src/foundry_sdk_v2

python 01_single_agent.py        # 단일 에이전트 (스트리밍)
python 02_sequential_workflow.py # 순차: 분석가 → 작가 → 편집자 (SequentialBuilder)
python 03_group_chat.py          # 협업 토론: 기획자·개발자·디자이너 (GroupChatBuilder)
python 04_concurrent_workflow.py # 동시 리뷰: 보안·성능·UX (ConcurrentBuilder)
python 05_mcp_agent.py           # MCP 도구 연동 (서버 측 MCPTool, Microsoft Learn)
python 06_rag_agent.py           # RAG (Azure AI Search 검색 + SDK v2 생성)
python 06_rag_agent_foundry_iq.py # RAG 변형 (Foundry IQ 지식 베이스 + SDK v2 생성)
```

각 예제는 시작 시 SDK v2로 에이전트를 만들고, MAF로 실행한 뒤, 끝나면 생성한
에이전트를 삭제합니다. 출력은 공용 헬퍼 [`src/_streaming.py`](../src/_streaming.py)로
스트리밍 표시합니다.

## MCP·RAG 연동 — 도구/데이터 결합

오케스트레이션(02~04)과 별개로, SDK v2 에이전트도 **외부 도구(MCP)** 와
**외부 데이터(RAG)** 에 연결할 수 있습니다.

- **05 MCP** — `azure.ai.projects.models.MCPTool`로 **서버 측 MCP 도구**를 붙입니다.
  Foundry 서비스가 직접 MCP 서버(`https://learn.microsoft.com/api/mcp`)를 호출하므로
  로컬 함수 호출이 필요 없습니다. 기존 [`src/05_mcp_agent.py`](../src/05_mcp_agent.py)의
  **클라이언트 측** `MCPStreamableHTTPTool`(로컬에서 도구 실행)과 대비됩니다.

  | 구분 | 클라이언트 측(루트 05) | 서버 측(SDK v2 05) |
  |------|----------------------|--------------------|
  | 도구 호출 주체 | 로컬 프로세스 | Foundry 서비스 |
  | 클래스 | `MCPStreamableHTTPTool` | `MCPTool` |
  | 승인 | 로컬 제어 | `require_approval="never"` |

  > 서버 측 MCP가 막히는 환경(승인 정책·네트워크)에서는 루트 05의 클라이언트 측
  > 방식으로 폴백하세요.

- **06 RAG** — 검색·증강은 Azure AI Search 하이브리드 검색
  ([`_rag_search.py`](../src/foundry_sdk_v2/_rag_search.py), 루트 06과 동일 로직),
  **생성 단계만 SDK v2 에이전트**가 담당합니다. 전 과정 키리스로 동작합니다.
  v2 네이티브 `AzureAISearchTool`(서버 측 검색)은 프로젝트에 Search 연결+인덱스
  등록이 필요해 이 예제에서는 사용하지 않습니다.

- **06 RAG 변형 (Foundry IQ)** — [`06_rag_agent_foundry_iq.py`](../src/foundry_sdk_v2/06_rag_agent_foundry_iq.py)는
  검색을 **Foundry IQ 지식 베이스(agentic retrieval)** 에 위임합니다. SDK v2 `FoundryAgent`에
  `AzureAISearchContextProvider`(agentic 모드)를 `context_providers`로 연결하면, 에이전트가
  질문마다 멀티홉 검색을 수행하고 결과를 컨텍스트로 자동 주입합니다. 인덱스 시드·프로바이더는
  저장소 공용 헬퍼 [`_rag_iq.py`](../src/_rag_iq.py)를 사용합니다.
  > 요구사항: Azure AI Search semantic ranker 활성화 + agentic 지원 리전(루트 README 1.2 참고).
  > 비동기 Search 클라이언트를 쓰므로 프로바이더에는 `azure.identity.aio` 자격 증명을 전달합니다.

## Application Insights 분산 추적 (트레이싱)

SDK v2 예제는 모두 시작 시 `factory.enable_tracing()`을 호출해 실행 스팬을
**Azure Monitor(Application Insights)** 로 전송합니다. 추적에는 **세 요소**가 모두
필요합니다.

1. Application Insights 리소스
2. Foundry **프로젝트의 `AppInsights` 연결**
3. `azure-monitor-opentelemetry` 패키지(오버레이에 포함)

```bash
# 1) Log Analytics 워크스페이스 + Application Insights 생성
az monitor log-analytics workspace create -g rg-maf-lab -n law-maflab -l eastus2
LAW_ID=$(az monitor log-analytics workspace show -g rg-maf-lab -n law-maflab --query id -o tsv)
az monitor app-insights component create --app appi-maflab -g rg-maf-lab -l eastus2 \
  --workspace "$LAW_ID"
APPI_ID=$(az monitor app-insights component show --app appi-maflab -g rg-maf-lab --query id -o tsv)
CONN=$(az monitor app-insights component show --app appi-maflab -g rg-maf-lab \
  --query connectionString -o tsv)

# 2) Foundry 프로젝트에 AppInsights 연결 생성
az resource create \
  --id "/subscriptions/<SUB>/resourceGroups/rg-maf-lab/providers/Microsoft.CognitiveServices/accounts/<ACCOUNT>/projects/<PROJECT>/connections/appinsights" \
  --api-version 2025-06-01 \
  --properties "{\"category\":\"AppInsights\",\"target\":\"$APPI_ID\",\"authType\":\"ApiKey\",\"isSharedToAll\":true,\"credentials\":{\"key\":\"$CONN\"},\"metadata\":{\"ApiType\":\"Azure\",\"ResourceId\":\"$APPI_ID\"}}"
```

`FoundryAgent.configure_azure_monitor()`가 프로젝트의 AppInsights 연결에서 연결
문자열을 자동으로 가져와 OpenTelemetry를 구성합니다. 짧은 프로세스에서 스팬이
유실되지 않도록 각 예제는 `finally`에서 `factory.flush_tracing()`을 호출합니다.

- **끄기**: `.env`에 `ENABLE_TRACING=false`를 두면 추적을 건너뜁니다.
- **연결 미설정 시**: 친절한 경고만 출력하고 예제는 정상 실행됩니다(추적만 비활성).
- **보기**: Azure Portal의 Application Insights → *Transaction search* / *Logs*
  (`traces`, `dependencies`)에서 확인합니다. 스팬은 도착까지 **1~2분** 지연될 수
  있습니다. Foundry 포털의 *Tracing* 탭에서도 볼 수 있습니다.
