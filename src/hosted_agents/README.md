# (심화) Hosted Agent 배포 실습

MAF로 만든 **에이전트**와 **워크플로우**를 **Microsoft Foundry Hosted Agent**
(관리형 컨테이너)로 배포하는 실습입니다. 기존 `src/01~06` 코드는 **그대로 두고**,
같은 에이전트 설계를 호스팅용으로 재구성해 배포하는 방법을 보여줍니다.

## 왜 Hosted Agent인가

Foundry Agent SDK v2로 **재작성하지 않아도**, MAF 에이전트/워크플로우를
컨테이너로 패키징해 Foundry에 배포하면 관리형 서비스의 이점을 그대로 얻습니다.

- **관리형 인프라** — 컨테이너·웹서버·스케일링을 직접 구성할 필요 없음
- **세션 관리 내장** — 대화 이력·업로드 파일을 플랫폼이 영속화
- **전용 에이전트 ID** — 모델·도구 접근용 Entra ID 자동 부여
- **자동 trace/monitoring** — 포털 Traces 탭 + Application Insights 연동
- **OpenAI 호환 엔드포인트** — `/responses` 프로토콜로 호출

## 핵심 패턴

```python
from agent_framework_foundry_hosting import ResponsesHostServer

# 단일 에이전트
server = ResponsesHostServer(agent)
server.run()

# 워크플로우 → .as_agent()로 감싸 동일하게 호스팅
workflow_agent = SequentialBuilder(participants=[...]).build().as_agent()
server = ResponsesHostServer(workflow_agent)
server.run()
```

## 예제 목록

| 폴더 | 원본 | 내용 |
| --- | --- | --- |
| [`01_single_agent/`](01_single_agent/) | `src/01_single_agent.py` | 단일 에이전트(기술 어시스턴트) 호스팅 |
| [`02_sequential_workflow/`](02_sequential_workflow/) | `src/02_sequential_workflow.py` | 순차 워크플로우(분석가→작가→편집자) 호스팅 |
| [`03_group_chat/`](03_group_chat/) | `src/03_group_chat.py` | GroupChat 워크플로우(기획자·개발자·디자이너) 호스팅 |
| [`04_concurrent_workflow/`](04_concurrent_workflow/) | `src/04_concurrent_workflow.py` | 동시 워크플로우(보안·성능·UX 리뷰어) 호스팅 |
| [`05_mcp_agent/`](05_mcp_agent/) | `src/05_mcp_agent.py` | MCP 도구 연동 에이전트(`get_mcp_tool`) 호스팅 |
| [`06_rag_agent/`](06_rag_agent/) | `src/06_rag_agent.py` | RAG 에이전트(하이브리드 검색 함수 도구) 호스팅 |

> 02~04 워크플로우는 `Workflow.as_agent()`로 감싸 호스팅하고, 05는 서버 측
> `client.get_mcp_tool(...)`, 06은 하이브리드 검색을 **함수 도구**로 노출합니다.

각 폴더는 독립 배포 가능한 azd 프로젝트로, 다음 파일을 포함합니다:
`main.py`, `requirements.txt`, `Dockerfile`, `agent.yaml`, `agent.manifest.yaml`,
`.env.example`, `.dockerignore`, `.azdignore`, `README.md`.

> `agent.manifest.yaml` 은 `azd ai agent init -m`의 **입력**이고,
> `agent.yaml` 은 init 후 azd가 **배포에 사용하는 런타임 스펙**입니다.

## 기존 실습과의 차이

| 기존 실습(01~06) | Hosted Agent 실습 |
| --- | --- |
| 프롬프트 1건 처리 후 종료 | `/responses` HTTP 서버 상시 구동 |
| `asyncio.run(main())` | `server.run()` (동기) |
| `AzureCliCredential` | `DefaultAzureCredential` (컨테이너 관리 ID) |
| 저장소 `.env`(`PROJECT_ENDPOINT`) | Foundry 주입 env(`FOUNDRY_PROJECT_ENDPOINT`) |

> 호스팅 `main.py`는 자체 완결적이라 `src/_streaming.py` 같은 저장소 헬퍼를
> import하지 않습니다(컨테이너 빌드 시 폴더 외부 파일에 의존하지 않도록).

## 사전 준비

```bash
pip install agent-framework agent-framework-foundry-hosting
azd ext install azure.ai.agents
azd auth login
```

## 빠른 시작 (각 폴더에서)

```bash
azd ai agent init -m ./agent.manifest.yaml   # azd 프로젝트 초기화
azd ai agent run                             # 로컬 호스트(:8088)
azd provision                                # (필요 시) 리소스 생성
azd deploy                                   # Foundry에 배포
```

자세한 단계와 호출 예시는 각 폴더의 `README.md`를 참고하세요.

> ⚠️ Hosted Agents는 현재 **preview**이며, `linux/amd64` 컨테이너 이미지를 요구합니다.
> Apple Silicon에서는 `docker build --platform linux/amd64 .` 로 빌드하세요.
