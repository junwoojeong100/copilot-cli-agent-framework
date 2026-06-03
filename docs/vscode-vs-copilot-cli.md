# VS Code(IDE) vs Copilot CLI(터미널) 비교

> GitHub Copilot은 **VS Code(IDE)**뿐 아니라 **Copilot CLI(터미널)**에서도 동일한 `.github/`
> 설정 파일을 인식합니다. 개발 환경에 따라 두 가지 방식을 선택하거나 병행할 수 있습니다.

---

GitHub Copilot은 **VS Code(IDE)**뿐 아니라 **Copilot CLI(터미널)**에서도 동일한 `.github/` 설정 파일을 인식합니다. 개발 환경에 따라 두 가지 방식을 선택하거나 병행할 수 있습니다.

| 항목 | 🖥️ VS Code (IDE) | 💻 Copilot CLI (터미널) |
|------|:---:|:---:|
| **설정 파일 인식** | `copilot-instructions.md`, `instructions/`, `skills/`, `prompts/`, `agents/` | `copilot-instructions.md`, `instructions/`, `skills/`, `agents/` + `AGENTS.md` 등 |
| **코드 생성** | 에디터 내 인라인 + 채팅 패널 | 터미널에서 직접 파일 생성/수정 |
| **프롬프트 호출** | `/프롬프트명` (채팅) | 자연어로 직접 요청 |
| **에이전트 호출** | `@에이전트명` (채팅) | `/agent`로 선택 |
| **스킬 관리** | 자동 로드 + `/스킬명` | `/skills`로 관리 |
| **MCP 서버** | 설정 기반 자동 연결 | `/mcp`로 관리 |
| **코드 리뷰** | `@reviewer` 에이전트 | `/review` 명령어 |
| **변경사항 확인** | Git 패널 | `/diff` 명령어 |
| **플랜 모드** | `Shift+Tab`으로 Plan 모드 전환 | `/plan` 명령어 또는 `Shift+Tab` |
| **PR 생성 위임** | Copilot Coding Agent에 이슈 할당 | `/delegate`로 Copilot에 위임 |
