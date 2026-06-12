# 프로젝트 글로벌 인스트럭션

> 공통 규칙(Python·Azure·한국어·Git 커밋)은 `.github/instructions/`에, MAF 코드 생성의 상세
> 패턴·시그니처는 `agent-framework-codegen` 스킬에 있습니다. 이 파일에는 **프로젝트 개요와
> 항상 적용되는 핵심 제약**만 둡니다.

## 프로젝트 개요

**Microsoft Agent Framework(MAF)** 멀티 에이전트를 **Microsoft Foundry**(`FoundryChatClient`)에
연결해 단계별로 학습하는 실습 랩입니다. `src/`에 6개 주제·7개 콘솔 스크립트(`01`~`06`, 06은
하이브리드/Foundry IQ 2변형)를 구현하고, 심화 예제는 `src/hosted_agents/`(Hosted Agent 배포)에
있습니다. 예제별 상세·매핑은 README와 스킬을 참조하세요.

## 기술 스택

- **프레임워크**: `agent-framework` **1.8.x** — 핵심 `agent_framework`, 오케스트레이션
  `.orchestrations`, Foundry 연동 `.foundry`, Azure 연동 `.azure` (import·빌더 상세는 스킬)
- **인증**: `azure-identity` → `AzureCliCredential` (로컬 `az login`, 키리스)
- **모델**: Microsoft Foundry 배포 모델 (기본 `gpt-5.4`)
- **환경변수**: `python-dotenv` → 루트 `.env`

## 핵심 제약 (항상 적용)

- 핵심 에이전트 클래스는 **`agent_framework.Agent`** (이 버전에 `ChatAgent` 없음).
- 모든 에이전트·워크플로우 호출은 **`async/await`**(동기 금지), 진입점은 `asyncio.run(main())`.
- `FoundryChatClient`는 **한 번만** 생성해 공유하고, 스트리밍은 `src/_streaming.py` 헬퍼를 쓴다.
- `instructions`·사용자 응답은 **한국어**, 비밀키·엔드포인트는 `.env`에서 로드한다.
- 새 예제는 `src/`에 `NN_<name>.py`로 추가하고, 원격 반영은 PR 기반으로만 한다(`AGENTS.md`).

## Agent Framework 코드 생성

에이전트·워크플로우 코드를 생성·수정할 때 **반드시 `agent-framework-codegen` 스킬**을 참조한다
(`.github/skills/agent-framework-codegen/SKILL.md` — import 경로, 5가지 오케스트레이션,
`WorkflowBuilder`, 에이전트 합성(`as_tool`), MCP 연동, RAG, 트러블슈팅의 검증된 1.8.x
패턴·시그니처 수록). `FoundryChatClient`/`Agent` 생성, 스트리밍 반환 타입, 빌더 시그니처,
Handoff 제약(ASCII 도구명·persistence) 등 **상세 패턴은 모두 스킬에 있다**.
