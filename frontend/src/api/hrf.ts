import { apiFetch } from './client'

export interface HrfSettings {
  hrf_folder_path: string
  team_id: number | null
  enabled: boolean
}

export interface HrfScanResult {
  status: string
  scanned_at: string
  files_imported: number
  players_upserted: number
}

export function getHrfSettings(): Promise<HrfSettings> {
  return apiFetch<HrfSettings>('/api/hrf/settings')
}

export function saveHrfSettings(settings: HrfSettings): Promise<{ status: string }> {
  return apiFetch<{ status: string }>('/api/hrf/settings', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(settings),
  })
}

export function scanHrf(): Promise<HrfScanResult> {
  return apiFetch<HrfScanResult>('/api/hrf/scan', { method: 'POST' })
}
