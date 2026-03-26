# Retention OS - 빌드 플랜 (최종)

> **해커톤 규칙 확인 완료:** 모든 코드는 해커톤 당일에만 작성. 사전 코딩 금지.
> **클라우드 불필요:** AWS/GCP 안 씀. 전부 로컬에서 돌림.

---

## 우리가 만드는 것

**AI Account Manager — 분석만 하는 도구가 아니라, 직접 일하는 AI 직원.**

해커톤 테마가 **"Build Your AI Employee in a Day"** 야. 핵심은:
> "It should handle real tasks, make real decisions, and operate with minimal hand-holding."

그래서 우리 AI는 **추천만 하고 기다리는 게 아니라, 직접 행동한다:**

```
이전 플랜 (도구):   스캔 → 분석 → 추천 → [멈춤] → 사람이 승인 → 상태만 변경
새 플랜 (직원):     스캔 → 분석 → 판단 → 직접 행동 → 사람에게 보고
                                         ↓
                                   Slack 알림 전송
                                   이메일 초안 작성
                                   (고위험만 승인 요청)
                                   (Linear 티켓 = 시간 되면 추가)
```

**심사 기준 (이걸 기억하고 만들자):**
| 기준 | 비중 | 우리 전략 |
|---|---|---|
| **Value (가치)** | **35%** | 고객 이탈은 실제 돈 문제 + AI가 실제로 일을 하니까 인건비 절약 |
| **Autonomy (자율성)** | **30%** | AI가 Slack 알림 보내고 이메일 작성. 고위험만 승인 요청. (Linear = 스트레치) |
| **Technical Complexity** | **20%** | Claude API tool_use + SSE + Slack API + SQLite + 룰엔진 |
| **Demo + Presentation** | **15%** | 실시간으로 Slack 알림 오는 거 보여주기 = 임팩트 |

### 핵심 차별점: 자율성 레벨 시스템
| 레벨 | 조건 | AI가 하는 것 | 사람 필요? |
|---|---|---|---|
| **자동 실행** | health score 40-70 (중간 위험) | Slack #retention-alerts에 알림 + 이메일 초안 작성 (+ Linear 티켓 = 스트레치) | ❌ 사후 확인만 |
| **승인 필요** | health score < 40 (고위험) 또는 ARR > $50K | Slack #retention-urgent에 긴급 알림 + 승인 요청 | ✅ 승인 후 실행 |

이게 진짜 "직원"이야. 루틴한 건 알아서 하고, 큰 건만 물어봄.

---

## 기술 스택

| 용도 | 도구 | 설명 |
|---|---|---|
| 백엔드 서버 | FastAPI + uvicorn | `pip install fastapi uvicorn` |
| 데이터베이스 | SQLite | Python 내장 |
| AI 두뇌 | Claude API (claude-sonnet-4-5) | `pip install anthropic` — tool_use로 구조화된 출력 |
| 실시간 스트리밍 | FastAPI 내장 SSE | `from fastapi.sse import EventSourceResponse` — 추가 패키지 불필요 |
| **행동: 팀 알림** | **Slack API** | Slack webhook으로 채널에 메시지 전송 |
| **행동: 작업 생성 (스트레치)** | **Linear API** | 시간 되면 추가. 핵심 아님 |
| 프론트엔드 | React + Vite | `npm create vite@latest` |
| 스타일 | Tailwind CSS | `npm install -D tailwindcss @tailwindcss/vite` |
| 라우팅 | react-router-dom | `npm install react-router-dom` |

**설치 명령어 (해커톤 시작하면 바로):**
```bash
# 백엔드
mkdir retention-os && cd retention-os
mkdir -p backend/data
pip install fastapi uvicorn anthropic aiofiles requests

# 프론트엔드
npm create vite@latest frontend -- --template react
cd frontend
npm install -D tailwindcss @tailwindcss/vite react-router-dom
```

### Slack 세팅 (Person 2가 담당, ~10분)

> ⚠️ **회사 Slack/Linear 절대 사용 금지!** 해커톤 규칙: "employer의 tools, systems 사용 불가". 새 무료 계정 만들어야 함.

1. slack.com → 새 워크스페이스 생성 (무료, 3분)
   - 이름: "RetentionOS Demo" 같은 거
2. api.slack.com → Create New App → From Scratch
3. Incoming Webhooks 켜기 → Add New Webhook
4. `#retention-alerts` 채널 만들고 webhook 연결
5. `#retention-urgent` 채널 만들고 webhook 연결
6. Webhook URL 2개를 Person 1에게 전달

**코드는 2줄이면 됨:**
```python
import requests
requests.post(webhook_url, json={"text": "🚨 Nimbus Analytics at risk"})
# 끝. 이게 전부.
```

### Linear 세팅 (스트레치 — 핵심 다 되면 추가)
> Linear는 시간 남으면 추가. Slack만으로도 "행동하는 AI" 충분히 증명 가능.

만약 추가한다면:
1. linear.app → 무료 계정 생성 (2분)
2. 워크스페이스 + 팀 → API 키 → "Retention OS" 프로젝트
3. API 키 + Team ID를 Person 1에게 전달

**Slack 세팅이 핵심.** 이 10분이 "AI 직원"과 "AI 도구"의 차이를 만듦.

---

## 빌드 시작 후 바로 고쳐야 할 데이터 문제 5가지

RavenStack CSV 데이터가 3개 데모 시나리오와 완벽히 맞지 않음. **안 고치면 데모 깨짐.**

| # | 문제 | 왜 깨지나 | 해결 |
|---|---|---|---|
| 1 | 계정 이름이 "Company_0" 같은 이름 | 데모에서 "Nimbus Analytics" 등 필요 | CSV에 3개 데모 계정 직접 추가 |
| 2 | 인보이스/연체 데이터 없음 | 시나리오 B가 "14일 연체" 필요 | subscriptions에 `days_overdue` 컬럼 추가 |
| 3 | 티켓에 텍스트 필드 없음 | 시나리오 C가 "competitor mention" 필요 | support_tickets에 `notes` 컬럼 추가 |
| 4 | feature_usage → subscription_id (account_id 아님) | 계정별 사용량 구하려면 JOIN 필요 | 백엔드에서 JOIN: feature_usage → subscriptions → accounts |
| 5 | "최근 30일" 기준인데 데이터가 2023-2024 | 오늘 기준 계산하면 아무것도 안 잡힘 | `REFERENCE_DATE` 상수 설정 |

### 준비할 데모 계정 데이터

**시나리오 A — Product Friction (제품 마찰):**
- 계정: "Nimbus Analytics" | DevTools | Enterprise
- 구독: MRR ~$3,000, 활성, 다운그레이드 없음
- 사용량: 6주 전 높은 사용 → 최근 3주 60% 하락
- 티켓: 4개, priority high/urgent, satisfaction_score 2, escalation_flag=True
- AI 행동: `training_call` → 자동 실행 (Slack 알림 + Linear 티켓)

**시나리오 B — Billing Risk (결제 위험):**
- 계정: "Vertex Systems" | FinTech | Pro
- 구독: MRR ~$1,500, 활성, 사용량 건강, `days_overdue=14`
- 티켓: 0-1개, 에스컬레이션 없음
- AI 행동: `finance_reminder` → 자동 실행 (Slack 알림 + Linear 티켓)

**시나리오 C — Enterprise Churn Risk (엔터프라이즈 이탈):**
- 계정: "Orion Global" | Enterprise
- 구독: MRR $8,500, ARR $102,000, 활성
- 티켓: 2개+, satisfaction_score 1-2, notes에 "evaluating competitor solutions"
- AI 행동: `senior_outreach` → **승인 필요** (ARR > $50K이라서) → 승인하면 Slack #retention-urgent에 긴급 알림

---

## 전체 시스템 구조도

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         사용자 (브라우저)                                 │
│                                                                         │
│   "Run Daily Review" 클릭                    계정 클릭 / Approve 클릭    │
│         │                                          │                     │
└─────────┼──────────────────────────────────────────┼─────────────────────┘
          │                                          │
          ▼                                          ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  FRONTEND — React + Vite + Tailwind (localhost:5173)                    │
│                                                                         │
│  ┌─ Dashboard (/) ──────────────────┐  ┌─ Account Detail ────────────┐ │
│  │                                   │  │ (/account/:id)              │ │
│  │  [StatsCard x4]                   │  │                             │ │
│  │  Total | At-Risk | ARR | Actions  │  │  Health Score (빨/노/초)    │ │
│  │                                   │  │  Risk Signals 리스트        │ │
│  │  [Run Daily Review] 버튼          │  │  추천 액션 + 이유           │ │
│  │       │                           │  │  왜 다른 건 아닌지          │ │
│  │       ▼                           │  │  ⏰ 긴급 기한               │ │
│  │  EventSource (SSE, GET)           │  │                             │ │
│  │       │                           │  │  [행동 로그 타임라인]       │ │
│  │       ▼                           │  │  ✅ Slack 전송 10:03        │ │
│  │  [ActivityFeed] 실시간 로그       │  │  📧 이메일 초안 준비        │ │
│  │  ✅ Analyzing Nimbus...           │  │                             │ │
│  │  ✅ Sent Slack alert...           │  │  [탭: Email|Memo|Slack]     │ │
│  │  ⚠️ Orion needs approval...      │  │                             │ │
│  │                                   │  │  [Approve] ← 고위험만      │ │
│  │  [Account Table]                  │  │       │                     │ │
│  │  이름 | 위험 | 액션 | 상태        │  │       │ POST /approve       │ │
│  │  클릭 → Account Detail ──────────┼──┼───→   ▼                     │ │
│  └───────────────────────────────────┘  └─────────────────────────────┘ │
└─────────┬───────────────────────────────────────────┬───────────────────┘
          │ SSE (GET)                                  │ fetch (GET/POST)
          │                                            │
┌─────────▼────────────────────────────────────────────▼───────────────────┐
│  BACKEND — FastAPI + uvicorn (localhost:8000)                             │
│                                                                           │
│  ┌─ routes.py ──────────────────────────────────────────────────────────┐│
│  │                                                                       ││
│  │  GET /api/review/run ──→ SSE EventSourceResponse                      ││
│  │       │                                                               ││
│  │       ▼                                                               ││
│  │  ┌─────────────────────────────────────────────────────────────┐     ││
│  │  │  에이전트 플로우 (이게 "직원"의 일하는 방식)                   │     ││
│  │  │                                                              │     ││
│  │  │  1. 전체 계정 스캔 (500개)                                    │     ││
│  │  │       │                                                      │     ││
│  │  │       ▼                                                      │     ││
│  │  │  2. health_score.py: 계정별 점수 계산                         │     ││
│  │  │     (100점에서 시작, 조건별 감점)                              │     ││
│  │  │       │                                                      │     ││
│  │  │       ▼                                                      │     ││
│  │  │  3. 위험 계정 선별 (점수 낮은 순)                              │     ││
│  │  │       │                                                      │     ││
│  │  │       ▼                                                      │     ││
│  │  │  4. 각 위험 계정마다:                                         │     ││
│  │  │     ┌──────────────────────────────────────────────────┐     │     ││
│  │  │     │  agent.py: Claude API (tool_use)                 │     │     ││
│  │  │     │  → churn_risk_score, risk_reasons,               │     │     ││
│  │  │     │    next_best_action, action_reasoning,            │     │     ││
│  │  │     │    why_not_others, generated_email,               │     │     ││
│  │  │     │    internal_memo, slack_message,                  │     │     ││
│  │  │     │    urgency_deadline                               │     │     ││
│  │  │     └──────────────┬───────────────────────────────────┘     │     ││
│  │  │                    │                                         │     ││
│  │  │                    ▼                                         │     ││
│  │  │  5. 자율성 판단 (health_score.py)                             │     ││
│  │  │     ┌──────────────────┬───────────────────────┐             │     ││
│  │  │     │ score>=40        │ score<40 AND arr>=$50K │             │     ││
│  │  │     │ OR arr<$50K      │                        │             │     ││
│  │  │     ▼                  ▼                        │             │     ││
│  │  │  자동 실행           승인 필요                   │             │     ││
│  │  │     │                  │                        │             │     ││
│  │  │     ▼                  ▼                        │             │     ││
│  │  │  actions.py:        actions.py:                 │             │     ││
│  │  │  Slack #alerts      Slack #urgent               │             │     ││
│  │  │  에 알림 전송       "승인 필요" 알림             │             │     ││
│  │  │     │                  │                        │             │     ││
│  │  │     ▼                  ▼                        │             │     ││
│  │  │  6. SQLite에 결과 + 행동 로그 저장               │             │     ││
│  │  │     │                                           │             │     ││
│  │  │     ▼                                           │             │     ││
│  │  │  7. SSE로 각 단계 실시간 스트리밍                │             │     ││
│  │  └─────────────────────────────────────────────────┘             │     ││
│  │                                                                       ││
│  │  GET /api/accounts ──→ 전체 계정 + health score + 행동 로그           ││
│  │  GET /api/accounts/:id ──→ 상세 + AI 분석 + actions_taken             ││
│  │  POST /api/accounts/:id/approve ──→ Slack #urgent 전송 + 상태 변경   ││
│  └───────────────────────────────────────────────────────────────────────┘│
│                                                                           │
│  ┌─ database.py ─────────┐  ┌─ 외부 서비스 ────────────────────────────┐│
│  │                        │  │                                           ││
│  │  SQLite (retention.db) │  │  Claude API (claude-sonnet-4-5-20250929) ││
│  │  ┌──────────────────┐ │  │  └→ tool_use로 구조화된 분석 반환         ││
│  │  │ accounts         │ │  │                                           ││
│  │  │ subscriptions    │ │  │  Slack Webhook                            ││
│  │  │ support_tickets  │ │  │  ├→ #retention-alerts (자동 알림)         ││
│  │  │ feature_usage    │ │  │  └→ #retention-urgent (승인 필요 알림)    ││
│  │  │ churn_events     │ │  │                                           ││
│  │  │ review_results   │ │  │  Linear API (스트레치)                    ││
│  │  │ action_log       │ │  │  └→ 팔로업 티켓 생성                      ││
│  │  └──────────────────┘ │  └───────────────────────────────────────────┘│
│  └────────────────────────┘                                               │
└───────────────────────────────────────────────────────────────────────────┘
```

### 파일 구조 + 담당자

```
retention-os/
├── backend/                          ← Person 1 (Eddy) 담당
│   ├── main.py                       ← FastAPI 앱 + CSV 로딩 + CORS
│   ├── database.py                   ← SQLite + CSV 로더 + 쿼리 헬퍼
│   ├── models.py                     ← Pydantic 응답 모델
│   ├── health_score.py               ← 점수 계산 + 자율성 레벨 판단
│   ├── agent.py                      ← Claude API tool_use 호출
│   ├── actions.py                    ← Slack webhook 전송 (+ Linear 스트레치)
│   ├── routes.py                     ← API 4개 + SSE 스트리밍
│   ├── requirements.txt
│   └── data/                         ← Person 2 (Jisu) 가 수정
│       ├── ravenstack_accounts.csv
│       ├── ravenstack_subscriptions.csv   ← +days_overdue 컬럼
│       ├── ravenstack_support_tickets.csv ← +notes 컬럼
│       ├── ravenstack_feature_usage.csv
│       └── ravenstack_churn_events.csv
├── frontend/                         ← Person 3 (Sky) 담당
│   ├── src/
│   │   ├── App.jsx                   ← React Router (2개 라우트)
│   │   ├── main.jsx
│   │   ├── pages/
│   │   │   ├── Dashboard.jsx         ← 메인 + Activity Feed + 테이블
│   │   │   └── AccountDetail.jsx     ← 상세 + 행동 로그 + 탭 + 승인
│   │   └── components/
│   │       ├── StatsCard.jsx
│   │       ├── RiskBadge.jsx
│   │       └── ActivityFeed.jsx
│   ├── package.json
│   └── vite.config.js                ← proxy: /api → localhost:8000
├── .env                              ← API 키들 (git에 안 올림)
├── .gitignore
└── README.md
```

### 데이터 흐름 요약

```
CSV 5개 → [시작 시] → SQLite 7개 테이블
                         │
                         ▼
             health_score.py가 계정별 점수 계산
                         │
                         ▼
              agent.py가 Claude API 호출
              (위험 계정만, tool_use)
                         │
                         ▼
              actions.py가 Slack webhook 전송
              (자동 실행 or 승인 대기)
                         │
                         ▼
              결과 → SQLite review_results + action_log
                         │
                         ▼
              routes.py가 SSE로 프론트에 실시간 전달
                         │
                         ▼
              React가 Dashboard + Account Detail에 표시
```

---

## 에이전트 플로우 (핵심 — 이게 "직원"의 일하는 방식)

```
GET /api/review/run 호출되면:

1. 전체 계정 스캔 (500개)
   → SSE: "Scanning 500 accounts..."

2. Health score 계산 → 위험 계정 선별
   → SSE: "Found 12 at-risk accounts, prioritizing top 3..."

3. 각 위험 계정마다:
   a. Claude API 호출 → 분석 + 액션 결정
      → SSE: "Analyzing Nimbus Analytics..."

   b. 자율성 레벨 판단:
      - health_score >= 40 OR arr < $50K → 자동 실행
      - health_score < 40 AND arr >= $50K → 승인 필요

   c. 자동 실행인 경우:
      → Slack #retention-alerts에 메시지 전송
      → SSE: "✅ Sent Slack alert for Nimbus Analytics"
      → (스트레치: Linear 티켓도 생성)
      → 상태: "auto_executed"

   d. 승인 필요인 경우:
      → Slack #retention-urgent에 "승인 필요" 메시지 전송
      → SSE: "⚠️ Orion Global needs approval — $102K ARR at risk"
      → 상태: "needs_approval"

4. 완료 보고
   → SSE: "Review complete. 2 actions auto-executed, 1 needs approval."
```

---

## API 스펙 (3명 모두 이거 기준으로 작업)

### GET /api/review/run
> ⚠️ **GET이어야 함 (POST 아님!)** — 브라우저 EventSource API가 GET만 지원.

SSE 스트림 (`Content-Type: text/event-stream`):
```
data: {"type": "progress", "message": "Scanning 500 accounts..."}
data: {"type": "progress", "message": "Found 12 at-risk accounts, prioritizing top 3"}
data: {"type": "analyzing", "account": "Nimbus Analytics", "index": 1, "total": 3}
data: {"type": "action", "account": "Nimbus Analytics", "action": "slack_sent", "message": "Sent alert to #retention-alerts"}
data: {"type": "analyzing", "account": "Vertex Systems", "index": 2, "total": 3}
data: {"type": "action", "account": "Vertex Systems", "action": "slack_sent", "message": "Sent reminder to #retention-alerts"}
data: {"type": "analyzing", "account": "Orion Global", "index": 3, "total": 3}
data: {"type": "action", "account": "Orion Global", "action": "needs_approval", "message": "$102K ARR at risk — senior outreach needs your approval"}
data: {"type": "complete", "auto_executed": 2, "needs_approval": 1}
```

### GET /api/accounts
```json
[
  {
    "account_id": "A-NIMBUS",
    "account_name": "Nimbus Analytics",
    "industry": "DevTools",
    "plan_tier": "Enterprise",
    "health_score": 35,
    "risk_level": "high",
    "mrr_amount": 3000,
    "next_best_action": "training_call",
    "status": "auto_executed",
    "actions_taken": ["slack_alert"]
  },
  {
    "account_id": "A-ORION",
    "account_name": "Orion Global",
    "plan_tier": "Enterprise",
    "health_score": 20,
    "risk_level": "high",
    "mrr_amount": 8500,
    "next_best_action": "senior_outreach",
    "status": "needs_approval",
    "actions_taken": ["slack_urgent_alert"]
  }
]
```

### GET /api/accounts/:id
```json
{
  "account_id": "A-NIMBUS",
  "account_name": "Nimbus Analytics",
  "industry": "DevTools",
  "plan_tier": "Enterprise",
  "seats": 45,
  "health_score": 35,
  "risk_level": "high",
  "mrr_amount": 3000,
  "arr_amount": 36000,
  "churn_risk_score": 85,
  "risk_reasons": [
    "Usage dropped 60% in 3 weeks",
    "4 unresolved support tickets",
    "2 tickets escalated",
    "Satisfaction score: 2/5"
  ],
  "next_best_action": "training_call",
  "action_reasoning": "Customer shows product friction. Training call addresses root cause.",
  "why_not_others": "finance_reminder not needed (no billing issues). senior_outreach premature (ARR under $50K threshold).",
  "generated_email": "Subject: We want to help...\n\nDear Nimbus Analytics team...",
  "internal_memo": "PRIORITY: HIGH\nAccount: Nimbus Analytics...",
  "status": "auto_executed",
  "actions_taken": [
    {"type": "slack_alert", "channel": "#retention-alerts", "timestamp": "10:03 AM", "status": "sent"},
    {"type": "email_draft", "status": "ready"}
  ],
  "autonomy_level": "auto",
  "autonomy_reason": "ARR under $50K threshold — auto-execution policy applied"
}
```

### POST /api/accounts/:id/approve
고위험 계정만 (status가 "needs_approval"일 때):
```json
// 요청: POST /api/accounts/A-ORION/approve
// 응답:
{
  "status": "approved",
  "actions_executed": [
    {"type": "slack_urgent", "channel": "#retention-urgent", "message": "APPROVED: Senior outreach for Orion Global"}
  ],
  "approved_at": "2026-03-26T14:30:00Z"
}
```

---

## Health Score 계산 로직

```python
REFERENCE_DATE = "2025-01-01"  # 데이터셋 최대 날짜에 맞추기

def calculate_health_score(account_id) -> int:
    score = 100

    # 1. 사용량 하락 (최근 30일 vs 이전 30일): -30
    #    JOIN: feature_usage → subscriptions → accounts
    if usage_dropped > 30%:
        score -= 30

    # 2. 서포트 티켓 증가: -20
    if ticket_count_increased:
        score -= 20

    # 3. 에스컬레이션 플래그: -15
    if any_ticket_escalated:
        score -= 15

    # 4. 다운그레이드 플래그: -20
    if subscription_downgraded:
        score -= 20

    # 5. 만족도 3 미만: -15
    if any_satisfaction < 3:
        score -= 15

    return max(0, score)

def get_autonomy_level(health_score, arr_amount) -> str:
    """고위험 + 고가치 = 승인 필요, 나머지 = 자동 실행"""
    if health_score < 40 and arr_amount >= 50000:
        return "needs_approval"
    return "auto"
```

---

## Claude API 연동

```python
import anthropic
client = anthropic.Anthropic()

tools = [{
    "name": "submit_analysis",
    "description": "Submit churn risk analysis and recommended action",
    "input_schema": {
        "type": "object",
        "properties": {
            "churn_risk_score": {"type": "integer", "minimum": 0, "maximum": 100},
            "risk_reasons": {"type": "array", "items": {"type": "string"}},
            "next_best_action": {
                "type": "string",
                "enum": ["training_call", "support_escalation",
                         "finance_reminder", "senior_outreach"]
            },
            "action_reasoning": {"type": "string"},
            "why_not_others": {"type": "string"},
            "generated_email": {"type": "string"},
            "internal_memo": {"type": "string"},
            "slack_message": {"type": "string",
                "description": "Ready-to-send Slack message for the CS team"},
            "urgency_deadline": {"type": "string",
                "description": "e.g. 'Action needed within 48 hours'"}
        },
        "required": ["churn_risk_score", "risk_reasons", "next_best_action",
                     "action_reasoning", "why_not_others",
                     "generated_email", "internal_memo",
                     "slack_message", "urgency_deadline"]
    }
}]

response = client.messages.create(
    model="claude-sonnet-4-5-20250929",
    max_tokens=1500,
    system="""You are an AI Account Manager employee (not an assistant — you ACT, not just recommend).
Analyze customer signals and decide what to do. Use the submit_analysis tool.
Be specific and business-focused.
- Explain why you chose this action AND why you rejected alternatives.
- Write a ready-to-send Slack message for the CS team.
- Set a clear urgency deadline.""",
    tools=tools,
    messages=[{"role": "user", "content": f"Analyze:\n{signals_json}"}]
)
```

## Slack 연동 (webhook 방식 — 간단)

```python
import requests, os

SLACK_ALERTS_WEBHOOK = os.environ.get("SLACK_ALERTS_WEBHOOK")
SLACK_URGENT_WEBHOOK = os.environ.get("SLACK_URGENT_WEBHOOK")

def send_slack_alert(channel_type: str, message: str) -> bool:
    """channel_type: 'alerts' or 'urgent'"""
    webhook = SLACK_ALERTS_WEBHOOK if channel_type == "alerts" else SLACK_URGENT_WEBHOOK
    if not webhook:
        print(f"[MOCK] Slack {channel_type}: {message}")
        return False
    resp = requests.post(webhook, json={"text": message})
    return resp.status_code == 200
```

## Linear 연동 (스트레치 — 시간 되면 추가)

```python
# 핵심 기능 다 되면 추가할 것. 없어도 데모 가능.
def create_linear_ticket(title: str, description: str, priority: int = 2):
    api_key = os.environ.get("LINEAR_API_KEY")
    team_id = os.environ.get("LINEAR_TEAM_ID")
    if not api_key:
        print(f"[MOCK] Linear ticket: {title}")
        return {"mock": True}
    resp = requests.post(
        "https://api.linear.app/graphql",
        headers={"Authorization": api_key, "Content-Type": "application/json"},
        json={"query": """
            mutation CreateIssue($input: IssueCreateInput!) {
                issueCreate(input: $input) { success issue { id identifier url } }
            }
        """, "variables": {"input": {
            "teamId": team_id, "title": title,
            "description": description, "priority": priority
        }}}
    )
    return resp.json()
```

---

## 역할 요약

> 각 사람의 구체적 작업은 개별 파일에 있음: `retention-os-eddy.md`, `retention-os-jisu.md`, `retention-os-sky.md`

| 역할 | 이름 | 담당 | 핵심 산출물 |
|---|---|---|---|
| **Person 1** | Eddy | Backend + AI Agent | `main.py`, `database.py`, `health_score.py`, `agent.py`, `actions.py`, `routes.py` |
| **Person 2** | Jisu | Data + Slack 세팅 + Glue | Slack 워크스페이스, CSV 수정, SQL 쿼리, SSE 연결, 통합 디버깅 |
| **Person 3** | Sky | Frontend UI | `Dashboard.jsx`, `AccountDetail.jsx`, `StatsCard`, `RiskBadge`, `ActivityFeed` |

---

## 통합 타임라인 (3명 동시에 보는 표)

> **제출 마감은 당일 현장에서 발표됨.** 심사 시간 필요하니까 마감은 3:00-4:30 PM 예상.
> **안전하게 3:00 PM 마감으로 잡자** = 코딩 시간 약 5시간.

| 시간 | Eddy (Backend) | Jisu (Glue) | Sky (Frontend) | 🔗 의존성 이벤트 |
|---|---|---|---|---|
| **9:30** | git init, pip install, 폴더 구조 | Slack 워크스페이스 생성 (무료) | npm create vite, tailwind 설치 | |
| **9:45** | `database.py` + `main.py` 시작 | Slack App + Webhook 2개 생성 | `App.jsx` 라우터 세팅 | |
| **10:00** | CSV→SQLite 로더 완성 | **🔴 Eddy에게 Webhook URL 전달** → CSV 수정 시작 | Dashboard 페이지 시작 (목 데이터) | ✅ Eddy가 Slack 환경변수 설정 가능 |
| **10:30** | `health_score.py` 시작 | CSV 수정 중 (accounts, subscriptions, tickets, usage) | StatsCard + RiskBadge 컴포넌트 | |
| **10:45** | health_score.py (Person 2 쿼리 활용) | **🔴 CSV 수정 완료 → git push** → SQL 쿼리 작성 시작 | ActivityFeed 컴포넌트 | ✅ Eddy가 실제 데이터로 테스트 가능 |
| **11:15** | `routes.py` GET 엔드포인트 시작 | SQL 쿼리 완성 → **🔴 Eddy에게 전달** | 계정 테이블 (클릭 → 상세 이동) | ✅ Eddy가 쿼리를 database.py에 통합 |
| **11:30** | GET /api/accounts 테스트 | Eddy와 함께 GET API 테스트 | Account Detail 페이지 시작 (목 데이터) | |
| **12:00** | **🔴 git push** (GET API 완성) | | | ✅ Sky가 목 데이터 → 실제 API 교체 가능 |
| **12:00** | 🍽️ 점심 | 🍽️ 점심 | 🍽️ 점심 | |
| **12:30** | `agent.py` (Claude API tool_use) | SSE EventSource 코드 작성 | 탭 구현 (Email/Memo/Slack) | |
| **13:00** | agent.py 1개 계정 수동 테스트 | Sky의 Dashboard에 SSE 로직 삽입 | Approve 버튼 + 자율성 배지 | |
| **13:15** | `actions.py` (Slack webhook) | SSE + ActivityFeed 연결 테스트 | 목 데이터 → fetch() API 교체 | |
| **13:45** | `GET /api/review/run` SSE 엔드포인트 | **🔗 Eddy의 SSE + Sky의 UI 연결** | API 연결 완료 → UI 다듬기 | ✅ 전체 플로우 연결 시작 |
| **14:00** | `POST /approve` 엔드포인트 | **통합 테스트 시작 (제일 중요!)** | 색상, 간격, 텍스트 정리 | |
| **14:15** | 3개 시나리오 테스트 | Run → SSE → Slack → UI 전체 확인 | 데모용 최종 폴리시 | ✅ Slack에 실제 메시지 확인 |
| **14:30** | 버그 수정 | Approve → Slack #urgent 확인 | 버그 수정 | |
| **14:45** | 데모 리허설 | 데모 리허설 | 데모 리허설 | |
| **~15:00** | 🚨 **제출** | 🚨 **제출** | 🚨 **제출** | |

### 의존성 체인 (시간순)

```
10:00  Jisu → Eddy: Slack Webhook URL 전달
         ↓
10:45  Jisu → Eddy: CSV 수정 완료 (git push) + SQL 쿼리 전달
         ↓
12:00  Eddy → Sky:  GET API 완성 (git push) → Sky가 fetch()로 교체
         ↓
13:45  Eddy → Jisu: SSE 엔드포인트 완성 → Jisu가 프론트 연결
         ↓
14:00  전원: 통합 테스트 시작

Sky는 의존성 없음 — 오전 내내 목 데이터로 독립 작업 가능
Eddy가 크리티컬 패스 — 12:00까지 GET API 안 되면 전원 막힘
Jisu는 오후가 핵심 — 3명 코드를 하나로 연결하는 사람
```

### 시간 부족할 때 자를 것 (우선순위 낮은 것부터)
1. ~~Linear 연동~~ → Slack만으로도 "행동하는 AI" 증명 가능
2. ~~Activity Feed~~ → 있으면 좋지만, 계정 테이블만 있어도 됨
3. ~~SSE~~ → 폴링으로 대체
4. **절대 자르면 안 되는 것:** Claude AI 분석 + Slack 알림 + 자율성 레벨 + 3개 시나리오

---

## 데모 전략 (이전보다 훨씬 강력)

**스토리라인:**
1. "매일 아침 8시, 이 AI 직원이 출근합니다" → Run Daily Review 클릭
2. 실시간으로 AI가 일하는 게 보임:
   - "Scanning 500 accounts..."
   - "Analyzing Nimbus Analytics..."
   - **"✅ Sent Slack alert to #retention-alerts"** ← 실제 Slack에 알림 감
   - **"✅ Created Linear ticket: RET-42"** ← 실제 Linear에 티켓 생김
3. **Slack 화면 보여주기** — "보세요, 진짜로 알림이 왔습니다"
4. Orion Global 클릭 → "이건 $102K ARR이라서 AI가 사람한테 물어봅니다"
5. Approve 클릭 → Slack #retention-urgent에 즉시 알림 → Linear 긴급 티켓 생성
6. **"이 AI 직원은 오늘 3개 계정을 분석하고, 2개는 알아서 처리하고, 1개만 물어봤습니다. 사람이 한 건 승인 한 번."**

**이전 데모 vs 새 데모:**
| | 이전 (도구) | 새 (직원) |
|---|---|---|
| 분석 | ✅ | ✅ |
| 추천 | ✅ | ✅ |
| **실제 행동** | ❌ 상태만 변경 | ✅ Slack 알림 + Linear 티켓 |
| **자율적 판단** | ❌ 전부 승인 필요 | ✅ 루틴은 알아서, 큰 건만 물어봄 |
| **증거** | 화면에 글자 | Slack에 진짜 메시지, Linear에 진짜 티켓 |

---

## 리스크 대비

| 리스크 | 대비 |
|---|---|
| Slack 세팅 실패 | 폴백: 콘솔 로그로 "보내진 것처럼" 보여주기 (최후의 수단) |
| Linear API 안 됨 | Linear는 첫 번째 자를 수 있는 기능. Slack만 되면 OK |
| SSE 안 됨 | 폴링으로 대체 |
| Slack webhook URL 노출 | .env 파일 사용, git에 안 올림 |
| 시간 부족 | Linear 자르기 → SSE 자르기 → Activity Feed 자르기 (순서대로) |
| ⚠️ 회사 Slack/Linear 사용 | **실격 사유!** 반드시 새 무료 계정 만들 것 |

---

## 해커톤 시작 직후 체크리스트 (첫 30분)

- [ ] Git 레포 생성: `git init retention-os`
- [ ] 백엔드 패키지 설치
- [ ] 프론트엔드 Vite 세팅
- [ ] CSV 파일 `backend/data/`에 복사
- [ ] **Slack 워크스페이스 + 앱 + 웹훅 생성** (Person 2, 필수)
- [ ] (스트레치) Linear 계정 + API 키 + 프로젝트 (Person 2)
- [ ] 환경변수 설정: `ANTHROPIC_API_KEY`, `SLACK_ALERTS_WEBHOOK`, `SLACK_URGENT_WEBHOOK`
- [ ] `.env` 파일 만들고 `.gitignore`에 추가
- [ ] 포트 확인: 백엔드 8000, 프론트엔드 5173
- [ ] 역할 최종 확인하고 각자 시작
