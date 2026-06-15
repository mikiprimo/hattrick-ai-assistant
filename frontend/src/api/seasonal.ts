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

export interface SeasonStatus {
  status: 'on_track' | 'at_risk' | 'off_track'
  projected_points: number
  current_points: number
  current_position: number
  played: number
  remaining: number
  message: string
  suggested_strategy: string | null
  history: { matchround: number; points: number; position: number }[]
}

export interface YouthPlayer {
  player_id: number
  name: string
  age: number
  primary_skill: string
  primary_skill_value: number
  primary_skill_label: string
  potential_score: number
  skill_delta: number
  speciality: string | null
}

export interface MaintainAnalysis {
  best_formation: string
  line_ratings: Record<string, number>
  weakest_sector: string
  weakest_sector_label: string
  weakest_rating: number
  message: string
}

export interface PromoteAnalysis {
  best_formation: string
  my_ratings: Record<string, number>
  rival_avg: Record<string, number> | null
  gaps: Record<string, number>
  needed_skills: { sector: string; sector_label: string; gap: number; min_skill_value: number; min_skill_label: string }[]
  sell_candidates: { player_id: number; name: string; age: number; salary: number; contribution: number }[]
  message: string
}

export function getSeasonalStatus(): Promise<SeasonStatus> {
  return apiFetch<SeasonStatus>('/api/seasonal/status')
}

export function getAnalysisYouth(): Promise<YouthPlayer[]> {
  return apiFetch<YouthPlayer[]>('/api/seasonal/analysis/youth')
}

export function getAnalysisMaintain(): Promise<MaintainAnalysis> {
  return apiFetch<MaintainAnalysis>('/api/seasonal/analysis/maintain')
}

export function getAnalysisPromote(): Promise<PromoteAnalysis> {
  return apiFetch<PromoteAnalysis>('/api/seasonal/analysis/promote')
}
