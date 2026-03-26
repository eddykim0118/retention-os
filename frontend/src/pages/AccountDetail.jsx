import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import RiskBadge from '../components/RiskBadge'
import { approveAccount, getAccountDetail } from '../lib/api'

function formatCurrency(value) {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    maximumFractionDigits: 0,
  }).format(value ?? 0)
}

function toActionLabel(action) {
  if (!action) {
    return 'Awaiting Review'
  }
  return action
    ?.split('_')
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(' ')
}

function AccountDetail() {
  const { id } = useParams()
  const [detail, setDetail] = useState(null)
  const [activeTab, setActiveTab] = useState('email')
  const [isApproving, setIsApproving] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    let cancelled = false

    async function loadDetail() {
      setError('')
      const data = await getAccountDetail(id)
      if (!cancelled) {
        if (data) {
          setDetail(data)
        } else {
          setError('Account detail is unavailable.')
        }
      }
    }

    loadDetail()
    return () => {
      cancelled = true
    }
  }, [id])

  async function handleApprove() {
    if (!detail || isApproving) {
      return
    }

    setIsApproving(true)
    try {
      await approveAccount(detail.account_id)
      setDetail((current) =>
        current
          ? {
              ...current,
              status: 'approved',
              autonomy_level: 'human',
              actions_taken: [
                ...(current.actions_taken ?? []),
                {
                  type: 'approval',
                  timestamp: new Date().toLocaleTimeString('en-US', {
                    hour: 'numeric',
                    minute: '2-digit',
                  }),
                  status: 'completed',
                },
              ],
            }
          : current,
      )
    } catch {
      setError('Approval failed. Try again when the backend is available.')
    } finally {
      setIsApproving(false)
    }
  }

  if (error && !detail) {
    return (
      <main className="shell-bg min-h-screen px-4 py-6 sm:px-6 lg:px-10">
        <div className="mx-auto max-w-5xl rounded-[2rem] border border-red-200 bg-white p-8 text-red-700 shadow-[0_18px_60px_rgba(15,23,42,0.08)]">
          <Link to="/" className="text-sm font-semibold uppercase tracking-[0.24em] text-slate-500">
            Back to Dashboard
          </Link>
          <p className="mt-6 text-lg">{error}</p>
        </div>
      </main>
    )
  }

  if (!detail) {
    return (
      <main className="shell-bg min-h-screen px-4 py-6 sm:px-6 lg:px-10">
        <div className="mx-auto max-w-6xl rounded-[2rem] border border-slate-200 bg-white p-8 shadow-[0_18px_60px_rgba(15,23,42,0.08)]">
          <div className="h-6 w-40 rounded-full bg-slate-100" />
          <div className="mt-8 grid gap-6 lg:grid-cols-[1.6fr_0.85fr]">
            <div className="space-y-4">
              <div className="h-10 rounded-full bg-slate-100" />
              <div className="h-28 rounded-[2rem] bg-slate-100" />
              <div className="h-40 rounded-[2rem] bg-slate-100" />
            </div>
            <div className="h-80 rounded-[2rem] bg-slate-100" />
          </div>
        </div>
      </main>
    )
  }

  const tabContent = {
    email: detail.generated_email,
    memo: detail.internal_memo,
    slack: detail.slack_message,
  }

  const reviewPending = !detail.status
  const needsApproval = detail.status === 'needs_approval'
  const approvalComplete = detail.status === 'approved'

  return (
    <main className="shell-bg min-h-screen px-4 py-6 sm:px-6 lg:px-10">
      <div className="relative mx-auto max-w-6xl">
        <div className="radial-orb radial-orb-one" />
        <div className="radial-orb radial-orb-two" />

        <section className="glass-panel relative rounded-[2.5rem] p-6 sm:p-8 lg:p-10">
          <Link to="/" className="text-xs font-semibold uppercase tracking-[0.3em] text-slate-500">
            Back to Dashboard
          </Link>

          <div className="mt-8 grid gap-8 lg:grid-cols-[1.45fr_0.85fr]">
            <div>
              <div className="flex flex-wrap items-start justify-between gap-4">
                <div>
                  <h1 className="text-4xl font-semibold tracking-tight text-slate-950">{detail.account_name}</h1>
                  <p className="mt-3 text-base text-slate-600">
                    {detail.industry} · {detail.plan_tier} · {detail.seats} seats
                  </p>
                  <p className="mt-2 text-base text-slate-600">
                    MRR: {formatCurrency(detail.mrr_amount)} · ARR: {formatCurrency(detail.arr_amount)}
                  </p>
                </div>

                <div className="rounded-[2rem] border border-slate-200 bg-white/80 px-5 py-4">
                  <p className="text-xs font-semibold uppercase tracking-[0.28em] text-slate-500">Execution Mode</p>
                  <p
                    className={`mt-3 inline-flex rounded-full px-3 py-1 text-sm font-semibold ${
                      reviewPending
                        ? 'bg-slate-100 text-slate-700'
                        : needsApproval
                          ? 'bg-orange-100 text-orange-800'
                          : approvalComplete
                            ? 'bg-sky-100 text-sky-800'
                            : 'bg-emerald-100 text-emerald-800'
                    }`}
                  >
                    {reviewPending ? 'Pending Review' : needsApproval ? 'Needs Approval' : approvalComplete ? 'Approved' : 'Auto-executed'}
                  </p>
                  <p className="mt-3 max-w-xs text-sm leading-6 text-slate-600">{detail.autonomy_reason}</p>
                </div>
              </div>

              <div className="mt-8 rounded-[2rem] border border-slate-200 bg-white/88 p-6 shadow-[0_18px_60px_rgba(15,23,42,0.06)]">
                <p className="text-xs font-semibold uppercase tracking-[0.28em] text-slate-500">Risk Signals</p>
                <div className="mt-5 grid gap-3">
                  {detail.risk_reasons?.map((reason) => (
                    <div key={reason} className="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-4 text-sm leading-6 text-slate-700">
                      {reason}
                    </div>
                  ))}
                </div>
              </div>

              <div className="mt-8 rounded-[2rem] border border-slate-200 bg-white/88 p-6 shadow-[0_18px_60px_rgba(15,23,42,0.06)]">
                <div className="flex flex-wrap items-start justify-between gap-4">
                  <div>
                    <p className="text-xs font-semibold uppercase tracking-[0.28em] text-slate-500">Recommended Action</p>
                    <h2 className="mt-2 text-2xl font-semibold tracking-tight text-slate-950">{toActionLabel(detail.next_best_action)}</h2>
                  </div>
                  <div
                    className={`inline-flex rounded-full px-3 py-1 text-sm font-semibold ${
                      reviewPending
                        ? 'bg-slate-100 text-slate-700'
                        : detail.autonomy_level === 'auto' && !approvalComplete
                          ? 'bg-emerald-100 text-emerald-800'
                          : 'bg-orange-100 text-orange-800'
                    }`}
                  >
                    {reviewPending
                      ? 'Pending Review'
                      : detail.autonomy_level === 'auto' && !approvalComplete
                        ? 'Auto-executed'
                        : approvalComplete
                          ? 'Approved'
                          : 'Needs Approval'}
                  </div>
                </div>
                <p className="mt-5 text-sm leading-7 text-slate-700">{detail.action_reasoning}</p>
                <div className="mt-5 rounded-2xl bg-slate-50 p-4 text-sm leading-7 text-slate-600">{detail.why_not_others}</div>
                <div className="mt-5 inline-flex rounded-full bg-slate-950 px-4 py-2 text-sm font-semibold text-white">
                  {detail.urgency_deadline}
                </div>
              </div>

              <div className="mt-8 rounded-[2rem] border border-slate-200 bg-white/88 p-6 shadow-[0_18px_60px_rgba(15,23,42,0.06)]">
                <div className="flex flex-wrap gap-2">
                  {[
                    ['email', 'Customer Email'],
                    ['memo', 'Internal Memo'],
                    ['slack', 'Slack Message'],
                  ].map(([value, label]) => (
                    <button
                      key={value}
                      type="button"
                      onClick={() => setActiveTab(value)}
                      className={`rounded-full px-4 py-2 text-sm font-semibold transition ${
                        activeTab === value ? 'bg-slate-950 text-white' : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
                      }`}
                    >
                      {label}
                    </button>
                  ))}
                </div>
                <pre className="mt-6 overflow-x-auto rounded-[1.5rem] bg-slate-950 p-5 text-sm leading-7 whitespace-pre-wrap text-slate-100">
                  {tabContent[activeTab]}
                </pre>
              </div>
            </div>

            <aside className="space-y-6">
              <div className="rounded-[2rem] border border-slate-200 bg-slate-950 p-6 text-white shadow-[0_18px_60px_rgba(15,23,42,0.18)]">
                <p className="text-xs font-semibold uppercase tracking-[0.28em] text-white/60">Health Score</p>
                <div className="mt-4 flex items-center justify-between">
                  <RiskBadge score={detail.health_score} />
                  <div className="text-right">
                    <p className="text-sm text-white/60">Churn Risk</p>
                    <p className="text-3xl font-semibold tracking-tight">{detail.churn_risk_score}%</p>
                  </div>
                </div>
              </div>

              <div className="rounded-[2rem] border border-slate-200 bg-white/88 p-6 shadow-[0_18px_60px_rgba(15,23,42,0.06)]">
                <p className="text-xs font-semibold uppercase tracking-[0.28em] text-slate-500">AI Actions Taken</p>
                <div className="mt-5 space-y-3">
                  {(detail.actions_taken ?? []).map((action, index) => (
                    <div key={`${action.type}-${index}`} className="rounded-2xl bg-slate-50 px-4 py-4">
                      <p className="text-sm font-semibold text-slate-900">{toActionLabel(action.type)}</p>
                      <p className="mt-1 text-sm text-slate-600">
                        {action.timestamp ?? 'Pending'} {action.channel ? `· ${action.channel}` : ''}
                      </p>
                      <p className="mt-1 text-xs font-semibold uppercase tracking-[0.24em] text-slate-400">{action.status}</p>
                    </div>
                  ))}
                </div>
              </div>

              {needsApproval || approvalComplete ? (
                <div className="rounded-[2rem] border border-orange-200 bg-orange-50 p-6 shadow-[0_18px_60px_rgba(251,146,60,0.12)]">
                  <p className="text-xs font-semibold uppercase tracking-[0.28em] text-orange-700">Approval Gate</p>
                  <h2 className="mt-2 text-2xl font-semibold tracking-tight text-slate-950">Senior outreach approval</h2>
                  <p className="mt-3 text-sm leading-7 text-slate-700">
                    Orion Global crosses the human approval threshold because executive involvement is part of the proposed action.
                  </p>
                  <button
                    type="button"
                    onClick={handleApprove}
                    disabled={isApproving || approvalComplete}
                    className="mt-5 w-full rounded-full bg-slate-950 px-5 py-3 text-sm font-semibold text-white transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:bg-slate-400"
                  >
                    {approvalComplete ? 'Approved' : isApproving ? 'Approving...' : 'Approve Senior Outreach'}
                  </button>
                </div>
              ) : null}

              {error ? <p className="rounded-2xl bg-red-50 px-4 py-3 text-sm text-red-700">{error}</p> : null}
            </aside>
          </div>
        </section>
      </div>
    </main>
  )
}

export default AccountDetail
