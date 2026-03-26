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
    // Trust the API response - if it returns empty, show empty (demo mode)
    // Only fall back to mock data on network/server errors
    return {
      accounts: Array.isArray(data) ? data : [],
      source: 'api',
    }
  } catch {
    // Network error or server down - use mock data so app still works
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
  // Start with empty feed - events will populate when "Run Daily Review" is clicked
  // This creates a clean slate for demos
  return []
}
