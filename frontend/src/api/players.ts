import { apiFetch } from './client'

export interface PlayerDetail {
  id: number
  first_name: string
  last_name: string
  age: number
  age_days: number
  tsi: number
  form: number
  stamina: number
  speed: number
  injury_days: number
  salary: number
  goalkeeper: number
  defending: number
  playmaking: number
  winger: number
  passing: number
  scoring: number
  set_pieces: number
  leadership: number
  experience: number
  loyalty: number
  market_value: number
  speciality: string | null
  last_match_rating: number | null
  transfer_listed: boolean
  country_id: number | null
  homegrown: boolean
  data_source: string
}

export interface SkillSnapshot {
  snapshot_date: string
  form: number
  stamina: number
  speed: number
  goalkeeper: number
  defending: number
  playmaking: number
  winger: number
  passing: number
  scoring: number
  set_pieces: number
  leadership: number
  experience: number
  loyalty: number
}

export function getPlayer(id: number): Promise<PlayerDetail> {
  return apiFetch<PlayerDetail>(`/api/players/${id}`)
}

export function getPlayerHistory(id: number): Promise<SkillSnapshot[]> {
  return apiFetch<SkillSnapshot[]>(`/api/players/${id}/history`)
}
