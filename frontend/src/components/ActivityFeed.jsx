const feedStyles = {
  progress: 'border-sky-200 bg-sky-50 text-sky-700',
  analyzing: 'border-violet-200 bg-violet-50 text-violet-700',
  action: 'border-emerald-200 bg-emerald-50 text-emerald-700',
  warning: 'border-amber-200 bg-amber-50 text-amber-700',
  complete: 'border-slate-200 bg-slate-100 text-slate-700',
}

const feedIcons = {
  progress: '•',
  analyzing: 'AI',
  action: 'OK',
  warning: '!',
  complete: 'END',
}

function ActivityFeed({ items }) {
  return (
    <div className="rounded-[2rem] border border-slate-200/80 bg-white/90 p-6 shadow-[0_18px_60px_rgba(15,23,42,0.08)]">
      <div className="flex items-center justify-between gap-3">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.28em] text-slate-500">Activity Feed</p>
          <h2 className="mt-2 text-2xl font-semibold tracking-tight text-slate-950">Live agent actions</h2>
        </div>
        <div className="rounded-full bg-slate-950 px-4 py-2 text-xs font-semibold uppercase tracking-[0.24em] text-white">
          SSE Ready
        </div>
      </div>

      <div className="mt-6 space-y-3">
        {items.map((item, index) => (
          <div
            key={`${item.message}-${index}`}
            className={`flex items-start gap-4 rounded-2xl border p-4 ${feedStyles[item.type] ?? feedStyles.progress}`}
          >
            <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-2xl bg-white/80 text-[11px] font-semibold tracking-[0.18em]">
              {feedIcons[item.type] ?? '•'}
            </div>
            <div className="min-w-0 flex-1">
              <p className="text-sm font-medium leading-6">{item.message}</p>
              <p className="mt-1 text-xs uppercase tracking-[0.24em] text-current/70">{item.time ?? 'Live'}</p>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

export default ActivityFeed
