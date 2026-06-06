import { apiFetch } from './client'

export interface SeasonalObjective {
  id: number
  season: number
  created_at: string
  league_position: number
  league_points: number
  league_series: string
  budget_manual: number
  strategy: 'promote' | 'maintain' | 'youth'
  notes: string
  recommendation: string
}

export interface SeasonalCurrentResponse {
  objective: SeasonalObjective | null
}

export function getSeasonalCurrent(): Promise<SeasonalCurrentResponse> {
  return apiFetch<SeasonalCurrentResponse>('/api/seasonal/current')
}

export function saveSeasonalObjective(params: {
  season: number
  league_position?: number
  league_points?: number
  league_series?: string
  budget_manual?: number
  strategy: 'promote' | 'maintain' | 'youth'
  notes?: string
}): Promise<SeasonalObjective> {
  return apiFetch<SeasonalObjective>('/api/seasonal', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(params),
  })
}

export function getSeasonalHistory(): Promise<{ history: SeasonalObjective[] }> {
  return apiFetch('/api/seasonal/history')
}
