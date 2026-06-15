import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts'
import {
  getSeasonalCurrent, getSeasonalHistory, saveSeasonalObjective,
  getSeasonalStatus, getAnalysisYouth, getAnalysisMaintain, getAnalysisPromote,
  type SeasonalObjective,
} from '../api/seasonal'
import { getLatestLeague } from '../api/matches'
import { useState, useEffect } from 'react'

type Strategy = 'promote' | 'maintain' | 'youth'

const STRATEGY_META: Record<Strategy, { label: string; color: string; icon: string }> = {
  promote:  { label: 'Promozione',       color: '#f59e0b', icon: '🏆' },
  maintain: { label: 'Mantenimento',     color: '#3b82f6', icon: '🛡️' },
  youth:    { label: 'Sviluppo Giovani', color: '#10b981', icon: '🌱' },
}

const STATUS_STYLE: Record<string, { bg: string; text: string; label: string }> = {
  on_track:  { bg: '#d1fae5', text: '#065f46', label: 'In linea ✓' },
  at_risk:   { bg: '#fef3c7', text: '#92400e', label: 'A rischio ⚠' },
  off_track: { bg: '#fee2e2', text: '#991b1b', label: 'Fuori strada ✗' },
}

const sec: React.CSSProperties = {
  background: '#fff', borderRadius: 8, padding: 20, marginBottom: 16,
  boxShadow: '0 1px 3px rgba(0,0,0,.08)',
}

const LINE_IT: Record<string, string> = {
  goalkeeper: 'Portiere', defense: 'Difesa', midfield: 'Centrocampo', attack: 'Attacco',
}

const SKILL_LABELS: Record<string, string> = {
  goalkeeper: 'Parate', defending: 'Difesa', playmaking: 'Regia',
  scoring: 'Attacco', passing: 'Passaggi', winger: 'Cross',
}

export function Stagione() {
  const qc = useQueryClient()
  const currentQ = useQuery({ queryKey: ['seasonal-current'], queryFn: getSeasonalCurrent })
  const historyQ = useQuery({ queryKey: ['seasonal-history'], queryFn: getSeasonalHistory })
  const latestQ  = useQuery({ queryKey: ['latest-league'],   queryFn: getLatestLeague })
  const statusQ  = useQuery({ queryKey: ['seasonal-status'], queryFn: getSeasonalStatus })

  const obj = currentQ.data?.objective
  const [strategy, setStrategy] = useState<Strategy>('maintain')

  useEffect(() => {
    if (!currentQ.isFetched || !latestQ.isFetched) return
    const hrf = latestQ.data
    if (obj && (!hrf || obj.season === hrf.season)) {
      setStrategy(obj.strategy as Strategy)
    }
  }, [currentQ.isFetched, latestQ.isFetched, obj, latestQ.data])

  const saveMut = useMutation({
    mutationFn: (s: Strategy) => saveSeasonalObjective({
      season: latestQ.data?.season ?? obj?.season ?? 0,
      league_position: latestQ.data?.league_position ?? obj?.league_position ?? 0,
      league_points: latestQ.data?.league_points ?? obj?.league_points ?? 0,
      league_series: latestQ.data?.league_series ?? obj?.league_series ?? '',
      budget_manual: obj?.budget_manual ?? 0,
      strategy: s,
      notes: obj?.notes ?? '',
    }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['seasonal-current'] })
      qc.invalidateQueries({ queryKey: ['seasonal-status'] })
    },
  })

  const handleStrategyChange = (s: Strategy) => {
    setStrategy(s)
    saveMut.mutate(s)
  }

  const status = statusQ.data
  const statusStyle = STATUS_STYLE[status?.status ?? 'on_track']

  const chartData = (status?.history ?? []).map(h => ({
    round: h.matchround,
    punti: h.points,
    obiettivo: strategy === 'promote' ? Math.round((26 / 14) * h.matchround)
             : strategy === 'maintain' ? Math.round((16 / 14) * h.matchround)
             : undefined,
  }))

  return (
    <div style={{ maxWidth: 800, margin: '0 auto' }}>
      <h2 style={{ fontSize: 20, fontWeight: 700, marginBottom: 20 }}>Stagione</h2>

      {/* ZONA 1: Selezione obiettivo */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 12, marginBottom: 16 }}>
        {(Object.entries(STRATEGY_META) as [Strategy, typeof STRATEGY_META[Strategy]][]).map(([key, meta]) => {
          const active = strategy === key
          const isStatus = active && status
          const ss = isStatus ? STATUS_STYLE[status.status] : null
          return (
            <button key={key} onClick={() => handleStrategyChange(key)}
              style={{
                padding: 16, borderRadius: 10, cursor: 'pointer', textAlign: 'left',
                border: `2px solid ${active ? meta.color : '#e5e7eb'}`,
                background: active ? '#fafafa' : '#fff',
                boxShadow: active ? `0 0 0 3px ${meta.color}22` : 'none',
              }}>
              <div style={{ fontSize: 22, marginBottom: 4 }}>{meta.icon}</div>
              <div style={{ fontWeight: 700, fontSize: 14, color: active ? meta.color : '#374151' }}>
                {meta.label}
              </div>
              {isStatus && ss && (
                <div style={{ marginTop: 6, fontSize: 11, background: ss.bg,
                  color: ss.text, borderRadius: 4, padding: '2px 6px', display: 'inline-block' }}>
                  {ss.label}
                </div>
              )}
            </button>
          )
        })}
      </div>

      {/* ZONA 2: Grafico andamento */}
      {status && status.played > 0 && (
        <div style={sec}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 16 }}>
            <div>
              <h3 style={{ margin: 0, fontSize: 15 }}>Andamento stagionale</h3>
              <p style={{ margin: '4px 0 0', fontSize: 13, color: '#6b7280' }}>
                Giornata {status.played}/14 · {status.current_position}° posto · {status.current_points} pt
                · Proiezione finale: <strong>{status.projected_points.toFixed(0)} pt</strong>
              </p>
            </div>
            <div style={{ padding: '4px 10px', borderRadius: 6, fontSize: 12, fontWeight: 600,
              background: statusStyle.bg, color: statusStyle.text }}>
              {statusStyle.label}
            </div>
          </div>

          <ResponsiveContainer width="100%" height={180}>
            <LineChart data={chartData} margin={{ top: 4, right: 12, bottom: 4, left: 0 }}>
              <XAxis dataKey="round" label={{ value: 'Giornata', position: 'insideBottom', offset: -2, fontSize: 11 }}
                tick={{ fontSize: 11 }} />
              <YAxis tick={{ fontSize: 11 }} domain={[0, 42]} />
              <Tooltip formatter={(v, name) =>
                [v, name === 'punti' ? 'Punti reali' : 'Obiettivo']} />
              <Line type="monotone" dataKey="punti" stroke="#3b82f6" strokeWidth={2} dot={{ r: 3 }} />
              {strategy !== 'youth' && (
                <Line type="monotone" dataKey="obiettivo" stroke="#d1d5db"
                  strokeDasharray="4 4" dot={false} strokeWidth={1.5} />
              )}
            </LineChart>
          </ResponsiveContainer>

          {status.suggested_strategy && (
            <div style={{ marginTop: 12, background: '#fff7ed', border: '1px solid #fed7aa',
              borderRadius: 6, padding: '10px 14px', fontSize: 13, color: '#9a3412' }}>
              ⚠ {status.message}
              {' '}
              <button onClick={() => handleStrategyChange(status.suggested_strategy as Strategy)}
                style={{ background: '#ea580c', color: '#fff', border: 'none', borderRadius: 4,
                  padding: '3px 10px', cursor: 'pointer', fontSize: 12, marginLeft: 8 }}>
                Passa a {STRATEGY_META[status.suggested_strategy as Strategy]?.label}
              </button>
            </div>
          )}
          {!status.suggested_strategy && (
            <p style={{ margin: '10px 0 0', fontSize: 13, color: '#6b7280' }}>{status.message}</p>
          )}
        </div>
      )}

      {/* ZONA 3: Analisi per obiettivo */}
      {strategy === 'youth'    && <YouthSection />}
      {strategy === 'maintain' && <MaintainSection />}
      {strategy === 'promote'  && <PromoteSection />}

      <PreviousSeasonsTable historyQ={historyQ} />
    </div>
  )
}

function YouthSection() {
  const q = useQuery({ queryKey: ['analysis-youth'], queryFn: getAnalysisYouth })
  if (q.isLoading) return <div style={{ textAlign: 'center', padding: 32, color: '#9ca3af' }}>Caricamento...</div>
  const players = q.data ?? []
  if (players.length === 0) return (
    <div style={{ ...sec, color: '#6b7280', textAlign: 'center' }}>
      Nessun giocatore under-24 in rosa.
    </div>
  )
  return (
    <div style={sec}>
      <h3 style={{ margin: '0 0 16px', fontSize: 15 }}>Giovani da valorizzare (under-24)</h3>
      <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
        <thead>
          <tr style={{ borderBottom: '2px solid #e5e7eb' }}>
            {['Giocatore', 'Età', 'Skill principale', 'Potenziale', 'Progressi'].map(h => (
              <th key={h} style={{ textAlign: 'left', padding: '6px 8px', color: '#6b7280', fontWeight: 600 }}>{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {players.map((p, i) => (
            <tr key={p.player_id} style={{ borderBottom: '1px solid #f3f4f6',
              background: i === 0 ? '#f0fdf4' : undefined }}>
              <td style={{ padding: '8px', fontWeight: 600 }}>{p.name}</td>
              <td style={{ padding: '8px', color: '#6b7280' }}>{p.age} anni</td>
              <td style={{ padding: '8px' }}>
                <span style={{ fontWeight: 600 }}>{SKILL_LABELS[p.primary_skill] ?? p.primary_skill}</span>
                {' '}<span style={{ color: '#6b7280', fontSize: 12 }}>({p.primary_skill_label})</span>
              </td>
              <td style={{ padding: '8px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                  <div style={{ width: 60, height: 6, background: '#e5e7eb', borderRadius: 3, overflow: 'hidden' }}>
                    <div style={{ width: `${(p.potential_score / 20) * 100}%`, height: '100%', background: '#10b981', borderRadius: 3 }} />
                  </div>
                  <span style={{ fontSize: 12, color: '#6b7280' }}>{p.potential_score.toFixed(1)}</span>
                </div>
              </td>
              <td style={{ padding: '8px' }}>
                {p.skill_delta > 0
                  ? <span style={{ color: '#059669', fontWeight: 600 }}>+{p.skill_delta} ↑</span>
                  : <span style={{ color: '#9ca3af' }}>—</span>}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

function MaintainSection() {
  const q = useQuery({ queryKey: ['analysis-maintain'], queryFn: getAnalysisMaintain })
  if (q.isLoading) return <div style={{ textAlign: 'center', padding: 32, color: '#9ca3af' }}>Caricamento...</div>
  const d = q.data
  if (!d || 'error' in d) return <div style={{ ...sec, color: '#dc2626' }}>{(d as Record<string, string> | undefined)?.error ?? 'Errore analisi'}</div>
  return (
    <div style={sec}>
      <h3 style={{ margin: '0 0 12px', fontSize: 15 }}>Analisi rosa — Mantenimento</h3>
      <div style={{ display: 'flex', gap: 12, marginBottom: 16, flexWrap: 'wrap' }}>
        <div style={{ background: '#eff6ff', borderRadius: 8, padding: '10px 16px' }}>
          <div style={{ fontSize: 11, color: '#6b7280', marginBottom: 2 }}>Schema consigliato</div>
          <div style={{ fontWeight: 700, fontSize: 18, color: '#1d4ed8' }}>{d.best_formation}</div>
        </div>
        <div style={{ background: '#fff1f2', borderRadius: 8, padding: '10px 16px' }}>
          <div style={{ fontSize: 11, color: '#6b7280', marginBottom: 2 }}>Reparto più debole</div>
          <div style={{ fontWeight: 700, fontSize: 18, color: '#dc2626' }}>{d.weakest_sector_label}</div>
          <div style={{ fontSize: 12, color: '#9ca3af' }}>rating {d.weakest_rating.toFixed(1)}</div>
        </div>
      </div>

      <div style={{ display: 'grid', gap: 8 }}>
        {(['goalkeeper', 'defense', 'midfield', 'attack'] as const).map(line => {
          const val = d.line_ratings[line] ?? 0
          const isWeak = line === d.weakest_sector
          return (
            <div key={line}>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 13, marginBottom: 3 }}>
                <span style={{ color: isWeak ? '#dc2626' : '#374151', fontWeight: isWeak ? 600 : 400 }}>
                  {LINE_IT[line]}
                </span>
                <span style={{ color: '#6b7280' }}>{val.toFixed(1)}</span>
              </div>
              <div style={{ height: 6, background: '#e5e7eb', borderRadius: 3, overflow: 'hidden' }}>
                <div style={{ width: `${(val / 12) * 100}%`, height: '100%', borderRadius: 3,
                  background: isWeak ? '#dc2626' : '#3b82f6' }} />
              </div>
            </div>
          )
        })}
      </div>
      <p style={{ margin: '12px 0 0', fontSize: 13, color: '#374151' }}>{d.message}</p>
    </div>
  )
}

function PromoteSection() {
  const q = useQuery({ queryKey: ['analysis-promote'], queryFn: getAnalysisPromote })
  if (q.isLoading) return <div style={{ textAlign: 'center', padding: 32, color: '#9ca3af' }}>Caricamento...</div>
  const d = q.data
  if (!d || 'error' in d) return <div style={{ ...sec, color: '#dc2626' }}>{(d as Record<string, string> | undefined)?.error ?? 'Errore analisi'}</div>

  return (
    <div>
      <div style={sec}>
        <h3 style={{ margin: '0 0 4px', fontSize: 15 }}>Analisi promozione</h3>
        <p style={{ margin: '0 0 16px', fontSize: 13, color: '#6b7280' }}>
          Schema consigliato: <strong>{d.best_formation}</strong>
        </p>
        {d.rival_avg ? (
          <div style={{ display: 'grid', gap: 10 }}>
            {(['goalkeeper', 'defense', 'midfield', 'attack'] as const)
              .filter(line => d.rival_avg![line] !== undefined)
              .map(line => {
              const mine = d.my_ratings[line] ?? 0
              const rival = d.rival_avg![line] ?? 0
              const gap = d.gaps[line] ?? 0
              return (
                <div key={line}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 13, marginBottom: 4 }}>
                    <span style={{ color: '#374151' }}>{LINE_IT[line]}</span>
                    <span>
                      <span style={{ fontWeight: 600, color: gap >= 0 ? '#059669' : '#dc2626' }}>
                        {mine.toFixed(1)}
                      </span>
                      <span style={{ color: '#9ca3af', margin: '0 6px' }}>vs</span>
                      <span style={{ color: '#6b7280' }}>{rival.toFixed(1)}</span>
                      <span style={{ marginLeft: 8, fontSize: 12,
                        color: gap >= 0 ? '#059669' : '#dc2626' }}>
                        {gap >= 0 ? `+${gap.toFixed(1)}` : gap.toFixed(1)}
                      </span>
                    </span>
                  </div>
                  <div style={{ height: 6, background: '#e5e7eb', borderRadius: 3, overflow: 'hidden' }}>
                    <div style={{ width: `${(mine / 12) * 100}%`, height: '100%',
                      background: gap >= 0 ? '#3b82f6' : '#ef4444', borderRadius: 3 }} />
                  </div>
                </div>
              )
            })}
          </div>
        ) : (
          <p style={{ color: '#9ca3af', fontSize: 13 }}>{d.message}</p>
        )}
      </div>

      {d.needed_skills.length > 0 && (
        <div style={sec}>
          <h3 style={{ margin: '0 0 12px', fontSize: 15 }}>Rinforzi necessari</h3>
          {d.needed_skills.map(ns => (
            <div key={ns.sector} style={{ display: 'flex', justifyContent: 'space-between',
              alignItems: 'center', padding: '8px 0', borderBottom: '1px solid #f3f4f6' }}>
              <span style={{ fontWeight: 600, fontSize: 13 }}>{ns.sector_label}</span>
              <span style={{ fontSize: 13, color: '#6b7280' }}>
                gap <span style={{ color: '#dc2626' }}>{ns.gap.toFixed(1)}</span> — cerca almeno{' '}
                <strong>{ns.min_skill_label}</strong> ({ns.min_skill_value})
              </span>
            </div>
          ))}
        </div>
      )}

      {d.sell_candidates.length > 0 && (
        <div style={sec}>
          <h3 style={{ margin: '0 0 12px', fontSize: 15 }}>Possibili cessioni</h3>
          {d.sell_candidates.map(p => (
            <div key={p.player_id} style={{ display: 'flex', justifyContent: 'space-between',
              alignItems: 'center', padding: '6px 0', borderBottom: '1px solid #f3f4f6', fontSize: 13 }}>
              <span style={{ fontWeight: 600 }}>{p.name}</span>
              <span style={{ color: '#6b7280' }}>
                {p.age} anni · €{p.salary.toLocaleString()} · contributo {p.contribution.toFixed(1)}
              </span>
            </div>
          ))}
        </div>
      )}

      {d.rival_avg && (
        <p style={{ fontSize: 13, color: '#374151', padding: '0 4px' }}>{d.message}</p>
      )}
    </div>
  )
}

function PreviousSeasonsTable({ historyQ }: { historyQ: ReturnType<typeof useQuery<{ history: SeasonalObjective[] }>> }) {
  const history = historyQ.data?.history ?? []
  if (history.length <= 1) return null
  const STRATEGY_LABELS: Record<string, string> = {
    promote: 'Promozione', maintain: 'Mantenimento', youth: 'Sviluppo giovani',
  }
  return (
    <div style={{ ...sec, marginTop: 8 }}>
      <h3 style={{ margin: '0 0 16px', fontSize: 15 }}>Stagioni precedenti</h3>
      <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
        <thead>
          <tr style={{ borderBottom: '2px solid #e5e7eb' }}>
            {['Stagione', 'Pos.', 'Punti', 'Serie', 'Obiettivo'].map(h => (
              <th key={h} style={{ textAlign: 'left', padding: '6px 8px', color: '#6b7280' }}>{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {history.slice(1).map((r: SeasonalObjective) => (
            <tr key={r.id} style={{ borderBottom: '1px solid #f3f4f6' }}>
              <td style={{ padding: '6px 8px', fontWeight: 600 }}>{r.season}</td>
              <td style={{ padding: '6px 8px' }}>{r.league_position}</td>
              <td style={{ padding: '6px 8px' }}>{r.league_points}</td>
              <td style={{ padding: '6px 8px' }}>{r.league_series}</td>
              <td style={{ padding: '6px 8px' }}>{STRATEGY_LABELS[r.strategy] ?? r.strategy}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
