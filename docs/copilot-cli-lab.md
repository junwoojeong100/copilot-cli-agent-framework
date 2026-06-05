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

## 목차

- [Part 1. Copilot CLI 시작하기](#part-1-copilot-cli-시작하기)
- [Part 2. Copilot을 "조종"하는 `.github/` 설정](#part-2-copilot을-조종하는-github-설정)
- [Part 3. 멀티 에이전트 패턴으로 개발하기](#part-3-멀티-에이전트-패턴으로-개발하기)
- [Part 4. 바이브 코딩 — 설정만으로 코드 생성하기](#part-4-바이브-코딩--설정만으로-코드-생성하기)
- [Part 5. 가드레일 (AGENTS.md)](#part-5-가드레일-agentsmd)

---

## Part 1. Copilot CLI 시작하기

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
**MCP 확장**(외부 시스템을 도구로 연결), **커스텀 에이전트**(`copilot --agent <name>`).

> 💡 이 실습에서는 Copilot CLI에게 "이런 에이전트를 만들어줘"라고 지시하고, 생성된 코드를
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

---

## Part 4. 바이브 코딩 — 설정만으로 코드 생성하기

**바이브 코딩**은 코드를 손으로 쓰는 대신, `.github/`의 instructions·prompts·skills로 의도를
정의하고 Copilot이 코드를 생성하게 하는 방식입니다.

| 개발자가 준비 | Copilot이 수행 |
|---------------|----------------|
| `instructions/` — 기술 스택·코딩 규칙 | 규칙을 지킨 코드 생성 |
| `prompts/` — 반복 작업 템플릿 | 일관된 산출물 생성 |
| `skills/` — SDK 사용법·패턴 | 정확한 SDK 호출 |
| `agents/` — 리뷰/디버그 역할 | 자동 리뷰·디버깅 |

> 📄 **더 알아보기(선택)**: CLI 바이브 코딩 워크플로우 흐름도·재사용 팁은
> [바이브 코딩 가이드](vibe-coding-guide.md)를 참고하세요.

### 실습 흐름 (Azure 없이 진행)

```text
1. (CLI) "UX 리뷰 전문 에이전트를 동시 워크플로우에 추가해줘"라고 자연어로 요청
   (VS Code Copilot Chat이라면 /add-agent 프롬프트로 호출)
2. Copilot이 agent-framework-codegen 스킬 규칙(import·async·instructions)에 맞춰 코드 생성
3. /diff 로 변경사항 확인 → copilot --agent reviewer 로 리뷰 → 수정
4. python -m py_compile src/04_concurrent_workflow.py 로 문법 검증 (Azure 불필요)
```

> 위 흐름은 **CLI 학습이 목적**이므로 Azure 리소스나 실제 실행이 필요 없습니다. `/diff`·`reviewer`
> 에이전트·`py_compile`만으로 "Copilot이 규칙에 맞는 코드를 생성했는가"를 확인합니다.

### (선택) 생성한 코드를 실제로 실행해 보기

생성된 에이전트를 **런타임에서 동작**시켜 보고 싶다면, [Microsoft Agent Framework 핸즈온 랩](../README.md)의
사전 준비(Azure/Microsoft Foundry 리소스 + Python + `.env`)를 끝낸 뒤 다음을 실행합니다.

```bash
python src/04_concurrent_workflow.py   # 실제 실행 (Azure·Python 필요, 선택)
```

> ✅ **최종 체크포인트**: 직접 만든 `.github/` 설정만으로 Copilot이 규칙에 맞는 새 에이전트/기능을
> 생성·리뷰하게 만들 수 있으면, **이 CLI 랩의 목표를 달성**한 것입니다. (실제 실행 여부는 선택)
>
> 📄 **자세히 보기**: [`docs/vibe-coding-guide.md`](vibe-coding-guide.md) — CLI 워크플로우 흐름도, 재사용 팁

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

---

> 📄 메인 실습으로 돌아가기: [README](../README.md)
>
> **더 알아보기(선택, 심화)**: [Copilot CLI 가이드](copilot-cli-guide.md) · [`.github/` 설정](github-config-guide.md) · [멀티 에이전트 패턴](custom-agents-guide.md) · [바이브 코딩](vibe-coding-guide.md) · [VS Code vs CLI](vscode-vs-copilot-cli.md) · [GitHub 멀티 계정 설정](github-multi-account-setup.md)
