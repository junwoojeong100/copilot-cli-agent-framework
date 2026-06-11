---
applyTo: "**"
---

# Git 커밋 메시지 컨벤션

> 커밋·PR은 영어로 통일하며, 이 규칙이 `korean.instructions.md`보다 우선한다.
> 브랜치 push·PR 생성 정책(보호 브랜치 금지, `--draft --base main`)은 `AGENTS.md`를 따른다.

- 커밋 제목·본문, PR 제목·본문은 모두 **영어**로 작성한다(나머지 문서는 한국어 유지).
- 형식: `type(scope): subject` — `feat`·`fix`·`docs`·`refactor`·`test`·`chore`·`perf`·`style`.
- 제목은 **50자 이내**, 명령형 현재 시제로 쓰고 끝에 마침표를 붙이지 않는다.
  - 좋은 예: `feat: add refund specialist agent`
  - 나쁜 예: `feat: added refund agent` / `feat: 환불 에이전트 추가`
- 본문이 필요하면 제목과 한 줄 띄우고 72자로 줄바꿈하며 "무엇을/왜"를 설명한다.
- 항상 트레일러를 포함한다: `Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>`
