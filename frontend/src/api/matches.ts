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

export interface LatestLeague {
  season: number
  matchround: number
  league_position: number
  league_points: number
  league_played: number
  league_goals_for: number
  league_goals_against: number
  league_series: string
  snapshot_date: string
}

export function getMatches(): Promise<Match[]> {
  return apiFetch<Match[]>('/api/matches')
}

export function getLatestLeague(): Promise<LatestLeague | null> {
  return apiFetch<LatestLeague | null>('/api/matches/latest-league')
}
