# Microsoft Agent Framework 핸즈온 랩 (Python · Microsoft Foundry)

> **Microsoft Foundry 기반의 Microsoft Agent Framework로 멀티 에이전트(+ MCP 도구 연동 · RAG)를
> Python으로 단계별로 직접 만들어보는 자체 완결형 핸즈온 랩.**

이 문서는 `src/`의 핵심 6가지 Agent Framework 예제(4가지 멀티 에이전트 패턴 + MCP 도구 연동 + RAG, 06번은 하이브리드·Foundry IQ 2가지 변형 포함, 총 7개 스크립트)를
다룹니다. 각 예제는 Python으로 작성되어 `FoundryChatClient`로 Microsoft Foundry에 연결하며, 루트에는
에이전트 공통 가드레일 `AGENTS.md`가 있습니다.

> **전제 지식**: Python 기초와 `async/await` 개념, 터미널(명령줄) 사용, 결제 가능한 **Azure 구독** 보유.
> 처음이라면 **Part 1(사전 준비)부터 순서대로** 진행한 뒤 Part 2부터 예제를 하나씩 실행하는 것을 권장합니다.

---

## 이 문서를 읽는 순서 (학습 경로)

아래 Part는 **순서대로 진행**하도록 구성되어 있습니다. Part 1에서 환경을 준비한 뒤,
Part 2부터 예제를 하나씩 실행하며 단계적으로 확장하세요.

| 대상 | 권장 범위 |
|------|-----------|
| 🟢 **처음 시작하는 분** | **Part 1 → Part 2 → … → Part 7** (단일 에이전트부터 RAG까지 핵심 6가지 예제 `01`~`06`, 06번은 2가지 변형) |
| 🔴 **배포까지** | 위 + **Part 8** (Microsoft Foundry Hosted Agent (Hosted Agent) 배포 — 예제별 배포·원격 테스트) |

---

## 목차

- [Part 0. 전체 그림](#part-0-전체-그림)
- [Part 1. 사전 준비](#part-1-사전-준비)
- [Part 2. 단일 에이전트](#part-2-단일-에이전트)
- [Part 3. 순차(Sequential) 워크플로우](#part-3-순차sequential-워크플로우)
- [Part 4. GroupChat 워크플로우](#part-4-groupchat-워크플로우)
- [Part 5. 동시(Concurrent) 워크플로우](#part-5-동시concurrent-워크플로우)
- [Part 6. MCP 도구 연동 에이전트](#part-6-mcp-도구-연동-에이전트)
- [Part 7. RAG — 검색 증강 생성](#part-7-rag--검색-증강-생성)
- [Part 8. Hosted Agent 배포 — MAF 에이전트·워크플로우를 관리형으로](#part-8-hosted-agent-배포--maf-에이전트워크플로우를-관리형으로)
- [부록 A. 트러블슈팅](#부록-a-트러블슈팅)
- [부록 B. 참고 자료](#부록-b-참고-자료)

---

## 프로젝트 구조

```
.
├── README.md                       # 이 가이드
├── AGENTS.md                       # 에이전트 공통 가드레일 (push 금지·영문 커밋·PR 규칙)
├── requirements.txt                # Python 의존성 (예제 01~06)
├── .env.example                    # 환경변수 템플릿
├── .github/
│   ├── copilot-instructions.md     # 프로젝트 전역 인스트럭션
│   ├── instructions/               # python · azure · korean · git-commit 규칙
│   ├── skills/
│   │   └── agent-framework-codegen/SKILL.md   # MAF 코드 생성 패턴
│   └── workflows/
│       └── smoke.yml               # 예제 스크립트 바이트컴파일 스모크 CI
└── src/                            # Microsoft Agent Framework 예제
    ├── 01_single_agent.py          # 단일 에이전트
    ├── 02_sequential_workflow.py   # 순차 (분석가→작가→편집자)
    ├── 03_group_chat.py            # GroupChat (다중 협업)
    ├── 04_concurrent_workflow.py   # 동시 (보안·성능·UX 병렬 검토)
    ├── 05_mcp_agent.py             # MCP 도구 연동 (외부 시스템 호출)
    ├── 06_rag_agent.py             # RAG (검색 증강 생성 — 하이브리드 검색)
    ├── 06_rag_agent_foundry_iq.py  # RAG 변형 (Foundry IQ 지식 베이스 + agentic retrieval)
    ├── _rag_iq.py                  # Foundry IQ RAG 공용 헬퍼 (인덱스 시드 + 컨텍스트 프로바이더)
    ├── _streaming.py               # 스트리밍 출력 공용 헬퍼 (전 예제 공유)
    │
    │   # ── 아래 폴더는 선택 사항입니다. 처음에는 건너뛰어도 됩니다 ──
    └── hosted_agents/              # MAF 에이전트·워크플로우를 Hosted Agent로 배포 (01~06 + 06 Foundry IQ 변형, Part 8)
```

---

## Part 0. 전체 그림

목표는 **Microsoft Agent Framework(MAF)로 멀티 에이전트를 단계적으로 구축**하는 것입니다.
단일 에이전트에서 시작해 순차·협업·병렬 워크플로우, MCP 도구 연동, RAG까지 확장합니다.

```
   [Python 예제 src/01~06]
            │
            ▼
   Microsoft Agent Framework (MAF)
     ├─ 단일 에이전트 (Agent)
     ├─ 워크플로우: Sequential · GroupChat · Concurrent
     ├─ MCP 도구 연동 (외부 시스템 호출)
     └─ RAG (검색 증강 생성)
            │
            ▼  FoundryChatClient  (AzureCliCredential = az login)
   Microsoft Foundry  (gpt-5.4 등 모델 배포)
```

| Part | 무엇을 하나 |
|------|-------------|
| **1** | **사전 준비 — Azure(Microsoft Foundry) 리소스·모델 배포 + 설치·`.env` (모든 실습의 전제)** |
| 2 | Agent Framework 단일 에이전트 실행 |
| 3~5 | Sequential / GroupChat / Concurrent Workflow |
| 6 | MCP 도구 연동 — 에이전트가 외부 시스템 호출 |
| 7 | RAG — 검색 증강 생성으로 근거 기반 답변 |
| 8 | Hosted Agent 배포 — 예제별 배포·원격 테스트 |

> **Part 1(사전 준비)이 모든 예제의 전제**입니다. Azure(Microsoft Foundry) 리소스·모델 배포와
> `.env` 설정을 먼저 끝낸 뒤, Part 2부터 예제를 순서대로 실행하세요.

### 0.1 핵심 기술 — 기능과 장점

| 기술 | 무엇인가 | 핵심 기능 | 장점 |
|------|----------|-----------|------|
| **Microsoft Agent Framework**<br/>(MAF) | 에이전트·멀티 에이전트 오케스트레이션 오픈소스 Python SDK (Semantic Kernel·AutoGen 통합 후속) | `Agent`, Handoff·GroupChat·Workflow 오케스트레이션, MCP 도구, 미들웨어·관측성 | 단일 SDK로 단순→복잡 확장, 모델/클라이언트 추상화, 표준 MCP 연동 |
| **Microsoft Foundry** | 모델 배포·평가·관측을 제공하는 Azure 통합 AI 플랫폼 | 프로젝트 단위 리소스, 모델 카탈로그·배포, `FoundryChatClient` 연결, Entra ID 인증 | 관리형 호스팅, 키 없는(`AzureCliCredential`) 엔터프라이즈 보안·거버넌스 |
| **MCP**<br/>(모델 컨텍스트 프로토콜) | 에이전트가 외부 시스템(문서·DB·API)을 호출하는 표준 프로토콜 | `MCPStreamableHTTPTool` 등으로 원격/로컬 서버 연결, LLM이 필요 시 도구 자동 호출 | LLM 내부 지식 한계 보완, 실시간 데이터 기반 응답, 표준화된 도구 연동 |
| **RAG**<br/>(검색 증강 생성) | 질문 관련 문서를 먼저 검색해 컨텍스트로 주입한 뒤 생성 | Azure AI Search 하이브리드(BM25+벡터) 검색 → 증강 프롬프트 → 생성 | 사내 데이터 근거 응답, 환각 감소, 출처 추적 가능 |

---

## Part 1. 사전 준비

### 1.1 도구

| 도구 | 용도 | 설치 |
|------|------|------|
| **Python 3.14.5** | Agent Framework 코드 (이 랩은 3.14.5 기준으로 검증) | <https://python.org> |
| **Azure CLI 2.81.0+** | Microsoft Foundry 인증(`az login` 키리스) | `az upgrade --yes` |

### 1.2 Azure 리소스 프로비저닝

> ⏱️ **예상 소요/비용**: 프로비저닝 + 첫 실행까지 약 **30~40분**. Foundry 모델·Azure AI Search는
> **사용량 기반 과금**이며, 본 실습 정도의 호출량이면 보통 **수백 원~수천 원** 수준입니다.
> 실습이 끝나면 [1.4 리소스 정리](#14-리소스-정리-실습-종료-후)로 리소스 그룹을 통째로 삭제해 비용을 막으세요.

예제 실행에는 **Microsoft Foundry 리소스·프로젝트·모델 배포**가 필요하고, 예제 `06`(RAG)에는
추가로 **Azure AI Search 서비스**가 필요합니다. 포털에서 만들어도 되지만, 아래 `az` CLI로
한 번에 프로비저닝할 수 있습니다. (Foundry 프로젝트·모델은 [Microsoft Foundry 포털](https://ai.azure.com)에서도 생성 가능합니다.)

```bash
az login

# 0) 변수 설정 (이름은 전역 고유해야 하며, 리전은 모델 가용성에 맞게 조정)
RG=rg-maf-lab
LOCATION=eastus2
FOUNDRY=foundry-maf-lab          # Foundry(AIServices) 리소스 이름
PROJECT=proj-maf-lab             # Foundry 프로젝트 이름
SEARCH=search-maf-lab            # Azure AI Search 서비스 이름

az group create -n $RG -l $LOCATION

# 1) Foundry(AIServices) 리소스 생성 (키리스 Entra ID 인증을 위해 custom-domain 지정)
az cognitiveservices account create \
  -n $FOUNDRY -g $RG -l $LOCATION \
  --kind AIServices --sku S0 --custom-domain $FOUNDRY --yes

# 2) Foundry 프로젝트 생성
az cognitiveservices account project create \
  -n $FOUNDRY -g $RG -l $LOCATION --project-name $PROJECT

# (선택) 배포 가능한 모델·버전 확인
az cognitiveservices account list-models -n $FOUNDRY -g $RG -o table

# 3) 채팅 모델 배포 (예제 01~06)
#    ⚠️  --model-version은 반드시 위 list-models 출력에서 확인한 실제 버전으로 바꾸세요.
#       아래 <version>은 placeholder입니다. 그대로 실행하면 배포가 실패합니다.
az cognitiveservices account deployment create \
  -n $FOUNDRY -g $RG \
  --deployment-name gpt-5.4 \
  --model-name gpt-5.4 --model-version <version> --model-format OpenAI \
  --sku-name GlobalStandard --sku-capacity 10

# 4) 임베딩 모델 배포 (예제 06 RAG 전용)
az cognitiveservices account deployment create \
  -n $FOUNDRY -g $RG \
  --deployment-name text-embedding-3-large \
  --model-name text-embedding-3-large --model-version 1 --model-format OpenAI \
  --sku-name Standard --sku-capacity 10

# 5) Azure AI Search 서비스 생성 (예제 06 RAG 전용)
#    --auth-options aadOrApiKey: 키리스(Entra ID) 데이터플레인 접근을 켭니다.
#    (기본값은 API 키 전용이라, 생략하면 RAG 실행 시 'Forbidden' 오류가 납니다.)
#    --aad-auth-failure-mode http403: aadOrApiKey 사용 시 최신 Azure CLI가 요구하는
#      필수 옵션입니다. (생략하면 'requires an AadAuthFailureMode parameter' 오류가 납니다.)
#    --semantic-search free: 예제 06 변형(Foundry IQ agentic retrieval)에 필요한
#      semantic ranker를 켭니다. (free 플랜은 월 무료 할당량 제공)
#    ⚠️ Foundry IQ를 쓰려면 LOCATION이 agentic retrieval 지원 리전이어야 합니다
#       (예: eastus2). 미지원 리전이면 기본 06(하이브리드) 예제만 동작합니다.
#    리전이 용량 부족(InsufficientResourcesAvailable)이면 다른 리전을 사용하세요.
#      (Search 서비스는 Foundry 리소스와 다른 리전이어도 됩니다. 예: Foundry=eastus2,
#       Search=eastus. eastus도 agentic retrieval 지원 리전입니다.)
az search service create -n $SEARCH -g $RG -l $LOCATION --sku basic \
  --auth-options aadOrApiKey --aad-auth-failure-mode http403 --semantic-search free

# 5-1) (Foundry IQ 전용) Search 서비스에 시스템 할당 관리 ID 부여
#      지식 베이스가 질의를 벡터화할 때 Search 서비스가 Azure OpenAI를 호출합니다.
az search service update -n $SEARCH -g $RG --identity-type SystemAssigned

# 6) 권한(RBAC) — 본인 계정에 데이터플레인(리소스의 실제 데이터를 읽고 쓰는 작업) 역할 부여 (키리스 인증)
ME=$(az ad signed-in-user show --query id -o tsv)
ACC_ID=$(az cognitiveservices account show -n $FOUNDRY -g $RG --query id -o tsv)
SEARCH_ID=$(az resource show -g $RG -n $SEARCH \
  --resource-type Microsoft.Search/searchServices --query id -o tsv)

az role assignment create --assignee $ME --role "Cognitive Services User" --scope $ACC_ID
az role assignment create --assignee $ME --role "Cognitive Services OpenAI User" --scope $ACC_ID
az role assignment create --assignee $ME --role "Search Service Contributor"     --scope $SEARCH_ID
az role assignment create --assignee $ME --role "Search Index Data Contributor"  --scope $SEARCH_ID
az role assignment create --assignee $ME --role "Search Index Data Reader"       --scope $SEARCH_ID

# 6-1) (Foundry IQ 전용) Search 서비스 관리 ID에 Azure OpenAI 사용 권한 부여
#      지식 베이스의 벡터화(임베딩) 호출에 필요합니다.
SEARCH_MI=$(az search service show -n $SEARCH -g $RG --query identity.principalId -o tsv)
az role assignment create --assignee-object-id $SEARCH_MI --assignee-principal-type ServicePrincipal \
  --role "Cognitive Services OpenAI User" --scope $ACC_ID

# 7) (선택) Application Insights 생성 — 에이전트 추적(Tracing) 활성화용
#    Foundry 프로젝트에 연결하면 Hosted Agent(Part 8) 런타임이 추적을 자동 전송하고,
#    포털 Agents → Traces 탭에서 모델·도구 호출을 추적할 수 있습니다.
APPINSIGHTS=appi-maf-lab
az extension add -n application-insights --upgrade --only-show-errors
az monitor app-insights component create \
  --app $APPINSIGHTS -g $RG -l $LOCATION --application-type web
```

> **추적(Tracing) 활성화 — App Insights 리소스 생성 또는 연결**: 위 `7)`에서 만든 Application
> Insights를 Foundry 프로젝트에 연결하면 추적이 켜집니다. [Microsoft Foundry 포털](https://ai.azure.com)에서
> 프로젝트를 열고 왼쪽 **Agents → 상단 `Traces` 탭 → 오른쪽 `Connect`**를 눌러
> **Application Insights 리소스를 생성하거나 연결**(*Create or connect an Application Insights
> resource to enable tracing*)합니다. 기존 리소스는 목록에서 선택해 **Connect**, 새 리소스는
> **Create new**로 마법사를 완료합니다. 연결되면 프로젝트가 추적을 사용할 준비가 됩니다.
> 이후 Hosted Agent(Part 8) 런타임은 `APPLICATIONINSIGHTS_CONNECTION_STRING`을 자동
> 주입받아 추적을 전송합니다.
> `Connect` 버튼이 보이지 않으면 프로젝트 이름 드롭다운 → **Project details → Connected
> resources 탭 → Add connection → Application Insights**로도 연결할 수 있습니다. 자세한 절차는
> [Set up tracing in Microsoft Foundry](https://learn.microsoft.com/azure/foundry/observability/how-to/trace-agent-setup#connect-application-insights-to-your-foundry-project)를 참고하세요.

> **로컬 예제(`src/`)에서 추적 켜기**: 콘솔 예제 `01`~`06`은 위 `7)`의 connection string을
> `.env`의 `APPLICATIONINSIGHTS_CONNECTION_STRING`에 넣으면 자동으로 트레이스·메트릭을
> Application Insights로 전송합니다(공유 헬퍼 `src/_observability.py`가 처리하며, 미설정 시
> 추적 없이 그대로 동작). connection string은
> `az monitor app-insights component show --app $APPINSIGHTS -g $RG --query connectionString -o tsv`로
> 확인합니다. 전송된 트레이스는 Application Insights **Transaction search**·KQL
> (`dependencies`/`traces`)이나, 같은 리소스를 Foundry에 연결했다면 포털 **Traces 탭**에서
> 확인합니다.

> **RAG 인덱스 생성**: 별도 명령이 필요 없습니다. 예제 06의 `06_rag_agent.py`(하이브리드)와
> `06_rag_agent_foundry_iq.py`(Foundry IQ)가 **첫 실행 시 인덱스를 자동 생성**하고 문서를
> 임베딩·업로드합니다(멱등). Foundry IQ 예제는 별도 인덱스(`maf-lab-knowledge-iq-v1`)와
> 지식 베이스(`maf-lab-knowledge-iq-v1-kb`)까지 자동으로 만듭니다.

> **이미 만든 Search 서비스에서 'Forbidden'이 난다면** 키리스(Entra ID) 인증이 꺼져 있는
> 경우입니다. 다음으로 활성화하세요.
> ```bash
> az search service update -n $SEARCH -g $RG --auth-options aadOrApiKey --aad-auth-failure-mode http403
> ```

`.env`에 채울 엔드포인트 값은 다음으로 확인합니다.

```bash
# PROJECT_ENDPOINT (Foundry API 엔드포인트)
echo "https://$FOUNDRY.services.ai.azure.com/api/projects/$PROJECT"

# AZURE_OPENAI_ENDPOINT (임베딩 호출용)
az cognitiveservices account show -n $FOUNDRY -g $RG --query "properties.endpoint" -o tsv

# SEARCH_SERVICE_ENDPOINT
echo "https://$SEARCH.search.windows.net"
```

> 이미 Foundry/Search 리소스가 있다면 이 단계를 건너뛰고 기존 엔드포인트를 `.env`에 입력하세요.

### 1.3 설치

```bash
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env        # 아래 값 입력
az login                    # 예제는 AzureCliCredential로 이 로그인 세션을 사용
```

컨텍스트별 주요 환경 변수는 다음과 같습니다.

| 변수명 | 설명 | 사용 컨텍스트 |
|--------|------|--------------|
| `PROJECT_ENDPOINT` | Azure AI Foundry 프로젝트 엔드포인트 | 로컬 실습 전체 |
| `MODEL_DEPLOYMENT_NAME` | 사용할 모델 배포 이름 | 로컬 실습 (선택, 기본값 있음) |
| `SEARCH_SERVICE_ENDPOINT` | Azure AI Search 서비스 엔드포인트 | RAG 실습 (06번) |
| `SEARCH_INDEX_NAME` | 검색 인덱스 이름 | RAG 실습 (06번) |
| `SEARCH_KNOWLEDGE_BASE_NAME` | Foundry IQ 지식 기반 이름 | RAG IQ 실습 (06_foundry_iq) |

> 참고: 로컬 Python 예제 `src/06_rag_agent_foundry_iq.py`는 `SEARCH_INDEX_NAME_IQ`를 사용해
> 지식 베이스를 자동 생성합니다. `SEARCH_KNOWLEDGE_BASE_NAME`은 Part 8 Hosted Agent의
> `06_rag_agent_foundry_iq/` 배포 예제에서 사용합니다.

`.env` 예시 값 (예제 01~05는 상단 2줄만 있으면 동작, 예제 06 RAG는 전체 필요):

```bash
# 예제 01~06 공통 (Foundry 채팅)
PROJECT_ENDPOINT=https://your-resource.services.ai.azure.com/api/projects/your-project
MODEL_DEPLOYMENT_NAME=gpt-5.4

# 예제 06 (RAG) — Azure AI Search + 임베딩
SEARCH_SERVICE_ENDPOINT=https://your-search-service.search.windows.net
SEARCH_INDEX_NAME=maf-lab-knowledge-v1
AZURE_OPENAI_ENDPOINT=https://your-resource.cognitiveservices.azure.com/
EMBEDDING_DEPLOYMENT_NAME=text-embedding-3-large
AZURE_OPENAI_API_VERSION=2024-10-21

# 예제 06 변형 (Foundry IQ RAG) — 지식 베이스 + agentic retrieval
SEARCH_INDEX_NAME_IQ=maf-lab-knowledge-iq-v1
# (선택) 일부 환경은 .openai.azure.com 형식의 벡터화 리소스 URL을 요구합니다.
# AZURE_OPENAI_RESOURCE_URL=https://your-resource.openai.azure.com/
# (선택) 질의 계획 추론 강도 (minimal/low/medium, 기본값: minimal)
# FOUNDRY_IQ_REASONING_EFFORT=minimal
```

### 1.4 리소스 정리 (실습 종료 후)

실습이 끝나면 **불필요한 비용을 막기 위해** 생성한 리소스를 정리하세요. 리소스 그룹을
통째로 삭제하면 Foundry·모델 배포·Search 서비스가 한 번에 제거됩니다.

```bash
# 1.2에서 만든 리소스 그룹을 통째로 삭제 (되돌릴 수 없음)
az group delete -n $RG --yes --no-wait
```

> ⚠️ `--no-wait`는 삭제 요청만 보내고 즉시 반환합니다. 진행 상황은
> `az group show -n $RG` 가 `NotFound`를 반환할 때까지 확인하세요.
> Part 8에서 만든 Hosted Agent가 있다면, 각 폴더 README의 정리 절차도 함께 수행하세요.

---

## Part 2. 단일 에이전트

> **Microsoft Agent Framework(MAF)** 는 에이전트 생성부터 멀티 에이전트 오케스트레이션까지 하나의
> Python SDK로 제공하는 오픈소스 프레임워크입니다(Semantic Kernel·AutoGen의 통합 후속).
> **Microsoft Foundry** 는 모델을 배포·관리하는 Azure 플랫폼으로, MAF의
> `FoundryChatClient`가 여기에 연결합니다. 인증은 키 없이 `AzureCliCredential`(= `az login` 세션,
> Entra ID)을 사용해 엔터프라이즈 보안을 유지합니다.

코드: [`src/01_single_agent.py`](src/01_single_agent.py)

핵심:

```python
client = FoundryChatClient(
    project_endpoint=os.getenv("PROJECT_ENDPOINT"),
    model=os.getenv("MODEL_DEPLOYMENT_NAME", "gpt-5.4"),
    credential=AzureCliCredential(),
)
agent = Agent(
    client=client,
    name="기술_어시스턴트",
    instructions="당신은 Microsoft 기술 전문 어시스턴트입니다. ... 한국어로 답변합니다.",
)

# 스트리밍: stream=True로 응답을 토큰 단위로 받아 생성 과정을 실시간 출력합니다.
# update.text가 None인 청크는 건너뜁니다 (도구 호출·메타 이벤트 등).
async for update in agent.run("Microsoft Agent Framework가 무엇인가요?", stream=True):
    text = getattr(update, "text", "") or ""
    if text:
        print(text, end="", flush=True)
print()
```

> 💡 **스트리밍 출력**: 예제별 스트리밍 방식은 두 가지입니다. 공통 로직은
> [`src/_streaming.py`](src/_streaming.py)에 모아 두었습니다.
> - `stream_agent(agent, prompt)` — 단일 에이전트 응답을 **토큰 단위**로 출력하고 전체 텍스트를 반환(01·05·06)
> - `stream_workflow(workflow, message)` — 워크플로우를 스트리밍 실행해 **참여자별 완성 응답 블록**을 순서대로 출력(02 Sequential·03 GroupChat·04 Concurrent)

실행:

```bash
python src/01_single_agent.py
```

**기대 출력(예시)** — 응답 본문은 모델에 따라 달라지지만, 골격과 종료 표시는 동일합니다.

```text
=== 단일 에이전트 실행 ===

질문: Microsoft Agent Framework가 무엇인가요?

에이전트 응답:
Microsoft Agent Framework는 ... (모델이 생성한 한국어 설명이 토큰 단위로 스트리밍됨) ...

=== 실행 완료 ===
```


| 요소 | 설명 |
|------|------|
| `FoundryChatClient` | Microsoft Foundry 프로젝트에 연결하는 채팅 클라이언트 |
| `Agent(client, name, instructions)` | 모델 + 역할 지시문의 단위 |
| `agent.run(..., stream=True)` | 입력을 받아 응답을 토큰 단위로 스트리밍 생성 |

---

## Part 3. 순차(Sequential) 워크플로우

코드: [`src/02_sequential_workflow.py`](src/02_sequential_workflow.py)

**시나리오**: 분석가 → 작가 → 편집자가 차례로 콘텐츠를 다듬는 제작 파이프라인.

```python
from agent_framework.orchestrations import SequentialBuilder

workflow = SequentialBuilder(
    participants=[analyzer_agent, writer_agent, editor_agent]  # 실행 순서대로 전달
).build()
result = await workflow.run("Kubernetes 클러스터 비용 최적화 전략")
for output in result.get_outputs():
    print(output)
```

> 실제 저장소 예제(`src/02_sequential_workflow.py`)는 각 단계 출력을 실시간으로 보여주기 위해
> `stream_workflow(workflow, topic)`(공통 헬퍼)를 사용합니다. `result.get_outputs()`는
> 최종 결과를 한 번에 받는 방법입니다.

**핵심**:
- `SequentialBuilder`가 참여자 순서대로 **앞 단계의 출력을 다음 단계 입력으로 전달**합니다.
- 각 에이전트는 네이티브 MAF `Agent`이며, 역할은 `instructions`로 부여합니다.
- 참여자 `name`은 도구명이 아니므로 한국어(예: `분석가`)를 그대로 써도 됩니다.
- 더 복잡한 분기·조건부 라우팅이 필요하면 `WorkflowBuilder` + `Case`/`Default`로
  선언적 그래프를 구성할 수 있습니다(상세는 `agent-framework-codegen` 스킬 참조).

```bash
python src/02_sequential_workflow.py
```

**기대 출력(예시)** — 분석가 → 작가 → 편집자 순서로 파이프라인이 진행됩니다.

```text
=== 순차 워크플로우 실행 ===

입력 주제: Kubernetes 클러스터 비용 최적화 전략
==================================================

[순차 파이프라인 결과]
... (분석가의 분석 → 작가의 초안 → 편집자의 최종본이 순서대로 출력됨) ...

=== 실행 완료 ===
```


---

## Part 4. GroupChat 워크플로우

코드: [`src/03_group_chat.py`](src/03_group_chat.py)

**시나리오**: 기획자·개발자·디자이너가 하나의 주제를 라운드 로빈으로 토론.

```python
from agent_framework.orchestrations import GroupChatBuilder, GroupChatState

def select_next_speaker(state: GroupChatState) -> str:
    speakers = ["기획자", "개발자", "디자이너"]
    return speakers[state.current_round % len(speakers)]

workflow = GroupChatBuilder(
    participants=[planner_agent, developer_agent, designer_agent],
    selection_func=select_next_speaker,
    max_rounds=6,          # 무한 토론 방지
).build()
result = await workflow.run("모바일 앱 신규 기능: AI 기반 개인화 추천 시스템 도입")
```

> 참고: 최종 토론 내용은 `result.get_outputs()`(종료 메시지)가 아니라 이벤트의
> `AgentExecutorResponse`에서 추출합니다 — `src/03_group_chat.py`의 스트리밍 출력 참고.

**Sequential vs GroupChat**

| | Sequential | GroupChat |
|---|------------|-----------|
| 구조 | 에이전트를 **순서대로 연결**(앞 출력 → 다음 입력) | 여러 에이전트가 **한 대화에 공동 참여** |
| 발화자 결정 | 고정된 참여자 순서 | `selection_func`(예: 라운드 로빈) |
| 종료 조건 | 마지막 단계 완료 | `max_rounds` |
| 적합 | 단계별 파이프라인 | 브레인스토밍·다관점 검토 |

```bash
python src/03_group_chat.py
```

**기대 출력(예시)** — 여러 에이전트가 라운드를 돌며 토론한 뒤 합의에 도달합니다.

```text
=== GroupChat 워크플로우 실행 ===

주제: 모바일 앱 신규 기능 기획: AI 기반 개인화 추천 시스템을 도입하려고 합니다.
==================================================

[GroupChat 토론 결과]
... (참여 에이전트들이 번갈아 발언하며 의견을 교환하고 결론을 정리함) ...

=== 실행 완료 ===
```


---

## Part 5. 동시(Concurrent) 워크플로우

코드: [`src/04_concurrent_workflow.py`](src/04_concurrent_workflow.py)

**시나리오**: 보안·성능·UX 리뷰어가 하나의 설계안을 각자 관점에서 **병렬** 검토.

```python
from agent_framework.orchestrations import ConcurrentBuilder

workflow = ConcurrentBuilder(
    participants=[security_agent, performance_agent, ux_agent]  # 같은 입력을 동시에 전달
).build()
result = await workflow.run("게스트 결제 + 단말 캐시 설계안을 검토해 주세요.")
for output in result.get_outputs():
    print(output)
```

> 실제 저장소 예제(`src/04_concurrent_workflow.py`)는 각 리뷰어 응답을 도착 순서대로 실시간
> 출력하기 위해 `stream_workflow(workflow, design)`을 사용합니다.

**핵심**:
- `ConcurrentBuilder`가 **모든 참여자에게 같은 입력을 병렬로 전달**하고 결과를 모읍니다.
- 순차 파이프라인과 달리 참여자 간 의존이 없어 **독립적 다관점 평가**에 적합합니다.
- 각 리뷰어의 응답은 도착 순서대로 스트리밍되며, 발화자 라벨로 구분됩니다.

```bash
python src/04_concurrent_workflow.py
```

**기대 출력(예시)** — 여러 전문가 에이전트가 같은 설계안을 병렬로 검토합니다.

```text
=== 동시 워크플로우 실행 ===

검토 대상 설계안: 신규 모바일 앱에 로그인 없이 게스트 결제를 허용하고, 추천 데이터를 단말에 캐시하는 설계안을 검토해 주세요.
==================================================

[동시 리뷰 결과]
... (보안·성능·UX 등 관점별 검토 의견이 각각 출력됨) ...

=== 실행 완료 ===
```


> ✅ **체크포인트**: Single → Sequential → GroupChat → Concurrent 4가지 패턴의 차이와
> 선택 기준을 설명할 수 있으면 Agent Framework 핵심을 익힌 것입니다.

---

## Part 6. MCP 도구 연동 에이전트

지금까지의 에이전트는 LLM의 내부 지식만 사용했습니다. **MCP(Model Context Protocol)** 도구를
연결하면 에이전트가 외부 시스템(문서 검색, 데이터베이스, API 등)의 기능을 **실시간으로 호출**할 수
있습니다. 여기서는 인증이 필요 없는 공개 서버인 **Microsoft Learn MCP**에 붙여, 에이전트가 공식
문서를 검색해 근거 기반으로 답하도록 만듭니다.

```
[질문] → [에이전트] → (MCP 도구로 Learn 문서 검색) → [출처가 포함된 답변]
```

> 💡 **에이전트의 MCP** (`MCPStreamableHTTPTool`): *내가 만든 MAF 에이전트* 가 런타임에 외부
> 시스템을 호출하는 도구입니다. 에이전트 코드 안에서 정의·연결하면, LLM이 필요하다고 판단할 때 스스로 호출합니다.

### 핵심 코드

```python
from agent_framework import Agent, MCPStreamableHTTPTool

# 1) MCP 도구 정의 (공개 서버라 인증 헤더 불필요)
learn_mcp = MCPStreamableHTTPTool(
    name="MicrosoftLearn",
    url="https://learn.microsoft.com/api/mcp",
    description="Microsoft/Azure 공식 문서·코드 샘플 검색 도구",
)

# 2) async with 블록 안에서만 MCP 세션이 활성화됨 (connect → close 자동 처리)
async with learn_mcp:
    agent = Agent(
        client=client,
        name="문서_리서치_어시스턴트",
        instructions="답변 전 MicrosoftLearn 도구로 검색해 출처와 함께 한국어로 답하세요.",
        tools=learn_mcp,                  # 도구를 에이전트에 연결
    )
    result = await agent.run("Handoff 방식이 무엇인지 공식 문서 근거로 설명해줘.")
    print(result)
```

| 항목 | 설명 |
|------|------|
| `MCPStreamableHTTPTool` | HTTP(SSE) 기반 원격 MCP 서버에 연결하는 도구 래퍼 |
| `header_provider` / 커스텀 `http_client` | 인증이 필요한 서버는 헤더를 직접 넘기지 말고 `header_provider` 콜백 또는 커스텀 `http_client`로 `Authorization` 등을 설정 |
| `async with mcp_tool:` | 세션 컨텍스트. 진입 시 도구 목록 로드, 종료 시 연결 정리 |
| `tools=` | 에이전트가 사용할 도구 전달. LLM이 필요 시 스스로 호출 |

> 로컬 프로세스형 서버는 `MCPStdioTool`, WebSocket 서버는 `MCPWebsocketTool`을 사용합니다.

```bash
python src/05_mcp_agent.py
```

**기대 출력(예시)** — 에이전트가 Microsoft Learn MCP 서버를 호출해 근거와 함께 답합니다.

```text
=== MCP 도구 연동 에이전트 실행 ===

질문: Microsoft Agent Framework에서 여러 에이전트를 협업시키는 Handoff 방식이 무엇인지 공식 문서를 근거로 설명해줘.

... (에이전트가 MCP 도구로 문서를 조회한 뒤 한국어로 설명하며 [출처]를 포함) ...

=== 실행 완료 ===
```


> ✅ **체크포인트**: 에이전트가 MCP 도구를 호출해 출처나 참고 문서를 언급하면 MCP 도구 호출이 성공한 것입니다. 응답 형식은 모델에 따라 달라질 수 있습니다.

---

## Part 7. RAG — 검색 증강 생성

**RAG(Retrieval-Augmented Generation)** 는 질문과 관련된 문서를 **먼저 검색**해 컨텍스트로
주입한 뒤 답하게 하는 패턴입니다. LLM이 모르는 사내 데이터에 근거해 답하게 하고, 환각을 줄입니다.

```
[질문] → [1.검색 Retrieval] → [2.증강 Augmentation] → [3.생성 Generation]
```

이 예제는 **Azure AI Search 하이브리드(키워드 + 벡터) 검색**으로 지식 베이스를 검색합니다.
처음 실행하면 인덱스를 자동 생성하고 문서를 임베딩하여 업로드하므로(자체 완결·**멱등**: 여러 번
실행해도 결과가 같아 중복 입력되지 않음), 별도 사전 준비 없이 바로 실행됩니다. 인증은 전부
키리스(`AzureCliCredential`)입니다.

### 핵심 코드

```python
# 0) 임베딩 차원을 모델에서 동적으로 확인 → 인덱스 자동 생성(없을 때만)
dim = len(embed(["차원 확인"])[0])
ensure_index(index_client, index_name, dim)        # HNSW(고속 근사 벡터 검색 인덱스) + 코사인, ko.microsoft 분석기

# 1) 문서 임베딩 후 업로드(멱등 upsert) + 인덱싱 반영 대기
await seed_documents(search_client, embed)

# 2) 검색: 질문을 임베딩해 하이브리드(BM25 + 벡터) 검색
docs = retrieve(search_client, embed, question, top_k=2)
context = build_context(docs)

# 3) 증강: 검색 결과를 프롬프트에 주입
augmented_prompt = (
    f"다음 참고 문서를 바탕으로 답하세요.\n\n"
    f"--- 참고 문서 ---\n{context}\n\n--- 질문 ---\n{question}"
)

# 4) 생성: 컨텍스트 안에서만 답하도록 지시된 에이전트가 응답
agent = Agent(
    client=client,
    name="고객지원_RAG_어시스턴트",
    instructions="제공된 '참고 문서' 안의 정보만 근거로 답하고, 없으면 모른다고 하세요.",
)
result = await agent.run(augmented_prompt)
```

하이브리드 검색은 키워드 검색(**BM25**: 단어 일치 기반 고전 랭킹 알고리즘)과 벡터 검색(의미 유사도)을
**RRF**(Reciprocal Rank Fusion, 두 검색의 순위를 합쳐 하나로 융합하는 방식)로 결합합니다.
`VectorizedQuery`로 질문 임베딩을 전달하고, `search_text`로 키워드 검색을 동시에 수행합니다. 핵심은 **(1) 검색 품질**과
**(2) "문서 밖 내용은 추측하지 말라"는 지시문**입니다. 이 둘이 RAG의 정확도를 결정합니다.

```bash
python src/06_rag_agent.py
```

**기대 출력(예시)** — 5단계(임베딩 → 인덱스 → 업로드 → 하이브리드 검색 → 생성)가 순서대로
진행됩니다. 검색 점수·응답 문구는 환경에 따라 달라질 수 있습니다.

```text
=== RAG 에이전트 (Azure AI Search) 실행 ===

[1단계] 임베딩 클라이언트 준비 및 차원 확인...
  → 임베딩 차원: 3072

[2단계] Azure AI Search 인덱스 확인/생성...
  → 기존 인덱스 사용: maf-lab-knowledge-v1

[3단계] 지식 베이스 임베딩 및 업로드...
  → 문서 4건 임베딩·업로드 완료

[4단계] 하이브리드 검색 — 질문: Pro 요금제는 얼마이고 기술 지원은 얼마나 빨리 받을 수 있나요?
  → 검색된 문서:
     - 구독 요금제 (doc-2, score=0.033)
     - 기술 지원 SLA (doc-3, score=0.033)

[5단계] 에이전트가 답변 생성 중...

에이전트 응답:
Pro 요금제는 월 29,900원입니다. 기술 지원은 우선 기술 지원이 제공되며, 24시간 이내
1차 응답을 보장받습니다. [출처: 구독 요금제, 기술 지원 SLA]

=== 실행 완료 ===
```

> ℹ️ 첫 실행 시 `[2단계]`는 `인덱스 생성 완료 ...`로, 인덱스가 이미 있으면 `기존 인덱스 사용 ...`으로
> 출력됩니다. 실행 시 `ExperimentalWarning`이 함께 표시될 수 있으나 동작에는 영향이 없습니다.


> ℹ️ `VectorizedQuery`의 후보 수 인자는 SDK 버전에 따라 이름이 다릅니다. 이 랩의
> `azure-search-documents==11.7.0b2`는 `k`(안정 버전은 `k_nearest_neighbors`)를 사용합니다.

### 필요 리소스 / 환경 변수

| 환경 변수 | 설명 |
|-----------|------|
| `SEARCH_SERVICE_ENDPOINT` | Azure AI Search 엔드포인트 (`https://<name>.search.windows.net`) |
| `SEARCH_INDEX_NAME` | RAG 인덱스 이름 (기본 `maf-lab-knowledge-v1`, 없으면 자동 생성) |
| `AZURE_OPENAI_ENDPOINT` | 임베딩 호출용 Azure OpenAI 엔드포인트 (`https://<name>.cognitiveservices.azure.com/`) |
| `EMBEDDING_DEPLOYMENT_NAME` | 임베딩 모델 배포 이름 (기본 `text-embedding-3-large`) |
| `AZURE_OPENAI_API_VERSION` | Azure OpenAI API 버전 (기본 `2024-10-21`) |

RBAC: 실행 사용자는 검색 서비스에 **Search Service Contributor**(인덱스 생성) +
**Search Index Data Contributor/Reader**(문서 업로드·조회) 역할이, 임베딩 호출에는 Azure OpenAI
사용 권한이 필요합니다.

### 한 단계 더 — Foundry IQ (지식 베이스 + agentic retrieval)

지식 베이스를 코드에서 직접 검색하는 대신 **Foundry IQ** 지식 베이스에 검색을
위임할 수 있습니다. `agent_framework.azure`의 `AzureAISearchContextProvider`(agentic
모드)를 에이전트의 `context_providers`에 연결하면, 에이전트가 질문을 받을 때마다
지식 베이스에 **멀티홉 검색**을 수행하고 그 결과를 컨텍스트로 자동 주입합니다.
검색·증강을 직접 코딩할 필요가 없습니다.

```python
from agent_framework.azure import AzureAISearchContextProvider
from azure.identity.aio import AzureCliCredential as AioAzureCliCredential

# 인덱스로부터 지식 소스/지식 베이스(<index>-kb)를 자동 생성하고 멀티홉 검색
async with AzureAISearchContextProvider(
    endpoint=search_endpoint,
    index_name="maf-lab-knowledge-iq-v1",
    mode="agentic",
    model=chat_model_deployment,                # 질의 계획용 채팅 모델(예: gpt-5.4)
    azure_openai_resource_url=aoai_endpoint,
    credential=AioAzureCliCredential(),          # 비동기 자격 증명 필수
) as provider:
    agent = Agent(client=client, instructions="...근거 기반 답변...",
                  context_providers=[provider])
    await agent.run("Pro 요금제는 얼마이고 기술 지원은 얼마나 빨리 받나요?")
```

```bash
python src/06_rag_agent_foundry_iq.py
```

기존 하이브리드 예제(`06_rag_agent.py`)와의 차이는 다음과 같습니다.

| 구분 | `06_rag_agent.py` (하이브리드) | `06_rag_agent_foundry_iq.py` (Foundry IQ) |
| --- | --- | --- |
| 검색 주체 | Python 코드(직접 BM25+벡터 융합) | Foundry IQ 지식 베이스(agentic 멀티홉) |
| 증강 | 직접 프롬프트 조립 | 컨텍스트 프로바이더가 자동 주입 |
| 인덱스 | `maf-lab-knowledge-v1` | `maf-lab-knowledge-iq-v1` (+ 기본 semantic 구성) |
| 추가 리소스 | — | semantic ranker 활성화 + agentic 지원 리전 |

> **요구사항**: Azure AI Search에 **semantic ranker 활성화**(`--semantic-search free`),
> **agentic retrieval 지원 리전**, 인덱스의 **기본 semantic 구성**(예제가 자동 생성),
> Search 서비스 관리 ID의 Azure OpenAI 사용 권한이 필요합니다([1.2 프로비저닝](#12-azure-리소스-프로비저닝) 참고).
> Part 8 Hosted Agent 트랙에도 동일한 Foundry IQ 변형 예제가 있습니다.

> ✅ **체크포인트**: 지식 베이스에 없는 질문(예: "배송비는 얼마인가요?")에 에이전트가
> "관련 정보를 찾을 수 없습니다"라고 답하면 RAG가 올바르게 동작하는 것입니다.

---

## Part 8. Hosted Agent 배포 — MAF 에이전트·워크플로우를 관리형으로

예제 01~06은 프롬프트 1건을 처리하고 종료하는 **로컬 콘솔 스크립트**입니다. 이 파트는 그
**코드를 거의 그대로** Microsoft Foundry **Hosted Agent**(관리형 컨테이너)로 배포해, 상시
구동되는 `/responses` HTTP 엔드포인트로 노출합니다. 에이전트를 SDK로 재작성하지 않아도
관리형 인프라 + **자동 trace/monitoring**을 그대로 얻는 것이 핵심입니다.

> 🚀 **바로 해보기**: **로컬 테스트 → 배포 → 호출**은 **[8.3](#83-로컬-실행--배포--호출--01-예제)**,
> **예제별 배포 명령**은 **[8.4](#84-예제별-배포-명령-7개-예제)**. 가장 간단한 호출은 `azd ai agent invoke "<질문>"`
> 한 줄입니다. 개념·파일 설명(8.1~8.2)은 건너뛰고 8.3부터 시작해도 됩니다.

> 위치: [`src/hosted_agents/`](src/hosted_agents/) — 7개 예제(01~06 + 06 Foundry IQ 변형)가 각각
> 독립 배포 가능한 azd 프로젝트(`main.py`·`Dockerfile`·`agent.yaml`·`agent.manifest.yaml`·
> `requirements.txt`·`.env.example`)로 들어 있습니다.
> 의존성: `agent-framework-foundry-hosting` (+ 02~04 워크플로우는 `agent-framework-orchestrations` 추가 필요)

> ⚠️ Hosted Agent 배포는 현재 **preview**입니다. 아래 권장 **코드(ZIP) 배포 모드**는 로컬 Docker가
> 필요 없습니다(Foundry가 원격에서 빌드). 컨테이너 모드를 선택할 때만 `linux/amd64` 이미지가 필요합니다.

### 8.1 로컬 스크립트 → Hosted Agent: 무엇이 바뀌나

배포해도 **에이전트의 정체성(이름·역할·instructions)은 그대로**입니다. 인증·실행 방식과, 도구·검색을 에이전트에 연결하는 '배선'만 호스팅 형태로 바뀝니다.

| 로컬 예제(01~06) | Hosted Agent |
|------------------|--------------|
| 프롬프트 1건 처리 후 종료 | `/responses` HTTP 서버 상시 구동 |
| `asyncio.run(main())` | `server.run()` (동기) |
| `AzureCliCredential`(내 로그인) | `DefaultAzureCredential`(컨테이너 전용 관리 ID) |
| 루트 `.env`의 `PROJECT_ENDPOINT` | Foundry 주입 env `FOUNDRY_PROJECT_ENDPOINT` |
| 대화 이력 직접 관리 | 호스팅 인프라가 관리 → 각 에이전트에 `default_options={"store": False}` |

실제로 `src/01_single_agent.py` → `src/hosted_agents/01_single_agent/main.py`에서 바뀌는 건 **딱 네 군데**입니다.

```diff
  # 1) 인증: 내 az 로그인 → 컨테이너 전용 관리 ID
- credential=AzureCliCredential()
+ credential=DefaultAzureCredential()

  # 2) 실행: 질문 1건 처리 후 종료 → 상시 HTTP 서버(동기)
- async for update in agent.run(question, stream=True): ...   # asyncio.run(main())
+ server = ResponsesHostServer(agent); server.run()

  # 3) 대화 이력: 직접 관리 → 플랫폼이 관리
- agent = Agent(client=client, name=..., instructions=...)
+ agent = Agent(client=client, name=..., instructions=..., default_options={"store": False})

  # 4) 환경변수: 루트 이름만 → Foundry 표준 이름 우선(+루트 폴백)
- os.getenv("PROJECT_ENDPOINT")
+ os.getenv("FOUNDRY_PROJECT_ENDPOINT") or os.getenv("PROJECT_ENDPOINT")
```

이 **네 군데**는 7개 예제에 **공통**으로 적용됩니다. 그 외에 예제마다 **구조 적응 한 가지**가
더 붙는데, 원인은 모두 같습니다 — 로컬은 "질문 1건 처리 후 종료"하는 **일회성 스크립트**이고,
호스팅은 여러 `/responses` 요청을 처리하는 **상시 대화형 서비스**이기 때문입니다. 그래서
워크플로우·도구·검색을 "에이전트가 매 요청마다 스스로 호출하는 형태"로 바꿔 줍니다.

| 예제 | 핵심(이름·역할·instructions) | 공통 4가지 | 예제별 구조 적응 (실행 모델 차이 때문) |
|------|:---:|:---:|------|
| `01_single_agent` | 동일 | ✅ | 없음 (가장 단순) |
| `02_sequential_workflow` | 동일 | ✅ | 워크플로우를 `.build().as_agent()`로 감싸 단일 에이전트화 |
| `03_group_chat` | 동일 | ✅ | `.as_agent()` (+ `max_rounds`를 단일 응답에 맞춰 6→3 축소) |
| `04_concurrent_workflow` | 동일 | ✅ | `.as_agent()` |
| `05_mcp_agent` | 동일 | ✅ | 클라이언트측 `MCPStreamableHTTPTool`+`async with` → **서버측** `client.get_mcp_tool(...)` (게이트웨이가 MCP 호출·수명 관리) |
| `06_rag_agent` | 동일 | ✅ | 1회성 "검색→증강→생성" → 하이브리드 검색을 **함수 도구**로 노출(에이전트가 호출) · 인덱스 시드는 사전 전제로 분리 |
| `06_rag_agent_foundry_iq` | 동일 | ✅ | 시드+프로바이더 생성 → **기존 지식 베이스에 연결**(`AzureAISearchContextProvider` agentic) |

> **워크플로우(02·03·04)**는 한 줄만 추가하면 됩니다 — `.build()` 결과를 `.as_agent()`로
> 감싸 단일 에이전트처럼 만든 뒤 똑같이 `ResponsesHostServer`에 넘깁니다.
>
> ```python
> workflow_agent = SequentialBuilder(participants=[...]).build().as_agent()
> ResponsesHostServer(workflow_agent).run()
> ```
>
> **05·06**처럼 도구·검색이 있는 예제는, 도구를 **에이전트에 연결하는 방식**(서버측 MCP /
> 함수 도구 / 컨텍스트 프로바이더)만 호스팅 형태로 바뀔 뿐, 에이전트의 역할·instructions는 그대로입니다.

### 8.2 폴더 구성 — 어떤 파일이 왜 필요한가

각 `src/hosted_agents/<예제>/` 폴더는 **그 자체로 배포 가능한 azd 프로젝트**입니다. 루트 예제 하나가
아래 파일 묶음으로 옮겨졌다고 보면 됩니다. 대부분 그대로 두면 되고, 보통 **`main.py`와 `requirements.txt`만**
신경 쓰면 됩니다. **내가 만든 MAF 코드를 직접 배포할 때 무엇을 손으로 만들고 무엇이 `azd`로 자동 생성되는지**는 아래 💡를 참고하세요.

| 파일 | 무엇을 하나 | 직접 손대나? |
|------|-------------|-------------|
| `main.py` | 에이전트를 만들고 `ResponsesHostServer(agent).run()`으로 `/responses` 서버를 띄우는 **진입점**. 루트 예제에서 8.1의 네 군데만 바뀐 형태 | 에이전트 로직을 바꿀 때만 |
| `requirements.txt` | 컨테이너가 설치할 **런타임 의존성**. 메타패키지 `agent-framework` 대신 하위 패키지(`-core`·`-foundry`·`-foundry-hosting`)만 명시 — 메타패키지는 x86 전용 의존성을 끌어와 원격 빌드를 깨뜨림 | 패키지 추가 시 |
| `agent.manifest.yaml` | **`azd ai agent init -m`의 입력 파일**. 에이전트 이름·프로토콜(`responses`)·필요 env·기본 모델을 선언. init이 이걸 읽어 azd 프로젝트를 생성 | 이름/모델/env 바꿀 때 |
| `agent.yaml` | **배포 런타임 스펙**(CPU·메모리·프로토콜·env). 이 저장소에 포함되어 있고 `azd deploy`가 참조 | 리소스 조정 시 |
| `Dockerfile` | 컨테이너 이미지 정의(`python:3.14.5-slim`, 포트 8088). **코드(ZIP) 모드에선 안 쓰임**, 컨테이너 모드에서만 사용 | 컨테이너 모드일 때만 |
| `.env.example` | **로컬 테스트용** 환경변수 템플릿. `cp .env.example .env` 후 값 입력(배포되면 런타임이 자동 주입) | 로컬 실행 전 |
| `.dockerignore`·`.azdignore` | 이미지·업로드에서 제외할 파일(`.venv`·`__pycache__`·매니페스트 등) | 보통 그대로 |

> 💡 **내 코드를 배포할 때 이 파일들을 일일이 만들어야 하나요?** 손으로 만드는 건 **에이전트를 정의하는 최소 파일**뿐입니다 —
> `main.py`(내 MAF 에이전트를 `ResponsesHostServer`로 감싼 코드)·`requirements.txt`·에이전트 정의 YAML
> (`agent.manifest.yaml` 또는 `agent.yaml`), 컨테이너 모드면 `Dockerfile`. 이마저도 맨손으로 시작할 필요 없이
> **`azd ai agent init -m <샘플 매니페스트>`가 이 골격을 `src/`에 내려받아** 주므로, 받은 `main.py`에 내 로직만 채우면 됩니다.
>
> 반대로 **배포에 필요한 나머지는 `azd`가 자동 생성**합니다(직접 작성하지 않음): `azure.yaml`(프로젝트 설정)·`infra/`(Bicep
> IaC)·`.azure/<env>/.env`. `azd ai agent init`이 매니페스트를 읽어 `azure.yaml`을 만들고/갱신하며, `azd provision`(또는
> `azd up`)이 인프라를 처리합니다. **이 저장소의 7개 예제는 그 "에이전트 정의 파일"을 미리 채워 둔 것**이고, `azure.yaml`은
> 저장소에 커밋돼 있지 않습니다(배포 시 작업 폴더에 생성).

### 8.3 로컬 실행 → 배포 → 호출 — 01 예제

`01_single_agent`을 **로컬에서 먼저 띄워 테스트한 뒤** 클라우드에 배포하고 호출하는 흐름입니다.
다른 예제는 폴더 이름과 `--agent-name`만 [8.4](#84-예제별-배포-명령-7개-예제) 값으로 바꾸세요.
(변수 `$RG`·`$FOUNDRY`·`$PROJECT`는 Part 1.2 그대로)

**① 준비 + init + 모델 고정** — 빈 작업 폴더에서
```bash
azd ext install azure.ai.agents && azd auth login          # 최초 1회
REPO=~/GitHub/agent-framework-labs                          # 이 저장소를 clone 한 경로
mkdir -p ~/deploy/single && cd ~/deploy/single
azd ai agent init --no-prompt \
  -m "$REPO/src/hosted_agents/01_single_agent/agent.manifest.yaml" \
  --agent-name maf-lab-single-agent \
  --project-id "$(az cognitiveservices account show -n $FOUNDRY -g $RG --query id -o tsv)/projects/$PROJECT" \
  --model-deployment gpt-5.4 --deploy-mode code --runtime python_3_14 \
  --entry-point main.py --protocol responses --force
azd env set AZURE_AI_MODEL_DEPLOYMENT_NAME gpt-5.4 && azd env set AI_AGENT_PENDING_PROVISION ""
```

**② 로컬 실행 & 테스트** — 배포 전에 동작을 먼저 확인합니다 (터미널 2개)
```bash
# 터미널 1 — 로컬에 /responses 서버를 띄움 (http://localhost:8088, 블로킹)
azd ai agent run

# 터미널 2 — 로컬 에이전트에 질문
azd ai agent invoke --local "Microsoft Agent Framework가 무엇인가요?"
```
> azd 없이 바로 돌려보려면: `cd $REPO/src/hosted_agents/01_single_agent` → `.env.example`을 `.env`로 복사·입력 →
> `pip install -r requirements.txt && python main.py`(로컬 `:8088`), 다른 터미널에서 `curl localhost:8088/responses ...`로 호출.

**③ 배포 & 호출** — 로컬 서버를 `Ctrl+C`로 끈 뒤
```bash
azd provision --no-prompt && azd deploy --no-prompt        # ZIP 업로드 → Foundry 원격 빌드·호스팅
azd ai agent invoke "Microsoft Agent Framework가 무엇인가요?"   # 배포된 엔드포인트로 호출
```
`azd deploy` 출력의 **플레이그라운드 링크**로 웹 UI에서도 대화할 수 있습니다. REST·로그 등은 **8.5** 참고.

> 💡 **빈 폴더에서 init 하는 이유**: init이 작업 폴더에 `azure.yaml`을 생성하므로, 매니페스트가 있는 폴더에서
> 실행하면 `target is inside the manifest directory` 오류가 납니다. · 모델이 새로 만들어지면 init이 만든
> `azure.yaml`의 `deployments` 블록을 지우고 `azd env set`으로 기존 배포(`gpt-5.4`)를 고정하세요.
> · 예제별 전체 명령은 각 폴더 [`README.md`](src/hosted_agents/)에도 있습니다.

### 8.4 예제별 배포 명령 (7개 예제)

| 예제 | `--agent-name` | 유형 | 배포 전 전제 | 원격 테스트 질문(예) |
|------|----------------|------|--------------|----------------------|
| [`01_single_agent/`](src/hosted_agents/01_single_agent/) | `maf-lab-single-agent` | 단일 에이전트 | — | `Microsoft Agent Framework가 무엇인가요?` |
| [`02_sequential_workflow/`](src/hosted_agents/02_sequential_workflow/) | `maf-lab-sequential-workflow` | 워크플로우 `.as_agent()` | — | `Kubernetes 클러스터 비용 최적화 전략` |
| [`03_group_chat/`](src/hosted_agents/03_group_chat/) | `maf-lab-group-chat` | 워크플로우 `.as_agent()` | — | `AI 기반 개인화 추천 시스템 도입 방안을 토론해줘` |
| [`04_concurrent_workflow/`](src/hosted_agents/04_concurrent_workflow/) | `maf-lab-concurrent` | 워크플로우 `.as_agent()` | — | `게스트 결제 + 단말 캐시 설계안을 검토해줘` |
| [`05_mcp_agent/`](src/hosted_agents/05_mcp_agent/) | `maf-lab-mcp-agent` | 단일 + 서버측 MCP | — | `Handoff가 무엇인지 공식 문서 근거로 설명해줘` |
| [`06_rag_agent/`](src/hosted_agents/06_rag_agent/) | `maf-lab-rag-agent` | 단일 + 검색 함수 도구 | ① 인덱스 시드 ② 에이전트 ID RBAC | `Pro 요금제는 얼마이고 기술 지원은 얼마나 빨리 받나요?` |
| [`06_rag_agent_foundry_iq/`](src/hosted_agents/06_rag_agent_foundry_iq/) | `maf-lab-rag-iq-agent` | 단일 + 컨텍스트 프로바이더 | ① 지식 베이스 생성 ② 에이전트 ID RBAC | `Pro 요금제는 얼마이고 기술 지원은 얼마나 빨리 받나요?` |

8.3의 ①에서 **`azd ai agent init` 줄만** 아래로 바꾸면 됩니다(나머지 단계는 동일). 공통 인자는 변수로 묶었습니다.

```bash
PROJECT_ID="$(az cognitiveservices account show -n $FOUNDRY -g $RG --query id -o tsv)/projects/$PROJECT"
R="$REPO/src/hosted_agents"
COMMON="--no-prompt --project-id $PROJECT_ID --model-deployment gpt-5.4 --deploy-mode code --runtime python_3_14 --entry-point main.py --protocol responses --force"

# 원하는 예제의 줄을 '그 예제 전용 빈 폴더'에서 실행하세요 (한 폴더 = 한 에이전트)
azd ai agent init -m "$R/01_single_agent/agent.manifest.yaml"          --agent-name maf-lab-single-agent        $COMMON
azd ai agent init -m "$R/02_sequential_workflow/agent.manifest.yaml"   --agent-name maf-lab-sequential-workflow $COMMON
azd ai agent init -m "$R/03_group_chat/agent.manifest.yaml"            --agent-name maf-lab-group-chat          $COMMON
azd ai agent init -m "$R/04_concurrent_workflow/agent.manifest.yaml"   --agent-name maf-lab-concurrent          $COMMON
azd ai agent init -m "$R/05_mcp_agent/agent.manifest.yaml"             --agent-name maf-lab-mcp-agent           $COMMON
azd ai agent init -m "$R/06_rag_agent/agent.manifest.yaml"             --agent-name maf-lab-rag-agent           $COMMON
azd ai agent init -m "$R/06_rag_agent_foundry_iq/agent.manifest.yaml"  --agent-name maf-lab-rag-iq-agent        $COMMON
```

init 뒤에는 8.3의 ②(로컬 테스트)·③(배포·호출)을 그대로 따릅니다. **유형별 차이와 05·06의 추가 처리**는 다음과 같습니다.

- **02·03·04 (워크플로우)** — `main.py`가 `SequentialBuilder`/`GroupChatBuilder`/`ConcurrentBuilder`의
  `.build().as_agent()`로 워크플로우를 단일 에이전트로 감싸 호스팅합니다. 추가 리소스 없이 01과 동일하게 배포합니다.
- **05 (MCP)** — 호스팅에서는 클라이언트 측 `MCPStreamableHTTPTool` 대신 **서버 측**
  `client.get_mcp_tool(..., approval_mode="never_require")`로 등록합니다(Foundry 게이트웨이가 MCP 호출 대행).
  공개 Learn MCP는 인증이 필요 없습니다. 인증이 필요한 서버는 `get_mcp_tool(headers=...)`로 헤더를 전달합니다.
- **06 (RAG 하이브리드)** — ① 먼저 루트에서 `python src/06_rag_agent.py`를 한 번 실행해
  인덱스(`maf-lab-knowledge-v1`)를 시드합니다. ② `azd env set`으로 `SEARCH_SERVICE_ENDPOINT`·
  `SEARCH_INDEX_NAME`·`AZURE_OPENAI_ENDPOINT`·`EMBEDDING_DEPLOYMENT_NAME`·`AZURE_OPENAI_API_VERSION`을
  주입합니다. ③ **배포 후** 에이전트 인스턴스 관리 ID에 RBAC을 부여합니다(아래).
- **06 변형 (Foundry IQ)** — ① 먼저 루트에서 `python src/06_rag_agent_foundry_iq.py`를 실행해
  지식 베이스(`maf-lab-knowledge-iq-v1-kb`)를 생성합니다. ② `SEARCH_SERVICE_ENDPOINT`·
  `SEARCH_KNOWLEDGE_BASE_NAME`을 주입합니다. ③ 배포 후 에이전트 ID에 **Search Index Data Reader**를 부여합니다.

```bash
# 06 · 06-IQ 전용: 배포 후 에이전트 인스턴스 관리 ID에 데이터 접근 권한 부여
azd ai agent show                          # 출력에서 Instance Identity Principal ID 확인
PRINC="<위에서 확인한 Principal ID>"
SEARCH_SCOPE="<Search 서비스 리소스 ID>"     # az resource show ... --query id -o tsv
az role assignment create --assignee-object-id "$PRINC" --assignee-principal-type ServicePrincipal \
  --role "Search Index Data Reader" --scope "$SEARCH_SCOPE"
# 06(하이브리드)은 임베딩도 호출하므로 추가로:
FOUNDRY_SCOPE="<Foundry(AIServices) 리소스 ID>"
az role assignment create --assignee-object-id "$PRINC" --assignee-principal-type ServicePrincipal \
  --role "Cognitive Services OpenAI User" --scope "$FOUNDRY_SCOPE"
```
> 권한 전파에 1~2분 걸리며, 누락 시 첫 호출이 `session_not_ready`로 끝납니다.

### 8.5 테스트 방법 더 보기 (상태 · REST · 포털)

가장 간단한 호출은 **8.3의 `azd ai agent invoke "<질문>"`** 입니다. 단일·워크플로우 모두 같은
`/responses` 프로토콜이라 호출 방법이 동일합니다. 그 밖의 방법은 다음과 같습니다.

**① 상태 확인 · 로그 (azd)**
```bash
azd ai agent show                 # "Active"가 되어야 호출 가능
azd ai agent invoke "<질문>"       # 배포된 엔드포인트로 호출 (--local 이면 로컬 서버로)
azd ai agent monitor --follow     # (선택) 컨테이너 로그·트레이스 실시간
```

**② REST로 직접 호출 (언어 무관·CI 연동)** — 전용 엔드포인트에 Entra 토큰을 실어 호출합니다.
```bash
BASE_URL="https://<account>.services.ai.azure.com/api/projects/<project>"
TOKEN=$(az account get-access-token --resource https://ai.azure.com --query accessToken -o tsv)

# <에이전트-이름>은 8.4 표의 값(예: maf-lab-single-agent / maf-lab-rag-agent)
curl -X POST "$BASE_URL/agents/<에이전트-이름>/endpoint/protocols/openai/responses?api-version=v1" \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"input": "<질문>", "store": false}'
#  본문에 "stream": true 를 추가하면 서버-전송 이벤트(SSE)로 토큰을 스트리밍받습니다.
```

**③ 포털 플레이그라운드** — [Foundry 포털](https://ai.azure.com) → **Build → Agents → 해당 에이전트
→ Open in playground** 에서 UI로 바로 대화 테스트.

> 컨테이너 안의 호출 신원은 **에이전트 전용 관리 ID**이고, 외부에서 호출하는 사용자/서비스는
> 해당 Foundry 프로젝트에 대한 호출 권한이 필요합니다.

### 8.6 (대안) 컨테이너 이미지로 배포

코드(ZIP) 대신 각 폴더의 `Dockerfile`(`python:3.14.5-slim`, 포트 `8088`)로 **직접 빌드한 이미지**를
배포할 수도 있습니다. `init` 시 `--deploy-mode container`(런타임은 Dockerfile이 정의하므로 `--runtime` 생략)로만
바꾸면 됩니다. 단, **`linux/amd64`** 이미지가 필요하고(Apple Silicon은 `docker build --platform linux/amd64 .`),
Azure Container Registry가 추가로 필요합니다(azd가 **AcrPull** 권한 자동 부여).

> 관측(트레이싱): Hosted Agent는 **server-side 트레이싱**이라 **코드 변경이 필요 없습니다**.
> Foundry 프로젝트에 **Application Insights를 연결**하면 자동으로 켜지며(런타임이
> `APPLICATIONINSIGHTS_CONNECTION_STRING`을 주입), 배포 후 포털 **Assets → 에이전트 →
> Traces 탭**에서 모델·도구 호출을, Application Insights에서 토큰·비용 메트릭을 확인합니다.
> 연결은 **배포 전·후 어느 시점이든** 가능하지만(연결 후 수 분 내 적용, 이미 배포된
> 에이전트도 **재배포 불필요**), **배포 전에 연결**해두면 첫 호출부터 빠짐없이 추적되므로
> 권장합니다. 연결 방법은 [§1.2 추적 활성화](#12-azure-리소스-프로비저닝)를 참고하세요.
> 폴더별 전체 명령·환경 변수·트러블슈팅은 각 폴더의 [`README.md`](src/hosted_agents/)를 참고하세요.

---

## 부록 A. 트러블슈팅

| 증상 | 해결 |
|------|------|
| `PROJECT_ENDPOINT 환경 변수를 설정해주세요` | 루트 `.env`에 엔드포인트/모델 입력 후 경로 확인 |
| 인증 실패 (`AzureCliCredential`) | `az login` 재실행, `az account set`으로 구독 선택 |
| `az`에 Foundry 명령 없음 | `az upgrade --yes`로 2.81.0+ 업그레이드 |
| `ImportError: agent_framework...` | `pip install -U agent-framework`, 가상환경 활성화 확인 |
| Workflow 출력이 `WorkflowEvent(...)` 객체로 보임 | `print(result)` 대신 `result.get_outputs()`(Sequential/Concurrent) / 이벤트의 `AgentExecutorResponse`(GroupChat)로 추출 |
| MCP 도구를 호출 안 함 | `tools=` 전달 누락, `async with mcp_tool:` 밖에서 실행, 서버 URL 확인 |
| RAG가 문서 밖 내용을 지어냄 | 검색 결과 빈약 또는 "추측 금지" 지시문 누락 |
| GroupChat이 끝나지 않음 | `max_rounds` 미설정 |
| Hosted Agent: `ModuleNotFoundError: agent_framework_foundry_hosting` | `pip install agent-framework-foundry-hosting` (배포 시점 의존성) |
| Hosted Agent: `azd ai agent` 명령 없음 | `azd ext install azure.ai.agents`, `azd auth login` |
| Hosted Agent: 배포 후 ARM 이미지 오류 | `linux/amd64` 필요 — `docker build --platform linux/amd64 .` |
| Hosted Agent: 인증 실패 | 컨테이너는 `DefaultAzureCredential`(관리 ID) 사용, 로컬은 `az login` |

## 부록 B. 참고 자료

### 프로젝트 문서

- [Hosted Agent 배포 예제](src/hosted_agents/) — 예제별 배포·원격 테스트(폴더별 `README.md`). 개요는 [Part 8](#part-8-hosted-agent-배포--maf-에이전트워크플로우를-관리형으로) 참고.

### 외부 링크

- [Microsoft Agent Framework (GitHub)](https://github.com/microsoft/agent-framework)
- [Microsoft Foundry 문서](https://learn.microsoft.com/azure/foundry/)
- [MCP 프로토콜 명세](https://modelcontextprotocol.io/)
- [Microsoft Learn MCP 서버](https://learn.microsoft.com/training/support/mcp)
