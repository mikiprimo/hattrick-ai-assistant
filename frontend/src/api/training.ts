import { apiFetch } from './client'

export type SkillKey =
  | 'form' | 'stamina' | 'speed' | 'goalkeeper' | 'defending' | 'playmaking'
  | 'winger' | 'passing' | 'scoring' | 'set_pieces' | 'leadership' | 'experience' | 'loyalty'

export interface TrainingPlayer {
  player_id: number
  first_name: string
  last_name: string
  age: number
  deltas: Record<SkillKey, number>
  previous_values: Partial<Record<SkillKey, number>>
  current_values: Partial<Record<SkillKey, number>>
}

export interface TrainingSession {
  synced_at: string
  previous_sync: string
  changed_players: TrainingPlayer[]
  unchanged_count: number
}

export interface TrainingResponse {
  sessions: TrainingSession[]
}

export function getTraining(): Promise<TrainingResponse> {
  return apiFetch<TrainingResponse>('/api/training')
}
