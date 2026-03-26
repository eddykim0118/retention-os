function StatsCard({ label, value, accent, detail, icon }) {
  return (
    <div className="rounded-3xl border border-white/60 bg-white/88 p-5 shadow-[0_18px_60px_rgba(15,23,42,0.08)] backdrop-blur">
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.28em] text-slate-500">{label}</p>
          <p className={`mt-3 text-3xl font-semibold tracking-tight ${accent ?? 'text-slate-950'}`}>{value}</p>
        </div>
        <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-slate-950/5 text-slate-700">
          {icon}
        </div>
      </div>
      {detail ? <p className="mt-4 text-sm text-slate-500">{detail}</p> : null}
    </div>
  )
}

export default StatsCard
