import { useEffect, useState } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import RiskBadge from '../components/RiskBadge'
import { listAccounts } from '../lib/api'
import { getPendingManualActionsFromSummary } from '../lib/workflow'

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
    .split('_')
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(' ')
}

function ActionRequired() {
  const location = useLocation()
  const navigate = useNavigate()
  const prefetchedAccounts = location.state?.accounts ?? []
  const [accounts, setAccounts] = useState(prefetchedAccounts)
  const [isLoading, setIsLoading] = useState(prefetchedAccounts.length === 0)

  useEffect(() => {
    if (prefetchedAccounts.length > 0) {
      setAccounts(prefetchedAccounts)
      setIsLoading(false)
      return
    }

    let cancelled = false

    async function loadAccounts() {
      setIsLoading(true)
      try {
        const response = await listAccounts()
        if (!cancelled) {
          setAccounts(response.accounts ?? [])
        }
      } finally {
        if (!cancelled) {
          setIsLoading(false)
        }
      }
    }

    loadAccounts()
    return () => {
      cancelled = true
    }
  }, [prefetchedAccounts])

  const pendingAccounts = accounts
    .map((account) => ({
      ...account,
      pendingActions: getPendingManualActionsFromSummary(account),
    }))
    .filter((account) => account.pendingActions.length > 0)
    .sort((left, right) => (left.health_score ?? 100) - (right.health_score ?? 100))

  return (
    <main className="shell-bg min-h-screen px-4 py-6 sm:px-6 lg:px-10">
      <div className="relative mx-auto max-w-6xl">
        <div className="radial-orb radial-orb-one" />
        <div className="radial-orb radial-orb-two" />

        <section className="glass-panel relative rounded-[2.5rem] p-6 sm:p-8 lg:p-10">
          <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
            <div>
              <Link to="/" className="text-xs font-semibold uppercase tracking-[0.3em] text-slate-500">
                Back to Dashboard
              </Link>
              <h1 className="mt-4 text-4xl font-semibold tracking-tight text-slate-950">Action required</h1>
              <p className="mt-3 max-w-2xl text-base leading-7 text-slate-600">
                Review every account that still needs a manual Linear ticket approval, email send approval, or both.
              </p>
            </div>
            <div className="rounded-[2rem] border border-slate-200 bg-white/80 px-5 py-4">
              <p className="text-xs font-semibold uppercase tracking-[0.28em] text-slate-500">Accounts Needing Action</p>
              <p className="mt-3 text-3xl font-semibold tracking-tight text-slate-950">{pendingAccounts.length}</p>
            </div>
          </div>

          {isLoading ? (
            <div className="mt-8 space-y-4">
              {Array.from({ length: 3 }).map((_, index) => (
                <div key={index} className="h-36 rounded-[2rem] border border-slate-200 bg-white/80" />
              ))}
            </div>
          ) : pendingAccounts.length === 0 ? (
            <div className="mt-8 rounded-[2rem] border border-sky-200 bg-sky-50 p-6 text-slate-700">
              <p className="text-sm font-semibold uppercase tracking-[0.24em] text-sky-700">All Clear</p>
              <p className="mt-3 text-base leading-7">
                There are no pending manual ticket or email approvals right now.
              </p>
            </div>
          ) : (
            <div className="mt-8 space-y-4">
              {pendingAccounts.map((account) => (
                <button
                  key={account.account_id}
                  type="button"
                  onClick={() => navigate(`/account/${account.account_id}`)}
                  className="w-full rounded-[2rem] border border-slate-200 bg-white/88 p-6 text-left shadow-[0_18px_60px_rgba(15,23,42,0.06)] transition hover:bg-slate-50"
                >
                  <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
                    <div className="min-w-0">
                      <div className="flex flex-wrap items-center gap-3">
                        <h2 className="text-2xl font-semibold tracking-tight text-slate-950">{account.account_name}</h2>
                        <RiskBadge score={account.health_score ?? 100} compact />
                      </div>
                      <p className="mt-3 text-sm text-slate-600">
                        {account.industry} · {account.plan_tier} · {formatCurrency(account.arr_amount ?? 0)} ARR
                      </p>
                      <p className="mt-4 text-sm font-semibold uppercase tracking-[0.24em] text-slate-500">Recommended Action</p>
                      <p className="mt-2 text-base font-semibold text-slate-900">{toActionLabel(account.next_best_action)}</p>
                    </div>

                    <div className="lg:max-w-sm">
                      <p className="text-sm font-semibold uppercase tracking-[0.24em] text-slate-500">Pending Approvals</p>
                      <div className="mt-3 flex flex-wrap gap-2">
                        {account.pendingActions.map((action) => (
                          <span
                            key={action.id}
                            className="inline-flex rounded-full bg-orange-100 px-3 py-1 text-sm font-semibold text-orange-800"
                          >
                            {action.label}
                          </span>
                        ))}
                      </div>
                      <p className="mt-4 text-sm leading-6 text-slate-600">
                        Slack has already been sent automatically. Open this account to review the drafts and approve the remaining follow-up actions.
                      </p>
                    </div>
                  </div>
                </button>
              ))}
            </div>
          )}
        </section>
      </div>
    </main>
  )
}

export default ActionRequired
