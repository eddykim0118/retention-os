import { useEffect, useMemo, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import ActivityFeed from '../components/ActivityFeed'
import RiskBadge from '../components/RiskBadge'
import StatsCard from '../components/StatsCard'
import { getInitialActivityFeed, listAccounts } from '../lib/api'
import { reviewSimulation } from '../lib/mockData'

const LAST_REVIEW_STORAGE_KEY = 'retention-os:last-review-time'

function AccountsIcon() {
  return (
    <svg viewBox="0 0 24 24" className="h-6 w-6" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <path d="M16 21v-2a4 4 0 0 0-4-4H7a4 4 0 0 0-4 4v2" />
      <circle cx="9.5" cy="7" r="3" />
      <path d="M20 8v6" />
      <path d="M23 11h-6" />
    </svg>
  )
}

function RiskIcon() {
  return (
    <svg viewBox="0 0 24 24" className="h-6 w-6" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <path d="M12 9v4" />
      <path d="M12 17h.01" />
      <path d="M10.29 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0Z" />
    </svg>
  )
}

function RevenueIcon() {
  return (
    <svg viewBox="0 0 24 24" className="h-6 w-6" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <path d="M3 3v18h18" />
      <path d="m7 15 4-4 3 3 5-6" />
      <path d="M18 8h1v1" />
    </svg>
  )
}

function ActionIcon() {
  return (
    <svg viewBox="0 0 24 24" className="h-6 w-6" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <path d="M13 2 3 14h7l-1 8 10-12h-7l1-8Z" />
    </svg>
  )
}

function formatCurrency(value) {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    maximumFractionDigits: 0,
  }).format(value ?? 0)
}

function formatReviewTime(date = new Date()) {
  return date.toLocaleTimeString('en-US', {
    hour: 'numeric',
    minute: '2-digit',
  })
}

function getStatusTone(status) {
  if (!status) {
    return 'bg-slate-100 text-slate-700'
  }
  if (status === 'needs_approval') {
    return 'bg-orange-100 text-orange-800'
  }
  if (status === 'approved') {
    return 'bg-sky-100 text-sky-800'
  }
  return 'bg-emerald-100 text-emerald-800'
}

function getStatusLabel(status) {
  if (!status) {
    return 'Pending Review'
  }
  if (status === 'needs_approval') {
    return 'Needs Approval'
  }
  if (status === 'approved') {
    return 'Approved'
  }
  return 'Auto-executed'
}

function getPendingManualActionCount(account) {
  if (!account.next_best_action) {
    return 0
  }

  const executedActions = new Set(account.actions_taken ?? [])
  let pendingCount = 0

  if (!executedActions.has('linear_ticket')) {
    pendingCount += 1
  }

  if (!executedActions.has('email_sent')) {
    pendingCount += 1
  }

  return pendingCount
}

function Dashboard() {
  const navigate = useNavigate()
  const [accounts, setAccounts] = useState([])
  const [feedItems, setFeedItems] = useState(getInitialActivityFeed())
  const [isLoading, setIsLoading] = useState(true)
  const [isRunning, setIsRunning] = useState(false)
  const [dataSource, setDataSource] = useState('mock')
  const [error, setError] = useState('')
  const [lastReviewTime, setLastReviewTime] = useState(() => {
    if (typeof window === 'undefined') {
      return null
    }
    return window.localStorage.getItem(LAST_REVIEW_STORAGE_KEY)
  })
  const eventSourceRef = useRef(null)
  const simulationRef = useRef([])

  useEffect(() => {
    loadAccounts()

    return () => {
      if (eventSourceRef.current) {
        eventSourceRef.current.close()
      }
      simulationRef.current.forEach((timerId) => window.clearTimeout(timerId))
    }
  }, [])

  async function loadAccounts() {
    setIsLoading(true)
    try {
      const { accounts: nextAccounts, source } = await listAccounts()
      setAccounts(nextAccounts)
      setDataSource(source)
      setError('')
    } catch {
      setError('Unable to load accounts.')
    } finally {
      setIsLoading(false)
    }
  }

  function appendFeedItem(item) {
    setFeedItems((current) => [...current, item])
  }

  function updateLastReviewTime(nextTime = formatReviewTime()) {
    setLastReviewTime(nextTime)
    if (typeof window !== 'undefined') {
      window.localStorage.setItem(LAST_REVIEW_STORAGE_KEY, nextTime)
    }
  }

  function runReviewFallback() {
    setDataSource('mock')
    reviewSimulation.forEach((item, index) => {
      const timerId = window.setTimeout(() => {
        appendFeedItem(item)
        if (item.type === 'complete') {
          updateLastReviewTime()
          setIsRunning(false)
          loadAccounts()
        }
      }, index * 500)
      simulationRef.current.push(timerId)
    })
  }

  function runReview() {
    if (isRunning) {
      return
    }

    setIsRunning(true)
    setFeedItems([])
    simulationRef.current.forEach((timerId) => window.clearTimeout(timerId))
    simulationRef.current = []

    try {
      const eventSource = new EventSource('/api/review/run')
      eventSourceRef.current = eventSource

      eventSource.onmessage = (event) => {
        const payload = JSON.parse(event.data)
        appendFeedItem({
          type: payload.type ?? 'progress',
          message:
            payload.message ??
            (payload.account ? `Analyzing ${payload.account} (${payload.index}/${payload.total})` : 'Processing'),
          time: formatReviewTime(),
        })

        if (payload.type === 'complete') {
          eventSource.close()
          eventSourceRef.current = null
          updateLastReviewTime()
          setIsRunning(false)
          loadAccounts()
        }
      }

      eventSource.onerror = () => {
        eventSource.close()
        eventSourceRef.current = null
        runReviewFallback()
      }
    } catch {
      runReviewFallback()
    }
  }

  const stats = useMemo(() => {
    const atRiskAccounts = accounts.filter((account) => (account.health_score ?? 100) < 70)
    const arrAtRisk = atRiskAccounts.reduce((sum, account) => sum + (account.arr_amount ?? (account.mrr_amount ?? 0) * 12), 0)
    const actionsRequired = accounts.reduce((sum, account) => sum + getPendingManualActionCount(account), 0)

    return {
      total: accounts.length,
      atRisk: atRiskAccounts.length,
      arrAtRisk,
      actionsRequired,
    }
  }, [accounts])
  const lastRunTime = lastReviewTime ?? feedItems.at(-1)?.time ?? 'Never'

  return (
    <main className="shell-bg min-h-screen px-4 py-6 text-slate-950 sm:px-6 lg:px-10">
      <div className="relative mx-auto max-w-7xl">
        <div className="radial-orb radial-orb-one" />
        <div className="radial-orb radial-orb-two" />

        <section className="glass-panel relative overflow-hidden rounded-[2.5rem] px-6 py-8 sm:px-8 lg:px-10">
          <div className="flex flex-col gap-8 lg:flex-row lg:items-end lg:justify-between">
            <div className="max-w-3xl">
              <p className="text-xs font-semibold uppercase tracking-[0.34em] text-slate-500">Retention OS</p>
              <h1 className="mt-4 text-4xl font-semibold tracking-tight text-slate-950 sm:text-5xl">
                AI account manager for churn intervention.
              </h1>
              <p className="mt-4 max-w-2xl text-base leading-7 text-slate-600">
                Review risk, watch the agent act in real time, and escalate only when a high-value account needs a human
                decision.
              </p>
            </div>

            <div className="grid gap-3 sm:grid-cols-2">
              <button
                type="button"
                onClick={runReview}
                disabled={isRunning}
                className="rounded-full bg-slate-950 px-6 py-3 text-sm font-semibold text-white transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:bg-slate-400"
              >
                {isRunning ? 'Running Review...' : 'Run Daily Review'}
              </button>
              <div className="rounded-full border border-slate-200 bg-white/70 px-5 py-3 text-sm text-slate-600">
                Last review: <span className="font-semibold text-slate-900">{lastRunTime}</span>
              </div>
            </div>
          </div>

          <div className="mt-8 grid gap-4 md:grid-cols-2 xl:grid-cols-4">
            <StatsCard label="Total Accounts" value={stats.total} icon={<AccountsIcon />} detail="Current portfolio under monitoring" />
            <StatsCard label="At-Risk Accounts" value={stats.atRisk} icon={<RiskIcon />} accent="text-red-600" detail="Health score under 70" />
            <StatsCard label="ARR At Risk" value={formatCurrency(stats.arrAtRisk)} icon={<RevenueIcon />} accent="text-amber-600" detail="Annualized revenue exposed" />
            <StatsCard label="Action Required" value={stats.actionsRequired} icon={<ActionIcon />} accent="text-emerald-600" detail="Manual email and ticket approvals still pending" />
          </div>
        </section>

        <section className="mt-8 grid gap-8 xl:grid-cols-[1.05fr_1.35fr]">
          <ActivityFeed items={feedItems} />

          <div className="rounded-[2rem] border border-slate-200/80 bg-white/90 p-6 shadow-[0_18px_60px_rgba(15,23,42,0.08)]">
            <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.28em] text-slate-500">Account Table</p>
                <h2 className="mt-2 text-2xl font-semibold tracking-tight text-slate-950">Priority queue</h2>
              </div>
              <div className="text-sm text-slate-500">
                Source: <span className="font-semibold uppercase tracking-[0.2em] text-slate-900">{dataSource}</span>
              </div>
            </div>

            {error ? <p className="mt-6 rounded-2xl bg-red-50 px-4 py-3 text-sm text-red-700">{error}</p> : null}

            <div className="mt-6 overflow-hidden rounded-[1.5rem] border border-slate-200">
              <div className="hidden grid-cols-[1.6fr_1fr_0.9fr_0.9fr_1fr] gap-4 bg-slate-50 px-5 py-4 text-xs font-semibold uppercase tracking-[0.24em] text-slate-500 md:grid">
                <span>Name</span>
                <span>Industry</span>
                <span>Plan</span>
                <span>Risk</span>
                <span>Status</span>
              </div>

              <div className="divide-y divide-slate-200">
                {isLoading
                  ? Array.from({ length: 3 }).map((_, index) => (
                      <div key={index} className="grid gap-3 px-5 py-5 md:grid-cols-[1.6fr_1fr_0.9fr_0.9fr_1fr]">
                        <div className="h-5 rounded-full bg-slate-100" />
                        <div className="h-5 rounded-full bg-slate-100" />
                        <div className="h-5 rounded-full bg-slate-100" />
                        <div className="h-5 rounded-full bg-slate-100" />
                        <div className="h-5 rounded-full bg-slate-100" />
                      </div>
                    ))
                  : accounts
                      .slice()
                      .sort((a, b) => (a.health_score ?? 100) - (b.health_score ?? 100))
                      .map((account) => (
                        <button
                          key={account.account_id}
                          type="button"
                          onClick={() => navigate(`/account/${account.account_id}`)}
                          className="grid w-full gap-3 px-5 py-5 text-left transition hover:bg-slate-50 md:grid-cols-[1.6fr_1fr_0.9fr_0.9fr_1fr]"
                        >
                          <div>
                            <p className="text-base font-semibold text-slate-950">{account.account_name}</p>
                            <p className="mt-1 text-sm text-slate-500">{formatCurrency(account.mrr_amount ?? 0)} MRR</p>
                          </div>
                          <div className="text-sm text-slate-600">{account.industry}</div>
                          <div className="text-sm text-slate-600">{account.plan_tier}</div>
                          <div>
                            <RiskBadge score={account.health_score ?? 100} compact />
                          </div>
                          <div>
                            <span className={`inline-flex rounded-full px-3 py-1 text-xs font-semibold ${getStatusTone(account.status)}`}>
                              {getStatusLabel(account.status)}
                            </span>
                          </div>
                        </button>
                      ))}
              </div>
            </div>
          </div>
        </section>
      </div>
    </main>
  )
}

export default Dashboard
