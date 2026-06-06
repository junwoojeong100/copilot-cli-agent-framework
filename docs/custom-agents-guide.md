# Copilot CLI 멀티 에이전트(Custom Agent) 패턴

> `.github/agents/`에 정의한 역할별 커스텀 에이전트와 4가지 멀티 에이전트 협업 패턴을 설명합니다.

---

`.github/agents/`에 역할별 에이전트를 정의하고 다양한 방법으로 호출할 수 있습니다.
이 저장소에는 **7개** 에이전트가 포함되어 있습니다.

## 커스텀 에이전트 파일 형식

커스텀 에이전트 파일은 `.github/agents/<이름>.agent.md` 경로에 저장합니다.
파일은 **YAML frontmatter + 본문 지시문** 구조를 따릅니다.

```yaml
---
name: 에이전트 표시 이름
description: 에이전트 역할 요약 (Copilot이 자동 선택 시 참고)
---
```

frontmatter 아래 본문에는 에이전트의 역할, 행동 규칙, 출력 형식, 위임 기준 같은
**행동 지침을 마크다운으로 작성**합니다.

이 저장소에서는 다음 파일이 실제 예시입니다.

- `.github/agents/orchestrator.agent.md`
- `.github/agents/reviewer.agent.md`

## 에이전트 호출 방법

커스텀 에이전트는 다음 3가지 방식으로 사용할 수 있습니다.

1. **CLI 플래그** — 세션 시작 시 특정 에이전트를 지정
   ```bash
   copilot --agent <에이전트명>
   ```
2. **슬래시 명령** — 대화 중 `/agent`를 입력한 뒤 에이전트를 선택
3. **자연어 지시** — 프롬프트에서 에이전트 이름을 직접 언급
   - 예: `reviewer 에이전트로 검토해줘`

CLI 플래그는 처음부터 역할을 고정할 때 유용하고, `/agent`와 자연어 지시는
대화 도중에 에이전트를 전환하거나 특정 역할을 요청할 때 편리합니다.

```bash
# 오케스트레이터 — 요청 분석 후 최적 패턴 자동 선택
copilot --agent orchestrator --yolo

# 4가지 협업 패턴 에이전트 직접 실행
copilot --agent planner_executor --yolo    # 📐 계획-실행 패턴
copilot --agent debate_critic --yolo       # ⚔️ 토론-비평 패턴
copilot --agent generator_evaluator --yolo # ⚡ 생성-평가 패턴
copilot --agent code_generation --yolo     # 🏗️ 코드 생성 패턴

# 단독 전문 에이전트
copilot --agent reviewer                   # 코드 리뷰 (읽기 전용)
copilot --agent debugger                   # 환경/런타임 문제 진단
```

`orchestrator`는 요청을 분석해 4가지 협업 패턴 중 하나를 선택하고 해당 패턴 에이전트에 위임합니다:

| 사용자 의도 | 선택 패턴 |
|------------|----------|
| "구현해줘", "셋업해줘", "마이그레이션" | 📐 Planner-Executor |
| "비교해줘", "장단점", "뭐가 나을까" | ⚔️ Debate & Critic |
| "생성해줘", "리뷰해줘", "개선해줘" | ⚡ Generator-Evaluator |
| "설계하고 구현해줘", "코드 작성하고 리뷰해줘" | 🏗️ Code Generation |

## 스킬(Skill) 연동

커스텀 스킬은 `.github/skills/<스킬명>/SKILL.md` 경로에 저장합니다.
스킬 파일은 에이전트가 특정 작업을 수행할 때 참고하는 **전문 지식 / 절차 문서**입니다.

- **자동 로드**: 관련 작업이 감지되면 Copilot이 적절한 스킬을 자동으로 참조합니다.
- **수동 호출**: `/skills`로 사용 가능한 스킬 목록을 확인하고, `/스킬명`으로 직접 호출할 수 있습니다.

이 저장소의 실제 예시는 `.github/skills/agent-framework-codegen/SKILL.md`입니다.
Microsoft Agent Framework 기반 코드 생성, 워크플로우 구성, Foundry 연동 시 참고하는
프로젝트 전용 지침이 이 파일에 정리되어 있습니다.

## 에이전트 패턴 상세

각 패턴은 **여러 전문 에이전트가 역할을 분담**하여 협업합니다. 모든 팀에는 과정·결과를 문서화하는 **Scribe**가 포함됩니다.

### 📐 Planner-Executor

> 계획 수립과 실행을 분리하여 체계적으로 작업을 완수

| 에이전트 | 역할 |
|---------|------|
| **Planner** | 요구사항 분석 → 태스크 목록·의존성·완료 기준 정의 |
| **Executor** | 계획에 따라 태스크를 순서대로 구현 |
| **Validator** | 각 태스크 검증 — Pass/Revise 판정 |
| **Scribe** | 계획·실행·검증 과정 문서화 |

```
요구사항 → Planner → Executor → Validator →(Revise)→ Planner
                                          →(Pass)→ 다음 태스크 → … → Scribe
```

적합한 작업: 구현, 마이그레이션, 리팩토링, 단계별 셋업

---

### ⚔️ Debate & Critic

> 대립적 논증과 비평을 통해 최선의 결론에 도달

| 에이전트 | 역할 |
|---------|------|
| **Proposer** | 찬성/제안 측 입장과 근거 제시 |
| **Opponent** | 반대 논증 및 대안 제시 |
| **Critic** | 양측 논증의 강점·약점 객관적 분석 |
| **Synthesizer** | 논의 종합 후 수렴 판단 — 수렴 시 권고안 도출 |
| **Scribe** | 논의 과정·최종 결론 문서화 |

```
주제 → Proposer → Opponent → Critic → Synthesizer →(수렴)→ Scribe
                                                  →(미수렴)→ Round 2 (최대 3 Rounds)
```

적합한 작업: 기술 선택, 아키텍처 비교, 장단점 분석

---

### ⚡ Generator-Evaluator

> 생성과 평가를 반복하여 품질을 높임

| 에이전트 | 역할 |
|---------|------|
| **Generator** | 요구사항을 충족하는 초안 생성 |
| **Evaluator** | 기준표 기반 품질 평가 — Pass/Fail 판정 |
| **Refiner** | Evaluator 피드백 반영하여 산출물 개선 |
| **Scribe** | Cycle별 개선 이력·최종 결과 문서화 |

```
요구사항 → Generator → Evaluator →(Pass)→ Scribe
                               →(Fail)→ Refiner → Evaluator (최대 3 Cycles)
```

적합한 작업: 코드·문서 생성, 리뷰 기반 반복 개선

---

### 🏗️ Code Generation

> 설계 → 구현 → 리뷰를 체계적으로 연결

| 에이전트 | 역할 |
|---------|------|
| **Architect** | 코드 구조·인터페이스·의존성·패턴 설계 |
| **Developer** | Architect 설계에 따라 코드 구현, Reviewer 피드백 반영 수정 |
| **Reviewer** | 보안·코드 품질·설계 준수 검증 — Pass/Revise 판정 |
| **Scribe** | 설계·구현·리뷰 과정·최종 명세 문서화 |

```
요구사항 → Architect → Developer → Reviewer →(Pass)→ Scribe
                                            →(Revise)→ Developer (최대 3 Cycles)
```

적합한 작업: 신규 기능 설계·구현·리뷰 통합

---

## 패턴별 비교

| 패턴 | 목적 | 핵심 루프 | 최대 반복 | 팀 구성 |
|---|---|---|---|---|
| 📐 **Planner-Executor** | 체계적 실행 | 계획→실행→검증 | 3회 Revise | Planner·Executor·Validator·Scribe |
| ⚔️ **Debate & Critic** | 최선의 결론 도출 | 제안→반론→평가 | 3 Rounds | Proposer·Opponent·Critic·Synthesizer·Scribe |
| ⚡ **Generator-Evaluator** | 반복 개선으로 품질 향상 | 생성→평가→개선 | 3 Cycles | Generator·Evaluator·Refiner·Scribe |
| 🏗️ **Code Generation** | 설계 기반 코드 생성 | 설계→구현→리뷰 | 3 Cycles | Architect·Developer·Reviewer·Scribe |
