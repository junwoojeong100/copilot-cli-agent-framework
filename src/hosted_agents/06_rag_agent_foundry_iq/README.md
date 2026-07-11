# 실습 6 (변형) — Foundry IQ RAG 에이전트를 Hosted Agent로 배포

이 저장소 `src/06_rag_agent_foundry_iq.py`의 **Foundry IQ RAG**(지식 베이스 + agentic
retrieval)를 Foundry **Hosted Agent**로 배포합니다. 기존
[`06_rag_agent/`](../06_rag_agent/)가 하이브리드 검색을 **함수 도구**로 노출하는 것과
달리, 이 변형은 검색을 **Foundry IQ 지식 베이스**에 위임합니다.
`AzureAISearchContextProvider`(agentic 모드)를 컨텍스트 프로바이더로 연결하면,
에이전트가 질문을 받을 때마다 지식 베이스에서 **질의 계획 기반 멀티쿼리 검색**을
수행하고 그 결과를 근거로 답변합니다.

> **Hosted 전용 호환성**: MAF core `1.11.0` + foundry/openai `1.10.1` +
> Azure AI Search provider `1.0.0b260521` + hosting `1.0.0a260709` +
> Responses `2.0.0` + azd `azure.ai.agents>=1.0.0-beta.5` 조합입니다.
> 콘솔 예제의 MAF 1.8.1 환경과 분리된 가상환경에 설치하세요.
> 배포 계정에는 Foundry 프로젝트 범위의 **Foundry Project Manager** 역할이 필요합니다.

## 전제 — 지식 베이스 사전 생성

이 호스팅 예제는 **이미 생성된 지식 베이스에 연결만** 합니다(검색=데이터 리더 권한).
저장소 루트에서 `src/06_rag_agent_foundry_iq.py`를 한 번 실행하면 인덱스 시드 +
지식 베이스(기본 `maf-lab-knowledge-iq-v3-kb`)가 자동 생성됩니다.

```bash
python src/06_rag_agent_foundry_iq.py   # IQ 인덱스 시드 + 지식 베이스 생성
```

> 지식 베이스 **생성**에는 컨트롤플레인 권한(Search Service Contributor)이 필요하지만,
> 이는 콘솔 실행 사용자에게만 요구됩니다. 호스팅 인스턴스는 **연결(검색)만** 하므로
> 데이터 리더 권한만 있으면 됩니다.

## 핵심 코드 (`main.py`)

```python
async def main() -> None:
    credential = DefaultAzureCredential()
    aio_credential = AioDefaultAzureCredential()
    try:
        async with AzureAISearchContextProvider(
            endpoint=SEARCH_ENDPOINT,
            knowledge_base_name="maf-lab-knowledge-iq-v3-kb",  # 기존 지식 베이스에 연결
            mode="agentic",
            credential=aio_credential,                          # 비동기 자격 증명 필수
            retrieval_reasoning_effort="low",                  # 질의 계획 활성화
        ) as provider:
            agent = Agent(client=FoundryChatClient(...), instructions="...근거 기반 답변...",
                          context_providers=[provider], default_options={"store": False})
            server = ResponsesHostServer(agent)
            await server.run_async()
    finally:
        await aio_credential.close()
        credential.close()
```

> ⚠️ `AzureAISearchContextProvider`는 내부적으로 **비동기** Search 클라이언트를 쓰므로
> 반드시 `azure.identity.aio` 자격 증명을 전달해야 합니다. `async with`와
> `run_async()`를 함께 사용하면 서버가 종료될 때 프로바이더의 Search 클라이언트와
> 동기·비동기 자격 증명을 모두 정리할 수 있습니다.

## 환경 변수

| 변수 | 설명 |
| --- | --- |
| `FOUNDRY_PROJECT_ENDPOINT` | Hosted Agent 표준. 런타임이 자동 주입 |
| `AZURE_AI_MODEL_DEPLOYMENT_NAME` | 모델 배포 이름. 런타임이 자동 주입 |
| `SEARCH_SERVICE_ENDPOINT` | Azure AI Search 엔드포인트 |
| `SEARCH_KNOWLEDGE_BASE_NAME` | 연결할 지식 베이스 이름(기본 `maf-lab-knowledge-iq-v3-kb`) |
| `FOUNDRY_IQ_REASONING_EFFORT` | 질의 계획 추론 강도(minimal/low/medium, 기본 low) |
| `PROJECT_ENDPOINT` / `MODEL_DEPLOYMENT_NAME` | 저장소 로컬 호환용 폴백 (선택) |

> 검색에는 에이전트(컨테이너의 관리형 ID, Managed Identity)에 Azure AI Search 데이터
> 접근 권한(RBAC)이 필요합니다. **배포 후** `azd ai agent show <name>` 으로 *Instance
> Identity Principal ID* 를 확인하고 아래 역할을 부여하세요(전파에 1~2분 소요).
>
> ```bash
> PRINC="00000000-0000-0000-0000-000000000000"
> SEARCH_SCOPE="/subscriptions/.../resourceGroups/.../providers/Microsoft.Search/searchServices/..."
> az role assignment create --assignee-object-id $PRINC --assignee-principal-type ServicePrincipal \
>   --role "Search Index Data Reader" --scope "$SEARCH_SCOPE"
> ```
>
> 추가로, Foundry IQ 지식 베이스가 질의를 계획·벡터화하려면 **Search 서비스의 관리 ID**가
> Microsoft Foundry 리소스에 `Cognitive Services User` 권한을 가져야 합니다
> (루트 README의 프로비저닝 절차에서 부여).

## 로컬 실행 & 배포

```bash
azd ext install microsoft.foundry
azd auth login
mkdir -p ~/deploy/rag-iq-agent && cd ~/deploy/rag-iq-agent
REPO="/path/to/agent-framework-labs"
azd ai agent init . --no-prompt \
  -m "$REPO/src/hosted_agents/06_rag_agent_foundry_iq/azure.yaml" \
  --project-id "<Foundry 프로젝트 리소스 ID>" \
  --model-deployment gpt-5.4

# .env.example을 참고해 Foundry IQ 관련 환경 변수까지 설정
export SEARCH_SERVICE_ENDPOINT="https://<your-search>.search.windows.net"
export SEARCH_KNOWLEDGE_BASE_NAME="maf-lab-knowledge-iq-v3-kb"
export FOUNDRY_IQ_REASONING_EFFORT="low"

azd env set AZURE_AI_MODEL_DEPLOYMENT_NAME gpt-5.4
azd env set SEARCH_SERVICE_ENDPOINT "$SEARCH_SERVICE_ENDPOINT"
azd env set SEARCH_KNOWLEDGE_BASE_NAME "$SEARCH_KNOWLEDGE_BASE_NAME"
azd env set FOUNDRY_IQ_REASONING_EFFORT "$FOUNDRY_IQ_REASONING_EFFORT"

azd ai agent run                                   # 터미널 1: 로컬 호스트(:8088, 블로킹)
azd ai agent invoke --local "Pro 요금제는 얼마이고 기술 지원은 얼마나 빨리 받나요?"  # 터미널 2

# 배포는 로컬 서버를 중지한 뒤 실행합니다.
azd provision --no-prompt   # (필요 시) 리소스 생성
azd deploy --no-prompt      # 코드 ZIP 원격 빌드 → Foundry에 배포
```

`low`와 `medium`은 LLM이 복합 질문을 하위 질의로 계획합니다. `minimal`은 비용과 지연을
줄이는 대신 질의 계획을 건너뛰고 단일 검색 의도를 그대로 실행합니다.

배포 후 포털 **Assets → 에이전트 → Traces 탭**에서 지식 베이스 검색과 모델 호출을
함께 추적할 수 있습니다.

> Hosted Agents는 현재 **preview**입니다. 권장 코드 ZIP 배포 모드는 로컬 Docker가
> 필요 없습니다. 컨테이너 배포 모드를 선택하는 경우에만 `linux/amd64` 이미지가
> 필요합니다.
