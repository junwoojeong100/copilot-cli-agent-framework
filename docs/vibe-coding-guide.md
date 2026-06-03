# 바이브 코딩 — 설정만으로 코드 생성하기

> `.github/`의 instructions·prompts·skills·agents로 "의도"를 정의하고 Copilot이 코드를 생성하게 하는
> 바이브 코딩 워크플로우를 자세히 설명합니다.

---

**바이브 코딩**은 코드를 손으로 쓰는 대신, `.github/`의 instructions·prompts·skills로 의도를
정의하고 Copilot이 코드를 생성하게 하는 방식입니다. 핵심은 **"무엇을 만들 것인가"와 "어떤 패턴을
따를 것인가"를 정확히 문서화**하면, AI가 일관된 품질의 코드를 생성한다는 것입니다.

| 개발자가 준비 | Copilot이 수행 |
|---------------|----------------|
| `instructions/` — 기술 스택·코딩 규칙 | 규칙을 지킨 코드 생성 |
| `prompts/` — 반복 작업 템플릿 | 일관된 산출물 생성 |
| `skills/` — SDK 사용법·패턴 | 정확한 SDK 호출 |
| `agents/` — 리뷰/디버그 역할 | 자동 리뷰·디버깅 |

## CLI 바이브 코딩 워크플로우

```text
┌─────────────────────────────────────────────────────────────────┐
│  1. 시작: copilot 실행 → .github/ 설정 자동 인식                  │
│     copilot-instructions.md, instructions/*.md → 자동 적용       │
├─────────────────────────────────────────────────────────────────┤
│  2. 계획: /plan 모드로 구현 계획 수립 (선택)                       │
│     "동시 워크플로우에 리뷰어를 추가하려면 어떤 순서로?"            │
├─────────────────────────────────────────────────────────────────┤
│  3. 생성: 자연어로 코드 생성/수정 요청                              │
│     "UX 리뷰 전문 에이전트를 04_concurrent_workflow.py에 추가해줘" │
├─────────────────────────────────────────────────────────────────┤
│  4. 검증: /diff로 변경사항 확인 → /review로 코드 리뷰              │
├─────────────────────────────────────────────────────────────────┤
│  5. 완료: 커밋 또는 /delegate로 PR 생성을 Copilot에 위임           │
└─────────────────────────────────────────────────────────────────┘
```

## 실습 흐름

```text
1. (CLI) "UX 리뷰 전문 에이전트를 동시 워크플로우에 추가해줘"라고 자연어로 요청
   (VS Code Copilot Chat이라면 /add-agent 프롬프트로 호출)
2. Copilot이 agent-framework-codegen 스킬 규칙(import·async·instructions)에 맞춰 코드 생성
3. copilot --agent reviewer 로 리뷰 → 수정
4. python src/04_concurrent_workflow.py 로 실행 검증
```

이후 자연어로 요청하면 `.github/copilot-instructions.md`와 `instructions/*.md`의 규칙을 반영한
코드를 생성합니다:

```text
> "RAG 에이전트에 top_k를 5로 변경해줘"
> "새 MCP 도구를 추가해줘"
> "동시 워크플로우에 새로운 검토 관점을 추가해줘"
```

## 재사용 팁

- **공용 인스트럭션 복사**: `instructions/python.instructions.md`·`azure.instructions.md`·
  `korean.instructions.md`·`git-commit.instructions.md`를 새 프로젝트의 `.github/instructions/`에
  복사하면 동일한 컨벤션·보안·작성 규칙이 즉시 적용됩니다.
- **새 예제 추가 규칙**: 예제는 `src/`에 `NN_<name>.py` 규칙으로 추가하고, 진입점은
  `if __name__ == "__main__": asyncio.run(main())` 패턴을 따릅니다.
- **설정 구조 참고**: `.github/` 설정의 동작 방식과 구성요소별 역할은
  [`docs/github-config-guide.md`](github-config-guide.md)를 참고하세요.

> ✅ **최종 체크포인트**: 직접 만든 `.github/` 설정만으로 Copilot이 새 에이전트/기능을 추가하게
> 만들 수 있으면, 이 실습의 목표를 달성한 것입니다.

> 📎 더 깊은 바이브 코딩 워크플로우 예시는 참고 프로젝트
> [`vibe-coded-foundry-agents`](https://github.com/junwoojeong100/vibe-coded-foundry-agents)에서
> 확인할 수 있습니다.
