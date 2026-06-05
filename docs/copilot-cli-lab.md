# GitHub Copilot CLI 실습 — CLI로 멀티 에이전트 개발 가속하기

> 이 문서는 [메인 README](../README.md)의 **부속 실습**입니다. 메인 README가 *Microsoft Agent
> Framework로 에이전트를 만드는 법*을 다룬다면, 이 문서는 **GitHub Copilot CLI 자체를 개발
> 도구로 활용**하는 법(설치 · `.github/` 설정 · 멀티 에이전트 패턴 · 바이브 코딩 · 가드레일)을 다룹니다.

> **사전 준비**: 먼저 메인 README의 [Part 1. 사전 준비](../README.md#part-1-사전-준비)를 끝내세요
> (Azure/Microsoft Foundry 리소스 + Python 설치 + `.env`). 이 실습의 코드 검증 단계에서
> `python src/...` 예제를 실행합니다.

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
**MCP 확장**, **커스텀 에이전트**(`copilot --agent <name>`).

> 💡 이 실습에서는 Copilot CLI에게 "이런 에이전트를 만들어줘"라고 지시하고, 생성된 코드를
> 검토·실행합니다. `src/`의 예제는 그 결과물의 완성본입니다.
>
> 📄 **자세히 보기**: [`docs/copilot-cli-guide.md`](copilot-cli-guide.md) — 설치부터 활용까지 ·
> [`docs/vscode-vs-copilot-cli.md`](vscode-vs-copilot-cli.md) — VS Code(IDE) vs CLI 비교

---

## Part 2. Copilot을 "조종"하는 `.github/` 설정

Copilot CLI/Chat는 작업 디렉토리의 `.github/` 설정과 `AGENTS.md`를 읽어 **동작 방식을 바꿉니다.**
지침(instructions)·에이전트(agents)·스킬(skills)·프롬프트(prompts) 구성과 각 구성요소의 역할,
`SKILL.md`·`*.agent.md` 구조에 대한 자세한 설명은 별도 문서로 분리했습니다.

> 📄 **자세히 보기**: [`docs/github-config-guide.md`](github-config-guide.md)

---

## Part 3. 멀티 에이전트 패턴으로 개발하기

`.github/agents/`에 역할별 에이전트를 정의하고 `copilot --agent <name>`으로 실행합니다.
이 저장소에는 **7개** 에이전트(오케스트레이터 + 4가지 협업 패턴 + reviewer·debugger)가 포함되어
있습니다. `orchestrator`는 요청을 분석해 4가지 협업 패턴(📐 Planner-Executor, ⚔️ Debate & Critic,
⚡ Generator-Evaluator, 🏗️ Code Generation) 중 하나를 자동 선택해 위임합니다.

각 에이전트의 실행 명령, 오케스트레이터 라우팅 규칙, 패턴별 팀 구성·협업 흐름·비교표 등 자세한
설명은 별도 문서로 분리했습니다.

> 📄 **자세히 보기**: [`docs/custom-agents-guide.md`](custom-agents-guide.md)

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

## Part 4. 바이브 코딩 — 설정만으로 코드 생성하기

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

> 📄 메인 실습으로 돌아가기: [README](../README.md) · 심화 가이드: [멀티 에이전트 패턴](custom-agents-guide.md) · [바이브 코딩](vibe-coding-guide.md)
