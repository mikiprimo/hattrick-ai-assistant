import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { getPrePartitaSquad, analyzeOpponent } from '../api/pre_partita'
import type { AnalysisResult, SquadPlayer } from '../api/pre_partita'

const card: React.CSSProperties = {
  background: '#fff',
  borderRadius: 8,
  border: '1px solid #e5e7eb',
  padding: '12px 16px',
  marginBottom: 12,
}

const LINE_LABELS: Record<string, string> = {
  goalkeeper: 'Portiere',
  defense: 'Difesa',
  midfield: 'Centrocampo',
  attack: 'Attacco',
}

const RESULT_STYLE: Record<string, React.CSSProperties> = {
  W: { background: '#dcfce7', color: '#16a34a' },
  D: { background: '#fef9c3', color: '#854d0e' },
  L: { background: '#fee2e2', color: '#dc2626' },
}

function LineBars({
  myRatings,
  oppRatings,
}: {
  myRatings: Record<string, number>
  oppRatings: Record<string, number>
}) {
  const lines = ['goalkeeper', 'defense', 'midfield', 'attack']
  const max = 20
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
      {lines.map(line => {
        const my = myRatings[line] ?? 0
        const opp = oppRatings[line] ?? 0
        return (
          <div key={line}>
            <div style={{ fontSize: 10, color: '#6b7280', marginBottom: 2 }}>
              {LINE_LABELS[line]} {my > opp ? '✅' : ''}
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
              <span style={{ width: 36, textAlign: 'right', fontSize: 11, color: '#1d4ed8', fontWeight: my > opp ? 600 : 400 }}>
                {my.toFixed(1)}
              </span>
              <div style={{ flex: 1, height: 12, background: '#e5e7eb', borderRadius: 6, position: 'relative', overflow: 'hidden' }}>
                <div style={{ position: 'absolute', left: 0, top: 0, width: `${(my / max) * 100}%`, height: '100%', background: '#3b82f6', borderRadius: '6px 0 0 6px', opacity: 0.8 }} />
                <div style={{ position: 'absolute', right: 0, top: 0, width: `${(opp / max) * 100}%`, height: '100%', background: '#ef4444', borderRadius: '0 6px 6px 0', opacity: 0.5 }} />
              </div>
              <span style={{ width: 36, fontSize: 11, color: '#dc2626' }}>{opp.toFixed(1)}</span>
            </div>
          </div>
        )
      })}
      <div style={{ display: 'flex', gap: 10, marginTop: 2, fontSize: 9, color: '#6b7280' }}>
        <span><span style={{ color: '#3b82f6' }}>■</span> Tu</span>
        <span><span style={{ color: '#ef4444' }}>■</span> Avversario</span>
      </div>
    </div>
  )
}

function TacticBadge({ label, value }: { label: string; value: string }) {
  return (
    <span style={{
      fontSize: 10, padding: '3px 8px', borderRadius: 12,
      background: '#eff6ff', color: '#1d4ed8',
    }}>
      {label}: <strong>{value}</strong>
    </span>
  )
}

export function PrePartita() {
  const [playersXml, setPlayersXml] = useState('')
  const [matchesXml, setMatchesXml] = useState('')
  const [result, setResult] = useState<AnalysisResult | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const { data: squadData } = useQuery({
    queryKey: ['pre-partita-squad'],
    queryFn: getPrePartitaSquad,
  })

  async function handleAnalyze() {
    if (!playersXml.trim()) return
    setLoading(true)
    setError(null)
    try {
      const res = await analyzeOpponent(playersXml, matchesXml)
      setResult(res)
    } catch (e) {
      setError((e as Error).message)
    } finally {
      setLoading(false)
    }
  }

  const myByLine = result
    ? (['goalkeeper', 'defense', 'midfield', 'attack'] as const).reduce(
        (acc, line) => {
          const entries = result.my_team.lineup[line] ?? []
          if (entries.length) acc[line] = entries.map(e => e.name).join(', ')
          return acc
        },
        {} as Record<string, string>,
      )
    : {}

  const squadByRole = (squadData?.players ?? []).reduce(
    (acc: Record<string, SquadPlayer[]>, p) => {
      const role = p.injury_days >= 0 ? 'Infortunati' : p.best_role
      if (!acc[role]) acc[role] = []
      acc[role].push(p)
      return acc
    },
    {},
  )

  return (
    <div>
      <h1 style={{ margin: '0 0 20px' }}>Pre-Partita</h1>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16, alignItems: 'start' }}>

        {/* LEFT */}
        <div>
          {/* Opponent input */}
          <div style={card}>
            <div style={{ fontWeight: 600, marginBottom: 10 }}>⚔️ Dati avversario</div>

            <div style={{ marginBottom: 8 }}>
              <div style={{ fontSize: 12, color: '#6b7280', marginBottom: 4 }}>players.xml</div>
              <textarea
                value={playersXml}
                onChange={e => setPlayersXml(e.target.value)}
                placeholder="Incolla qui il players.xml dell'avversario..."
                rows={5}
                style={{ width: '100%', fontFamily: 'monospace', fontSize: 11, border: '1px solid #e5e7eb', borderRadius: 4, padding: 8, resize: 'vertical', boxSizing: 'border-box' }}
              />
            </div>

            <div style={{ marginBottom: 12 }}>
              <div style={{ fontSize: 12, color: '#6b7280', marginBottom: 4 }}>matches.xml (opzionale)</div>
              <textarea
                value={matchesXml}
                onChange={e => setMatchesXml(e.target.value)}
                placeholder="Incolla qui il matches.xml dell'avversario (opzionale)..."
                rows={5}
                style={{ width: '100%', fontFamily: 'monospace', fontSize: 11, border: '1px solid #e5e7eb', borderRadius: 4, padding: 8, resize: 'vertical', boxSizing: 'border-box' }}
              />
            </div>

            <button
              onClick={handleAnalyze}
              disabled={loading || !playersXml.trim()}
              style={{
                width: '100%', padding: '8px 0', background: loading ? '#93c5fd' : '#3b82f6',
                color: '#fff', border: 'none', borderRadius: 6, cursor: loading ? 'not-allowed' : 'pointer',
                fontWeight: 600, fontSize: 14,
              }}
            >
              {loading ? 'Analisi in corso…' : 'Analizza avversario'}
            </button>

            {error && <p style={{ color: '#ef4444', fontSize: 12, marginTop: 8 }}>{error}</p>}
          </div>

          {/* Opponent card */}
          {result && (
            <div style={card}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
                <strong>{result.opponent.team_name}</strong>
                <span style={{ fontSize: 11, color: '#6b7280' }}>
                  Formazione ottimale: <strong>{result.opponent.best_formation}</strong>
                </span>
              </div>

              {(['goalkeeper', 'defense', 'midfield', 'attack'] as const).map(line => {
                const rating = result.opponent.line_ratings[line]
                const pct = (rating / 20) * 100
                return (
                  <div key={line} style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
                    <span style={{ width: 90, fontSize: 11, color: '#6b7280' }}>{LINE_LABELS[line]}</span>
                    <div style={{ flex: 1, height: 8, background: '#e5e7eb', borderRadius: 4 }}>
                      <div style={{ width: `${pct}%`, height: '100%', background: '#ef4444', borderRadius: 4 }} />
                    </div>
                    <span style={{ width: 28, fontSize: 11, textAlign: 'right', color: '#374151' }}>{rating.toFixed(1)}</span>
                  </div>
                )
              })}

              {result.opponent.recent_results.length > 0 && (
                <div style={{ marginTop: 8 }}>
                  <div style={{ fontSize: 11, color: '#6b7280', marginBottom: 4 }}>Forma recente:</div>
                  <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap' }}>
                    {result.opponent.recent_results.map((r, i) => (
                      <span key={i} style={{ ...RESULT_STYLE[r.result], fontSize: 10, padding: '2px 6px', borderRadius: 4 }}>
                        {r.result} {r.goals_for}-{r.goals_against}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

          {/* My squad */}
          {squadData && squadData.players.length > 0 && (
            <div style={card}>
              <div style={{ fontWeight: 600, marginBottom: 8 }}>👥 Mia rosa</div>
              {Object.entries(squadByRole).map(([role, players]) => (
                <div key={role} style={{ marginBottom: 6 }}>
                  <div style={{ fontSize: 11, color: '#6b7280', marginBottom: 2 }}>{role}</div>
                  {players.map(p => (
                    <div key={p.id} style={{
                      display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                      fontSize: 11, padding: '2px 6px', borderRadius: 3,
                      background: p.injury_days >= 0 ? '#fef2f2' : '#eff6ff',
                      marginBottom: 2, opacity: p.injury_days >= 0 ? 0.5 : 1,
                    }}>
                      <span>{p.name} {p.injury_days >= 0 ? '🤕' : ''}</span>
                      <span style={{ color: '#6b7280' }}>Form {p.form} · Stam {p.stamina}</span>
                    </div>
                  ))}
                </div>
              ))}
            </div>
          )}
        </div>

        {/* RIGHT: Piano di gara */}
        <div style={{ ...card, border: result ? '2px solid #3b82f6' : '1px solid #e5e7eb' }}>
          {!result ? (
            <div style={{ textAlign: 'center', padding: '40px 0', color: '#9ca3af' }}>
              <div style={{ fontSize: 32, marginBottom: 8 }}>🎯</div>
              <div>Incolla i dati dell'avversario e clicca "Analizza"</div>
            </div>
          ) : (
            <>
              <div style={{ color: '#1d4ed8', fontWeight: 700, marginBottom: 12 }}>🎯 Piano di Gara</div>

              {/* Formazione */}
              <div style={{ background: '#eff6ff', borderRadius: 6, padding: 10, marginBottom: 12 }}>
                <div style={{ fontSize: 12, fontWeight: 600, color: '#1d4ed8', marginBottom: 6 }}>
                  Formazione: {result.my_team.best_formation}
                </div>
                {(['goalkeeper', 'defense', 'midfield', 'attack'] as const).map(line =>
                  myByLine[line] ? (
                    <div key={line} style={{ fontSize: 11, color: '#1e40af', marginBottom: 2, textAlign: 'center' }}>
                      {myByLine[line]}
                    </div>
                  ) : null,
                )}
              </div>

              {/* Confronto reparti */}
              <div style={{ marginBottom: 12 }}>
                <div style={{ fontSize: 12, fontWeight: 600, marginBottom: 8 }}>Confronto reparti</div>
                <LineBars myRatings={result.my_team.line_ratings} oppRatings={result.opponent.line_ratings} />
              </div>

              {/* Tattica */}
              <div style={{ marginBottom: 12 }}>
                <div style={{ fontSize: 12, fontWeight: 600, marginBottom: 6 }}>Impostazioni tattiche</div>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                  <TacticBadge label="Pressing" value={result.tactics.pressing ? 'Sì' : 'No'} />
                  <TacticBadge label="Attacco" value={result.tactics.attack_direction === 'center' ? 'Centro' : 'Fasce'} />
                  {result.tactics.set_pieces_taker && (
                    <TacticBadge
                      label="CP"
                      value={`${result.tactics.set_pieces_taker.name} (SP ${result.tactics.set_pieces_taker.set_pieces})`}
                    />
                  )}
                  <TacticBadge label="Att." value={result.tactics.attitude === 'normal' ? 'Normale' : 'Difensivo'} />
                </div>
              </div>

              {/* Spiegazione */}
              <div style={{ background: '#f8fafc', borderLeft: '3px solid #3b82f6', padding: 10, borderRadius: '0 6px 6px 0' }}>
                <div style={{ fontSize: 11, fontWeight: 600, marginBottom: 4 }}>💡 Analisi</div>
                <div style={{ fontSize: 11, color: '#4b5563', lineHeight: 1.6 }}>{result.explanation}</div>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  )
}
