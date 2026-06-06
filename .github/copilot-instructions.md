# 프로젝트 글로벌 인스트럭션

> 공통 규칙(Python 컨벤션, Azure 인증, 한국어 작성, Git 커밋)은 `.github/instructions/` 아래
> 파일에서 관리합니다. 이 파일에는 **이 프로젝트에만 해당하는 규칙**을 작성합니다.

## 프로젝트 개요

이 프로젝트는 **GitHub Copilot CLI**로 **Microsoft Agent Framework** 기반 멀티 에이전트를
단계별로 학습하는 실습 랩입니다. `src/` 디렉토리에 6개 주제, 총 7개 콘솔 스크립트 예제를 구현합니다:

1. **단일 에이전트** (`01_single_agent.py`) — 하나의 에이전트가 질문에 응답
2. **순차(Sequential) 워크플로우** (`02_sequential_workflow.py`) — 분석가→작가→편집자 파이프라인
3. **GroupChat 워크플로우** (`03_group_chat.py`) — 여러 에이전트가 협업 토론
4. **동시(Concurrent) 워크플로우** (`04_concurrent_workflow.py`) — 여러 전문가가 병렬 검토
5. **MCP 도구 연동** (`05_mcp_agent.py`) — `MCPStreamableHTTPTool`로 외부 시스템 호출
6. **RAG** (`06_rag_agent.py`, `06_rag_agent_foundry_iq.py`) — 검색 증강 생성
   (기본 버전과 Foundry IQ 버전 2가지 변형 제공)

## 기술 스택

- **AI Framework**: Microsoft Agent Framework (`agent-framework`)
- **Foundry 연동**: `FoundryChatClient` (`agent_framework.foundry`)
- **오케스트레이션**: `SequentialBuilder`, `GroupChatBuilder`, `ConcurrentBuilder` (`agent_framework.orchestrations`)
- **인증**: `azure-identity` → `AzureCliCredential` (로컬은 `az login` 세션 사용)
- **모델**: Microsoft Foundry 배포 모델 (기본 `gpt-5.4`)
- **환경변수**: `python-dotenv` → 루트 `.env`

## 프로젝트 코드 패턴

코드 생성 시 이 프로젝트의 기존 패턴을 따른다:

- Chat 클라이언트는 `FoundryChatClient(project_endpoint=..., model=..., credential=...)`로 생성 (키워드 인자)
- 에이전트는 `Agent(client=client, name=..., instructions=...)`로 생성하고(모든 인자 키워드 형태), 역할은 `instructions`로 부여
- Sequential은 `SequentialBuilder(participants=[...]).build()`로 순차 파이프라인 구성
- GroupChat은 `GroupChatBuilder(participants=..., selection_func=..., max_rounds=...).build()`
- Concurrent는 `ConcurrentBuilder(participants=[...]).build()`로 병렬 검토 구성
- 모든 진입점은 `if __name__ == "__main__": asyncio.run(main())`
- 환경변수는 `load_dotenv`로 로드하고, `PROJECT_ENDPOINT` 누락 시 친절한 오류 후 종료
- 새 예제는 `src/`에 `NN_<name>.py` 규칙으로 추가한다

## Agent Framework 코드 생성

에이전트·워크플로우 코드 생성 시 **`agent-framework-codegen` 스킬**을 참조한다.
(`.github/skills/agent-framework-codegen/SKILL.md`)

### 핵심 제약 (항상 적용)

- 모든 에이전트 호출은 `async/await` — 동기 호출 금지
- 에이전트 `instructions`와 사용자 응답은 **한국어**로 작성
- 비밀키·엔드포인트는 코드에 하드코딩하지 않고 `.env`에서 로드
- 원격 반영은 PR 기반으로만 (`AGENTS.md` 준수)
