# GitHub Copilot CLI 랩 — CLI로 멀티 에이전트 개발 가속하기

> **완전히 독립된 실습입니다.** [Microsoft Agent Framework 핸즈온 랩](../README.md)과 별개로, 이 문서만으로
> **GitHub Copilot CLI 자체를 개발 도구로 활용**하는 법(설치 · `.github/` 설정 · 멀티 에이전트 패턴 ·
> 바이브 코딩 · 가드레일)을 익힙니다.
>
> 두 실습은 서로 의존하지 않습니다. **Azure 리소스나 Python 코드 실행 없이도** 이 랩을 완주할 수 있습니다.

## 사전 준비

| 도구 | 필수/선택 | 용도 | 설치 |
|------|-----------|------|------|
| **GitHub Copilot 구독** | 필수 | Copilot CLI 사용 권한 | <https://github.com/features/copilot> |
| **GitHub Copilot CLI** | 필수 | 터미널 AI 에이전트 | `npm install -g @github/copilot` |
| **Node.js 22+** | 필수 | CLI 런타임 (+ `npx`로 실행되는 MCP 서버) | <https://nodejs.org> |
| **이 저장소 클론** | 필수 | `.github/`·`.copilot/` 설정을 실습 대상으로 사용 | `git clone <repo>` |
| **GitHub PAT** | 선택 | `github` MCP 블록 사용 시에만 (Part 3) | <https://github.com/settings/tokens> |
| **Azure CLI + `az login`** | 선택 | `azure` MCP 서버 인증 시에만 (Part 3) | `az upgrade --yes` |

> 💡 **범위 안내**: 이 랩은 같은 저장소의 Microsoft Agent Framework 코드(`src/`)를 **예시 도메인**으로
> 삼아 "Copilot에게 에이전트 코드를 생성·리뷰시키는" 흐름을 보여줍니다. 다만 생성된 코드를 **실제로
> 실행(= Azure·Python 필요)하는 것은 선택**이며, CLI 학습 자체에는 필요하지 않습니다. 실행까지 해보고
> 싶다면 [Microsoft Agent Framework 핸즈온 랩](../README.md)의 사전 준비를 따르세요.

## 핵심 개념 — Copilot CLI를 조종하는 요소

| 기술 | 무엇인가 | 핵심 기능 | 장점 |
|------|----------|-----------|------|
| **GitHub Copilot CLI** | 터미널에서 동작하는 에이전틱 코딩 도구 | 자연어 지시 → 계획·실행·검증 루프, 슬래시 커맨드(`/plan`·`/fleet`·`/model`), MCP·커스텀 에이전트 확장 | IDE 없이 터미널·CI에서 동작, 명령 실행 전 승인으로 안전, 모델 자유 선택 |
| **Custom Agent**<br/>(`.github/agents/*.agent.md`) | 역할·도구가 제한된 전용 에이전트 | frontmatter로 `description`·`tools`·`model` 지정, `copilot --agent <name>` 실행 | 역할 격리(리뷰어=읽기전용)로 안전·집중, 재사용·팀 공유 |
| **Skill**<br/>(`.github/skills/*/SKILL.md`) | Copilot에 주입하는 전문 지식·패턴 묶음 | `description`으로 트리거, 필요 시에만 본문 로드(점진적 공개) | 정확한 SDK 호출 유도, 토큰 절약, 환각 감소 |
| **Instructions**<br/>(`.github/*instructions.md`) | 항상/조건부로 적용되는 규칙 | `copilot-instructions.md`(전역) + `instructions/*`(`applyTo` 글롭) | 일관된 스타일·규칙 자동 준수, 반복 지시 제거 |

> 🎯 **이 랩을 마치면**: ① Copilot CLI를 설치·인증해 터미널에서 대화하고, ② `.github/` 설정으로
> Copilot의 동작을 "조종"하며, ③ 커스텀 에이전트 + MCP 도구로 멀티 에이전트 개발을 수행하고,
> ④ 바이브 코딩으로 규칙에 맞는 코드를 생성·리뷰하고, ⑤ 가드레일로 안전하게 커밋/PR 할 수 있습니다.
>
> ⏱️ **전체 예상 소요: 약 45–60분** (Azure/Python으로 실제 실행하는 부분은 선택)
>
> 👉 **진행 방법**: 각 Part의 코드 블록을 **위에서 아래로** 그대로 따라 입력하고, 끝에 있는
> ✅ **확인** 체크포인트로 결과를 점검한 뒤 다음 Part로 넘어가세요.

## 목차

- [Part 1. Copilot CLI 시작하기](#part-1-copilot-cli-시작하기)
- [Part 2. Copilot을 "조종"하는 `.github/` 설정](#part-2-copilot을-조종하는-github-설정)
- [Part 3. 멀티 에이전트 패턴으로 개발하기](#part-3-멀티-에이전트-패턴으로-개발하기)
- [Part 4. 바이브 코딩 — 설정만으로 코드 생성하기](#part-4-바이브-코딩--설정만으로-코드-생성하기)
- [Part 5. 가드레일 (AGENTS.md)](#part-5-가드레일-agentsmd)
- [부록. 트러블슈팅](#부록-트러블슈팅)

---

## Part 1. Copilot CLI 시작하기

> 🎯 **목표**: Copilot CLI를 설치·인증하고 터미널에서 첫 대화를 나눠 봅니다.
> ⏱️ 예상 소요: 약 10분 · 준비물: GitHub Copilot 구독, Node.js 22+

### 1단계 — 설치하고 버전 확인

```bash
# 설치 (전 플랫폼, Node.js 22+ 필요)
npm install -g @github/copilot
# 또는 macOS/Linux: curl -fsSL https://gh.io/copilot-install | bash
# 또는: brew install copilot-cli   /   winget install GitHub.Copilot

# 설치 확인
copilot --version
```

설치가 끝나면 버전 번호가 출력됩니다.

```text
1.0.x
```

### 2단계 — 실행하고 로그인

```bash
# 이 저장소 디렉토리에서 실행해야 .github/·.copilot/ 설정을 함께 읽습니다
cd copilot-cli-agent-framework
copilot
```

처음 실행하면 배너가 뜨고, 로그인이 안 되어 있으면 안내가 나옵니다. 세션 프롬프트(`>`)에
`/login`을 입력하세요.

```text
> /login
# 브라우저가 열리고 device code 인증을 안내합니다. 완료하면 세션으로 돌아옵니다.
```

> 💡 PAT로 인증하려면 `export GH_TOKEN=...` 후 `copilot`을 실행합니다. 자세한 내용은
> [Copilot CLI 가이드 — 인증 및 첫 실행](copilot-cli-guide.md#인증-및-첫-실행)을 참고하세요.

### 3단계 — 첫 대화 해보기

세션 프롬프트(`>`)에 자연어로 입력합니다.

```text
> 이 저장소의 구조를 한 문단으로 설명해줘
```

Copilot이 파일을 읽고(필요하면 실행 승인을 먼저 요청) 한국어로 요약해 줍니다. 파일 변경이나
명령 실행이 필요한 작업은 **실행 전에 항상 승인을 묻습니다**(기본 Interactive 모드).

### 4단계 — 모드 전환·모델 선택·종료

| 동작 | 방법 |
|------|------|
| Plan(계획 우선) ↔ Interactive 모드 전환 | `Shift+Tab` |
| 모델 변경 | `/model` (Claude Sonnet/Opus, GPT-5 등) |
| 전체 슬래시 커맨드 보기 | `/help` |
| 세션 종료 | `Ctrl+D` 또는 `Ctrl+C` 두 번 |

자주 쓰는 슬래시 커맨드:

```text
/plan      # 구현 계획 수립 (실행 전 설계)
/fleet     # 병렬 서브에이전트 실행
/model     # 모델 선택 (Claude Sonnet/Opus, GPT-5 등)
/diff      # 변경사항 리뷰
/mcp       # 등록된 MCP 서버 상태 확인
/env       # 로드된 인스트럭션·스킬·에이전트 확인
```

특성: **에이전트 코딩**(계획→실행→검증), **안전 실행**(명령 실행 전 승인, 신뢰 환경에서만 `--yolo`),
**MCP 확장**(외부 시스템을 도구로 연결), **커스텀 에이전트**(`copilot --agent <name>`).

> ✅ **확인**: `copilot` 세션이 열리고 첫 질문에 한국어 답변을 받았다면 Part 1 완료입니다.
> 막히면 [부록. 트러블슈팅](#부록-트러블슈팅)을 보세요.

> 💡 이 랩에서는 Copilot CLI에게 "이런 에이전트를 만들어줘"라고 지시하고, 생성된 코드를
> 검토·실행합니다. `src/`의 예제는 그 결과물의 완성본입니다.
>
> 📄 **더 알아보기(선택)**: [Copilot CLI 가이드](copilot-cli-guide.md) — 설치·인증·슬래시 커맨드 전체 레퍼런스 ·
> [VS Code(IDE) vs CLI 비교](vscode-vs-copilot-cli.md)

---

## Part 2. Copilot을 "조종"하는 `.github/` 설정

Copilot CLI/Chat는 작업 디렉토리의 `.github/` 설정과 `AGENTS.md`를 읽어 **동작 방식을 바꿉니다.**
이 저장소의 구성은 다음과 같습니다.

```text
.github/
├── copilot-instructions.md   # 전역 페르소나·코딩 스타일·프로젝트 규칙
├── instructions/             # 경로/언어별 세부 규칙 (applyTo 글롭)
│   ├── python.instructions.md
│   ├── azure.instructions.md
│   ├── korean.instructions.md
│   └── git-commit.instructions.md
├── prompts/                  # 재사용 프롬프트 (VS Code Chat에서 /프롬프트명)
├── agents/                   # 커스텀 에이전트 (copilot --agent <name>)
└── skills/                   # SDK 사용법·패턴 주입 (SKILL.md)
```

| 구성요소 | 역할 |
|----------|------|
| `copilot-instructions.md` | 프로젝트 전반에 항상 적용되는 규칙 |
| `instructions/*` | `applyTo` 글롭으로 특정 파일/언어에만 적용되는 규칙 |
| `prompts/*` | 반복 작업 템플릿. **VS Code Chat**에서 `/프롬프트명` 호출(CLI는 자연어로 동일 요청) |
| `agents/*` | `copilot --agent`로 실행하는 역할별 에이전트 |
| `skills/*` | SDK 사용법·패턴을 Copilot에 "교육"하는 전문 지식 |

### 직접 확인해 보기

`copilot` 세션을 연 상태에서 다음을 순서대로 해봅니다.

```text
1. (셸) 전역 규칙 파일을 직접 열어 봅니다 — ! 로 시작하면 로컬 셸에서 바로 실행됩니다
   > !cat .github/copilot-instructions.md
2. (CLI) 현재 세션에 무엇이 로드됐는지 확인합니다
   > /env
3. (CLI) 규칙이 실제로 적용되는지 물어봅니다
   > 지금 적용 중인 코딩 규칙과 커밋 메시지 규칙을 요약해줘
```

`/env` 출력에는 로드된 인스트럭션·스킬·커스텀 에이전트·MCP 서버가 함께 표시됩니다.

> ✅ **확인**: `/env`에 `copilot-instructions.md`와 `instructions/*`가 로드되어 있고, 3번 질문에
> Copilot이 "커밋 메시지는 영문 Conventional Commits" 같은 **이 저장소의 규칙**을 답하면 성공입니다.
> 즉, 같은 질문이라도 `.github/` 설정에 따라 답이 달라진다는 것을 직접 확인한 것입니다.

> 📄 **더 알아보기(선택)**: `SKILL.md`·`*.agent.md` frontmatter 구조, 파일 유형별 동작·재사용 범위는
> [`.github/` 설정 가이드](github-config-guide.md)를 참고하세요.

---

## Part 3. 멀티 에이전트 패턴으로 개발하기

> 이 Part는 **① 에이전트 정의(`.github/agents/`) → ② 에이전트가 쓸 도구 연결(MCP 서버) →
> ③ 둘을 합친 실습** 순서로 진행합니다. 에이전트는 "일꾼", MCP 서버는 "일꾼이 쓰는 연장"이라
> 같은 Part에서 함께 다룹니다.

`.github/agents/`에 역할별 에이전트를 정의하고 `copilot --agent <name>`으로 실행합니다.
이 저장소에는 **7개** 에이전트(오케스트레이터 + 4가지 협업 패턴 + reviewer·debugger)가 포함되어
있습니다.

```bash
# 오케스트레이터 — 요청 분석 후 최적 패턴 자동 선택
copilot --agent orchestrator --yolo

# 4가지 협업 패턴 에이전트 직접 실행
copilot --agent planner_executor --yolo    # 📐 계획-실행 패턴
copilot --agent debate_critic --yolo       # ⚔️ 토론-비평 패턴
copilot --agent generator_evaluator --yolo # ⚡ 생성-평가 패턴
copilot --agent code_generation --yolo     # 🏗️ 코드 생성 패턴

# 단독 전문 에이전트
copilot --agent reviewer                   # 코드 리뷰 (읽기 전용)
copilot --agent debugger                   # 환경/런타임 문제 진단
```

`orchestrator`는 요청을 분석해 4가지 협업 패턴 중 하나를 선택해 위임합니다:

| 사용자 의도 | 선택 패턴 |
|------------|----------|
| "구현해줘", "셋업해줘", "마이그레이션" | 📐 Planner-Executor |
| "비교해줘", "장단점", "뭐가 나을까" | ⚔️ Debate & Critic |
| "생성해줘", "리뷰해줘", "개선해줘" | ⚡ Generator-Evaluator |
| "설계하고 구현해줘", "코드 작성하고 리뷰해줘" | 🏗️ Code Generation |

> 📄 **더 알아보기(선택)**: 패턴별 팀 구성·협업 흐름·비교표는
> [멀티 에이전트 패턴 가이드](custom-agents-guide.md)를 참고하세요.

### 에이전트에게 줄 도구 — MCP 서버 연결

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
# 1) (선택) github 서버를 쓸 때만 — GitHub PAT를 환경변수로 등록
export GITHUB_PERSONAL_ACCESS_TOKEN=ghp_xxx

# 2) (선택) azure 서버를 쓸 때만 — Azure CLI 로그인 세션을 사용
#    여기서 az login은 'azure MCP 서버 인증' 용도일 뿐, CLI 학습 자체에는 필요 없습니다.
az login

# 3) Copilot CLI 세션에서 등록된 MCP 서버 확인
copilot
> /mcp           # 설정된 서버 목록·상태 확인
> /env           # 로드된 MCP 서버·인스트럭션·스킬 확인
```

`/mcp`를 실행하면 등록된 서버와 연결 상태가 표시됩니다(이름·유형은 환경에 따라 다를 수 있음).

```text
> /mcp
  github          http    ✓ connected
  azure           local   ✓ connected
  microsoftLearn  http    ✓ connected
```

> 💡 위 1)·2)는 **모두 선택**입니다. PAT·Azure 없이도 `microsoftLearn`(인증 불필요) 서버만으로
> 이 Part의 흐름을 따라갈 수 있습니다.
>
> 참고: Copilot CLI는 GitHub MCP 서버를 기본 내장하고 있어, 위 `github` 항목 없이도 기본 GitHub
> 기능은 사용할 수 있습니다. **단, `github` 블록을 유지하면 `GITHUB_PERSONAL_ACCESS_TOKEN`이 반드시
> 설정되어 있어야 인증 오류가 나지 않습니다.** PAT를 쓰지 않으려면 이 블록을 제거하고 기본 내장
> 서버를 사용하세요. `tools`는 `["*"]`로 모든 도구를 허용하므로, 읽기 전용만 노출하려면 서버 문서의
> 도구명으로 좁히세요.

> ⚠️ **Azure MCP 권한 주의**: `azure` 서버는 `tools: ["*"]`이므로 구독 리소스를 **조회뿐 아니라
> 변경/삭제**할 수 있습니다. 실제 가능한 작업은 `az login` 계정의 **RBAC 권한** 범위로 제한되며,
> Copilot CLI는 실행 전 명령을 확인받습니다. 조회만 허용하려면 `tools`를 읽기 전용 도구명으로
> 좁히거나, 읽기 권한만 가진 계정으로 `az login` 하세요.

> **실습**: `copilot --agent orchestrator --yolo`를 띄우고
> *"Microsoft Learn에서 Agent Framework Concurrent 오케스트레이션 문서를 찾아 동시 워크플로우에
> 비용 리뷰 전문 에이전트를 추가하고 리뷰해줘"* 라고 요청해 보세요. (Learn 문서 검색 + 코드 생성 + 리뷰 연계)

> ✅ **확인**: `/mcp`에 서버가 `connected`로 보이고, 위 요청으로 오케스트레이터가 Learn 문서를
> 검색해 새 에이전트 코드를 제안하면 Part 3 완료입니다. (PAT·Azure 없이 `microsoftLearn`만으로도 가능)

---

## Part 4. 바이브 코딩 — 설정만으로 코드 생성하기

> 🎯 **목표**: 손으로 코드를 쓰지 않고 `.github/` 설정만으로 Copilot이 규칙에 맞는 코드를
> 생성·리뷰하게 만듭니다.
> ⏱️ 예상 소요: 약 15분 · Azure/Python 실행은 선택

**바이브 코딩**은 코드를 손으로 쓰는 대신, `.github/`의 instructions·prompts·skills로 의도를
정의하고 Copilot이 코드를 생성하게 하는 방식입니다. 핵심은 **"무엇을 만들 것인가"와 "어떤 패턴을
따를 것인가"를 정확히 문서화**하면, AI가 일관된 품질의 코드를 생성한다는 것입니다.

| 개발자가 준비 | Copilot이 수행 |
|---------------|----------------|
| `instructions/` — 기술 스택·코딩 규칙 | 규칙을 지킨 코드 생성 |
| `prompts/` — 반복 작업 템플릿 | 일관된 산출물 생성 |
| `skills/` — SDK 사용법·패턴 | 정확한 SDK 호출 |
| `agents/` — 리뷰/디버그 역할 | 자동 리뷰·디버깅 |

### 바이브 코딩 워크플로우 한눈에 보기

```text
┌─────────────────────────────────────────────────────────────────┐
│  1. 시작: copilot 실행 → .github/ 설정 자동 인식                  │
│     copilot-instructions.md, instructions/*.md → 자동 적용       │
├─────────────────────────────────────────────────────────────────┤
│  2. 계획: /plan 모드로 구현 계획 수립 (선택)                       │
│     "동시 워크플로우에 리뷰어를 추가하려면 어떤 순서로?"            │
├─────────────────────────────────────────────────────────────────┤
│  3. 생성: 자연어로 코드 생성/수정 요청                              │
│     "UX 리뷰 전문 에이전트를 04_concurrent_workflow.py에 추가해줘" │
├─────────────────────────────────────────────────────────────────┤
│  4. 검증: /diff로 변경사항 확인 → /review로 코드 리뷰              │
├─────────────────────────────────────────────────────────────────┤
│  5. 완료: 커밋 또는 /delegate로 PR 생성을 Copilot에 위임           │
└─────────────────────────────────────────────────────────────────┘
```

### 실습 흐름 (Azure 없이 진행)

```text
1. (CLI) "UX 리뷰 전문 에이전트를 동시 워크플로우에 추가해줘"라고 자연어로 요청
   (VS Code Copilot Chat이라면 /add-agent 프롬프트로 호출)
2. Copilot이 agent-framework-codegen 스킬 규칙(import·async·instructions)에 맞춰 코드 생성
3. /diff 로 변경사항 확인 → copilot --agent reviewer 로 리뷰 → 수정
4. (선택: Python이 설치된 경우) `python -m py_compile src/04_concurrent_workflow.py`로 문법 검증
   (Azure 불필요)
```

> 💡 **선택 사항**: `py_compile` 단계는 Python이 설치된 환경에서만 실행 가능합니다. 이 문서의 핵심은
> Copilot CLI 학습이므로, Python이 없다면 `/diff`와 `reviewer` 에이전트 검토만으로도 실습을 계속
> 진행할 수 있습니다.
>
> `py_compile`은 문법 오류가 없으면 **아무것도 출력하지 않고 종료**합니다(종료 코드 0). 그게 정상입니다.

> 위 흐름은 **CLI 학습이 목적**이므로 Azure 리소스나 실제 실행이 필요 없습니다. `/diff`·`reviewer`
> 에이전트·`py_compile`만으로 "Copilot이 규칙에 맞는 코드를 생성했는가"를 확인합니다.

이후에도 자연어로 요청하면 `.github/copilot-instructions.md`와 `instructions/*.md`의 규칙을 반영한
코드를 생성합니다.

```text
> RAG 에이전트에 top_k를 5로 변경해줘
> 새 MCP 도구를 추가해줘
> 동시 워크플로우에 새로운 검토 관점을 추가해줘
```

### 재사용 팁

- **공용 인스트럭션 복사**: `instructions/python.instructions.md`·`azure.instructions.md`·
  `korean.instructions.md`·`git-commit.instructions.md`를 새 프로젝트의 `.github/instructions/`에
  복사하면 동일한 컨벤션·보안·작성 규칙이 즉시 적용됩니다.
- **새 예제 추가 규칙**: 예제는 `src/`에 `NN_<name>.py` 규칙으로 추가하고, 진입점은
  `if __name__ == "__main__": asyncio.run(main())` 패턴을 따릅니다.
- **설정 구조 참고**: `.github/` 설정의 동작 방식과 구성요소별 역할은
  [`.github/` 설정 가이드](github-config-guide.md)를 참고하세요.

### (선택) 생성한 코드를 실제로 실행해 보기

생성된 에이전트를 **런타임에서 동작**시켜 보고 싶다면, [Microsoft Agent Framework 핸즈온 랩](../README.md)의
사전 준비(Azure/Microsoft Foundry 리소스 + Python + `.env`)를 끝낸 뒤 다음을 실행합니다.

```bash
python src/04_concurrent_workflow.py   # 실제 실행 (Azure·Python 필요, 선택)
```

> ✅ **최종 체크포인트**: 직접 만든 `.github/` 설정만으로 Copilot이 규칙에 맞는 새 에이전트/기능을
> 생성·리뷰하게 만들 수 있으면, **이 CLI 랩의 목표를 달성**한 것입니다. (실제 실행 여부는 선택)
>
> 📎 더 깊은 바이브 코딩 워크플로우 예시는 참고 프로젝트
> [`vibe-coded-foundry-agents`](https://github.com/junwoojeong100/vibe-coded-foundry-agents)에서 확인할 수 있습니다.

---

## Part 5. 가드레일 (AGENTS.md)

루트의 [`AGENTS.md`](../AGENTS.md)는 **모든** Copilot 에이전트가 git/외부 명령 실행 전에 따르는
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

> ✅ **확인**: 기능 브랜치(`feat/*`)에서 영문 Conventional Commits로 커밋하고 `--draft --base main`
> 으로 PR을 만들 수 있으면 Part 5 완료입니다. Copilot에게 커밋/PR을 맡겨도 이 가드레일을 따릅니다.

---

## 부록. 트러블슈팅

| 증상 | 원인 | 해결 |
|------|------|------|
| `copilot: command not found` | 전역 설치 경로가 PATH에 없음 | `npm install -g @github/copilot` 재실행 후 새 터미널 열기. 전역 경로 확인: `npm prefix -g` |
| 실행 시 로그인 안내만 반복 | GitHub 인증 미완료 | 세션에서 `/login` 후 브라우저 인증 완료, 또는 `export GH_TOKEN=...` 설정 |
| `/mcp`에 서버가 안 보임 | `.copilot/mcp-config.json` 미인식 또는 JSON 오류 | 저장소 루트에서 `copilot` 실행, JSON 문법 확인 후 세션 재시작 |
| github 서버 인증 오류 | `GITHUB_PERSONAL_ACCESS_TOKEN` 미설정 | PAT를 `export` 하거나, `github` 블록을 제거하고 기본 내장 GitHub 서버 사용 |
| azure 서버 연결 실패 | `az login` 세션 없음/만료 | `az login` 재실행, `az account show`로 로그인 상태 확인 |
| `--agent <name>` 실행 안 됨 | 에이전트 파일명/위치 불일치 | `.github/agents/<name>.agent.md` 존재 확인, 세션에서 `/agent`로 목록 확인 |
| Node.js 버전 오류 | Node 22 미만 | `node -v`로 확인 후 22+ 설치 (<https://nodejs.org>) |

> 📄 더 많은 사례: [Copilot CLI 가이드 — 트러블슈팅](copilot-cli-guide.md#트러블슈팅)

---

> 📄 메인 실습으로 돌아가기: [README](../README.md)
>
> **더 알아보기(선택, 심화)**: [Copilot CLI 가이드](copilot-cli-guide.md) · [`.github/` 설정](github-config-guide.md) · [멀티 에이전트 패턴](custom-agents-guide.md) · [VS Code vs CLI](vscode-vs-copilot-cli.md) · [GitHub 멀티 계정 설정](github-multi-account-setup.md)
