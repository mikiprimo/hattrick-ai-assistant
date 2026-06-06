import { useParams, Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { getPlayer, getPlayerHistory } from '../api/players'
import { SkillLineChart } from '../components/SkillLineChart'
import { RoleRadarChart } from '../components/RoleRadarChart'

const MAIN_SKILLS = ['goalkeeper', 'defending', 'playmaking', 'winger', 'passing', 'scoring']

const SKILL_LABELS: Record<string, string> = {
  goalkeeper: 'Portiere', defending: 'Difesa', playmaking: 'Centrocampo',
  winger: 'Ala', passing: 'Passaggi', scoring: 'Attacco',
  stamina: 'Resistenza', speed: 'Velocità', set_pieces: 'Cal. piazzati',
  form: 'Forma', leadership: 'Leadership', experience: 'Esperienza', loyalty: 'Fedeltà',
}

const ALL_SKILLS = [...MAIN_SKILLS, 'stamina', 'speed', 'set_pieces', 'form', 'leadership', 'experience', 'loyalty']

const cardStyle: React.CSSProperties = {
  background: '#fff',
  borderRadius: 8,
  padding: 20,
  border: '1px solid #e5e7eb',
}

export function PlayerDetail() {
  const { id } = useParams<{ id: string }>()
  const playerId = Number(id)

  const { data: player, isLoading, error } = useQuery({
    queryKey: ['player', playerId],
    queryFn: () => getPlayer(playerId),
    enabled: !isNaN(playerId),
  })

  const { data: history = [], isLoading: loadingHistory } = useQuery({
    queryKey: ['player-history', playerId],
    queryFn: () => getPlayerHistory(playerId),
    enabled: !isNaN(playerId),
  })

  if (isNaN(playerId)) return <p style={{ color: '#ef4444' }}>ID giocatore non valido.</p>
  if (isLoading) return <p>Caricamento…</p>
  if (error) return <p style={{ color: '#ef4444' }}>Errore: {(error as Error).message}</p>
  if (!player) return null

  return (
    <div>
      <div style={{ marginBottom: 20 }}>
        <Link to="/squad" style={{ color: '#6b7280', fontSize: 13, textDecoration: 'none' }}>
          ← Rosa
        </Link>
      </div>

      <h1 style={{ marginTop: 0, marginBottom: 24 }}>
        {player.first_name} {player.last_name}
      </h1>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 24, marginBottom: 24 }}>
        <div style={cardStyle}>
          <h2 style={{ marginTop: 0, fontSize: 15, marginBottom: 12 }}>Dati</h2>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
            <tbody>
              {([
                ['Età', `${player.age} anni (${player.age_days} giorni)`],
                ['TSI', player.tsi?.toLocaleString('it-IT') ?? '—'],
                ['Forma', player.form],
                ['Resistenza', player.stamina],
                ['Stipendio', player.salary ? `€${player.salary.toLocaleString('it-IT')}` : '—'],
                ['Valore di mercato', player.market_value ? `€${player.market_value.toLocaleString('it-IT')}` : '—'],
                ['Infortuni', player.injury_days === -1 ? 'Sano' : `${player.injury_days} settimane`],
                ['Fonte dati', player.data_source ?? '—'],
              ] as [string, string | number][]).map(([label, value]) => (
                <tr key={label}>
                  <td style={{ padding: '4px 0', color: '#6b7280', width: '55%' }}>{label}</td>
                  <td style={{ padding: '4px 0', fontWeight: 500 }}>{value}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <div style={cardStyle}>
          <h2 style={{ marginTop: 0, fontSize: 15, marginBottom: 12 }}>Skill</h2>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
            <tbody>
              {ALL_SKILLS.map((sk) => (
                <tr key={sk}>
                  <td style={{ padding: '3px 0', color: '#6b7280', width: '55%' }}>
                    {SKILL_LABELS[sk] ?? sk}
                  </td>
                  <td style={{ padding: '3px 0', fontWeight: 500 }}>
                    {(player as unknown as Record<string, unknown>)[sk] as number ?? '—'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 24 }}>
        <div style={cardStyle}>
          <h2 style={{ marginTop: 0, fontSize: 15, marginBottom: 12 }}>Andamento skill</h2>
          {loadingHistory ? (
            <p style={{ fontSize: 13, color: '#6b7280' }}>Caricamento…</p>
          ) : history.length < 2 ? (
            <p style={{ fontSize: 13, color: '#6b7280' }}>
              Servono almeno 2 snapshot HRF per visualizzare l&apos;andamento.
            </p>
          ) : (
            <SkillLineChart history={history} skills={MAIN_SKILLS} />
          )}
        </div>

        <div style={cardStyle}>
          <h2 style={{ marginTop: 0, fontSize: 15, marginBottom: 12 }}>Radar ruoli</h2>
          <RoleRadarChart player={player} />
        </div>
      </div>
    </div>
  )
}
