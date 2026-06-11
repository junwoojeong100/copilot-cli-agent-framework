---
applyTo: "**/*.py"
---

# Azure 프로젝트 공통 인스트럭션

- **인증**: 로컬은 `AzureCliCredential`(`az login`), 배포는 `DefaultAzureCredential`/Managed Identity. credential·Chat 클라이언트는 재사용한다(요청마다 재생성 금지).
- **환경변수/시크릿**: `.env`(python-dotenv 로드, `.gitignore` 제외)로 관리하고, 필요한 키 목록은 `.env.example`에 공유한다. 키·엔드포인트·연결 문자열은 하드코딩하지 않는다.
- 필수 환경변수(`PROJECT_ENDPOINT` 등)는 시작 시 검증하고 누락 시 명확히 안내 후 종료한다.
- **보안**: 사용자 입력은 검증 후 사용하고, 로그에 토큰·키·비밀번호 등 민감정보를 출력하지 않는다.
