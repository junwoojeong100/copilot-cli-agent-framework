# MCP 서버 연결 — 개념과 구성

> [GitHub Copilot CLI 랩](copilot-cli-lab.md) Part 3에서 사용하는 **MCP 서버의 개념·구성·인증·권한**을
> 정리합니다. 실제 적용·확인 절차(`/mcp`, `az login` 등)는 랩 문서에서 다룹니다.

---

## MCP 서버란

모델 컨텍스트 프로토콜(MCP)은 에이전트가 **외부 시스템(문서·DB·API·리포지토리)을 도구로 호출**하기
위한 표준 프로토콜입니다. Copilot CLI는 `.copilot/mcp-config.json`에 등록된 서버를 읽어, 에이전트가
필요할 때 해당 도구를 자동으로 사용합니다. 즉 에이전트가 "일꾼"이라면 MCP 서버는 "일꾼이 쓰는 연장"입니다.

## 이 저장소에 설정된 서버

`.copilot/mcp-config.json`에는 **Azure · GitHub · Microsoft Learn** 세 가지 서버가 설정되어 있습니다.

```json
{
  "mcpServers": {
    "github": {
      "type": "http",
      "url": "https://api.githubcopilot.com/mcp/",
      "headers": { "Authorization": "Bearer ${GITHUB_PERSONAL_ACCESS_TOKEN}" },
      "tools": ["*"]
    },
    "azure": {
      "type": "local",
      "command": "npx",
      "args": ["-y", "@azure/mcp@latest", "server", "start"],
      "tools": ["*"]
    },
    "microsoftLearn": {
      "type": "http",
      "url": "https://learn.microsoft.com/api/mcp",
      "tools": ["*"]
    }
  }
}
```

| 서버 | 유형 | 용도 | 인증 |
|------|------|------|------|
| **github** | 원격(http) | 이슈·PR·리포지토리 탐색/조작 | PAT — `GITHUB_PERSONAL_ACCESS_TOKEN` 환경변수 |
| **azure** | 로컬(npx) | 구독 내 Azure 리소스 조회·관리 (Foundry 포함) | `az login` 세션 |
| **microsoftLearn** | 원격(http) | Microsoft/Azure 공식 문서·코드 샘플 검색 | 불필요 |

## 인증과 선택 사항

- **github · azure 서버 인증은 모두 선택**입니다. PAT·Azure 없이도 `microsoftLearn`(인증 불필요)
  서버만으로 기본 흐름을 따라갈 수 있습니다.
- Copilot CLI는 GitHub MCP 서버를 **기본 내장**하고 있어, 위 `github` 항목 없이도 기본 GitHub 기능은
  사용할 수 있습니다. 명시적으로 두면 사용할 토큰/도구를 직접 제어할 수 있습니다.
- **단, `github` 블록을 유지하면 `GITHUB_PERSONAL_ACCESS_TOKEN`이 반드시 설정되어 있어야 인증 오류가
  나지 않습니다.** PAT를 쓰지 않으려면 이 블록을 제거하고 기본 내장 서버를 사용하세요.
- `tools`는 `["*"]`로 모든 도구를 허용하므로, 읽기 전용만 노출하려면 서버 문서의 도구명으로 좁히세요.

## ⚠️ Azure MCP 권한 주의

`azure` 서버는 `tools: ["*"]`이므로 구독 리소스를 **조회뿐 아니라 변경/삭제**할 수 있습니다. 실제 가능한
작업은 `az login` 계정의 **RBAC 권한** 범위로 제한되며, Copilot CLI는 실행 전 명령을 확인받습니다.
조회만 허용하려면 `tools`를 읽기 전용 도구명으로 좁히거나, 읽기 권한만 가진 계정으로 `az login` 하세요.

## 더 읽어보기

- [Copilot CLI 핵심 개념](copilot-cli-concepts.md) — 구성요소 개요
- [Copilot CLI 가이드](copilot-cli-guide.md) — 설치부터 활용까지
