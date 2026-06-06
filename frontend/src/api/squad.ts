import { apiFetch } from './client'

export interface Player {
  id: number
  first_name: string
  last_name: string
  age: number
  age_days: number
  tsi: number
  form: number
  stamina: number
  injury_days: number
  salary: number
  goalkeeper: number
  defending: number
  playmaking: number
  winger: number
  passing: number
  scoring: number
  speed: number
  leadership: number
  experience: number
  loyalty: number
  market_value: number
  speciality: string | null
  last_match_rating: number | null
  transfer_listed: boolean
  data_source: string
}

export function getSquad(): Promise<Player[]> {
  return apiFetch<Player[]>('/api/squad')
}
