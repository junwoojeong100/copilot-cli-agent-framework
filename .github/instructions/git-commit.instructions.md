---
applyTo: "**"
---

# Git 커밋 메시지 컨벤션

> 이 규칙은 한국어 작성 컨벤션(`korean.instructions.md`)보다 **우선 적용**됩니다.
> 커밋 메시지는 오픈소스 관례·CI 도구·외부 기여자와의 호환성을 위해 영어로 통일합니다.

## 언어

- 모든 커밋 메시지(제목·본문)는 **영어**로 작성한다.
- 코드 주석·docstring·README 등 나머지 문서는 기존대로 한국어를 유지한다.

## 형식 (Conventional Commits)

- 형식: `type(scope): subject`
- 사용 가능한 `type`:
  - `feat` — 새 기능 / `fix` — 버그 수정 / `docs` — 문서만 변경
  - `refactor` — 기능 변화 없는 리팩터링 / `test` — 테스트 / `chore` — 부수 작업
  - `perf` — 성능 개선 / `style` — 포매팅

## 작성 규칙

- 제목은 **50자 이내**, **명령형 현재 시제**(imperative mood)로 작성한다.
  - 좋은 예: `feat: add refund specialist agent`
  - 나쁜 예: `feat: added refund agent` / `feat: 환불 에이전트 추가`
- 제목 끝에 마침표를 붙이지 않는다.
- 본문이 필요하면 제목과 한 줄 띄우고 **72자 단위로 줄바꿈**하며 "무엇을/왜"를 설명한다.

## 트레일러

- 이 프로젝트에서는 다음 트레일러를 항상 포함한다:

  ```
  Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>
  ```

## PR 생성 워크플로우

- 기능/수정 브랜치(`feat/*`, `fix/*`, `docs/*` 등)에 푸시한 직후 PR을 생성한다.
- PR 생성은 `gh pr create --draft --base main --head <branch>`를 사용한다 (AGENTS.md 준수).
- PR 제목과 본문도 커밋 메시지와 동일하게 **영어**로 작성한다.
