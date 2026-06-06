import { apiFetch } from './client'

export function triggerSync(entity: string): Promise<{ status: string; synced_at: string }> {
  return apiFetch(`/api/sync/${entity}`, { method: 'POST' })
}
