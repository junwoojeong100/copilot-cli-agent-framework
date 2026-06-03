# 📘 GitHub Copilot CLI 가이드

> GitHub Copilot의 힘을 터미널에서 — 설치부터 활용까지

---

## 목차

1. [빠른 시작 (5분)](#빠른-시작-5분)
2. [Copilot CLI란?](#copilot-cli란)
3. [설치 방법](#설치-방법)
4. [인증 및 첫 실행](#인증-및-첫-실행)
5. [기본 사용법](#기본-사용법)
6. [CLI 실행 옵션](#cli-실행-옵션)
7. [슬래시 커맨드 레퍼런스](#슬래시-커맨드-레퍼런스)
8. [에이전트 실행](#에이전트-실행)
9. [커스텀 에이전트 만들기](#커스텀-에이전트-만들기)
10. [MCP 서버 설정](#mcp-서버-설정)
11. [LSP 서버 설정](#lsp-서버-설정)
12. [커스텀 인스트럭션](#커스텀-인스트럭션)
13. [유용한 팁](#유용한-팁)
14. [트러블슈팅](#트러블슈팅)

---

## 빠른 시작 (5분)

Copilot CLI를 처음 사용한다면 이 순서대로 따라하세요:

```bash
# 1. 설치
# macOS / Linux
curl -fsSL https://gh.io/copilot-install | bash

# Windows (PowerShell)
winget install GitHub.Copilot

# 2. 실행
copilot

# 3. 로그인 (첫 실행 시)
/login

# 4. 코드가 있는 디렉토리에서 질문하기
cd my-project
copilot
> 이 프로젝트의 구조를 설명해줘
```

> 💡 더 상세한 내용은 아래 각 섹션을 참고하세요.

---

## Copilot CLI란?

GitHub Copilot CLI는 **터미널에서 직접 AI 코딩 에이전트와 대화**할 수 있는 도구입니다.
GitHub Copilot coding agent와 동일한 에이전틱 하네스를 기반으로 동작하며, 자연어로 코드를 빌드·디버그·리팩터링할 수 있습니다.

### 핵심 특징

| 특징 | 설명 |
|------|------|
| **터미널 네이티브** | IDE 전환 없이 CLI에서 바로 작업 |
| **GitHub 통합** | 리포지토리, 이슈, PR을 자연어로 접근 — GitHub 계정 인증 자동 연동 |
| **에이전틱 기능** | 복잡한 태스크를 계획하고 실행하는 AI 협업자 |
| **MCP 확장성** | GitHub MCP 서버 기본 탑재, 커스텀 MCP 서버 추가 가능 |
| **완전한 제어** | 모든 동작을 실행 전에 미리보기 — 명시적 승인 없이는 실행되지 않음 |

---

## 설치 방법

### 지원 플랫폼

- **macOS**
- **Linux**
- **Windows** (PowerShell v6 이상)

### 사전 요구 사항

- [GitHub Copilot](https://github.com/features/copilot) 구독 활성화

> ⚠️ 조직(Organization) 또는 엔터프라이즈를 통해 Copilot을 사용하는 경우, 관리자가 Copilot CLI를 비활성화했을 수 있습니다.
> [조직의 Copilot 정책 관리](https://docs.github.com/copilot/managing-copilot/managing-github-copilot-in-your-organization/managing-github-copilot-features-in-your-organization/managing-policies-for-copilot-in-your-organization)를 확인하세요.

### 설치 스크립트 (macOS / Linux)

```bash
# curl 사용
curl -fsSL https://gh.io/copilot-install | bash

# wget 사용
wget -qO- https://gh.io/copilot-install | bash
```

루트 권한으로 설치하려면 `| sudo bash`를 사용합니다. 설치 경로를 변경하려면 `PREFIX` 환경변수를 지정합니다.

```bash
# 특정 버전을 커스텀 경로에 설치
curl -fsSL https://gh.io/copilot-install | VERSION="v0.0.369" PREFIX="$HOME/custom" bash
```

### Homebrew (macOS / Linux)

```bash
brew install copilot-cli

# 프리릴리즈 버전
brew install copilot-cli@prerelease
```

### WinGet (Windows)

```bash
winget install GitHub.Copilot

# 프리릴리즈 버전
winget install GitHub.Copilot.Prerelease
```

### npm (macOS / Linux / Windows)

```bash
npm install -g @github/copilot

# 프리릴리즈 버전
npm install -g @github/copilot@prerelease
```

---

## 인증 및 첫 실행

### 첫 실행

```bash
copilot
```

처음 실행하면 애니메이션 배너가 표시됩니다. GitHub에 로그인되어 있지 않으면 `/login` 슬래시 커맨드를 입력하라는 안내가 나타납니다.

### GitHub 계정 인증

```
/login
```

화면의 안내에 따라 브라우저에서 인증을 완료합니다.

### PAT(Personal Access Token) 인증

PAT를 사용해 인증할 수도 있습니다:

1. https://github.com/settings/personal-access-tokens/new 에서 토큰 생성
2. "Permissions" → "Copilot Requests" 권한 추가
3. 환경변수로 설정:

```bash
export GH_TOKEN="your-token-here"
# 또는
export GITHUB_TOKEN="your-token-here"
```

> `GH_TOKEN`이 `GITHUB_TOKEN`보다 우선 적용됩니다.

---

## 기본 사용법

### 모델 선택

기본 모델은 **Claude Sonnet 4.5**입니다. 다른 모델을 선택하려면:

```
/model
```

Claude Sonnet 4, GPT-5 등 사용 가능한 모델 목록에서 선택할 수 있습니다.

### 모드 전환

`Shift+Tab`으로 모드를 전환합니다:

| 모드 | 설명 |
|------|------|
| **Interactive** | 기본 모드. 각 단계마다 승인 필요 |
| **Plan** | 실행 전에 구현 계획을 먼저 세움 |

### 파일 멘션

프롬프트에서 `@`를 입력하면 파일을 멘션하여 컨텍스트에 포함시킬 수 있습니다:

```
@src/auth.ts 이 파일의 인증 로직을 설명해줘
```

### 로컬 셸 명령어 실행

`!`로 시작하면 Copilot을 거치지 않고 로컬 셸에서 직접 실행됩니다:

```
!ls -la
!npm run test
```

### 키보드 단축키

#### 일반

| 단축키 | 기능 |
|--------|------|
| `Ctrl+S` | 입력을 유지하면서 명령 실행 |
| `Ctrl+T` | 모델 추론 과정 표시 토글 |
| `Ctrl+O` | 최근 타임라인 확장 (입력 없을 때) |
| `Ctrl+E` | 전체 타임라인 확장 (입력 없을 때) |
| `↑` `↓` | 명령 히스토리 탐색 |
| `Ctrl+C` | 취소 / 입력 지우기 / 선택 복사 |
| `Ctrl+C ×2` | CLI 종료 |
| `Esc` | 현재 작업 취소 |
| `Ctrl+D` | 종료 |
| `Ctrl+L` | 화면 지우기 |
| `Ctrl+X → O` | 최근 타임라인의 링크 열기 |

#### 편집

| 단축키 | 기능 |
|--------|------|
| `Ctrl+A` | 줄 맨 앞으로 이동 |
| `Ctrl+E` | 줄 맨 끝으로 이동 (입력 중일 때) |
| `Ctrl+H` | 이전 글자 삭제 |
| `Ctrl+W` | 이전 단어 삭제 |
| `Ctrl+U` | 커서부터 줄 시작까지 삭제 |
| `Ctrl+K` | 커서부터 줄 끝까지 삭제 |
| `Meta+← →` | 단어 단위로 커서 이동 |
| `Ctrl+G` | 외부 에디터에서 프롬프트 편집 |

---

## CLI 실행 옵션

`copilot` 명령어와 함께 사용할 수 있는 주요 플래그:

| 플래그 | 설명 |
|--------|------|
| `--agent <name>` | 특정 에이전트를 지정하여 실행 |
| `--yolo` | 자동 승인 모드 — 도구 실행을 매번 확인하지 않음 |
| `--experimental` | 실험적 기능 활성화 (Autopilot 등) |
| `--banner` | 시작 시 애니메이션 배너 다시 표시 |

```bash
# 예시: 에이전트 + 자동 승인 + 실험적 기능
copilot --agent orchestrator --yolo --experimental
```

> ⚠️ `--yolo` 모드는 편리하지만, 모든 파일 변경과 명령어가 자동 실행됩니다. 신뢰할 수 있는 환경에서만 사용하세요.

---

## 슬래시 커맨드 레퍼런스

### 에이전트 환경

| 커맨드 | 설명 |
|--------|------|
| `/init` | 리포지토리용 Copilot 인스트럭션 초기화 |
| `/agent` | 사용 가능한 에이전트 탐색·선택 |
| `/skills` | 스킬 관리 (Azure 등 확장 기능) |
| `/mcp` | MCP 서버 설정 관리 |
| `/plugin` | 플러그인 및 마켓플레이스 관리 |

### 모델 및 서브에이전트

| 커맨드 | 설명 |
|--------|------|
| `/model` | AI 모델 선택 |
| `/delegate` | 세션을 GitHub에 보내 Copilot이 PR 생성 |
| `/fleet` | 병렬 서브에이전트 실행 모드 활성화 |
| `/tasks` | 백그라운드 태스크(서브에이전트, 셸 세션) 관리 |

### 코드 작업

| 커맨드 | 설명 |
|--------|------|
| `/ide` | IDE 워크스페이스 연결 |
| `/diff` | 현재 디렉토리의 변경 사항 리뷰 |
| `/pr` | 현재 브랜치의 PR 관련 작업 |
| `/review` | 코드 리뷰 에이전트 실행 |
| `/plan` | 코딩 전에 구현 계획 작성 |
| `/research` | GitHub 검색과 웹 소스를 활용한 심층 리서치 |
| `/lsp` | 언어 서버 설정 관리 |
| `/terminal-setup` | 멀티라인 입력 지원 설정 (Shift+Enter) |

### 권한

| 커맨드 | 설명 |
|--------|------|
| `/allow-all` | 모든 권한 활성화 (도구, 경로, URL) |
| `/add-dir` | 파일 접근 허용 디렉토리 추가 |
| `/list-dirs` | 허용된 디렉토리 목록 표시 |
| `/cwd` | 작업 디렉토리 변경 또는 표시 |
| `/reset-allowed-tools` | 허용된 도구 목록 초기화 |

### 세션

| 커맨드 | 설명 |
|--------|------|
| `/resume` | 다른 세션으로 전환 |
| `/rename` | 현재 세션 이름 변경 |
| `/new` | 새로운 대화 시작 |
| `/context` | 컨텍스트 윈도우 토큰 사용량 확인 |
| `/usage` | 세션 사용량 통계 표시 |
| `/session` | 세션 조회·관리 |
| `/compact` | 대화 히스토리 요약으로 컨텍스트 절약 |
| `/share` | 세션을 마크다운, HTML, GitHub Gist로 공유 |
| `/copy` | 마지막 응답을 클립보드에 복사 |
| `/rewind` | 마지막 턴 되돌리기 및 파일 변경 복원 |

### 도움말 및 피드백

| 커맨드 | 설명 |
|--------|------|
| `/help` | 도움말 표시 |
| `/changelog` | CLI 버전별 변경 로그 (`summarize` 추가 시 AI 요약) |
| `/feedback` | CLI에 대한 피드백 제출 |
| `/theme` | 색상 모드 설정 |
| `/update` | 최신 버전으로 업데이트 |
| `/version` | 버전 정보 표시 |
| `/experimental` | 실험적 기능 관리 |
| `/clear` | 현재 세션 폐기 후 새로 시작 |
| `/instructions` | 커스텀 인스트럭션 파일 확인·토글 |
| `/streamer-mode` | 스트리머 모드 토글 (모델명·할당량 숨김) |

---

## 에이전트 실행

### `--agent` 옵션

`.github/agents/` 디렉토리에 정의된 커스텀 에이전트를 직접 실행할 수 있습니다:

```bash
# 에이전트 지정 실행
copilot --agent orchestrator

# 에이전트 + 자동 승인 모드
copilot --agent orchestrator --yolo
```

### 이 프로젝트의 에이전트

| 에이전트 | 설명 |
|---------|------|
| `orchestrator` | 요청을 분석하여 최적의 패턴 팀 자동 선택 |
| `planner_executor` | 계획 수립 → 실행 → 검증 패턴 |
| `debate_critic` | 대립적 논증을 통한 최선의 결론 도출 |
| `generator_evaluator` | 생성 → 평가 → 개선 반복 패턴 |
| `code_generation` | 설계 → 구현 → 리뷰 통합 패턴 |

> 에이전트 패턴의 상세 설명은 [README.md](../README.md#에이전트-패턴)를 참고하세요.

### `/agent` 슬래시 커맨드

CLI 내에서 대화형으로 에이전트를 탐색하고 선택할 수도 있습니다:

```
/agent
```

---

## 커스텀 에이전트 만들기

나만의 에이전트를 정의하려면 `.github/agents/` 디렉토리에 `.agent.md` 파일을 생성합니다.

### 파일 구조

```
.github/agents/
└── my_agent.agent.md    # copilot --agent my_agent 로 실행
```

### 에이전트 파일 작성 예시

```markdown
# My Agent

> 에이전트의 역할과 목적을 설명하는 한 줄 요약

## 역할 (Role)

이 에이전트는 [구체적인 역할]을 수행합니다.

## 규칙 (Rules)

1. 항상 [특정 규칙]을 따릅니다
2. [제약 조건]을 준수합니다

## 워크플로우 (Workflow)

1. 사용자 요청을 분석합니다
2. [단계별 수행 절차]
3. 결과를 문서화합니다
```

### 팁

- 파일명에서 `.agent.md`를 제외한 부분이 에이전트 이름이 됩니다
- 마크다운으로 에이전트의 역할, 규칙, 워크플로우를 자유롭게 정의합니다
- 다른 에이전트를 `task` 도구의 커스텀 에이전트로 호출할 수 있습니다
- 이 프로젝트의 [`.github/agents/`](../.github/agents/) 디렉토리를 참고하세요

---

## MCP 서버 설정

MCP(Model Context Protocol) 서버를 통해 Copilot CLI의 기능을 확장할 수 있습니다.
GitHub의 MCP 서버가 기본 탑재되어 있으며, 추가 MCP 서버를 연결할 수 있습니다.

### 설정 파일

| 레벨 | 경로 | 적용 범위 |
|------|------|----------|
| **유저** | `~/.copilot/mcp-config.json` | 모든 프로젝트 |
| **리포지토리** | `.copilot/mcp-config.json` | 해당 프로젝트만 |

### 설정 예시

```json
{
  "mcpServers": {
    "github": {
      "command": "github-mcp-server",
      "args": ["--stdio"]
    },
    "my-custom-server": {
      "command": "npx",
      "args": ["-y", "@my-org/mcp-server"],
      "env": {
        "API_KEY": "your-api-key"
      }
    }
  }
}
```

### `/mcp` 커맨드

CLI 내에서 MCP 서버 상태를 확인하고 관리합니다:

```
/mcp
```

---

## LSP 서버 설정

LSP(Language Server Protocol) 서버를 연결하면 go-to-definition, hover 정보, 진단 등 향상된 코드 인텔리전스를 사용할 수 있습니다.

### 설정 파일 위치

| 레벨 | 경로 | 적용 범위 |
|------|------|----------|
| **유저** | `~/.copilot/lsp-config.json` | 모든 프로젝트 |
| **리포지토리** | `.github/lsp.json` | 해당 프로젝트만 |

### 설정 예시 (TypeScript)

```bash
# LSP 서버 설치
npm install -g typescript-language-server
```

```json
{
  "lspServers": {
    "typescript": {
      "command": "typescript-language-server",
      "args": ["--stdio"],
      "fileExtensions": {
        ".ts": "typescript",
        ".tsx": "typescript"
      }
    }
  }
}
```

### 설정 예시 (Python)

```bash
# LSP 서버 설치
pip install python-lsp-server
```

```json
{
  "lspServers": {
    "python": {
      "command": "pylsp",
      "args": [],
      "fileExtensions": {
        ".py": "python"
      }
    }
  }
}
```

### LSP 상태 확인

```
/lsp
```

---

## 커스텀 인스트럭션

Copilot CLI는 다양한 위치의 인스트럭션 파일을 자동으로 인식합니다:

| 파일 | 설명 |
|------|------|
| `AGENTS.md` | 에이전트 공통 가드레일 (Git 루트 & cwd) |
| `CLAUDE.md` | Claude 모델 전용 인스트럭션 |
| `GEMINI.md` | Gemini 모델 전용 인스트럭션 |
| `.github/instructions/**/*.instructions.md` | 디렉토리별 세부 인스트럭션 |
| `.github/copilot-instructions.md` | 리포지토리 전체 인스트럭션 |
| `~/.copilot/copilot-instructions.md` | 유저 전체 글로벌 인스트럭션 |

환경변수 `COPILOT_CUSTOM_INSTRUCTIONS_DIRS`로 추가 디렉토리를 지정할 수도 있습니다.

### 적용 우선순위

인스트럭션 파일이 여러 개 존재할 때, 모든 파일이 동시에 적용됩니다.
단, 리포지토리 레벨 인스트럭션이 유저 레벨보다 구체적이므로, 충돌 시 리포지토리 레벨이 우선됩니다.

```
유저 글로벌 (~/.copilot/)  →  리포지토리 (.github/)  →  디렉토리별 (instructions/)
               낮음                    ↑                       높음
```

### 인스트럭션 확인

```
/instructions
```

이 프로젝트에서는 [`AGENTS.md`](../AGENTS.md)를 통해 모든 에이전트에 공통 가드레일(예: `git push` 금지)을 적용하고 있습니다.

---

## 유용한 팁

### 업데이트

최신 버전으로 업데이트하려면:

```
/update
```

또는 설치한 패키지 매니저를 통해 업데이트할 수 있습니다:

```bash
# Homebrew
brew upgrade copilot-cli

# npm
npm update -g @github/copilot

# WinGet
winget upgrade GitHub.Copilot
```

> 💡 Copilot CLI는 빠르게 개발 중이므로 **최신 버전 유지를 권장**합니다.

### 실전 활용 시나리오

#### 새 프로젝트에서 코드 이해하기

```
이 프로젝트의 전체 아키텍처를 설명해줘
```

#### 버그 디버깅

```
@src/api/users.ts 이 파일에서 404 에러가 발생하는 원인을 찾아줘
```

#### 테스트 작성

```
@src/utils/parser.ts 이 모듈에 대한 단위 테스트를 작성해줘
```

#### PR 리뷰 지원

```
/pr    # 현재 브랜치의 PR 변경 사항을 분석
```

#### 리서치

```
/research React Server Components와 기존 SSR의 차이점
```

### Autopilot 모드 (Experimental)

Experimental 모드를 활성화하면 Autopilot 모드를 사용할 수 있습니다.
에이전트가 작업이 완료될 때까지 자동으로 진행합니다.

```bash
# 실험 모드 활성화 (첫 번째 방법)
copilot --experimental

# 또는 CLI 내에서
/experimental
```

활성화 후 `Shift+Tab`으로 Autopilot 모드를 선택합니다.

### 컨텍스트 관리

대화가 길어지면 `/compact`로 히스토리를 요약하여 컨텍스트 윈도우를 확보합니다:

```
/compact
```

`/context`로 현재 토큰 사용량을 확인할 수 있습니다.

### 코드 리뷰

```
/diff     # 현재 디렉토리의 변경 사항 확인
/review   # AI 코드 리뷰 에이전트 실행
/pr       # 현재 브랜치 PR 관련 작업
```

### 세션 공유

작업 결과를 팀과 공유하려면:

```
/share    # 마크다운, HTML, GitHub Gist로 내보내기
```

### Premium Request

Copilot CLI에 프롬프트를 보낼 때마다 월간 프리미엄 요청 할당량이 1개씩 차감됩니다.
자세한 내용은 [About premium requests](https://docs.github.com/copilot/managing-copilot/monitoring-usage-and-entitlements/about-premium-requests)를 참고하세요.

---

## 트러블슈팅

### "command not found: copilot"

설치 후 `copilot` 명령어를 찾지 못하는 경우:

```bash
# PATH에 설치 경로가 포함되어 있는지 확인
echo $PATH

# 기본 설치 경로 확인
ls ~/.local/bin/copilot    # 일반 사용자
ls /usr/local/bin/copilot  # root 설치

# PATH에 추가 (필요 시)
export PATH="$HOME/.local/bin:$PATH"
```

### 로그인이 되지 않는 경우

- 브라우저가 자동으로 열리지 않으면 터미널에 표시된 URL을 수동으로 복사하여 열어주세요
- 조직 관리자가 Copilot CLI를 비활성화했을 수 있습니다 → 관리자에게 문의
- PAT 인증으로 대체할 수 있습니다 ([PAT 인증](#patpersonal-access-token-인증) 참고)

### 컨텍스트 윈도우 초과

대화가 길어져서 응답 품질이 떨어지는 경우:

```
/compact    # 대화 히스토리 요약
/context    # 현재 토큰 사용량 확인
/clear      # 세션 초기화 후 새로 시작
```

### 에이전트를 찾을 수 없는 경우

```bash
# 에이전트 파일이 올바른 위치에 있는지 확인
ls .github/agents/*.agent.md

# CLI 내에서 사용 가능한 에이전트 목록 확인
/agent
```

### MCP 서버 연결 실패

```
/mcp    # MCP 서버 상태 확인
```

MCP 서버 바이너리가 설치되어 있고 PATH에 포함되어 있는지 확인하세요.

---

## 참고 링크

- [GitHub Copilot CLI 공식 문서](https://docs.github.com/copilot/concepts/agents/about-copilot-cli)
- [GitHub Copilot CLI 사용 가이드](https://docs.github.com/en/copilot/how-tos/use-copilot-agents/use-copilot-cli)
- [Copilot 플랜 및 가격](https://github.com/features/copilot/plans)
- [이 프로젝트의 멀티 에이전트 패턴](../README.md)
