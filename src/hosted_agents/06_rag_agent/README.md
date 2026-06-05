# 실습 6 — RAG 에이전트를 Hosted Agent로 배포

이 저장소 `src/06_rag_agent.py`의 RAG(검색 증강 생성)를 Foundry **Hosted Agent**로
배포합니다. Azure AI Search 하이브리드(키워드+벡터) 검색을 **함수 도구**로 노출해,
에이전트가 질문을 받으면 스스로 검색→증강→생성을 수행합니다.

## 전제 — 인덱스 시드

이 호스팅 예제는 **이미 시드된 검색 인덱스**를 읽습니다.
저장소 루트에서 `src/06_rag_agent.py`를 한 번 실행하면 동일한 인덱스
(기본값 `maf-lab-knowledge-v1`)가 생성·시드됩니다.

```bash
python src/06_rag_agent.py   # 인덱스 생성 + 지식 베이스 시드
```

## 핵심 코드 (`main.py`)

```python
def search_knowledge_base(query: Annotated[str, "검색어"]) -> str:
    """하이브리드(키워드+벡터) 검색으로 관련 문서를 찾아 컨텍스트로 반환."""
    ...  # Azure AI Search 하이브리드 검색

agent = Agent(client=..., instructions="...검색 후 근거 기반 답변...",
              tools=[search_knowledge_base], default_options={"store": False})
server = ResponsesHostServer(agent)
server.run()
```

## 환경 변수

| 변수 | 설명 |
| --- | --- |
| `FOUNDRY_PROJECT_ENDPOINT` | Hosted Agent 표준. 런타임이 자동 주입 |
| `AZURE_AI_MODEL_DEPLOYMENT_NAME` | 모델 배포 이름. 런타임이 자동 주입 |
| `SEARCH_SERVICE_ENDPOINT` | Azure AI Search 엔드포인트 |
| `SEARCH_INDEX_NAME` | 검색 인덱스 이름(기본 `maf-lab-knowledge-v1`) |
| `AZURE_OPENAI_ENDPOINT` | 임베딩 호출용 Azure OpenAI 엔드포인트 |
| `EMBEDDING_DEPLOYMENT_NAME` | 임베딩 모델 배포 이름 |
| `AZURE_OPENAI_API_VERSION` | Azure OpenAI API 버전 |
| `PROJECT_ENDPOINT` / `MODEL_DEPLOYMENT_NAME` | 저장소 로컬 호환용 폴백 (선택) |

> RAG 실행에는 에이전트(컨테이너의 관리형 ID, Managed Identity)에 Azure AI Search·Azure OpenAI 접근
> 권한(RBAC)이 필요합니다. **배포 후** `azd ai agent show <name>` 으로 *Instance Identity
> Principal ID* 를 확인하고 아래 두 역할을 부여하세요(전파에 1~2분 소요).
>
> ```bash
> PRINC="00000000-0000-0000-0000-000000000000"
> SEARCH_SCOPE="/subscriptions/.../resourceGroups/.../providers/Microsoft.Search/searchServices/..."
> FOUNDRY_SCOPE="/subscriptions/.../resourceGroups/.../providers/Microsoft.CognitiveServices/accounts/..."
> az role assignment create --assignee-object-id $PRINC --assignee-principal-type ServicePrincipal \
>   --role "Search Index Data Reader" --scope "$SEARCH_SCOPE"
> az role assignment create --assignee-object-id $PRINC --assignee-principal-type ServicePrincipal \
>   --role "Cognitive Services OpenAI User" --scope "$FOUNDRY_SCOPE"
> ```
>
> 권한이 없으면 검색 함수가 실패하고 첫 호출이 `session_not_ready`로 끝납니다.

## 로컬 실행 & 배포

```bash
azd ext install azure.ai.agents && azd auth login
mkdir -p ~/deploy/rag-agent && cd ~/deploy/rag-agent
REPO="/path/to/copilot-cli-agent-framework"
azd ai agent init --no-prompt \
  -m "$REPO/src/hosted_agents/06_rag_agent/agent.manifest.yaml" \
  --agent-name maf-lab-rag-agent \
  --project-id "<Foundry 프로젝트 리소스 ID>" \
  --model-deployment gpt-5.4 \
  --deploy-mode code --runtime python_3_13 --entry-point main.py \
  --protocol responses --force

# .env.example을 참고해 검색/임베딩 관련 환경 변수까지 설정
export FOUNDRY_PROJECT_ENDPOINT="https://<account>.services.ai.azure.com/api/projects/<project>"
export AZURE_AI_MODEL_DEPLOYMENT_NAME="gpt-5.4"
export SEARCH_SERVICE_ENDPOINT="https://<your-search>.search.windows.net"
export SEARCH_INDEX_NAME="maf-lab-knowledge-v1"
export AZURE_OPENAI_ENDPOINT="https://<resource>.cognitiveservices.azure.com/"
export EMBEDDING_DEPLOYMENT_NAME="text-embedding-3-large"
export AZURE_OPENAI_API_VERSION="2024-10-21"

# 배포 시 기존 모델 배포를 그대로 사용하려면 init이 만든 azure.yaml의
# deployments 블록을 제거하고 azd 환경값을 고정합니다.
azd env set AZURE_AI_MODEL_DEPLOYMENT_NAME "$AZURE_AI_MODEL_DEPLOYMENT_NAME"
azd env set AI_AGENT_PENDING_PROVISION ""
azd env set SEARCH_SERVICE_ENDPOINT "$SEARCH_SERVICE_ENDPOINT"
azd env set SEARCH_INDEX_NAME "$SEARCH_INDEX_NAME"
azd env set AZURE_OPENAI_ENDPOINT "$AZURE_OPENAI_ENDPOINT"
azd env set EMBEDDING_DEPLOYMENT_NAME "$EMBEDDING_DEPLOYMENT_NAME"
azd env set AZURE_OPENAI_API_VERSION "$AZURE_OPENAI_API_VERSION"

azd ai agent run                                   # 터미널 1: 로컬 호스트(:8088, 블로킹)
azd ai agent invoke --local "Pro 요금제는 얼마이고 기술 지원은 얼마나 빨리 받나요?"  # 터미널 2

# 배포는 로컬 서버를 중지한 뒤 실행합니다.
azd provision --no-prompt   # (필요 시) 리소스 생성
azd deploy --no-prompt      # 코드 ZIP 원격 빌드 → Foundry에 배포
```

배포 후 포털 **Assets → 에이전트 → Traces 탭**에서 검색 도구 호출과 모델 호출을
함께 추적할 수 있습니다.

> Hosted Agents는 현재 **preview**입니다. 권장 코드 ZIP 배포 모드는 로컬 Docker가
> 필요 없습니다. 컨테이너 배포 모드를 선택하는 경우에만 `linux/amd64` 이미지가
> 필요합니다.
