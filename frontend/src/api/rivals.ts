import { apiFetch } from './client'

export interface RivalTeam {
  team_id: number
  team_name: string
  league_series: string
  season: number
  updated_at: string | null
  player_count: number
  manual_ratings: { defense: number | null; midfield: number | null; attack: number | null } | null
}

export function getRivals(): Promise<RivalTeam[]> {
  return apiFetch<RivalTeam[]>('/api/rivals')
}

export function createRival(body: {
  team_id: number; team_name: string; league_series: string; season: number
}): Promise<RivalTeam> {
  return apiFetch<RivalTeam>('/api/rivals', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
}

export function importRivalXml(team_id: number, xml: string): Promise<{ players_imported: number }> {
  return apiFetch(`/api/rivals/${team_id}/import-xml`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ xml }),
  })
}

export function setRivalRatings(
  team_id: number,
  ratings: { defense?: number; midfield?: number; attack?: number }
): Promise<{ team_id: number; defense: number; midfield: number; attack: number }> {
  return apiFetch(`/api/rivals/${team_id}/ratings`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(ratings),
  })
}

export function deleteRival(team_id: number): Promise<{ deleted: number }> {
  return apiFetch(`/api/rivals/${team_id}`, { method: 'DELETE' })
}
