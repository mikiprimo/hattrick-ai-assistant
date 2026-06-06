import { useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { getTraining } from '../api/training'
import { DeltaBadge } from '../components/DeltaBadge'
import { HrfScanButton } from '../components/HrfScanButton'
import type { SkillKey } from '../api/training'

const SKILL_LABELS: Record<SkillKey, string> = {
  form: 'Forma', stamina: 'Resistenza', speed: 'Velocità',
  goalkeeper: 'Portiere', defending: 'Difesa', playmaking: 'Regia',
  winger: 'Ala', passing: 'Passaggi', scoring: 'Attacco',
  set_pieces: 'Cal. piazzati', leadership: 'Leadership',
  experience: 'Esperienza', loyalty: 'Fedeltà',
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString('it-IT', { day: 'numeric', month: 'short' })
}

const cardStyle: React.CSSProperties = {
  background: '#fff',
  borderRadius: 8,
  border: '1px solid #e5e7eb',
  padding: '12px 16px',
}

export function Training() {
  const qc = useQueryClient()
  const [selectedIdx, setSelectedIdx] = useState(0)

  const { data, isLoading, error } = useQuery({
    queryKey: ['training'],
    queryFn: getTraining,
  })

  const sessions = data?.sessions ?? []
  const session = sessions[selectedIdx]

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <h1 style={{ margin: 0 }}>Allenamento</h1>
        <HrfScanButton onScanned={() => {
          qc.invalidateQueries({ queryKey: ['training'] })
          qc.invalidateQueries({ queryKey: ['squad'] })
        }} />
      </div>

      {isLoading && <p>Caricamento…</p>}
      {error && <p style={{ color: '#ef4444' }}>Errore: {(error as Error).message}</p>}

      {!isLoading && sessions.length === 0 && (
        <p style={{ color: '#6b7280' }}>
          Servono almeno 2 file HRF importati per vedere i delta di allenamento.
        </p>
      )}

      {sessions.length > 1 && (
        <div style={{ display: 'flex', gap: 8, marginBottom: 20, flexWrap: 'wrap' }}>
          {sessions.map((s, i) => (
            <button
              key={s.synced_at}
              onClick={() => setSelectedIdx(i)}
              style={{
                padding: '4px 14px',
                borderRadius: 20,
                border: 'none',
                cursor: 'pointer',
                fontSize: 13,
                background: i === selectedIdx ? '#3b82f6' : '#e5e7eb',
                color: i === selectedIdx ? '#fff' : '#374151',
                fontWeight: i === selectedIdx ? 600 : 400,
              }}
            >
              {formatDate(s.synced_at)}
            </button>
          ))}
        </div>
      )}

      {session && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          {session.changed_players.length === 0 && session.unchanged_count > 0 && (
            <p style={{ color: '#6b7280', fontSize: 13 }}>
              Nessun giocatore ha variazioni di skill in questa sessione.
            </p>
          )}

          {session.changed_players.map((player) => {
            const changedSkills = Object.keys(player.previous_values) as SkillKey[]
            return (
              <div key={player.player_id} style={cardStyle}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <div>
                    <span style={{ fontWeight: 600, fontSize: 14 }}>
                      {player.first_name} {player.last_name}
                    </span>
                    <span style={{ color: '#9ca3af', fontSize: 12, marginLeft: 8 }}>{player.age} anni</span>
                  </div>
                  <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', justifyContent: 'flex-end' }}>
                    {changedSkills.map((skill) => (
                      <span key={skill} style={{ fontSize: 12, color: '#6b7280' }}>
                        {SKILL_LABELS[skill]}{' '}
                        <DeltaBadge value={player.deltas[skill]} />
                      </span>
                    ))}
                  </div>
                </div>
                <div style={{ display: 'flex', gap: 20, marginTop: 8, flexWrap: 'wrap' }}>
                  {changedSkills.map((skill) => (
                    <div key={skill} style={{ fontSize: 12 }}>
                      <span style={{ color: '#9ca3af' }}>{SKILL_LABELS[skill]}: </span>
                      <span style={{ color: '#6b7280' }}>{player.previous_values[skill]}</span>
                      <span style={{ color: '#9ca3af' }}> → </span>
                      <span style={{ color: '#16a34a', fontWeight: 600 }}>{player.current_values[skill]}</span>
                    </div>
                  ))}
                </div>
              </div>
            )
          })}

          {session.unchanged_count > 0 && (
            <p style={{ fontSize: 13, color: '#9ca3af', textAlign: 'center', margin: '4px 0 0' }}>
              {session.unchanged_count} giocator{session.unchanged_count === 1 ? 'e' : 'i'} senza variazioni
            </p>
          )}
        </div>
      )}
    </div>
  )
}
