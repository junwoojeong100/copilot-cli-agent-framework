# GitHub Copilot CLI 핵심 개념 — 구성요소

> [GitHub Copilot CLI 랩](copilot-cli-lab.md)에서 사용하는 **핵심 구성요소의 개념**을 정리합니다.
> 실제 실습 절차는 랩 문서에서 다루고, 이 문서는 "무엇인가 · 왜 쓰는가"에 집중합니다.

---

## Copilot CLI를 조종하는 4가지 요소

| 기술 | 무엇인가 | 핵심 기능 | 장점 |
|------|----------|-----------|------|
| **GitHub Copilot CLI** | 터미널에서 동작하는 에이전틱 코딩 도구 | 자연어 지시 → 계획·실행·검증 루프, 슬래시 커맨드(`/plan`·`/fleet`·`/model`), MCP·커스텀 에이전트 확장 | IDE 없이 터미널·CI에서 동작, 명령 실행 전 승인으로 안전, 모델 자유 선택 |
| **Custom Agent**<br/>(`.github/agents/*.agent.md`) | 역할·도구가 제한된 전용 에이전트 | frontmatter로 `description`·`tools`·`model` 지정, `copilot --agent <name>` 실행 | 역할 격리(리뷰어=읽기전용)로 안전·집중, 재사용·팀 공유 |
| **Skill**<br/>(`.github/skills/*/SKILL.md`) | Copilot에 주입하는 전문 지식·패턴 묶음 | `description`으로 트리거, 필요 시에만 본문 로드(점진적 공개) | 정확한 SDK 호출 유도, 토큰 절약, 환각 감소 |
| **Instructions**<br/>(`.github/*instructions.md`) | 항상/조건부로 적용되는 규칙 | `copilot-instructions.md`(전역) + `instructions/*`(`applyTo` 글롭) | 일관된 스타일·규칙 자동 준수, 반복 지시 제거 |

## Copilot CLI의 동작 특성

- **에이전트 코딩**: 자연어 지시를 "계획 → 실행 → 검증" 루프로 처리합니다.
- **안전 실행**: 명령을 실행하기 전에 사용자 승인을 받습니다. 신뢰할 수 있는 환경에서만 `--yolo`로
  자동 승인할 수 있습니다.
- **MCP 확장**: 모델 컨텍스트 프로토콜(MCP) 서버를 붙여 외부 시스템(문서·리소스·리포지토리)을
  도구로 사용합니다. → [MCP 서버 연결 가이드](mcp-servers-guide.md)
- **커스텀 에이전트**: `copilot --agent <name>`으로 역할이 한정된 에이전트를 실행합니다.

## 더 읽어보기

- [Copilot CLI 가이드](copilot-cli-guide.md) — 설치부터 활용까지
- [`.github/` 설정 가이드](github-config-guide.md) — 구성요소별 구조와 역할
- [멀티 에이전트 패턴](custom-agents-guide.md) — 에이전트 협업 패턴 상세
- [VS Code(IDE) vs Copilot CLI(터미널) 비교](vscode-vs-copilot-cli.md)
