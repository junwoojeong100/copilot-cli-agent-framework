# GitHub Copilot CLI로 만드는 Microsoft Agent Framework 실습

> **터미널에서 GitHub Copilot CLI와 대화하며, Microsoft Agent Framework 기반의 멀티 에이전트를
> 단계별로 직접 만들어보는 자체 완결형 핸즈온.**

이 저장소 하나로 실습이 완결됩니다. `src/`에 6가지 Agent Framework 예제(4가지 멀티 에이전트
패턴 + MCP 도구 연동 + RAG)가 있고,
`.github/`에는 Copilot CLI/Chat를 "조종"하는 설정(인스트럭션·프롬프트·에이전트·스킬)이,
루트에는 안전 가드레일 `AGENTS.md`가 들어 있습니다. 또한 `.copilot/mcp-config.json`에는
**Azure · GitHub · Microsoft Learn** MCP 서버가 미리 구성되어 있습니다.

---

## 목차

- [Part 0. 전체 그림](#part-0-전체-그림)
- [Part 1. 사전 준비](#part-1-사전-준비)
- [Part 2. Copilot CLI 시작하기](#part-2-copilot-cli-시작하기)
- [Part 3. Copilot을 "조종"하는 `.github/` 설정](#part-3-copilot을-조종하는-github-설정)
- [Part 4. 단일 에이전트](#part-4-단일-에이전트)
- [Part 5. 순차(Sequential) 워크플로우](#part-5-순차sequential-워크플로우)
- [Part 6. GroupChat 워크플로우](#part-6-groupchat-워크플로우)
- [Part 7. 동시(Concurrent) 워크플로우](#part-7-동시concurrent-워크플로우)
- [Part 8. MCP 도구 연동 에이전트](#part-8-mcp-도구-연동-에이전트)
- [Part 9. RAG — 검색 증강 생성](#part-9-rag--검색-증강-생성)
- [Part 10. Copilot CLI 멀티 에이전트 패턴으로 개발하기](#part-10-copilot-cli-멀티-에이전트-패턴으로-개발하기)
- [Part 11. 바이브 코딩 — 설정만으로 코드 생성하기](#part-11-바이브-코딩--설정만으로-코드-생성하기)
- [Part 12. 가드레일 (AGENTS.md)](#part-12-가드레일-agentsmd)
- [Part 13. (심화) Foundry Agent SDK v2 + MAF 오케스트레이션](#part-13-심화-foundry-agent-sdk-v2--maf-오케스트레이션)
- [Part 14. (심화) Hosted Agent 배포 — MAF 에이전트·워크플로우를 관리형으로](#part-14-심화-hosted-agent-배포--maf-에이전트워크플로우를-관리형으로)
- [부록 A. 트러블슈팅 / 부록 B. 참고 자료](#부록-a-트러블슈팅)

---

## 프로젝트 구조

```
.
├── README.md                       # 이 가이드
├── AGENTS.md                       # 에이전트 공통 가드레일 (push 금지·영문 커밋·PR 규칙)
├── requirements.txt                # Python 의존성 (실습 01~06)
├── requirements-foundry-sdk-v2.txt # Foundry Agent SDK v2 예제 전용 의존성 (오버레이)
├── .env.example                    # 환경변수 템플릿
├── .copilot/
│   └── mcp-config.json             # MCP 서버 설정 (azure · github · microsoftLearn)
├── .github/
│   ├── copilot-instructions.md     # 프로젝트 전역 인스트럭션
│   ├── instructions/               # python · azure · korean · git-commit 규칙
│   ├── prompts/                    # add-agent · review-code (재사용 프롬프트)
│   ├── agents/                     # orchestrator · reviewer · debugger (커스텀 에이전트)
│   └── skills/
│       └── agent-framework-codegen/SKILL.md   # MAF 코드 생성 패턴
└── src/                            # Microsoft Agent Framework 예제
    ├── 01_single_agent.py          # 단일 에이전트
    ├── 02_sequential_workflow.py   # 순차 (분석가→작가→편집자)
    ├── 03_group_chat.py            # GroupChat (다중 협업)
    ├── 04_concurrent_workflow.py   # 동시 (보안·성능·UX 병렬 검토)
    ├── 05_mcp_agent.py             # MCP 도구 연동 (외부 시스템 호출)
    ├── 06_rag_agent.py             # RAG (검색 증강 생성)
    ├── _streaming.py               # 스트리밍 출력 공용 헬퍼 (전 예제 공유)
    ├── foundry_sdk_v2/             # (심화) Foundry Agent SDK v2로 생성 + MAF 오케스트레이션
    │   ├── _foundry_agents.py      # SDK v2 에이전트 생성·정리·추적 헬퍼 (FoundryAgent 래핑)
    │   ├── _rag_search.py          # RAG 검색·증강 로직 (Azure AI Search, 루트 06 미러)
    │   ├── 01_single_agent.py      # 단일 에이전트
    │   ├── 02_sequential_workflow.py   # 순차 (SequentialBuilder)
    │   ├── 03_group_chat.py        # GroupChat (GroupChatBuilder)
    │   ├── 04_concurrent_workflow.py   # 동시 (ConcurrentBuilder)
    │   ├── 05_mcp_agent.py         # MCP 도구 연동 (서버 측 MCPTool)
    │   └── 06_rag_agent.py         # RAG (Azure AI Search 검색 + SDK v2 생성)
    └── hosted_agents/              # (심화) MAF 에이전트·워크플로우를 Foundry Hosted Agent로 배포
        ├── 01_single_agent/        # 단일 에이전트 호스팅 (ResponsesHostServer)
        ├── 02_sequential_workflow/ # 순차 워크플로우 호스팅 (Workflow.as_agent())
        ├── 03_group_chat/          # GroupChat 호스팅 (Workflow.as_agent())
        ├── 04_concurrent_workflow/ # 동시 워크플로우 호스팅 (Workflow.as_agent())
        ├── 05_mcp_agent/           # MCP 도구 연동 호스팅 (get_mcp_tool)
        └── 06_rag_agent/           # RAG 호스팅 (하이브리드 검색 함수 도구)
```

---

## Part 0. 전체 그림

목표는 Copilot CLI의 도움을 받아 **고객 지원 멀티 에이전트**를 단계적으로 완성하는 것입니다.

```
        ┌──────────────────────────────────────────────────────────────┐
        │  개발자  ──(자연어 지시)──▶  GitHub Copilot CLI                │
        │                                  │                            │
        │            .github/ 설정 ────────┤  (페르소나·규칙·스킬 주입)  │
        │            AGENTS.md  ───────────┘  (안전 가드레일)            │
        └──────────────────────────────────┬───────────────────────────┘
                                            ▼  코드 생성/리뷰/실행
        ┌──────────────────────────────────────────────────────────────┐
        │           Microsoft Agent Framework  (Python)                │
        │   Single → Sequential → GroupChat → Concurrent → MCP · RAG   │
        │                          │                                   │
        │                          ▼  FoundryChatClient                │
        │                 Azure AI Foundry (gpt-5.4 배포)              │
        └──────────────────────────────────────────────────────────────┘
```

| Part | 무엇을 하나 |
|------|-------------|
| 2~3 | Copilot CLI 설치 + `.github/` 설정 이해 |
| 4 | Agent Framework 단일 에이전트 실행 |
| 5~7 | Sequential / GroupChat / Concurrent Workflow |
| 8 | MCP 도구 연동 — 에이전트가 외부 시스템 호출 |
| 9 | RAG — 검색 증강 생성으로 근거 기반 답변 |
| 10 | Copilot CLI 멀티 에이전트 패턴(`--agent`)으로 개발 가속 |
| 11 | 바이브 코딩 — 설정만으로 새 기능 자동 생성 |
| 12 | 안전 가드레일 적용 |

### 0.1 핵심 기술 6가지 — 기능과 장점

| 기술 | 무엇인가 | 핵심 기능 | 장점 |
|------|----------|-----------|------|
| **GitHub Copilot CLI** | 터미널에서 동작하는 에이전틱 코딩 도구 | 자연어 지시 → 계획·실행·검증 루프, 슬래시 커맨드(`/plan`·`/fleet`·`/model`), MCP·커스텀 에이전트 확장 | IDE 없이 터미널·CI에서 동작, 명령 실행 전 승인으로 안전, 모델 자유 선택 |
| **Custom Agent**<br/>(`.github/agents/*.agent.md`) | 역할·도구가 제한된 전용 에이전트 | frontmatter로 `description`·`tools`·`model` 지정, `copilot --agent <name>` 실행 | 역할 격리(리뷰어=읽기전용)로 안전·집중, 재사용·팀 공유 |
| **Skill**<br/>(`.github/skills/*/SKILL.md`) | Copilot에 주입하는 전문 지식·패턴 묶음 | `description`으로 트리거, 필요 시에만 본문 로드(점진적 공개) | 정확한 SDK 호출 유도, 토큰 절약, 환각 감소 |
| **Instructions**<br/>(`.github/*instructions.md`) | 항상/조건부로 적용되는 규칙 | `copilot-instructions.md`(전역) + `instructions/*`(`applyTo` 글롭) | 일관된 스타일·규칙 자동 준수, 반복 지시 제거 |
| **Microsoft Agent Framework** | 에이전트·멀티 에이전트 오케스트레이션 오픈소스 Python SDK (Semantic Kernel·AutoGen 통합 후속) | `Agent`, Handoff·GroupChat·Workflow 오케스트레이션, MCP 도구, 미들웨어·관측성 | 단일 SDK로 단순→복잡 확장, 모델/클라이언트 추상화, 표준 MCP 연동 |
| **Microsoft Foundry**<br/>(Azure AI Foundry) | 모델 배포·평가·관측을 제공하는 Azure 통합 AI 플랫폼 | 프로젝트 단위 리소스, 모델 카탈로그·배포, `FoundryChatClient` 연결, Entra ID 인증 | 관리형 호스팅, 키 없는(`AzureCliCredential`) 엔터프라이즈 보안·거버넌스 |

---

## Part 1. 사전 준비

### 1.1 도구

| 도구 | 용도 | 설치 |
|------|------|------|
| **GitHub Copilot 구독** | Copilot CLI/Chat | <https://github.com/features/copilot> |
| **GitHub Copilot CLI** | 터미널 AI 에이전트 | `brew install copilot-cli` / `winget install GitHub.Copilot` |
| **Node.js 22+** | Copilot CLI 런타임 + Azure MCP 서버(`npx`) | <https://nodejs.org> |
| **Python 3.10+** | Agent Framework 코드 | <https://python.org> |
| **Azure CLI 2.81.0+** | Foundry 인증 + Azure MCP 서버 자격증명 | `az upgrade --yes` |
| **GitHub PAT** | GitHub MCP 서버 인증 (`github` 블록 사용 시 필수, 미사용 시 선택) | <https://github.com/settings/tokens> |

### 1.2 Azure 리소스 프로비저닝

예제 실행에는 **Azure AI Foundry 리소스·프로젝트·모델 배포**가 필요하고, 실습 6(RAG)에는
추가로 **Azure AI Search 서비스**가 필요합니다. 포털에서 만들어도 되지만, 아래 `az` CLI로
한 번에 프로비저닝할 수 있습니다. (Foundry 프로젝트·모델은 [Azure AI Foundry 포털](https://ai.azure.com)에서도 생성 가능합니다.)

```bash
az login

# 0) 변수 설정 (이름은 전역 고유해야 하며, 리전은 모델 가용성에 맞게 조정)
RG=rg-maf-lab
LOCATION=eastus2
FOUNDRY=foundry-maf-lab          # Foundry(AIServices) 리소스 이름
PROJECT=proj-maf-lab             # Foundry 프로젝트 이름
SEARCH=search-maf-lab            # Azure AI Search 서비스 이름

az group create -n $RG -l $LOCATION

# 1) Foundry(AIServices) 리소스 생성 (키리스 AAD 인증을 위해 custom-domain 지정)
az cognitiveservices account create \
  -n $FOUNDRY -g $RG -l $LOCATION \
  --kind AIServices --sku S0 --custom-domain $FOUNDRY --yes

# 2) Foundry 프로젝트 생성
az cognitiveservices account project create \
  -n $FOUNDRY -g $RG -l $LOCATION --project-name $PROJECT

# (선택) 배포 가능한 모델·버전 확인
az cognitiveservices account list-models -n $FOUNDRY -g $RG -o table

# 3) 채팅 모델 배포 (실습 1~6) — 리전에서 사용 가능한 버전으로 변경
az cognitiveservices account deployment create \
  -n $FOUNDRY -g $RG \
  --deployment-name gpt-5.4 \
  --model-name gpt-5.4 --model-version 2026-03-05 --model-format OpenAI \
  --sku-name GlobalStandard --sku-capacity 10

# 4) 임베딩 모델 배포 (실습 6 RAG 전용)
az cognitiveservices account deployment create \
  -n $FOUNDRY -g $RG \
  --deployment-name text-embedding-3-large \
  --model-name text-embedding-3-large --model-version 1 --model-format OpenAI \
  --sku-name Standard --sku-capacity 10

# 5) Azure AI Search 서비스 생성 (실습 6 RAG 전용)
#    --auth-options aadOrApiKey: 키리스(Entra ID) 데이터플레인 접근을 켭니다.
#    (기본값은 API 키 전용이라, 생략하면 RAG 실행 시 'Forbidden' 오류가 납니다.)
#    리전이 용량 부족(InsufficientResourcesAvailable)이면 다른 리전을 사용하세요.
az search service create -n $SEARCH -g $RG -l $LOCATION --sku basic \
  --auth-options aadOrApiKey

# 6) 권한(RBAC) — 본인 계정에 데이터플레인 역할 부여 (키리스 인증)
ME=$(az ad signed-in-user show --query id -o tsv)
ACC_ID=$(az cognitiveservices account show -n $FOUNDRY -g $RG --query id -o tsv)
SEARCH_ID=$(az resource show -g $RG -n $SEARCH \
  --resource-type Microsoft.Search/searchServices --query id -o tsv)

az role assignment create --assignee $ME --role "Cognitive Services User" --scope $ACC_ID
az role assignment create --assignee $ME --role "Cognitive Services OpenAI User" --scope $ACC_ID
az role assignment create --assignee $ME --role "Search Service Contributor"     --scope $SEARCH_ID
az role assignment create --assignee $ME --role "Search Index Data Contributor"  --scope $SEARCH_ID
az role assignment create --assignee $ME --role "Search Index Data Reader"       --scope $SEARCH_ID
```

> **RAG 인덱스 생성**: 별도 명령이 필요 없습니다. 실습 6의 `06_rag_agent.py`가 **첫 실행 시
> 인덱스를 자동 생성**하고 문서를 임베딩·업로드합니다(멱등). 위에서 만든 **Search 서비스**만 있으면 됩니다.

> **이미 만든 Search 서비스에서 'Forbidden'이 난다면** 키리스(Entra ID) 인증이 꺼져 있는
> 경우입니다. 다음으로 활성화하세요.
> ```bash
> az search service update -n $SEARCH -g $RG --auth-options aadOrApiKey
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
# (심화) Foundry Agent SDK v2 예제도 실행하려면 — 오버레이 의존성 추가 설치
pip install -r requirements-foundry-sdk-v2.txt
cp .env.example .env        # 아래 값 입력
az login                    # 예제는 AzureCliCredential로 이 로그인 세션을 사용
```

`.env` 값 (실습 1~5는 상단 2줄만 있으면 동작, 실습 6 RAG는 전체 필요):

```bash
# 실습 1~6 공통 (Foundry 채팅)
PROJECT_ENDPOINT=https://your-resource.services.ai.azure.com/api/projects/your-project
MODEL_DEPLOYMENT_NAME=gpt-5.4

# 실습 6 (RAG) — Azure AI Search + 임베딩
SEARCH_SERVICE_ENDPOINT=https://your-search-service.search.windows.net
SEARCH_INDEX_NAME=maf-lab-knowledge-v1
AZURE_OPENAI_ENDPOINT=https://your-resource.cognitiveservices.azure.com/
EMBEDDING_DEPLOYMENT_NAME=text-embedding-3-large
AZURE_OPENAI_API_VERSION=2024-10-21
```

---

## Part 2. Copilot CLI 시작하기

```bash
# 설치 (전 플랫폼, Node.js 22+ 필요)
npm install -g @github/copilot
# 또는 macOS/Linux: curl -fsSL https://gh.io/copilot-install | bash
# 또는: brew install copilot-cli   /   winget install GitHub.Copilot

# 실행 (대화형 세션)
copilot
```

자주 쓰는 슬래시 커맨드:

```text
/plan      # 구현 계획 수립 (실행 전 설계)
/fleet     # 병렬 서브에이전트 실행
/model     # 모델 선택 (Claude Sonnet/Opus, GPT-5 등)
/diff      # 변경사항 리뷰
/pr        # PR 생성/관리
```

특성: **에이전트 코딩**(계획→실행→검증), **안전 실행**(명령 실행 전 승인, 신뢰 환경에서만 `--yolo`),
**MCP 확장**, **커스텀 에이전트**(`copilot --agent <name>`).

> 💡 이 실습에서는 Copilot CLI에게 "이런 에이전트를 만들어줘"라고 지시하고, 생성된 코드를
> 검토·실행합니다. `src/`의 예제는 그 결과물의 완성본입니다.

---

## Part 3. Copilot을 "조종"하는 `.github/` 설정

Copilot CLI/Chat는 작업 디렉토리의 `.github/` 설정과 `AGENTS.md`를 읽어 **동작 방식을 바꿉니다.**

```text
.github/
├── copilot-instructions.md   # 전역 페르소나·코딩 스타일·프로젝트 규칙
├── instructions/             # 경로/언어별 세부 규칙
│   ├── python.instructions.md
│   ├── azure.instructions.md
│   ├── korean.instructions.md
│   └── git-commit.instructions.md
├── prompts/                  # 재사용 프롬프트 (VS Code Copilot Chat에서 /프롬프트명)
│   ├── add-agent.prompt.md
│   └── review-code.prompt.md
├── agents/                   # 커스텀 에이전트 (copilot --agent <name>)
│   ├── orchestrator.agent.md
│   ├── reviewer.agent.md
│   └── debugger.agent.md
└── skills/
    └── agent-framework-codegen/SKILL.md   # MAF 코드 생성 패턴 주입
```

| 구성요소 | 역할 |
|----------|------|
| `copilot-instructions.md` | 프로젝트 전반에 항상 적용되는 규칙 |
| `instructions/*` | `applyTo` 글롭으로 특정 파일/언어에만 적용되는 규칙 |
| `prompts/*` | 반복 작업 템플릿. **VS Code Copilot Chat**에서 `/프롬프트명`으로 호출(CLI는 자연어로 동일 요청) |
| `agents/*` | `copilot --agent`로 실행하는 역할별 에이전트 |
| `skills/*` | SDK 사용법·패턴을 Copilot에 "교육"하는 전문 지식 |

#### `SKILL.md` 구조 (Skill)

| 필드 | 설명 |
|------|------|
| `name` | 스킬 식별자 |
| `description` | **언제 쓰는지**(USE FOR / DO NOT USE FOR). Copilot이 이 설명을 보고 로드 여부를 결정 |
| 본문 | SDK 패턴·예제. 관련 작업일 때만 로드됨(**점진적 공개** → 토큰 절약) |

#### `*.agent.md` frontmatter (Custom Agent)

| 필드 | 설명 |
|------|------|
| `name` | 선택 (생략 시 파일명 사용) |
| `description` | **필수** — 에이전트의 역할 |
| `tools` | 허용 도구 별칭: `read`·`search`·`edit`·`execute`·`agent`·`web` (생략=전체 허용, `[]`=없음) |
| `model` / `target` | 선택 — 사용할 모델, 실행 대상(`vscode`/`github-copilot`) |

> ✅ **체크포인트**: 이 폴더에서 `copilot`을 실행하면, 생성되는 코드가 위 규칙(async·한국어·
> `AzureCliCredential`·`FoundryChatClient` 패턴)을 자동으로 따릅니다.

---

## Part 4. 단일 에이전트

> **Microsoft Agent Framework(MAF)** 는 에이전트 생성부터 멀티 에이전트 오케스트레이션까지 하나의
> Python SDK로 제공하는 오픈소스 프레임워크입니다(Semantic Kernel·AutoGen의 통합 후속).
> **Microsoft(Azure AI) Foundry** 는 모델을 배포·관리하는 Azure 플랫폼으로, MAF의
> `FoundryChatClient`가 여기에 연결합니다. 인증은 키 없이 `AzureCliCredential`(= `az login` 세션,
> Entra ID)을 사용해 엔터프라이즈 보안을 유지합니다.

코드: [`src/01_single_agent.py`](src/01_single_agent.py)

> **Copilot CLI 프롬프트 예시**
> `src/01_single_agent.py를 만들어줘. agent_framework의 Agent와 FoundryChatClient로 Foundry에
> 연결하고, "기술 어시스턴트" 에이전트가 질문에 한국어로 답하게. AzureCliCredential, async로.`

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
async for update in agent.run("Microsoft Agent Framework가 무엇인가요?", stream=True):
    print(update.text, end="", flush=True)
print()
```

> 💡 **스트리밍 출력**: 모든 예제(01~06)는 답변을 **토큰 단위로 실시간 출력**해 생성 과정을
> 눈으로 볼 수 있습니다. 공통 로직은 [`src/_streaming.py`](src/_streaming.py)에 모아 두었습니다.
> - `stream_agent(agent, prompt)` — 단일 에이전트 응답을 토큰 단위로 출력하고 전체 텍스트를 반환(01·05·06)
> - `stream_workflow(workflow, message)` — 워크플로우를 스트리밍 실행해 발화자별로 출력(02 Sequential·03 GroupChat·04 Concurrent)

실행:

```bash
python src/01_single_agent.py
```

| 요소 | 설명 |
|------|------|
| `FoundryChatClient` | Azure AI Foundry 프로젝트에 연결하는 채팅 클라이언트 |
| `Agent(name, instructions)` | 모델 + 역할 지시문의 단위 |
| `agent.run(..., stream=True)` | 입력을 받아 응답을 토큰 단위로 스트리밍 생성 |

---

## Part 5. 순차(Sequential) 워크플로우

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

**핵심**:
- `SequentialBuilder`가 참여자 순서대로 **앞 단계의 출력을 다음 단계 입력으로 전달**합니다.
- 각 에이전트는 네이티브 MAF `Agent`이며, 역할은 `instructions`로 부여합니다.
- 참여자 `name`은 도구명이 아니므로 한국어(예: `분석가`)를 그대로 써도 됩니다.
- 더 복잡한 분기·조건부 라우팅이 필요하면 `WorkflowBuilder` + `Case`/`Default`로
  선언적 그래프를 구성할 수 있습니다(상세는 `agent-framework-codegen` 스킬 참조).

```bash
python src/02_sequential_workflow.py
```

---

## Part 6. GroupChat 워크플로우

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

---

## Part 7. 동시(Concurrent) 워크플로우

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

**핵심**:
- `ConcurrentBuilder`가 **모든 참여자에게 같은 입력을 병렬로 전달**하고 결과를 모읍니다.
- 순차 파이프라인과 달리 참여자 간 의존이 없어 **독립적 다관점 평가**에 적합합니다.
- 각 리뷰어의 응답은 도착 순서대로 스트리밍되며, 발화자 라벨로 구분됩니다.

```bash
python src/04_concurrent_workflow.py
```

> ✅ **체크포인트**: Single → Sequential → GroupChat → Concurrent 4가지 패턴의 차이와
> 선택 기준을 설명할 수 있으면 Agent Framework 핵심을 익힌 것입니다.

---

## Part 8. MCP 도구 연동 에이전트

지금까지의 에이전트는 LLM의 내부 지식만 사용했습니다. **MCP(Model Context Protocol)** 도구를
연결하면 에이전트가 외부 시스템(문서 검색, 데이터베이스, API 등)의 기능을 **실시간으로 호출**할 수
있습니다. 여기서는 인증이 필요 없는 공개 서버인 **Microsoft Learn MCP**에 붙여, 에이전트가 공식
문서를 검색해 근거 기반으로 답하도록 만듭니다.

```
[질문] → [에이전트] → (MCP 도구로 Learn 문서 검색) → [출처가 포함된 답변]
```

> 💡 **두 가지 MCP 사용처를 구분하세요.**
> - **Copilot CLI의 MCP** (`.copilot/mcp-config.json`): *개발자(나)* 가 CLI에서 쓰는 도구 (Part 10).
> - **에이전트의 MCP** (`MCPStreamableHTTPTool`): *내가 만든 MAF 에이전트* 가 런타임에 쓰는 도구 (이번 Part).

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
| `headers={...}` | 인증이 필요한 서버는 `{"Authorization": "Bearer ..."}` 추가 |
| `async with mcp_tool:` | 세션 컨텍스트. 진입 시 도구 목록 로드, 종료 시 연결 정리 |
| `tools=` | 에이전트가 사용할 도구 전달. LLM이 필요 시 스스로 호출 |

> 로컬 프로세스형 서버는 `MCPStdioTool`, WebSocket 서버는 `MCPWebsocketTool`을 사용합니다.

```bash
python src/05_mcp_agent.py
```

> ✅ **체크포인트**: 에이전트가 답변에 `[출처]`를 포함하면 MCP 도구 호출이 성공한 것입니다.

---

## Part 9. RAG — 검색 증강 생성

**RAG(Retrieval-Augmented Generation)** 는 질문과 관련된 문서를 **먼저 검색**해 컨텍스트로
주입한 뒤 답하게 하는 패턴입니다. LLM이 모르는 사내 데이터에 근거해 답하게 하고, 환각을 줄입니다.

```
[질문] → [1.검색 Retrieval] → [2.증강 Augmentation] → [3.생성 Generation]
```

이 예제는 **Azure AI Search 하이브리드(키워드 + 벡터) 검색**으로 지식 베이스를 검색합니다.
처음 실행하면 인덱스를 자동 생성하고 문서를 임베딩하여 업로드하므로(자체 완결·멱등),
별도 사전 준비 없이 바로 실행됩니다. 인증은 전부 키리스(`AzureCliCredential`)입니다.

### 핵심 코드

```python
# 0) 임베딩 차원을 모델에서 동적으로 확인 → 인덱스 자동 생성(없을 때만)
dim = len(embed(["차원 확인"])[0])
ensure_index(index_client, index_name, dim)        # HNSW + 코사인, ko.microsoft 분석기

# 1) 문서 임베딩 후 업로드(멱등 upsert) + 인덱싱 반영 대기
seed_documents(search_client, embed)

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

하이브리드 검색은 키워드 검색(BM25)과 벡터 검색을 RRF로 융합합니다. `VectorizedQuery`로 질문
임베딩을 전달하고, `search_text`로 키워드 검색을 동시에 수행합니다. 핵심은 **(1) 검색 품질**과
**(2) "문서 밖 내용은 추측하지 말라"는 지시문**입니다. 이 둘이 RAG의 정확도를 결정합니다.

```bash
python src/06_rag_agent.py
```

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

### 한 단계 더 — Foundry IQ

지식 베이스를 코드에서 관리하는 대신 **Foundry IQ** 지식 베이스로 자동 동기화하고,
`agent_framework.azure`의 `AzureAISearchContextProvider`(semantic / agentic 모드)를 사용하면
검색 단계를 프레임워크에 위임할 수 있습니다.

> ✅ **체크포인트**: 지식 베이스에 없는 질문(예: "배송비는 얼마인가요?")에 에이전트가
> "관련 정보를 찾을 수 없습니다"라고 답하면 RAG가 올바르게 동작하는 것입니다.

---

## Part 10. Copilot CLI 멀티 에이전트 패턴으로 개발하기

`.github/agents/`에 역할별 에이전트를 정의하고 `copilot --agent <name>`으로 실행합니다.
이 저장소에는 `orchestrator`, `reviewer`, `debugger`가 포함되어 있습니다.

```bash
copilot --agent orchestrator --yolo   # 요청 분석 후 최적 패턴 자동 선택
copilot --agent reviewer              # 코드 리뷰 (읽기 전용)
copilot --agent debugger              # 환경/런타임 문제 진단
```

`orchestrator`는 요청을 분석해 4가지 협업 패턴 중 하나를 선택합니다:

| 사용자 의도 | 선택 패턴 |
|------------|----------|
| "구현해줘", "셋업해줘", "마이그레이션" | 📐 Planner-Executor |
| "비교해줘", "장단점", "뭐가 나을까" | ⚔️ Debate & Critic |
| "생성해줘", "리뷰해줘", "개선해줘" | ⚡ Generator-Evaluator |
| "설계하고 구현해줘", "코드 작성하고 리뷰해줘" | 🏗️ Code Generation |

### MCP 서버 연결

`.copilot/mcp-config.json`로 MCP 서버를 Copilot CLI에 붙입니다. 이 저장소에는 **Azure · GitHub ·
Microsoft Learn** 세 가지 서버가 설정되어 있습니다.

```json
{
  "mcpServers": {
    "github": {
      "type": "http",
      "url": "https://api.githubcopilot.com/mcp/",
      "headers": { "Authorization": "Bearer ${GITHUB_PERSONAL_ACCESS_TOKEN}" },
      "tools": ["*"]
    },
    "azure": {
      "type": "local",
      "command": "npx",
      "args": ["-y", "@azure/mcp@latest", "server", "start"],
      "tools": ["*"]
    },
    "microsoftLearn": {
      "type": "http",
      "url": "https://learn.microsoft.com/api/mcp",
      "tools": ["*"]
    }
  }
}
```

| 서버 | 유형 | 용도 | 인증 |
|------|------|------|------|
| **github** | 원격(http) | 이슈·PR·리포지토리 탐색/조작 | PAT — `GITHUB_PERSONAL_ACCESS_TOKEN` 환경변수 |
| **azure** | 로컬(npx) | 구독 내 Azure 리소스 조회·관리 (Foundry 포함) | `az login` 세션 |
| **microsoftLearn** | 원격(http) | Microsoft/Azure 공식 문서·코드 샘플 검색 | 불필요 |

설정 적용 및 확인:

```bash
# 1) GitHub PAT를 환경변수로 등록 (github 서버용)
export GITHUB_PERSONAL_ACCESS_TOKEN=ghp_xxx

# 2) Azure 서버는 npx로 자동 실행되며, Azure CLI 로그인 세션을 사용
az login

# 3) Copilot CLI 세션에서 등록된 MCP 서버 확인
copilot
> /mcp           # 설정된 서버 목록·상태 확인
> /env           # 로드된 MCP 서버·인스트럭션·스킬 확인
```

> 참고: Copilot CLI는 GitHub MCP 서버를 기본 내장하고 있어, 위 `github` 항목 없이도 기본 GitHub
> 기능은 사용할 수 있습니다. 명시적으로 두면 사용할 토큰/도구를 직접 제어할 수 있습니다.
> **단, `github` 블록을 유지하면 `GITHUB_PERSONAL_ACCESS_TOKEN`이 반드시 설정되어 있어야 인증 오류가
> 나지 않습니다.** PAT를 쓰지 않으려면 이 블록을 제거하고 기본 내장 서버를 사용하세요.
> `tools`는 `["*"]`로 모든 도구를 허용하므로, 읽기 전용만 노출하려면 서버 문서의 도구명으로 좁히세요.

> ⚠️ **Azure MCP 권한 주의**: `azure` 서버는 `tools: ["*"]`이므로 구독 리소스를 **조회뿐 아니라
> 변경/삭제**할 수 있습니다. 실제 가능한 작업은 `az login` 계정의 **RBAC 권한** 범위로 제한되며,
> Copilot CLI는 실행 전 명령을 확인받습니다. 조회만 허용하려면 `tools`를 읽기 전용 도구명으로
> 좁히거나, 읽기 권한만 가진 계정으로 `az login` 하세요.

> **실습**: `copilot --agent orchestrator --yolo`를 띄우고
> *"Microsoft Learn에서 Agent Framework Concurrent 오케스트레이션 문서를 찾아 동시 워크플로우에
> 비용 리뷰 전문 에이전트를 추가하고 리뷰해줘"* 라고 요청해 보세요. (Learn 문서 검색 + 코드 생성 + 리뷰 연계)

---

## Part 11. 바이브 코딩 — 설정만으로 코드 생성하기

**바이브 코딩**은 코드를 손으로 쓰는 대신, `.github/`의 instructions·prompts·skills로 의도를
정의하고 Copilot이 코드를 생성하게 하는 방식입니다.

| 개발자가 준비 | Copilot이 수행 |
|---------------|----------------|
| `instructions/` — 기술 스택·코딩 규칙 | 규칙을 지킨 코드 생성 |
| `prompts/` — 반복 작업 템플릿 | 일관된 산출물 생성 |
| `skills/` — SDK 사용법·패턴 | 정확한 SDK 호출 |
| `agents/` — 리뷰/디버그 역할 | 자동 리뷰·디버깅 |

### 실습 흐름

```text
1. (CLI) "UX 리뷰 전문 에이전트를 동시 워크플로우에 추가해줘"라고 자연어로 요청
   (VS Code Copilot Chat이라면 /add-agent 프롬프트로 호출)
2. Copilot이 agent-framework-codegen 스킬 규칙(import·async·instructions)에 맞춰 코드 생성
3. copilot --agent reviewer 로 리뷰 → 수정
4. python src/04_concurrent_workflow.py 로 실행 검증
```

> ✅ **최종 체크포인트**: 직접 만든 `.github/` 설정만으로 Copilot이 새 에이전트/기능을 추가하게
> 만들 수 있으면, 이 실습의 목표를 달성한 것입니다.

---

## Part 12. 가드레일 (AGENTS.md)

루트의 [`AGENTS.md`](AGENTS.md)는 **모든** Copilot 에이전트가 git/외부 명령 실행 전에 따르는
안전 규칙입니다.

| 규칙 | 내용 |
|------|------|
| **Rule 1** | 기능 브랜치 push 허용, **보호 브랜치(main) 직접 push·force push·`--all`/`--mirror` 금지** |
| **Rule 2** | 커밋/PR 메시지는 **영문 + Conventional Commits**(`feat:`, `fix:` …) |
| **Rule 3** | PR은 항상 `--base main` 명시 + `--draft`로 생성 |

```bash
# ✅ 허용
git checkout -b feat/add-cost-reviewer
git add . && git commit -m "feat: add cost reviewer agent to concurrent workflow"
git push -u origin feat/add-cost-reviewer
gh pr create --draft --base main --title "feat: add cost reviewer agent" --body "Summary in English."

# ❌ 금지
git checkout main && git push origin main      # 보호 브랜치 직접 push
git push --force-with-lease origin <branch>     # force push
```

---

## Part 13. (심화) Foundry Agent SDK v2 + MAF 오케스트레이션

실습 01~06은 에이전트를 **MAF `FoundryChatClient`(모델 채팅)** 로 구성합니다. 이 심화
세트는 **에이전트 "생성"은 Microsoft Foundry Agent SDK v2(`azure-ai-projects`)** 가
맡고, **에이전트 "오케스트레이션"은 MAF 워크플로우 빌더**가 맡는 분리 구조를 보여
줍니다. 기존 소스(01~06)는 그대로 두고, 가이드·의존성도 분리했습니다.

> 위치: [`src/foundry_sdk_v2/`](src/foundry_sdk_v2/) · 의존성: `requirements-foundry-sdk-v2.txt`

### 핵심 패턴 — 생성은 SDK v2, 실행은 MAF

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

생성·정리 로직은 [`src/foundry_sdk_v2/_foundry_agents.py`](src/foundry_sdk_v2/_foundry_agents.py)의
`FoundryAgentFactory`로 모았습니다. 실행마다 고유 이름으로 에이전트를 만들고,
`finally`에서 `cleanup()`으로 삭제(베스트 에포트)해 프로젝트에 누적되지 않습니다.

### 예제 목록 / 실행

```bash
pip install -r requirements-foundry-sdk-v2.txt   # 최초 1회 (오버레이 설치)
cd src/foundry_sdk_v2

python 01_single_agent.py        # 단일 에이전트 (스트리밍)
python 02_sequential_workflow.py # 순차: 분석가 → 작가 → 편집자 (SequentialBuilder)
python 03_group_chat.py          # 협업 토론: 기획자·개발자·디자이너 (GroupChatBuilder)
python 04_concurrent_workflow.py # 동시 리뷰: 보안·성능·UX (ConcurrentBuilder)
python 05_mcp_agent.py           # MCP 도구 연동 (서버 측 MCPTool, Microsoft Learn)
python 06_rag_agent.py           # RAG (Azure AI Search 검색 + SDK v2 생성)
```

각 예제는 시작 시 SDK v2로 에이전트를 만들고, MAF로 실행한 뒤, 끝나면 생성한
에이전트를 삭제합니다. 출력은 공용 헬퍼 [`src/_streaming.py`](src/_streaming.py)로
스트리밍 표시합니다.

### MCP·RAG 연동 — 도구/데이터 결합

오케스트레이션(02~04)과 별개로, SDK v2 에이전트도 **외부 도구(MCP)** 와
**외부 데이터(RAG)** 에 연결할 수 있습니다.

- **05 MCP** — `azure.ai.projects.models.MCPTool`로 **서버 측 MCP 도구**를 붙입니다.
  Foundry 서비스가 직접 MCP 서버(`https://learn.microsoft.com/api/mcp`)를 호출하므로
  로컬 함수 호출이 필요 없습니다. 기존 [`src/05_mcp_agent.py`](src/05_mcp_agent.py)의
  **클라이언트 측** `MCPStreamableHTTPTool`(로컬에서 도구 실행)과 대비됩니다.

  | 구분 | 클라이언트 측(루트 05) | 서버 측(SDK v2 05) |
  |------|----------------------|--------------------|
  | 도구 호출 주체 | 로컬 프로세스 | Foundry 서비스 |
  | 클래스 | `MCPStreamableHTTPTool` | `MCPTool` |
  | 승인 | 로컬 제어 | `require_approval="never"` |

  > 서버 측 MCP가 막히는 환경(승인 정책·네트워크)에서는 루트 05의 클라이언트 측
  > 방식으로 폴백하세요.

- **06 RAG** — 검색·증강은 Azure AI Search 하이브리드 검색
  ([`_rag_search.py`](src/foundry_sdk_v2/_rag_search.py), 루트 06과 동일 로직),
  **생성 단계만 SDK v2 에이전트**가 담당합니다. 전 과정 키리스로 동작합니다.
  v2 네이티브 `AzureAISearchTool`(서버 측 검색)은 프로젝트에 Search 연결+인덱스
  등록이 필요해 이 예제에서는 사용하지 않습니다.

### Application Insights 분산 추적 (트레이싱)

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

### ⚠️ Handoff는 제외 — 이유

이 세트에는 **Handoff 예제가 없습니다.** MAF `HandoffBuilder`는 참여자에게
`handoff_to_*` 도구를 **로컬에서 주입·호출**하고 클로닝·미들웨어를 적용하기 위해
네이티브 MAF `Agent`를 요구합니다. SDK v2로 만든 **서버 측 영속 에이전트**는 이
로컬 함수 호출 주입 방식과 맞지 않아(`"chat client does not support function
invoking"`), Handoff에 바로 넣을 수 없습니다.

| MAF 오케스트레이션 | SDK v2 `FoundryAgent` 호환 |
|--------------------|:--------------------------:|
| `SequentialBuilder` | ✅ |
| `GroupChatBuilder` | ✅ |
| `ConcurrentBuilder` | ✅ |
| `HandoffBuilder` | ❌ (네이티브 MAF `Agent` 필요) |

> Handoff 패턴 자체를 학습하려면 `agent-framework-codegen` 스킬의 Handoff 섹션
> ([`.github/skills/agent-framework-codegen/SKILL.md`](.github/skills/agent-framework-codegen/SKILL.md))을
> 참고하세요. 이 패턴은 네이티브 MAF `Agent`(`FoundryChatClient` 기반)로 구성합니다.

---

## Part 14. (심화) Hosted Agent 배포 — MAF 에이전트·워크플로우를 관리형으로

Part 13이 **에이전트 "생성"을 SDK v2로** 바꾸는 접근이라면, 이 파트는 코드를
**그대로 둔 채** MAF 에이전트·워크플로우를 **Microsoft Foundry Hosted Agent**
(관리형 컨테이너)로 **배포**합니다. SDK v2로 재작성하지 않아도 관리형 인프라와
**자동 trace/monitoring**을 그대로 얻는 것이 핵심입니다.

> 위치: [`src/hosted_agents/`](src/hosted_agents/) · 의존성: `agent-framework-foundry-hosting`

### 핵심 패턴 — `ResponsesHostServer`로 호스팅

```python
from agent_framework_foundry_hosting import ResponsesHostServer

# 단일 에이전트
server = ResponsesHostServer(agent)
server.run()                       # /responses 엔드포인트(:8088), 동기 호출

# 워크플로우 → .as_agent()로 감싸 동일하게 호스팅
workflow_agent = SequentialBuilder(participants=[...]).build().as_agent()
server = ResponsesHostServer(workflow_agent)
server.run()
```

- 대화 이력은 호스팅 인프라가 관리하므로 각 에이전트에 `default_options={"store": False}`를 지정합니다.
- 컨테이너에서는 전용 관리 ID로 인증되므로 `DefaultAzureCredential`을 사용합니다.

### 예제 목록

| 폴더 | 원본 | 내용 |
|------|------|------|
| [`01_single_agent/`](src/hosted_agents/01_single_agent/) | `src/01_single_agent.py` | 단일 에이전트 호스팅 |
| [`02_sequential_workflow/`](src/hosted_agents/02_sequential_workflow/) | `src/02_sequential_workflow.py` | 순차 워크플로우(`Workflow.as_agent()`) |
| [`03_group_chat/`](src/hosted_agents/03_group_chat/) | `src/03_group_chat.py` | GroupChat 워크플로우(`Workflow.as_agent()`) |
| [`04_concurrent_workflow/`](src/hosted_agents/04_concurrent_workflow/) | `src/04_concurrent_workflow.py` | 동시 워크플로우(`Workflow.as_agent()`) |
| [`05_mcp_agent/`](src/hosted_agents/05_mcp_agent/) | `src/05_mcp_agent.py` | MCP 도구 연동(서버 측 `get_mcp_tool`) |
| [`06_rag_agent/`](src/hosted_agents/06_rag_agent/) | `src/06_rag_agent.py` | RAG(하이브리드 검색 함수 도구) |

각 폴더는 독립 배포 가능한 azd 프로젝트로 `main.py`·`Dockerfile`·`agent.yaml`·
`agent.manifest.yaml` 등을 포함합니다(`agent.manifest.yaml`은 `azd ai agent init`의
입력, `agent.yaml`은 배포 런타임 스펙).

### 배포 흐름

```bash
pip install agent-framework agent-framework-foundry-hosting
azd ext install azure.ai.agents && azd auth login

cd src/hosted_agents/01_single_agent      # 또는 02_sequential_workflow
azd ai agent init -m ./agent.manifest.yaml   # azd 프로젝트 초기화
azd ai agent run                             # 로컬 호스트(:8088)
azd ai agent invoke --local "질문"            # 호출 테스트
azd provision                                # (필요 시) 리소스 생성
azd deploy                                   # 컨테이너 빌드 → ACR → Foundry 배포
```

배포 후 포털 **Assets → 에이전트 → Traces 탭**에서 단계별 모델 호출을 추적하고,
Application Insights에서 토큰·비용 메트릭을 확인할 수 있습니다(런타임이
`APPLICATIONINSIGHTS_CONNECTION_STRING`을 자동 주입).

### 기존 실습과의 차이

| 기존 실습(01~06) | Hosted Agent 실습 |
|------------------|-------------------|
| 프롬프트 1건 처리 후 종료 | `/responses` HTTP 서버 상시 구동 |
| `asyncio.run(main())` | `server.run()` (동기) |
| `AzureCliCredential` | `DefaultAzureCredential` (컨테이너 관리 ID) |
| 저장소 `.env`(`PROJECT_ENDPOINT`) | Foundry 주입 env(`FOUNDRY_PROJECT_ENDPOINT`) |

> ⚠️ Hosted Agents는 현재 **preview**이며 `linux/amd64` 이미지를 요구합니다.
> 자세한 단계는 각 폴더의 `README.md`를 참고하세요.

---

## 부록 A. 트러블슈팅

| 증상 | 해결 |
|------|------|
| `PROJECT_ENDPOINT 환경 변수를 설정해주세요` | 루트 `.env`에 엔드포인트/모델 입력 후 경로 확인 |
| 인증 실패 (`AzureCliCredential`) | `az login` 재실행, `az account set`으로 구독 선택 |
| `az`에 Foundry 명령 없음 | `az upgrade --yes`로 2.81.0+ 업그레이드 |
| `ImportError: agent_framework...` | `pip install -U agent-framework`, 가상환경 활성화 확인 |
| SDK v2 `FoundryAgent`를 Handoff에 못 넣음 | 구조적 제약(Part 13 참조) — Handoff는 네이티브 MAF `Agent` 필요. Sequential/GroupChat/Concurrent 사용 |
| Workflow 출력이 `WorkflowEvent(...)` 객체로 보임 | `print(result)` 대신 `result.get_outputs()`(Sequential/Concurrent) / 이벤트의 `AgentExecutorResponse`(GroupChat)로 추출 |
| MCP 도구를 호출 안 함 | `tools=` 전달 누락, `async with mcp_tool:` 밖에서 실행, 서버 URL 확인 |
| RAG가 문서 밖 내용을 지어냄 | 검색 결과 빈약 또는 "추측 금지" 지시문 누락 |
| GroupChat이 끝나지 않음 | `max_rounds` 미설정 |
| Copilot CLI가 명령을 실행 안 함 | 정상 — 실행 전 승인 필요. 신뢰 환경이면 `--yolo` |
| `/mcp`에 azure 서버가 안 보임 | Node.js 22+ 설치 확인, 첫 실행 시 `npx`가 패키지 다운로드 |
| azure MCP 도구 401/권한 오류 | `az login` 재실행, 계정 RBAC 권한·구독 확인 |
| github MCP 인증 실패 | `GITHUB_PERSONAL_ACCESS_TOKEN` 환경변수 설정 여부 확인 |
| Hosted Agent: `ModuleNotFoundError: agent_framework_foundry_hosting` | `pip install agent-framework-foundry-hosting` (배포 시점 의존성) |
| Hosted Agent: `azd ai agent` 명령 없음 | `azd ext install azure.ai.agents`, `azd auth login` |
| Hosted Agent: 배포 후 ARM 이미지 오류 | `linux/amd64` 필요 — `docker build --platform linux/amd64 .` |
| Hosted Agent: 인증 실패 | 컨테이너는 `DefaultAzureCredential`(관리 ID) 사용, 로컬은 `az login` |

> 더 체계적인 진단은 `copilot --agent debugger`를 사용하세요.

## 부록 B. 참고 자료

- [GitHub Copilot CLI 공식 문서](https://docs.github.com/copilot/concepts/agents/about-copilot-cli)
- [Microsoft Agent Framework (GitHub)](https://github.com/microsoft/agent-framework)
- [Azure AI Foundry 문서](https://learn.microsoft.com/azure/foundry/)
- [Azure AI Projects SDK](https://learn.microsoft.com/python/api/overview/azure/ai-projects-readme)
- [MCP 프로토콜 명세](https://modelcontextprotocol.io/)
- [Azure MCP 서버](https://github.com/Azure/azure-mcp)
- [Microsoft Learn MCP 서버](https://learn.microsoft.com/training/support/mcp)
