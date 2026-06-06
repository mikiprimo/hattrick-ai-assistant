import { apiFetch } from './client'

export interface PlayerSkills {
  goalkeeper: number
  defending: number
  playmaking: number
  scoring: number
  passing: number
  winger: number
  set_pieces: number
}

export interface SquadPlayer {
  id: number
  name: string
  form: number
  stamina: number
  injury_days: number
  best_role: string
  role_rating: number
  skills: PlayerSkills
}

export interface SquadResponse {
  players: SquadPlayer[]
}

export interface TacticEntry {
  name: string
  score: number
  explanation: string
}

export interface AttitudeResult {
  attitude: 'normal' | 'mots' | 'cool'
  reason: string
}

export interface MatchResult {
  result: 'W' | 'D' | 'L'
  goals_for: number
  goals_against: number
}

export interface AnalysisResult {
  opponent: {
    team_name: string
    team_id: number
    best_formation: string
    line_ratings: Record<string, number>
    recent_results: MatchResult[]
  }
  my_team: {
    best_formation: string
    xp_level: number
    xp_warning: boolean
    xp_alternative: string | null
    lineup: Record<string, Array<{ id: number; name: string; rating: number }>>
    line_ratings: Record<string, number>
    modified_ratings: Record<string, number>
  }
  tactic_ranking: TacticEntry[]
  attitude: AttitudeResult
  explanation: string
}

export interface FormationXPMap {
  formation_xp: Record<string, number>
}

export interface MatchPrepHistoryEntry {
  id: number
  created_at: string
  opponent_name: string
  match_type: string
  my_formation: string
  my_tactic: string
  my_attitude: string
  explanation: string
}

export function getPrePartitaSquad(): Promise<SquadResponse> {
  return apiFetch<SquadResponse>('/api/pre-partita/squad')
}

export function getFormationXP(): Promise<FormationXPMap> {
  return apiFetch<FormationXPMap>('/api/pre-partita/formation-xp')
}

export function putFormationXP(formation_name: string, xp_level: number): Promise<void> {
  return apiFetch('/api/pre-partita/formation-xp', {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ formation_name, xp_level }),
  })
}

export function analyzeOpponent(params: {
  players_xml: string
  matches_xml?: string
  match_type: string
  spirit: number
  confidence: number
  formation_xp: Record<string, number>
}): Promise<AnalysisResult> {
  return apiFetch<AnalysisResult>('/api/pre-partita/analyze', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(params),
  })
}

export function saveAnalysis(params: {
  analysis: AnalysisResult
  my_spirit: number
  my_confidence: number
  my_attitude: string
  match_type: string
}): Promise<void> {
  return apiFetch('/api/pre-partita/save', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(params),
  })
}

export function getMatchPrepHistory(): Promise<{ history: MatchPrepHistoryEntry[] }> {
  return apiFetch('/api/pre-partita/history')
}
