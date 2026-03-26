import { getMockDetail, mockAccounts, mockActivityFeed } from './mockData'

async function requestJson(url, options) {
  const response = await fetch(url, options)
  if (!response.ok) {
    throw new Error(`Request failed: ${response.status}`)
  }
  return response.json()
}

export async function listAccounts() {
  try {
    const data = await requestJson('/api/accounts')
    return {
      accounts: Array.isArray(data) && data.length > 0 ? data : mockAccounts,
      source: 'api',
    }
  } catch {
    return {
      accounts: mockAccounts,
      source: 'mock',
    }
  }
}

export async function getAccountDetail(accountId) {
  try {
    return await requestJson(`/api/accounts/${accountId}`)
  } catch {
    return getMockDetail(accountId)
  }
}

export async function approveAccount(accountId) {
  try {
    return await requestJson(`/api/accounts/${accountId}/approve`, { method: 'POST' })
  } catch {
    return {
      status: 'approved',
      approved_at: new Date().toISOString(),
      mock: true,
    }
  }
}

export function getInitialActivityFeed() {
  return mockActivityFeed
}
