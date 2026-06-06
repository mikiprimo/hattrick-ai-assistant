import {
  RadarChart, Radar, PolarGrid, PolarAngleAxis,
  PolarRadiusAxis, ResponsiveContainer, Tooltip,
} from 'recharts'
import type { PlayerDetail } from '../api/players'

interface RoleScore {
  role: string
  score: number
}

function computeRoles(p: PlayerDetail): RoleScore[] {
  return [
    {
      role: 'Portiere',
      score: Math.round((p.goalkeeper * 0.85 + p.stamina * 0.10 + p.set_pieces * 0.05) * 10) / 10,
    },
    {
      role: 'Difensore',
      score: Math.round((p.defending * 0.50 + p.playmaking * 0.20 + p.passing * 0.15 + p.stamina * 0.15) * 10) / 10,
    },
    {
      role: 'Terzino',
      score: Math.round((p.defending * 0.35 + p.winger * 0.35 + p.passing * 0.15 + p.stamina * 0.15) * 10) / 10,
    },
    {
      role: 'Centrocampista',
      score: Math.round((p.playmaking * 0.50 + p.passing * 0.20 + p.defending * 0.15 + p.stamina * 0.15) * 10) / 10,
    },
    {
      role: 'Ala',
      score: Math.round((p.winger * 0.50 + p.passing * 0.20 + p.scoring * 0.15 + p.stamina * 0.15) * 10) / 10,
    },
    {
      role: 'Attaccante',
      score: Math.round((p.scoring * 0.55 + p.winger * 0.20 + p.passing * 0.10 + p.stamina * 0.15) * 10) / 10,
    },
  ]
}

interface Props {
  player: PlayerDetail
}

export function RoleRadarChart({ player }: Props) {
  const data = computeRoles(player)

  return (
    <ResponsiveContainer width="100%" height={300}>
      <RadarChart data={data} margin={{ top: 10, right: 30, bottom: 10, left: 30 }}>
        <PolarGrid />
        <PolarAngleAxis dataKey="role" tick={{ fontSize: 11 }} />
        <PolarRadiusAxis domain={[0, 20]} tickCount={5} tick={{ fontSize: 9 }} />
        <Tooltip formatter={(value) => [value, 'Punteggio']} />
        <Radar
          dataKey="score"
          stroke="#3b82f6"
          fill="#3b82f6"
          fillOpacity={0.25}
        />
      </RadarChart>
    </ResponsiveContainer>
  )
}
