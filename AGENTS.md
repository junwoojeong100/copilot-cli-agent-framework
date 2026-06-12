# AGENTS.md — Agent Harness

> 모든 에이전트가 역할과 무관하게 반드시 준수하는 가드레일이다. Git·외부 시스템 호출 **전에**
> 참조하며, 개별 에이전트 정의와 충돌하면 **이 문서가 우선**한다.

## Rule 1 — 기능 브랜치 push만 허용, 보호 브랜치·force push 금지 🟡

`main`·`master`·`develop`·`release/*`·`hotfix/*`는 **보호 브랜치**다. push는 그 외 기능
브랜치(`feat/*`·`fix/*`·`docs/*`·`chore/*`·`refactor/*` 등)에만 한다.

```bash
# ✅ 허용: 기능 브랜치 push
git push -u origin <feature-branch>

# ❌ 보호 브랜치 직접 push (main·master·develop)
git push origin main
# ❌ 히스토리 재작성 push — 모든 브랜치 (--force-with-lease, -f 포함)
git push --force
# ❌ 광역 push — --mirror, --tags 포함 (태그는 사용자가 직접 푼다)
git push --all
```

보호 브랜치는 **PR + 리뷰로만** 반영해 Human Review와 감사 추적을 보장하고, force push로 인한
공유 히스토리 손상을 차단하기 위함이다.

## Rule 2 — 커밋·PR 메시지는 영문 🟢

커밋·PR의 제목·본문을 모두 **영문**으로 쓰고,
[Conventional Commits](https://www.conventionalcommits.org/)(`feat`·`fix`·`docs`·`chore`·
`refactor`·`test` 등) + 명령형 현재 시제를 따른다. 예: `feat: add refund specialist agent`.
(상세 형식은 `.github/instructions/git-commit.instructions.md` 참조.)

## Rule 3 — PR은 항상 `main` 대상 Draft로 생성 🟢

```bash
gh pr create --draft --base main --title "..." --body "..."
```

## 표준 워크플로우 · 위반 시 처리

```bash
git checkout -b feat/my-change
git commit -m "feat: describe the change in English"
git push -u origin feat/my-change
gh pr create --draft --base main --title "..." --body "..."
```

위반을 감지하면 즉시 작업을 중단하고 사용자에게 보고하며, 필요하면 `git reset`/`git revert`로 복구한다.
