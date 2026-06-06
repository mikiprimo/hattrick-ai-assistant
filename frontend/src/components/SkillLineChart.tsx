import {
  LineChart, Line, XAxis, YAxis, CartesianGrid,
  Tooltip, Legend, ResponsiveContainer,
} from 'recharts'
import type { SkillSnapshot } from '../api/players'

const SKILL_COLORS: Record<string, string> = {
  goalkeeper: '#ef4444',
  defending: '#f97316',
  playmaking: '#eab308',
  winger: '#22c55e',
  passing: '#06b6d4',
  scoring: '#3b82f6',
  set_pieces: '#8b5cf6',
  stamina: '#ec4899',
  speed: '#14b8a6',
  leadership: '#a855f7',
  experience: '#f59e0b',
  loyalty: '#84cc16',
  form: '#6b7280',
}

const SKILL_LABELS: Record<string, string> = {
  goalkeeper: 'Portiere', defending: 'Difesa', playmaking: 'Centrocampo',
  winger: 'Ala', passing: 'Passaggi', scoring: 'Attacco',
  set_pieces: 'Cal. piazzati', stamina: 'Resistenza', speed: 'Velocità',
  leadership: 'Leadership', experience: 'Esperienza', loyalty: 'Fedeltà', form: 'Forma',
}

interface Props {
  history: SkillSnapshot[]
  skills: string[]
}

export function SkillLineChart({ history, skills }: Props) {
  const data = history.map((s) => ({
    date: s.snapshot_date.slice(0, 10),
    ...Object.fromEntries(skills.map((sk) => [sk, (s as unknown as Record<string, unknown>)[sk]])),
  }))

  return (
    <ResponsiveContainer width="100%" height={300}>
      <LineChart data={data} margin={{ top: 5, right: 10, bottom: 5, left: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
        <XAxis dataKey="date" tick={{ fontSize: 11 }} />
        <YAxis domain={[0, 20]} tick={{ fontSize: 11 }} width={24} />
        <Tooltip />
        <Legend formatter={(value) => SKILL_LABELS[value] ?? value} />
        {skills.map((sk) => (
          <Line
            key={sk}
            type="monotone"
            dataKey={sk}
            name={sk}
            stroke={SKILL_COLORS[sk] ?? '#6b7280'}
            strokeWidth={2}
            dot={{ r: 3 }}
            activeDot={{ r: 5 }}
          />
        ))}
      </LineChart>
    </ResponsiveContainer>
  )
}
