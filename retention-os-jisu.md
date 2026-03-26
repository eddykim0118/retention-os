# Retention OS — Jisu 작업 시트
## 역할: Data + Slack/Linear 세팅 + Glue (Person 2, 연결 담당)

> 오전에는 세팅 + 데이터. 오후에는 **3명의 코드를 하나로 연결하는 사람**. 오후가 네 핵심 시간.

---

## 우리가 만드는 것

AI **직원** (도구 아님):
- 500개 SaaS 계정 자동 스캔
- 이탈 위험 고객 감지 → Claude AI가 분석
- **진짜 행동**: Slack에 알림 전송, Linear에 티켓 생성
- 루틴한 건 알아서 처리, 고가치 계정($50K+ ARR)만 승인 요청

---

## 네가 만들 것 / 세팅할 것

| 작업 | 타입 | 시간대 |
|---|---|---|
| Slack 워크스페이스 + 앱 + 웹훅 | 세팅 (필수) | 오전 (9:30-10:00) |
| Linear 계정 + API 키 (스트레치) | 세팅 (시간 되면) | 핵심 다 된 후 |
| CSV 데이터 수정 (3개 데모 계정) | 데이터 | 오전 (10:00-10:45) |
| SQL aggregation 쿼리 | 코드 | 오전 (10:45-12:00) |
| SSE 프론트엔드 연결 | 코드 | 오후 (12:30-13:30) |
| 통합 디버깅 | 디버깅 | 오후 (13:30-제출) |

---

## Step-by-Step

### 9:30-10:00 — Slack 세팅 (필수!)

> ⚠️ **회사 Slack/Linear 절대 사용 금지!** 해커톤 규칙 위반 = 실격. 새 무료 계정 만들어야 함.

#### Slack (약 10분, 필수)
1. **slack.com** → "Create a new workspace" 클릭
   - 워크스페이스 이름: `RetentionOS Demo` (아무거나 OK)
   - 이메일: 개인 이메일 사용
2. 채널 2개 만들기:
   - `#retention-alerts` (일반 알림용)
   - `#retention-urgent` (긴급 = 승인 필요한 것)
3. **api.slack.com** → "Create New App" → "From Scratch"
   - App 이름: `Retention OS Bot`
   - 워크스페이스: 방금 만든 거 선택
4. 왼쪽 메뉴 → **Incoming Webhooks** → 켜기
5. "Add New Webhook to Workspace" 클릭
   - `#retention-alerts` 선택 → Webhook URL 복사 → 메모
   - 다시 "Add New Webhook" → `#retention-urgent` 선택 → URL 복사 → 메모
6. **Eddy에게 전달:**
   ```
   SLACK_ALERTS_WEBHOOK=https://hooks.slack.com/services/xxx/yyy/zzz
   SLACK_URGENT_WEBHOOK=https://hooks.slack.com/services/xxx/yyy/zzz
   ```

#### Linear (스트레치 — 핵심 다 되면 추가)
> Slack만으로도 "행동하는 AI" 충분히 증명됨. Linear는 시간 남으면 하기.
>
> 만약 한다면: linear.app 무료 가입 → API 키 발급 → Team ID → Eddy에게 전달

**Slack 테스트 (선택):** 터미널에서 이거 한 번 쳐보면 Slack에 메시지 옴:
```bash
curl -X POST -H 'Content-type: application/json' \
  --data '{"text":"테스트 메시지입니다!"}' \
  YOUR_WEBHOOK_URL
```

---

### 10:00-10:45 — CSV 데이터 수정

`backend/data/` 폴더의 CSV 파일들을 수정해서 3개 데모 계정을 추가해야 함.

#### 1. `ravenstack_accounts.csv` — 행 3개 추가

```csv
A-NIMBUS,Nimbus Analytics,DevTools,US,2024-01-15,organic,Enterprise,45,False,False
A-VERTEX,Vertex Systems,FinTech,US,2024-03-01,partner,Pro,12,False,False
A-ORION,Orion Global,Cybersecurity,US,2023-06-10,event,Enterprise,85,False,False
```

#### 2. `ravenstack_subscriptions.csv` — 행 3개 추가 + 컬럼 1개 추가

**먼저 `days_overdue` 컬럼을 기존 모든 행에 추가** (기본값 0):
- 헤더에 `,days_overdue` 추가
- 기존 모든 행 끝에 `,0` 추가

**새 행 추가:**
```csv
S-NIMBUS,A-NIMBUS,2024-01-15,,Enterprise,45,3000,36000,False,False,False,False,monthly,True,0
S-VERTEX,A-VERTEX,2024-03-01,,Pro,12,1500,18000,False,False,False,False,monthly,True,14
S-ORION,A-ORION,2023-06-10,,Enterprise,85,8500,102000,False,False,False,False,annual,True,0
```
- Vertex만 `days_overdue=14` (인보이스 연체 시나리오)

#### 3. `ravenstack_support_tickets.csv` — 행 6개 추가 + 컬럼 1개 추가

**먼저 `notes` 컬럼 추가** (기존 행은 빈 값):
- 헤더에 `,notes` 추가
- 기존 모든 행 끝에 `,` 추가

**Nimbus 티켓 4개 (product friction):**
```csv
T-NIM001,A-NIMBUS,2024-12-20,,0,high,120,2.0,True,Dashboard crashes when loading large datasets
T-NIM002,A-NIMBUS,2024-12-22,,0,urgent,180,2.0,True,Export feature not working for 3 weeks
T-NIM003,A-NIMBUS,2024-12-28,,0,high,90,1.0,False,API response times degraded significantly
T-NIM004,A-NIMBUS,2025-01-02,,0,medium,150,2.0,False,Team unable to complete onboarding workflow
```
- `closed_at` 비워둠 (미해결)
- `resolution_time_hours` = 0 (아직 해결 안 됨)
- `satisfaction_score` = 1-2 (불만족)
- `escalation_flag` = True (일부)

**Orion 티켓 2개 (competitor mention):**
```csv
T-ORI001,A-ORION,2024-12-15,2024-12-16 10:00:00,34.0,high,45,1.0,False,Performance issues compared to competitors. Team is evaluating competitor solutions.
T-ORI002,A-ORION,2024-12-28,,0,urgent,200,2.0,True,Critical workflow broken - considering alternative platforms
```

#### 4. `ravenstack_feature_usage.csv` — 여러 행 추가

Nimbus subscription_id = `S-NIMBUS`

**6주 전 (높은 사용량):**
```csv
U-NIM001,S-NIMBUS,2024-11-20,feature_1,45,18000,0,False
U-NIM002,S-NIMBUS,2024-11-25,feature_3,38,15200,0,False
U-NIM003,S-NIMBUS,2024-11-30,feature_5,42,16800,1,False
U-NIM004,S-NIMBUS,2024-12-05,feature_1,40,16000,0,False
```

**최근 3주 (60% 하락):**
```csv
U-NIM005,S-NIMBUS,2024-12-15,feature_1,15,6000,2,False
U-NIM006,S-NIMBUS,2024-12-20,feature_3,12,4800,3,False
U-NIM007,S-NIMBUS,2024-12-25,feature_5,18,7200,2,False
U-NIM008,S-NIMBUS,2025-01-01,feature_1,10,4000,4,False
```

**Vertex (건강한 사용량):**
```csv
U-VTX001,S-VERTEX,2024-11-20,feature_1,30,12000,0,False
U-VTX002,S-VERTEX,2024-12-01,feature_1,32,12800,0,False
U-VTX003,S-VERTEX,2024-12-15,feature_1,35,14000,0,False
U-VTX004,S-VERTEX,2025-01-01,feature_1,33,13200,0,False
```

**Orion (보통 사용량):**
```csv
U-ORI001,S-ORION,2024-11-20,feature_1,25,10000,1,False
U-ORI002,S-ORION,2024-12-01,feature_1,22,8800,1,False
U-ORI003,S-ORION,2024-12-15,feature_1,20,8000,2,False
U-ORI004,S-ORION,2025-01-01,feature_1,18,7200,2,False
```

#### 5. `ravenstack_churn_events.csv` — 수정 없음
데모 계정 3개는 아직 이탈 안 했으므로 추가할 것 없음.

**완료되면 🔴 git push** — Eddy가 바로 써야 함.

---

### 10:45-12:00 — SQL 쿼리 작성

Eddy의 `database.py`와 `health_score.py`에 들어갈 쿼리. 작성 후 Eddy에게 전달.

**1. 계정별 사용량 합계 (feature_usage → subscriptions → accounts JOIN):**
```sql
SELECT a.account_id, a.account_name,
       SUM(fu.usage_count) as total_usage
FROM accounts a
JOIN subscriptions s ON a.account_id = s.account_id
JOIN feature_usage fu ON s.subscription_id = fu.subscription_id
WHERE fu.usage_date >= ? AND fu.usage_date < ?
GROUP BY a.account_id
```

**2. 최근 30일 vs 이전 30일 비교:**
```sql
-- REFERENCE_DATE 기준
-- recent = REFERENCE_DATE - 30일 ~ REFERENCE_DATE
-- previous = REFERENCE_DATE - 60일 ~ REFERENCE_DATE - 30일
```

**3. 계정별 티켓 수 + 에스컬레이션:**
```sql
SELECT account_id,
       COUNT(*) as ticket_count,
       SUM(CASE WHEN escalation_flag = 'True' THEN 1 ELSE 0 END) as escalations,
       MIN(satisfaction_score) as min_satisfaction
FROM support_tickets
WHERE submitted_at >= ?
GROUP BY account_id
```

**4. 다운그레이드 여부:**
```sql
SELECT account_id, downgrade_flag, days_overdue
FROM subscriptions
WHERE account_id = ?
  AND end_date IS NULL  -- 활성 구독만
```

Eddy와 같이 테스트해서 GET /api/accounts가 제대로 된 데이터 반환하는지 확인.

---

### 12:00-12:30 — 점심

---

### 12:30-13:30 — SSE 프론트엔드 연결

Sky의 `Dashboard.jsx`에 SSE 연결 코드를 넣어야 함.

**EventSource 로직 (EventSource는 자동으로 GET 사용 — POST 안 됨!):**
```jsx
// Dashboard.jsx에 추가할 코드
const [progress, setProgress] = useState([]);
const [isRunning, setIsRunning] = useState(false);

const runReview = () => {
  setIsRunning(true);
  setProgress([]);

  const eventSource = new EventSource("http://localhost:8000/api/review/run");

  eventSource.onmessage = (event) => {
    const data = JSON.parse(event.data);
    setProgress(prev => [...prev, data]);

    if (data.type === "complete") {
      eventSource.close();
      setIsRunning(false);
      // Refresh account list
      fetchAccounts();
    }
  };

  eventSource.onerror = () => {
    eventSource.close();
    setIsRunning(false);
  };
};
```

**SSE 이벤트 타입 4가지:**
| type | 의미 | UI에 보여줄 것 |
|---|---|---|
| `progress` | 전체 진행 | 프로그레스 바 + 텍스트 |
| `analyzing` | 특정 계정 분석 중 | "Analyzing Nimbus Analytics (1/3)" |
| `action` | AI가 행동함 | "✅ Sent Slack alert" / "✅ Created Linear ticket" |
| `complete` | 완료 | "Done. 2 auto-executed, 1 needs approval" |

**Activity Feed 컴포넌트에 이 데이터 연결:**
- progress 배열을 Activity Feed에 넘기면 됨
- 각 아이템을 타입별로 다른 색/아이콘으로 표시

---

### 13:30-제출 — 통합 디버깅 (제일 중요한 시간)

**체크리스트:**
- [ ] "Run Daily Review" 클릭 → SSE 스트림 오는지
- [ ] SSE 이벤트가 Activity Feed에 표시되는지
- [ ] Slack #retention-alerts에 실제 메시지 도착하는지
- [ ] 계정 테이블에 결과 표시되는지
- [ ] 계정 클릭 → Account Detail로 이동하는지
- [ ] Account Detail에 AI 분석 결과 표시되는지
- [ ] 이메일/메모 탭 동작하는지
- [ ] Orion Global → "Approve" 버튼 보이는지
- [ ] Approve 클릭 → Slack #urgent에 메시지 오는지
- [ ] Approve 후 상태가 "approved"로 변경되는지

**흔한 버그:**
- CORS 에러 → Eddy에게 말해서 FastAPI CORS 설정 확인
- SSE 연결 안 됨 → `Content-Type: text/event-stream` 확인
- Slack 안 감 → webhook URL 환경변수 확인
- 데이터 안 나옴 → CSV 컬럼 수 맞는지 확인 (새 컬럼 추가 후)

---

## 시간 부족할 때

1. ~~Linear~~ → Slack만으로 충분
2. ~~Activity Feed SSE~~ → 결과만 테이블에 보이면 OK
3. **절대 자르면 안 되는 것:** Slack 알림 + 3개 시나리오 데이터
