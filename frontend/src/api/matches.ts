import { apiFetch } from './client'

export interface LineupEntry {
  line: string
  position: string
  player_id: number
  name: string
  rating: number | null
}

export interface LeagueData {
  position: number
  points: number
  played: number
  goals_for: number
  goals_against: number
}

export interface Match {
  snapshot_date: string
  season: number
  matchround: number
  lineup: LineupEntry[]
  league: LeagueData
}

export function getMatches(): Promise<Match[]> {
  return apiFetch<Match[]>('/api/matches')
}
