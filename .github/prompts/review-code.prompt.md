---
description: "코드를 리뷰하고 개선사항을 제안합니다"
mode: "agent"
---

# 코드 리뷰 요청

## 대상

{{file_or_feature}} 코드를 리뷰해주세요.

## 체크리스트

아래 관점에서 검토하고 개선사항을 한국어로 알려주세요:

1. **에러 처리** — 예외 상황이 적절히 처리되는가? `PROJECT_ENDPOINT` 등 필수 환경변수를 검증하는가?
2. **보안** — 환경변수 노출, 입력값 검증 누락, 민감정보 하드코딩은 없는가?
3. **패턴 준수** — `FoundryChatClient` + `Agent` + 빌더(`SequentialBuilder`/`GroupChatBuilder`/`ConcurrentBuilder`/`HandoffBuilder`) 패턴을 따르는가?
4. **비동기** — 모든 에이전트 호출이 `async/await`이고 진입점이 `asyncio.run(main())`인가?
5. **워크플로우 정합성** — Handoff의 `add_handoff` 대상이 명시되었는가? GroupChat에 `max_rounds`가 있는가?
6. **한국어 품질** — docstring, 주석, 사용자 메시지, 에이전트 instructions가 자연스러운가?

## 출력 형식

```
### ✅ 잘된 점
- ...

### ⚠️ 개선 제안
- [파일:줄번호] 설명

### 🔴 반드시 수정
- [파일:줄번호] 설명
```
