# Copilot을 "조종"하는 `.github/` 설정

> Copilot CLI/Chat가 읽는 지침(instructions)·에이전트(agents)·스킬(skills)·프롬프트(prompts)
> 구성과 각 구성요소의 역할을 설명합니다.

---

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
│   ├── orchestrator.agent.md       # 오케스트레이터 — 패턴 자동 선택
│   ├── planner_executor.agent.md   # 계획-실행 패턴
│   ├── debate_critic.agent.md      # 토론-비평 패턴
│   ├── generator_evaluator.agent.md # 생성-평가 패턴
│   ├── code_generation.agent.md    # 코드 생성 패턴
│   ├── reviewer.agent.md           # 코드 리뷰 (읽기 전용)
│   └── debugger.agent.md           # 환경/런타임 진단
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

## `SKILL.md` 구조 (Skill)

| 필드 | 설명 |
|------|------|
| `name` | 스킬 식별자 |
| `description` | **언제 쓰는지**(USE FOR / DO NOT USE FOR). Copilot이 이 설명을 보고 로드 여부를 결정 |
| 본문 | SDK 패턴·예제. 관련 작업일 때만 로드됨(**점진적 공개** → 토큰 절약) |

## `*.agent.md` frontmatter (Custom Agent)

| 필드 | 설명 |
|------|------|
| `name` | 선택 (생략 시 파일명 사용) |
| `description` | **필수** — 에이전트의 역할 |
| `tools` | 허용 도구 별칭: `read`·`search`·`edit`·`execute`·`agent`·`web` (생략=전체 허용, `[]`=없음) |
| `model` / `target` | 선택 — 사용할 모델, 실행 대상(`vscode`/`github-copilot`) |

> ✅ **체크포인트**: 이 폴더에서 `copilot`을 실행하면, 생성되는 코드가 위 규칙(async·한국어·
> `AzureCliCredential`·`FoundryChatClient` 패턴)을 자동으로 따릅니다.

---

## 파일 유형별 동작 방식

| 파일 유형 | 위치 | 호출 방법 | 적용 방식 |
|----------|------|----------|----------|
| **글로벌 인스트럭션** | `.github/copilot-instructions.md` | 없음 | ✅ 자동 — 모든 Copilot 요청에 항상 포함 |
| **파일 패턴 인스트럭션** | `.github/instructions/*.instructions.md` | 없음 | ✅ 자동 — `applyTo` 패턴에 매칭되는 파일 작업 시 포함 |
| **스킬** | `.github/skills/*/SKILL.md` | 채팅에서 `/스킬명` | ✅ 자동 + 🔘 수동 — 관련 주제 감지 시 자동 로드, 명시적 호출도 가능 |
| **재사용 프롬프트** | `.github/prompts/*.prompt.md` | 채팅에서 `/프롬프트명` | 🔘 수동 |
| **커스텀 에이전트** | `.github/agents/*.agent.md` | 채팅에서 `/agent` 선택 또는 CLI `--agent <name>` | 🔘 수동 |

## 언제, 어떤 파일 유형을 사용해야 하나요?

| 파일 유형 | 주요 용도 | 사용 시점 예시 |
|----------|----------|--------------|
| **인스트럭션** | **"항상 이 규칙을 따라라"** — 코드 컨벤션·보안 정책·언어 규칙 등 모든 작업에 자동 적용되는 상시 규칙 | Python 코드마다 Google docstring·타입 힌트를 쓰게 하고 싶을 때, Azure 코드에서 항상 `AzureCliCredential`을 쓰게 하고 싶을 때 |
| **스킬** | **"이 분야의 전문 지식을 참고해라"** — 특정 SDK·프레임워크의 API 레퍼런스·코드 패턴·트러블슈팅 가이드 | Agent Framework SDK로 에이전트를 만들 때 올바른 import 경로와 API 사용법이 필요할 때 |
| **재사용 프롬프트** | **"지금 이 작업을 이 방식으로 해라"** — 반복 작업을 템플릿화해 일관된 결과를 보장하는 작업 지시서 | 새 예제를 `NN_<name>.py` 규칙으로 추가할 때, 코드 리뷰를 매번 같은 체크리스트로 수행하고 싶을 때 |
| **커스텀 에이전트** | **"이 역할을 맡아서 수행해라"** — 특정 역할(오케스트레이터·리뷰어·디버거)에 특화된 페르소나와 도구 권한을 가진 전문 AI | 요청에 맞는 협업 패턴을 자동 선택하고 싶을 때, 런타임 에러를 환경→인증→런타임 순으로 진단하고 싶을 때 |

> **요약**: 인스트럭션은 "상시 규칙", 스킬은 "참고 자료", 프롬프트는 "작업 템플릿", 에이전트는 "전문가 역할"입니다.

## CLI에서 `.github/` 설정 파일 동작 방식

이 프로젝트의 `.github/` 설정 파일 중 **Copilot CLI**가 인식하는 범위는 다음과 같습니다.

| `.github/` 파일 | CLI 인식 | CLI에서의 활용 |
|------|:---:|------|
| `copilot-instructions.md` | ✅ 자동 | 프로젝트 기술 스택·코드 패턴·컨벤션이 모든 요청에 반영 |
| `instructions/*.instructions.md` | ✅ 자동 | Python 컨벤션, Azure 보안, 한국어, Git 커밋 규칙이 자동 적용 |
| `skills/*/SKILL.md` | ✅ `/skills`, `/스킬명` | `/skills`로 목록 확인·관리, 스킬 직접 호출은 `/스킬명` 또는 프롬프트 내 명시로 가능 |
| `prompts/*.prompt.md` | ⚠️ 직접 호출 불가 | 프롬프트 내용을 자연어로 풀어서 요청 (예: "add-agent 프롬프트 패턴으로 새 예제를 만들어줘") |
| `agents/*.agent.md` | ✅ `/agent` | `/agent` 명령으로 에이전트를 선택·전환 (예: orchestrator, reviewer, debugger) |

> **핵심**: `copilot-instructions.md`와 `instructions/` 파일들은 **IDE와 CLI 모두에서 자동 적용**됩니다.
> 이 파일들만으로도 프로젝트의 기술 스택·컨벤션·보안 규칙이 일관되게 반영됩니다.

## 재사용 범위: 공용 🌐 vs 프로젝트 전용 🔒

### 🌐 공용 — 다른 프로젝트에 복사하여 즉시 재사용 가능

| 파일 | `applyTo` | 역할 |
|------|-----------|------|
| `instructions/python.instructions.md` | `**/*.py` | Python 3.10+ 가상환경, 의존성 관리, 코드 컨벤션(Google docstring·타입 힌트·import 순서) |
| `instructions/azure.instructions.md` | `**/*.py` | 키리스 인증(`AzureCliCredential`), `.env` 관리, 민감정보 보안 규칙 |
| `instructions/korean.instructions.md` | `**` | 한국어 응답·주석·docstring, 변수명은 영어, 기술 용어 병기 |
| `instructions/git-commit.instructions.md` | `**` | 영문 Conventional Commits, 트레일러 규칙 |

> **재사용 시나리오**: 새 Python + Azure 프로젝트 시작 시 위 파일들을 `.github/instructions/`에
> 복사하면 Copilot이 자동으로 동일한 컨벤션·보안·작성 규칙을 적용합니다.

### 🔒 프로젝트 전용 — 이 프로젝트의 기술 스택(Agent Framework·Foundry·MCP)에 특화

| 파일 | 역할 |
|------|------|
| `copilot-instructions.md` | 프로젝트 전체 규칙 — 6개 주제(총 7개 스크립트) 정의, SDK import 경로, `FoundryChatClient`/`SequentialBuilder` 등 API 패턴 |
| `prompts/add-agent.prompt.md` | 새 에이전트·예제 추가 템플릿 (`NN_<name>.py` 규칙, `Agent`/워크플로우 구성) |
| `prompts/review-code.prompt.md` | 코드 리뷰 요청 — 패턴 준수·보안·비동기 정합성 체크리스트 |
| `skills/agent-framework-codegen/SKILL.md` | Agent Framework 코드 생성 스킬 — import 경로, 에이전트·워크플로우·MCP·RAG 생성 패턴 |
| `agents/orchestrator.agent.md` | 요청 분석 후 최적 협업 패턴 자동 선택 |
| `agents/planner_executor.agent.md` · `debate_critic.agent.md` · `generator_evaluator.agent.md` · `code_generation.agent.md` | 4가지 멀티 에이전트 협업 패턴 |
| `agents/reviewer.agent.md` | 코드 리뷰어 (읽기 전용) |
| `agents/debugger.agent.md` | 트러블슈터 — 환경·인증·런타임 진단 |

## Copilot 커스텀 파일 전체 관계도

```text
.github/
├── copilot-instructions.md          ← 🔒 항상 자동 적용 (프로젝트 전체 규칙)
│
├── instructions/                    ← 🌐 파일 패턴별 자동 적용 (재사용 가능)
│   ├── python.instructions.md       ← *.py 편집 시 자동
│   ├── azure.instructions.md        ← *.py 편집 시 자동
│   ├── korean.instructions.md       ← 모든 파일 편집 시 자동
│   └── git-commit.instructions.md   ← 모든 파일 편집 시 자동
│
├── skills/                          ← 🔒 자동 로드 + /스킬명으로 수동 호출
│   └── agent-framework-codegen/     ← MAF SDK 코드 생성 시
│       └── SKILL.md
│
├── prompts/                         ← 🔒 /이름으로 수동 호출 (CLI는 자연어)
│   ├── add-agent.prompt.md          ← /add-agent
│   └── review-code.prompt.md        ← /review-code
│
└── agents/                          ← 🔒 @이름 또는 --agent로 호출
    ├── orchestrator.agent.md        ← 패턴 자동 선택
    ├── planner_executor.agent.md    ← 계획-실행
    ├── debate_critic.agent.md       ← 토론-비평
    ├── generator_evaluator.agent.md ← 생성-평가
    ├── code_generation.agent.md     ← 코드 생성
    ├── reviewer.agent.md            ← @reviewer (읽기 전용)
    └── debugger.agent.md            ← @debugger (진단)
```

> 📎 더 깊은 바이브 코딩 워크플로우 예시는 참고 프로젝트
> [`vibe-coded-foundry-agents`](https://github.com/junwoojeong100/vibe-coded-foundry-agents)에서 확인할 수 있습니다.
