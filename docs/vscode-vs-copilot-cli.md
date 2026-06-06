# VS Code(IDE) vs Copilot CLI(터미널) 비교

> GitHub Copilot은 **VS Code(IDE)**와 **Copilot CLI(터미널)**에서 일부 `.github/`
> 커스터마이징을 공유하지만, 지원 범위와 적용 방식은 서로 다릅니다.

---

GitHub Copilot은 **VS Code(IDE)**와 **Copilot CLI(터미널)**에서 일부 `.github/` 커스터마이징을 공유하지만, 지원 범위와 적용 방식은 서로 다릅니다. 개발 환경에 따라 두 가지 방식을 선택하거나 병행할 수 있습니다.

| 항목 | 🖥️ VS Code (IDE) | 💻 Copilot CLI (터미널) |
|------|:---:|:---:|
| **설정 파일 인식** | `copilot-instructions.md`, `instructions/`, `skills/`, `prompts/`, `agents/` | `copilot-instructions.md`, `instructions/`, `skills/`, `agents/` + `AGENTS.md` 등 |
| **코드 생성** | 에디터 내 인라인 + 채팅 패널 | 터미널에서 직접 파일 생성/수정 |
| **프롬프트 호출** | `/프롬프트명` (채팅) | 프롬프트 파일 직접 호출 없음 (일반 자연어 입력 사용) |
| **에이전트 호출** | 에이전트 피커에서 선택 | `/agent` 선택 또는 `--agent` 플래그 |
| **스킬 관리** | 자동 로드 + `/스킬명` | `/skills`로 관리 |
| **MCP 서버** | 설정 기반 자동 연결 | `/mcp`로 관리 |
| **코드 리뷰** | 리뷰용 커스텀 에이전트 또는 적절한 에이전트 선택 | `/review` 명령어 |
| **변경사항 확인** | Git 패널 | `/diff` 명령어 |
| **플랜 모드** | Plan 에이전트(코딩 에이전트) 선택 | `/plan` 명령어 |
| **PR 생성 위임** | Copilot Coding Agent에 이슈 할당 | `/delegate`로 Copilot에 위임 |
