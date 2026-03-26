function getRiskTone(score) {
  if (score < 40) {
    return 'bg-red-50 text-red-700 ring-1 ring-red-200'
  }
  if (score < 70) {
    return 'bg-amber-50 text-amber-700 ring-1 ring-amber-200'
  }
  return 'bg-emerald-50 text-emerald-700 ring-1 ring-emerald-200'
}

function getRiskLabel(score) {
  if (score < 40) {
    return 'High Risk'
  }
  if (score < 70) {
    return 'Medium Risk'
  }
  return 'Healthy'
}

function RiskBadge({ score, compact = false }) {
  return (
    <span
      className={`inline-flex items-center gap-2 rounded-full px-3 py-1.5 text-sm font-medium ${getRiskTone(score)} ${
        compact ? 'px-2.5 py-1 text-xs' : ''
      }`}
    >
      <span className="font-semibold">{score}</span>
      {!compact ? <span className="text-current/80">{getRiskLabel(score)}</span> : null}
    </span>
  )
}

export default RiskBadge
