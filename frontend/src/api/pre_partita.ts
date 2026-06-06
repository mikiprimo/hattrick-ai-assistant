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

export interface LineupEntry {
  id: number
  name: string
  rating: number
}

export interface MatchResult {
  result: 'W' | 'D' | 'L'
  goals_for: number
  goals_against: number
}

export interface AnalysisResult {
  opponent: {
    team_name: string
    best_formation: string
    line_ratings: Record<string, number>
    recent_results: MatchResult[]
  }
  my_team: {
    best_formation: string
    lineup: Record<string, LineupEntry[]>
    line_ratings: Record<string, number>
  }
  tactics: {
    pressing: boolean
    attack_direction: 'center' | 'wings'
    set_pieces_taker: { name: string; set_pieces: number } | null
    attitude: 'normal' | 'defensive'
  }
  explanation: string
}

export function getPrePartitaSquad(): Promise<SquadResponse> {
  return apiFetch<SquadResponse>('/api/pre-partita/squad')
}

export function analyzeOpponent(
  players_xml: string,
  matches_xml: string,
): Promise<AnalysisResult> {
  return apiFetch<AnalysisResult>('/api/pre-partita/analyze', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ players_xml, matches_xml }),
  })
}
