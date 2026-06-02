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

> RAG 실행에는 에이전트(컨테이너 관리 ID)에 Azure AI Search·Azure OpenAI 접근
> 권한(RBAC)이 필요합니다. 배포 후 에이전트 ID에 역할을 부여하세요.

## 로컬 실행 & 배포

```bash
azd ext install azure.ai.agents && azd auth login
azd ai agent init -m ./agent.manifest.yaml

# .env.example을 참고해 검색/임베딩 관련 환경 변수까지 설정
export FOUNDRY_PROJECT_ENDPOINT="https://<account>.services.ai.azure.com/api/projects/<project>"
export AZURE_AI_MODEL_DEPLOYMENT_NAME="gpt-5.4"
export SEARCH_SERVICE_ENDPOINT="https://<your-search>.search.windows.net"
export AZURE_OPENAI_ENDPOINT="https://<resource>.cognitiveservices.azure.com/"
export EMBEDDING_DEPLOYMENT_NAME="text-embedding-3-large"

azd ai agent run                                   # 로컬 호스트(:8088)
azd ai agent invoke --local "Pro 요금제는 얼마이고 기술 지원은 얼마나 빨리 받나요?"

azd provision   # (필요 시) 리소스 생성
azd deploy      # Foundry에 배포
```

배포 후 포털 **Assets → 에이전트 → Traces 탭**에서 검색 도구 호출과 모델 호출을
함께 추적할 수 있습니다.

> Hosted Agents는 현재 **preview**이며 `linux/amd64` 이미지를 요구합니다.
