---
applyTo: "**/*.py"
---

# Azure 프로젝트 공통 인스트럭션

## Azure 인증

- 로컬 개발 환경에서는 `AzureCliCredential`을 사용하고 `az login`으로 인증한다.
- 배포 환경에서는 `DefaultAzureCredential` / Managed Identity를 사용한다.
- 인증 객체와 Chat 클라이언트는 재사용하고, 요청마다 새로 생성하지 않는다.

## 환경변수 / 시크릿 관리

- 환경변수는 `.env` 파일에 저장하고 `python-dotenv`로 로드한다.
- `.env` 파일은 `.gitignore`에 포함하여 절대 커밋하지 않는다.
- `.env.example`에 필요한 환경변수 키 목록을 공유한다.
- API 키, 엔드포인트 등 민감정보는 코드에 하드코딩하지 않는다.
- 필수 환경변수(`PROJECT_ENDPOINT` 등)는 앱 시작 시 검증하고, 누락 시 명확히 안내 후 종료한다.

## 보안

- 엔드포인트 URL, 연결 문자열 등은 환경변수로 관리한다.
- 사용자 입력은 항상 검증한 후 사용한다.
- 로그에 민감정보(토큰, 키, 비밀번호)를 출력하지 않는다.
