# Retention OS — Sky 작업 시트
## 역할: Frontend UI (Person 3, 디자인 담당)

> 오전에는 목(mock) 데이터로 독립 작업. 오후에 실제 API 연결. 네가 가장 자유로움 — 아무도 안 기다려도 됨.

---

## 우리가 만드는 것

AI **직원**이 SaaS 고객 이탈을 자동으로 감지하고 행동하는 대시보드.
화면은 딱 2개:
1. **Dashboard** (`/`) — 계정 목록 + AI 행동 로그 + "Run Daily Review" 버튼
2. **Account Detail** (`/account/:id`) — 위험 분석 + 추천 액션 + 이메일/메모 + 승인 버튼

---

## 네가 만들 파일

| 파일 | 역할 |
|---|---|
| `frontend/src/App.jsx` | React Router (2개 라우트) |
| `frontend/src/pages/Dashboard.jsx` | 메인 대시보드 |
| `frontend/src/pages/AccountDetail.jsx` | 계정 상세 페이지 |
| `frontend/src/components/StatsCard.jsx` | 통계 카드 컴포넌트 |
| `frontend/src/components/RiskBadge.jsx` | 위험도 배지 (빨강/노랑/초록) |
| `frontend/src/components/ActivityFeed.jsx` | AI 행동 로그 (실시간) |

---

## Step-by-Step

### 9:30-10:00 — 세팅

```bash
npm create vite@latest frontend -- --template react
cd frontend
npm install -D tailwindcss @tailwindcss/vite react-router-dom
```

**vite.config.js** — proxy 설정 (CORS 문제 방지):
```js
export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    proxy: {
      '/api': 'http://localhost:8000'
    }
  }
})
```

**App.jsx** — 라우터:
```jsx
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import Dashboard from './pages/Dashboard'
import AccountDetail from './pages/AccountDetail'

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/account/:id" element={<AccountDetail />} />
      </Routes>
    </BrowserRouter>
  )
}
```

---

### 10:00-11:30 — Dashboard 페이지

**목 데이터 (API 연결 전까지 이걸로 작업):**
```js
const mockAccounts = [
  {
    account_id: "A-NIMBUS",
    account_name: "Nimbus Analytics",
    industry: "DevTools",
    plan_tier: "Enterprise",
    health_score: 35,
    risk_level: "high",
    mrr_amount: 3000,
    next_best_action: "training_call",
    status: "auto_executed",
    actions_taken: ["slack_alert"]
  },
  {
    account_id: "A-VERTEX",
    account_name: "Vertex Systems",
    industry: "FinTech",
    plan_tier: "Pro",
    health_score: 65,
    risk_level: "medium",
    mrr_amount: 1500,
    next_best_action: "finance_reminder",
    status: "auto_executed",
    actions_taken: ["slack_alert"]
  },
  {
    account_id: "A-ORION",
    account_name: "Orion Global",
    industry: "Cybersecurity",
    plan_tier: "Enterprise",
    health_score: 20,
    risk_level: "high",
    mrr_amount: 8500,
    next_best_action: "senior_outreach",
    status: "needs_approval",
    actions_taken: ["slack_urgent_alert"]
  }
]

const mockActivityFeed = [
  { type: "progress", message: "Scanned 500 accounts", time: "10:01 AM" },
  { type: "action", message: "Sent Slack alert for Nimbus Analytics", time: "10:03 AM" },
  { type: "action", message: "Sent Slack alert for Vertex Systems", time: "10:04 AM" },
  { type: "action", message: "Orion Global needs approval — $102K ARR at risk", time: "10:05 AM" },
  { type: "complete", message: "Review complete. 2 auto-executed, 1 needs approval.", time: "10:05 AM" }
]
```

**Dashboard 레이아웃:**
```
┌─────────────────────────────────────────────────────────────┐
│  Retention OS — AI Account Manager                          │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐      │
│  │ Total    │ │ At-Risk  │ │ ARR at   │ │ Actions  │      │
│  │ Accounts │ │ Accounts │ │ Risk     │ │ Today    │      │
│  │   500    │ │    12    │ │ $156K    │ │    5     │      │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘      │
│                                                             │
│  [🚀 Run Daily Review]    Last auto-run: 8:00 AM today     │
│                                                             │
│  ┌─ Activity Feed ────────────────────────────────────────┐ │
│  │ ✅ 10:03 Sent Slack alert for Nimbus Analytics         │ │
│  │ ✅ 10:03 Email draft ready for Nimbus Analytics         │ │
│  │ ✅ 10:04 Sent Slack alert for Vertex Systems           │ │
│  │ ⚠️ 10:05 Orion Global needs approval — $102K ARR      │ │
│  │ ✅ 10:05 Review complete. 2 auto, 1 needs approval.   │ │
│  └────────────────────────────────────────────────────────┘ │
│                                                             │
│  ┌─ Account Table ────────────────────────────────────────┐ │
│  │ Name              │ Industry │ Plan  │ Risk │ Status   │ │
│  │ Orion Global      │ Cyber    │ Ent   │ 🔴20 │ ⚠️ 승인  │ │
│  │ Nimbus Analytics  │ DevTools │ Ent   │ 🔴35 │ ✅ 자동  │ │
│  │ Vertex Systems    │ FinTech  │ Pro   │ 🟡65 │ ✅ 자동  │ │
│  └────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

**디자인 가이드:**
- 배경: `bg-gray-50` 또는 `bg-slate-50`
- 카드: `bg-white rounded-lg shadow p-6`
- 위험 색상:
  - 빨강 (score < 40): `text-red-600 bg-red-50`
  - 노랑 (40-70): `text-yellow-600 bg-yellow-50`
  - 초록 (> 70): `text-green-600 bg-green-50`
- 상태 배지:
  - `auto_executed`: `bg-green-100 text-green-800` → "Auto-executed"
  - `needs_approval`: `bg-orange-100 text-orange-800` → "Needs Approval"
- 테이블 행 클릭 → `/account/:id`로 이동

**StatsCard 컴포넌트:**
```jsx
function StatsCard({ label, value, color }) {
  return (
    <div className="bg-white rounded-lg shadow p-6">
      <p className="text-sm text-gray-500">{label}</p>
      <p className={`text-3xl font-bold ${color || 'text-gray-900'}`}>{value}</p>
    </div>
  )
}
```

**RiskBadge 컴포넌트:**
```jsx
function RiskBadge({ score }) {
  const color = score < 40 ? 'bg-red-100 text-red-800'
    : score < 70 ? 'bg-yellow-100 text-yellow-800'
    : 'bg-green-100 text-green-800'
  return (
    <span className={`px-2 py-1 rounded-full text-sm font-medium ${color}`}>
      {score}
    </span>
  )
}
```

---

### 11:30-12:00 — Account Detail 페이지

**목 데이터:**
```js
const mockDetail = {
  account_id: "A-NIMBUS",
  account_name: "Nimbus Analytics",
  industry: "DevTools",
  plan_tier: "Enterprise",
  seats: 45,
  health_score: 35,
  risk_level: "high",
  mrr_amount: 3000,
  arr_amount: 36000,
  churn_risk_score: 85,
  risk_reasons: [
    "Usage dropped 60% in 3 weeks",
    "4 unresolved support tickets",
    "2 tickets escalated",
    "Satisfaction score: 2/5"
  ],
  next_best_action: "training_call",
  action_reasoning: "Customer shows strong product friction. Training call addresses root cause — team may not know how to use key features. Support escalation handles immediate ticket backlog.",
  why_not_others: "finance_reminder: no billing issues detected. senior_outreach: premature — ARR $36K is under $50K threshold for executive involvement.",
  generated_email: "Subject: We want to help — dedicated training session for your team\n\nDear Nimbus Analytics team,\n\nWe've noticed your team may be running into some friction with our platform. We'd love to set up a complimentary training session tailored to your team's workflow...",
  internal_memo: "PRIORITY: HIGH\nAccount: Nimbus Analytics (Enterprise, $3K MRR, 45 seats)\nRisk: Product friction — usage down 60% in 3 weeks, 4 unresolved tickets (2 escalated)\nAction: Schedule training call within 48 hours. Escalate all open tickets to Tier 2 support.\nDeadline: Action needed within 48 hours\nOwner: [Assign CSM]",
  status: "auto_executed",
  autonomy_level: "auto",
  autonomy_reason: "ARR $36K under $50K threshold — auto-execution policy applied",
  actions_taken: [
    { type: "slack_alert", channel: "#retention-alerts", timestamp: "10:03 AM", status: "sent" },
    { type: "email_draft", status: "ready" }
  ],
  urgency_deadline: "Action needed within 48 hours"
}
```

**Account Detail 레이아웃:**
```
┌─────────────────────────────────────────────────────────────┐
│  ← Back to Dashboard                                        │
│                                                             │
│  Nimbus Analytics                    ┌────────────────────┐ │
│  DevTools · Enterprise · 45 seats    │   Health Score     │ │
│  MRR: $3,000 · ARR: $36,000        │      🔴 35         │ │
│                                      │  Churn Risk: 85%   │ │
│                                      └────────────────────┘ │
│                                                             │
│  ┌─ Risk Signals ─────────────────────────────────────────┐ │
│  │ 📉 Usage dropped 60% in 3 weeks                       │ │
│  │ 🎫 4 unresolved support tickets                       │ │
│  │ 🚨 2 tickets escalated                                │ │
│  │ 😞 Satisfaction score: 2/5                            │ │
│  └────────────────────────────────────────────────────────┘ │
│                                                             │
│  ┌─ Recommended Action ──────────────────────────────────┐ │
│  │ 📞 Training Call                  🤖 Auto-executed     │ │
│  │                                                        │ │
│  │ Why: Customer shows product friction. Training call    │ │
│  │ addresses root cause...                                │ │
│  │                                                        │ │
│  │ Why not others: finance_reminder — no billing issues.  │ │
│  │ senior_outreach — ARR under $50K threshold.            │ │
│  │                                                        │ │
│  │ ⏰ Action needed within 48 hours                      │ │
│  └────────────────────────────────────────────────────────┘ │
│                                                             │
│  ┌─ AI Actions Taken ────────────────────────────────────┐ │
│  │ ✅ 10:03 AM — Slack #retention-alerts에 알림 전송     │ │
│  │ 📧 10:03 AM — 이메일 초안 준비됨                       │ │
│  │ 📧 이메일 초안 준비됨                                  │ │
│  └────────────────────────────────────────────────────────┘ │
│                                                             │
│  ┌─ Tabs ────────────────────────────────────────────────┐ │
│  │ [Customer Email] [Internal Memo] [Slack Msg]          │ │
│  │                                                        │ │
│  │ Subject: We want to help — dedicated training session  │ │
│  │                                                        │ │
│  │ Dear Nimbus Analytics team,                            │ │
│  │                                                        │ │
│  │ We've noticed your team may be running into some       │ │
│  │ friction with our platform...                          │ │
│  └────────────────────────────────────────────────────────┘ │
│                                                             │
│  (Orion Global만: [✅ Approve Senior Outreach] 버튼)       │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

**Orion Global (needs_approval) 전용:**
- "Approve" 버튼 크게 표시
- `status === "needs_approval"`일 때만 보임
- 클릭하면 `POST /api/accounts/A-ORION/approve` 호출
- 성공하면 상태가 "approved"로 바뀌고 버튼 비활성화

---

### 12:00-12:30 — 점심

---

### 12:30-13:30 — 나머지 UI + API 연결

**탭 구현:**
- 3개 탭: Customer Email | Internal Memo | Slack Message
- 간단한 state로 전환:
```jsx
const [activeTab, setActiveTab] = useState('email')

// 탭 내용
{activeTab === 'email' && <pre className="whitespace-pre-wrap">{detail.generated_email}</pre>}
{activeTab === 'memo' && <pre className="whitespace-pre-wrap">{detail.internal_memo}</pre>}
{activeTab === 'slack' && <pre className="whitespace-pre-wrap">{detail.slack_message}</pre>}
```

**자율성 레벨 배지:**
```jsx
{detail.autonomy_level === "auto" ? (
  <span className="bg-green-100 text-green-800 px-3 py-1 rounded-full">
    🤖 Auto-executed
  </span>
) : (
  <span className="bg-orange-100 text-orange-800 px-3 py-1 rounded-full">
    ⚠️ Needs Approval
  </span>
)}
```

**목 데이터 → 실제 API 교체:**
```jsx
// Dashboard.jsx
useEffect(() => {
  fetch('/api/accounts')  // proxy가 localhost:8000으로 보냄
    .then(res => res.json())
    .then(data => setAccounts(data))
}, [])

// AccountDetail.jsx
const { id } = useParams()
useEffect(() => {
  fetch(`/api/accounts/${id}`)
    .then(res => res.json())
    .then(data => setDetail(data))
}, [id])

// Approve button
const handleApprove = async () => {
  const res = await fetch(`/api/accounts/${id}/approve`, { method: 'POST' })
  if (res.ok) {
    setDetail(prev => ({ ...prev, status: 'approved' }))
  }
}
```

---

### 13:30-제출 — SSE + 마무리

**Jisu(Person 2)가 SSE 연결 코드를 가져다줄 것.** 그게 Dashboard의 Activity Feed와 연결됨.

**마무리 체크리스트:**
- [ ] Dashboard 통계 카드가 실제 숫자 표시
- [ ] 계정 테이블이 실제 데이터 표시
- [ ] 행 클릭 → Account Detail 이동
- [ ] Account Detail에 분석 결과 표시
- [ ] 탭 전환 (이메일/메모/Slack) 동작
- [ ] Orion Global에만 Approve 버튼 표시
- [ ] Approve 클릭 → 상태 변경
- [ ] Activity Feed 표시 (SSE 연결되면)
- [ ] 색상 + 간격 깔끔

---

## 핵심 포인트

- **오전에는 아무도 안 기다려도 됨.** 목 데이터로 전부 만들기.
- **오후에 API 연결은 fetch() 한 줄 바꾸면 됨.** 목 데이터 구조를 API 응답과 맞춰놨으니까.
- **Approve 버튼이 데모의 하이라이트.** Orion Global($102K ARR)을 승인하면 실제 Slack에 알림이 가고 Linear에 티켓이 생김. 이걸 심사위원이 봄.

## 시간 부족할 때

1. ~~Slack Message 탭~~ → Email + Memo만 있어도 OK
2. ~~Activity Feed~~ → 있으면 좋지만, 테이블만 있어도 됨
3. **절대 자르면 안 되는 것:** 계정 테이블 + Account Detail + Approve 버튼
