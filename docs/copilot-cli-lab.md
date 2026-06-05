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

## 핵심 개념

이 랩에서 쓰는 구성요소(Copilot CLI · Custom Agent · Skill · Instructions)의 "무엇인가 · 왜 쓰는가"는
개념 문서로 분리했습니다. 처음이라면 아래 문서를 먼저 훑어보세요.

> 📄 [**Copilot CLI 핵심 개념 — 구성요소**](copilot-cli-concepts.md)

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

특성·구성요소 개념은 [Copilot CLI 핵심 개념](copilot-cli-concepts.md)으로 분리했습니다.

> 💡 이 실습에서는 Copilot CLI에게 "이런 에이전트를 만들어줘"라고 지시하고, 생성된 코드를
> 검토·실행합니다. `src/`의 예제는 그 결과물의 완성본입니다.
>
> 📄 **자세히 보기**: [Copilot CLI 핵심 개념](copilot-cli-concepts.md) · [Copilot CLI 가이드](copilot-cli-guide.md) — 설치부터 활용까지 ·
> [VS Code(IDE) vs CLI 비교](vscode-vs-copilot-cli.md)

---

## Part 2. Copilot을 "조종"하는 `.github/` 설정

Copilot CLI/Chat는 작업 디렉토리의 `.github/` 설정과 `AGENTS.md`를 읽어 **동작 방식을 바꿉니다.**
지침(instructions)·에이전트(agents)·스킬(skills)·프롬프트(prompts) 구성과 각 구성요소의 역할,
`SKILL.md`·`*.agent.md` 구조에 대한 자세한 설명은 별도 문서로 분리했습니다.

> 📄 **자세히 보기**: [`docs/github-config-guide.md`](github-config-guide.md)

---

## Part 3. 멀티 에이전트 패턴으로 개발하기

> 이 Part는 **① 에이전트 정의(`.github/agents/`) → ② 에이전트가 쓸 도구 연결(MCP 서버) →
> ③ 둘을 합친 실습** 순서로 진행합니다. 에이전트는 "일꾼", MCP 서버는 "일꾼이 쓰는 연장"이라
> 같은 Part에서 함께 다룹니다.

`.github/agents/`에 역할별 에이전트를 정의하고 `copilot --agent <name>`으로 실행합니다.
이 저장소에는 **7개** 에이전트(오케스트레이터 + 4가지 협업 패턴 + reviewer·debugger)가 포함되어
있습니다. `orchestrator`는 요청을 분석해 4가지 협업 패턴(📐 Planner-Executor, ⚔️ Debate & Critic,
⚡ Generator-Evaluator, 🏗️ Code Generation) 중 하나를 자동 선택해 위임합니다.

각 에이전트의 실행 명령, 오케스트레이터 라우팅 규칙, 패턴별 팀 구성·협업 흐름·비교표 등 자세한
설명은 별도 문서로 분리했습니다.

> 📄 **자세히 보기**: [`docs/custom-agents-guide.md`](custom-agents-guide.md)

### 에이전트에게 줄 도구 — MCP 서버 연결

`.copilot/mcp-config.json`로 MCP 서버를 Copilot CLI에 붙입니다. 이 저장소에는 **Azure · GitHub ·
Microsoft Learn** 세 가지 서버가 설정되어 있습니다. 서버별 구성·인증·권한 등 자세한 개념은 별도
문서로 분리했습니다.

> 📄 **자세히 보기**: [MCP 서버 연결 — 개념과 구성](mcp-servers-guide.md)

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
> 이 Part의 흐름을 따라갈 수 있습니다. (인증·권한 주의사항은
> [MCP 서버 연결 가이드](mcp-servers-guide.md)를 참고하세요.)

> **실습**: `copilot --agent orchestrator --yolo`를 띄우고
> *"Microsoft Learn에서 Agent Framework Concurrent 오케스트레이션 문서를 찾아 동시 워크플로우에
> 비용 리뷰 전문 에이전트를 추가하고 리뷰해줘"* 라고 요청해 보세요. (Learn 문서 검색 + 코드 생성 + 리뷰 연계)

---

## Part 4. 바이브 코딩 — 설정만으로 코드 생성하기

**바이브 코딩**은 코드를 손으로 쓰는 대신, `.github/`의 instructions·prompts·skills로 의도를
정의하고 Copilot이 코드를 생성하게 하는 방식입니다. 개념·구성요소별 역할은 개념 문서로 분리했습니다.

> 📄 **자세히 보기**: [바이브 코딩 — 설정만으로 코드 생성하기](vibe-coding-guide.md)

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
> **개념·이론 문서**: [Copilot CLI 핵심 개념](copilot-cli-concepts.md) · [`.github/` 설정](github-config-guide.md) · [멀티 에이전트 패턴](custom-agents-guide.md) · [MCP 서버 연결](mcp-servers-guide.md) · [바이브 코딩](vibe-coding-guide.md) · [Copilot CLI 가이드](copilot-cli-guide.md) · [VS Code vs CLI](vscode-vs-copilot-cli.md) · [GitHub 멀티 계정 설정](github-multi-account-setup.md)
