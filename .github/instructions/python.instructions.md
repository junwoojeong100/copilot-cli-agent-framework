---
applyTo: "**/*.py"
---

# Python 프로젝트 공통 인스트럭션

## 가상환경 설정

- Python 3.10+ 기반 `.venv` 가상환경을 사용한다.
- 권장 버전은 Python 3.12이다.
- 가상환경 생성 및 활성화:
  ```bash
  python -m venv .venv
  source .venv/bin/activate   # macOS / Linux
  # .venv\Scripts\activate    # Windows
  ```
- 패키지 설치는 가상환경 활성화 후 진행한다:
  ```bash
  pip install -r requirements.txt
  ```
- `.venv/` 디렉토리는 `.gitignore`에 포함하여 버전 관리에서 제외한다.

## 의존성 관리

- 프로젝트 의존성은 `requirements.txt`에 명시한다.
- 새 패키지를 추가하면 `requirements.txt`를 갱신한다.
- **SDK·핵심 패키지는 `==` 또는 `>=x,<y` 형태로 버전을 명시한다.**
- **프리릴리스 패키지는 `>=` 형태의 최소 버전 지정도 허용한다.**
- 일반 라이브러리를 추가할 때도 버전 범위를 명시해 재현 가능성을 유지한다.

## 코드 컨벤션

- 한국어 주석과 docstring을 사용한다.
- 모듈 최상단에 모듈 설명 docstring을 작성한다.
- 함수에는 Args/Returns를 포함한 Google 스타일 docstring을 작성한다.
- 타입 힌트를 적극 활용한다.
- import 순서: 표준 라이브러리 → 서드파티 → 로컬 모듈 (각 그룹 사이에 빈 줄).
- 모든 에이전트/IO 호출은 `async/await`로 작성하고, 진입점은
  `if __name__ == "__main__": asyncio.run(main())` 형태를 따른다.
- 예외는 `try/except`로 감싸고 사용자 친화적인 한국어 메시지를 출력한다.
