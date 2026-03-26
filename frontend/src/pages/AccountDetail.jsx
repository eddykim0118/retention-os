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

function getPendingManualActions(detail) {
  if (!detail?.next_best_action) {
    return []
  }

  const executedActions = new Set((detail.actions_taken ?? []).map((action) => action.type))
  const pendingActions = []

  if (detail.linear_ticket_title && !executedActions.has('linear_ticket')) {
    pendingActions.push('linear_ticket')
  }

  if (detail.generated_email && !executedActions.has('email_sent')) {
    pendingActions.push('send_email')
  }

  return pendingActions
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

  async function handleApprove(selectedActions) {
    if (!detail || isApproving || selectedActions.length === 0) {
      return
    }

    setIsApproving(true)
    try {
      await approveAccount(detail.account_id, selectedActions)
      const refreshed = await getAccountDetail(detail.account_id)
      if (refreshed) {
        setDetail(refreshed)
      }
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
    email: detail.generated_email ?? 'No email draft available yet.',
    linear: detail.linear_ticket_title
      ? `${detail.linear_ticket_title}\n\n${detail.linear_ticket_description ?? ''}`.trim()
      : 'No Linear ticket preview available yet.',
    memo: detail.internal_memo ?? 'No internal memo available yet.',
  }

  const reviewPending = !detail.status
  const executedActionTypes = new Set((detail.actions_taken ?? []).map((action) => action.type))
  const pendingManualActions = getPendingManualActions(detail)
  const manualApprovalRequired = !reviewPending && pendingManualActions.length > 0
  const approvalComplete = !reviewPending && pendingManualActions.length === 0
  const canCreateLinear = pendingManualActions.includes('linear_ticket')
  const canSendEmail = pendingManualActions.includes('send_email')
  const combinedActions = pendingManualActions
  const executionModeTone = reviewPending
    ? 'bg-slate-100 text-slate-700'
    : manualApprovalRequired
      ? 'bg-orange-100 text-orange-800'
      : 'bg-sky-100 text-sky-800'
  const executionModeLabel = reviewPending
    ? 'Pending Review'
    : manualApprovalRequired
      ? 'Approval Required'
      : 'Completed'
  const recommendedActionTone = reviewPending
    ? 'bg-slate-100 text-slate-700'
    : manualApprovalRequired
      ? 'bg-orange-100 text-orange-800'
      : 'bg-sky-100 text-sky-800'
  const recommendedActionLabel = reviewPending
    ? 'Pending Review'
    : manualApprovalRequired
      ? 'Approval Required'
      : 'Completed'
  const executionModeDescription = reviewPending
    ? detail.autonomy_reason
    : manualApprovalRequired
      ? 'Slack notification has already been sent. Review the recommended Linear ticket and email draft, then approve the follow-up actions manually.'
      : 'Slack notification was sent and the recommended follow-up actions have already been completed.'

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
                    className={`mt-3 inline-flex rounded-full px-3 py-1 text-sm font-semibold ${executionModeTone}`}
                  >
                    {executionModeLabel}
                  </p>
                  <p className="mt-3 max-w-xs text-sm leading-6 text-slate-600">{executionModeDescription}</p>
                </div>
              </div>

              <div className="mt-8 rounded-[2rem] border border-slate-200 bg-white/88 p-6 shadow-[0_18px_60px_rgba(15,23,42,0.06)]">
                <p className="text-xs font-semibold uppercase tracking-[0.28em] text-slate-500">Risk Signals</p>
                <div className="mt-5 grid gap-3">
                  {detail.slack_message ? (
                    <div className="rounded-2xl border border-sky-200 bg-sky-50 px-4 py-4 text-sm leading-6 text-sky-800">
                      <p className="text-xs font-semibold uppercase tracking-[0.24em] text-sky-600">Slack Alert Preview</p>
                      <p className="mt-2">{detail.slack_message}</p>
                    </div>
                  ) : null}
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
                    className={`inline-flex rounded-full px-3 py-1 text-sm font-semibold ${recommendedActionTone}`}
                  >
                    {recommendedActionLabel}
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
                    ['linear', 'Linear Ticket'],
                    ['memo', 'Internal Memo'],
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

              {manualApprovalRequired ? (
                <div className="rounded-[2rem] border border-orange-200 bg-orange-50 p-6 shadow-[0_18px_60px_rgba(251,146,60,0.12)]">
                  <p className="text-xs font-semibold uppercase tracking-[0.28em] text-orange-700">Approval Gate</p>
                  <h2 className="mt-2 text-2xl font-semibold tracking-tight text-slate-950">Approve manual follow-up</h2>
                  <p className="mt-3 text-sm leading-7 text-slate-700">
                    Slack has already been sent automatically. Review the Linear ticket and customer email below, then approve either action or both.
                  </p>
                  <div className="mt-5 space-y-3">
                    <button
                      type="button"
                      onClick={() => handleApprove(['linear_ticket'])}
                      disabled={isApproving || !canCreateLinear}
                      className="w-full rounded-full bg-slate-950 px-5 py-3 text-sm font-semibold text-white transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:bg-slate-400"
                    >
                      {executedActionTypes.has('linear_ticket') ? 'Linear Ticket Created' : isApproving ? 'Processing...' : 'Approve Linear Ticket'}
                    </button>
                    <button
                      type="button"
                      onClick={() => handleApprove(['send_email'])}
                      disabled={isApproving || !canSendEmail}
                      className="w-full rounded-full border border-slate-300 bg-white px-5 py-3 text-sm font-semibold text-slate-900 transition hover:bg-slate-50 disabled:cursor-not-allowed disabled:border-slate-200 disabled:text-slate-400"
                    >
                      {executedActionTypes.has('email_sent') ? 'Email Sent' : isApproving ? 'Processing...' : 'Approve Email Send'}
                    </button>
                    <button
                      type="button"
                      onClick={() => handleApprove(combinedActions)}
                      disabled={isApproving || combinedActions.length < 2}
                      className="w-full rounded-full border border-orange-300 bg-orange-100 px-5 py-3 text-sm font-semibold text-orange-900 transition hover:bg-orange-200 disabled:cursor-not-allowed disabled:border-orange-100 disabled:bg-orange-50 disabled:text-orange-400"
                    >
                      {isApproving ? 'Processing...' : 'Approve Both'}
                    </button>
                  </div>
                </div>
              ) : approvalComplete ? (
                <div className="rounded-[2rem] border border-sky-200 bg-sky-50 p-6 shadow-[0_18px_60px_rgba(59,130,246,0.10)]">
                  <p className="text-xs font-semibold uppercase tracking-[0.28em] text-sky-700">Workflow Complete</p>
                  <h2 className="mt-2 text-2xl font-semibold tracking-tight text-slate-950">All follow-up actions approved</h2>
                  <p className="mt-3 text-sm leading-7 text-slate-700">
                    Slack was sent automatically, and the recommended Linear ticket and email workflow no longer require approval for this account.
                  </p>
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
