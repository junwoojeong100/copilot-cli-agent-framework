---
applyTo: "**/*.py"
---

# Python 프로젝트 공통 인스트럭션

- **버전/환경**: Python 3.14.5 + `.venv` 가상환경(`.gitignore` 제외). 설치는 `pip install -r requirements.txt`.
- **의존성**: `requirements.txt`에 명시하고 추가 시 갱신한다. SDK·핵심 패키지는 `==` 또는 `>=x,<y`로 버전을 고정하고, 프리릴리스는 `>=` 최소 버전 지정을 허용한다.
- **타입 힌트**를 적극 사용한다.
- **import 순서**: 표준 라이브러리 → 서드파티 → 로컬 모듈(그룹 사이 빈 줄).
- 모듈 최상단에 모듈 docstring, 함수에는 Google 스타일 docstring을 작성한다(언어 규칙은 `korean.instructions.md`).
- 모든 에이전트/IO 호출은 `async/await`, 진입점은 `if __name__ == "__main__": asyncio.run(main())`.
- 예외는 `try/except`로 감싸 사용자 친화적 한국어 메시지를 출력한다.
