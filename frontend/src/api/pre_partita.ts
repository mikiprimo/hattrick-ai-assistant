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

export interface SubPlanEntry {
  minute: number
  out_name: string
  out_id: number
  out_stamina: number
  in_name: string
  in_id: number
  reason: string
}

export interface AttitudeOrderEntry {
  minute: number
  condition: string
  attitude: string
  reason: string
}

export interface AnalysisResult {
  opponent: {
    team_name: string
    team_id: number
    typical_formation: string
    dominant_tactic: number | null
    avg_tactic_skill: number
    chpp_ratings: Record<string, number>
    recent_results: MatchResult[]
    matches_used: number
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
  tactic_recommendation: { recommended: string }
  sub_plan: SubPlanEntry[]
  attitude_orders: AttitudeOrderEntry[]
  attitude: AttitudeResult
  explanation: string
}

export interface FormationXPMap {
  formation_xp: Record<string, number>
}

export interface TacticXPMap {
  tactic_xp: Record<string, number>
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

export function getTacticXP(): Promise<TacticXPMap> {
  return apiFetch<TacticXPMap>('/api/pre-partita/tactic-xp')
}

export function putTacticXP(tactic_name: string, xp_level: number): Promise<void> {
  return apiFetch('/api/pre-partita/tactic-xp', {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ tactic_name, xp_level }),
  })
}

export function analyzeOpponent(params: {
  matchdetails_xml_1: string
  matchdetails_xml_2?: string
  matchdetails_xml_3?: string
  is_home: boolean
  match_type: string
  spirit: number
  confidence: number
  formation_xp: Record<string, number>
  tactic_xp?: Record<string, number>
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
