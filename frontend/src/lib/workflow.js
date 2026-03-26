export function getPendingManualActionsFromSummary(account) {
  if (!account?.next_best_action) {
    return []
  }

  const executedActions = new Set(account.actions_taken ?? [])
  const pendingActions = []

  if (!executedActions.has('linear_ticket')) {
    pendingActions.push({
      id: 'linear_ticket',
      label: 'Create Linear ticket',
    })
  }

  if (!executedActions.has('email_sent')) {
    pendingActions.push({
      id: 'send_email',
      label: 'Send customer email',
    })
  }

  return pendingActions
}

export function getPendingManualActionCountFromSummary(account) {
  return getPendingManualActionsFromSummary(account).length
}
