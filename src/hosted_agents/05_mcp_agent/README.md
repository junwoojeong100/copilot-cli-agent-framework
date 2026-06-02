# 실습 5 — MCP 도구 연동 에이전트를 Hosted Agent로 배포

이 저장소 `src/05_mcp_agent.py`의 MCP 도구 연동 에이전트를 Foundry **Hosted Agent**로
배포합니다. 공개 MCP 서버 **Microsoft Learn MCP**에 연결해 공식 문서를 검색합니다.

## 호스팅에서의 차이 — 서버 측 MCP 등록

기존 예제는 `async with MCPStreamableHTTPTool(...)`로 **클라이언트 측** MCP 세션을
직접 관리합니다. 호스팅 환경에서는 `server.run()`이 자체 루프를 관리하므로,
`client.get_mcp_tool(...)`로 **서버 측 MCP 도구**를 등록합니다. Foundry 게이트웨이가
MCP 서버 호출과 도구 수명주기를 대신 관리합니다.

```python
from agent_framework_foundry_hosting import ResponsesHostServer

learn_mcp = client.get_mcp_tool(
    name="MicrosoftLearn",
    url="https://learn.microsoft.com/api/mcp",
    approval_mode="never_require",   # 매 호출 승인 없이 자동 사용
)
agent = Agent(client=client, instructions="...", tools=[learn_mcp],
              default_options={"store": False})
server = ResponsesHostServer(agent)
server.run()
```

> 인증이 필요한 MCP 서버는 `headers={"Authorization": "Bearer ..."}`를 추가하고,
> 비밀값은 `agent.yaml`의 `environment_variables`로 주입하세요(코드에 하드코딩 금지).

## 환경 변수

| 변수 | 설명 |
| --- | --- |
| `FOUNDRY_PROJECT_ENDPOINT` | Hosted Agent 표준. 런타임이 자동 주입 |
| `AZURE_AI_MODEL_DEPLOYMENT_NAME` | 모델 배포 이름. 런타임이 자동 주입 |
| `PROJECT_ENDPOINT` / `MODEL_DEPLOYMENT_NAME` | 저장소 로컬 호환용 폴백 (선택) |

## 로컬 실행 & 배포

```bash
azd ext install azure.ai.agents && azd auth login
azd ai agent init -m ./agent.manifest.yaml

export FOUNDRY_PROJECT_ENDPOINT="https://<account>.services.ai.azure.com/api/projects/<project>"
export AZURE_AI_MODEL_DEPLOYMENT_NAME="gpt-5.4"

azd ai agent run                                   # 로컬 호스트(:8088)
azd ai agent invoke --local "Agent Framework의 Handoff가 무엇인지 공식 문서 근거로 설명해줘"

azd provision   # (필요 시) 리소스 생성
azd deploy      # Foundry에 배포
```

배포 후 포털 **Assets → 에이전트 → Traces 탭**에서 MCP 도구 호출까지 추적할 수 있습니다.

> Hosted Agents는 현재 **preview**이며 `linux/amd64` 이미지를 요구합니다.
