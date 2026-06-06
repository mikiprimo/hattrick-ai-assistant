import { apiFetch } from './client'

export interface Settings {
  configured: boolean
  consumer_key?: string
  access_token?: string
}

export interface SettingsPayload {
  consumer_key: string
  consumer_secret: string
  access_token: string
  access_token_secret: string
}

export function getSettings(): Promise<Settings> {
  return apiFetch<Settings>('/api/settings')
}

export function saveSettings(payload: SettingsPayload): Promise<{ status: string }> {
  return apiFetch('/api/settings', { method: 'POST', body: JSON.stringify(payload) })
}
