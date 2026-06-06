import { useState, useEffect } from 'react'
import { useQuery, useMutation } from '@tanstack/react-query'
import { getSeasonalCurrent, getSeasonalHistory, saveSeasonalObjective, type SeasonalObjective } from '../api/seasonal'

const STRATEGY_LABELS = { promote: 'Promozione', maintain: 'Mantenimento', youth: 'Sviluppo giovani' }

export function Stagione() {
  const currentQ  = useQuery({ queryKey: ['seasonal-current'], queryFn: getSeasonalCurrent })
  const historyQ  = useQuery({ queryKey: ['seasonal-history'], queryFn: getSeasonalHistory })

  const [season, setSeason] = useState(0)
  const [position, setPosition] = useState(5)
  const [points, setPoints] = useState(0)
  const [series, setSeries] = useState('')
  const [budget, setBudget] = useState(0)
  const [strategy, setStrategy] = useState<'promote'|'maintain'|'youth'>('maintain')
  const [notes, setNotes] = useState('')
  const [saved, setSaved] = useState<SeasonalObjective | null>(null)

  useEffect(() => {
    const obj = currentQ.data?.objective
    if (obj) {
      setSeason(obj.season)
      setPosition(obj.league_position)
      setPoints(obj.league_points)
      setSeries(obj.league_series)
      setBudget(obj.budget_manual)
      setStrategy(obj.strategy)
      setNotes(obj.notes)
    }
  }, [currentQ.data])

  const saveMut = useMutation({
    mutationFn: () => saveSeasonalObjective({
      season, league_position: position, league_points: points,
      league_series: series, budget_manual: budget, strategy, notes,
    }),
    onSuccess: (data) => { setSaved(data); currentQ.refetch(); historyQ.refetch() },
  })

  const inputStyle: React.CSSProperties = { border: '1px solid #d1d5db', borderRadius: 6, padding: '6px 10px', fontSize: 14, width: '100%', boxSizing: 'border-box' }
  const labelStyle: React.CSSProperties = { fontSize: 13, color: '#6b7280', marginBottom: 4, display: 'block' }
  const sectionStyle: React.CSSProperties = { background: '#fff', borderRadius: 8, padding: 20, marginBottom: 16, boxShadow: '0 1px 3px rgba(0,0,0,.08)' }
  const btnPrimary: React.CSSProperties = { background: '#3b82f6', color: '#fff', border: 'none', borderRadius: 6, padding: '8px 20px', cursor: 'pointer', fontSize: 14, fontWeight: 600 }
  const btnSecondary: React.CSSProperties = { background: '#f3f4f6', color: '#374151', border: '1px solid #d1d5db', borderRadius: 6, padding: '8px 16px', cursor: 'pointer', fontSize: 13 }

  return (
    <div style={{ maxWidth: 700, margin: '0 auto' }}>
      <h2 style={{ fontSize: 20, fontWeight: 700, marginBottom: 20 }}>Obiettivo Stagionale</h2>

      <div style={sectionStyle}>
        <h3 style={{ margin: '0 0 16px', fontSize: 16 }}>Situazione attuale</h3>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 12 }}>
          <div>
            <label style={labelStyle}>Stagione HT</label>
            <input type="number" value={season} onChange={e => setSeason(+e.target.value)} style={inputStyle} />
          </div>
          <div>
            <label style={labelStyle}>Posizione</label>
            <input type="number" min={1} max={16} value={position} onChange={e => setPosition(+e.target.value)} style={inputStyle} />
          </div>
          <div>
            <label style={labelStyle}>Punti</label>
            <input type="number" min={0} value={points} onChange={e => setPoints(+e.target.value)} style={inputStyle} />
          </div>
          <div>
            <label style={labelStyle}>Serie</label>
            <input type="text" value={series} onChange={e => setSeries(e.target.value)} placeholder="es. VII.935" style={inputStyle} />
          </div>
          <div>
            <label style={labelStyle}>Budget disponibile (€)</label>
            <input type="number" min={0} step={10000} value={budget} onChange={e => setBudget(+e.target.value)} style={inputStyle} />
          </div>
        </div>
      </div>

      <div style={sectionStyle}>
        <h3 style={{ margin: '0 0 16px', fontSize: 16 }}>Strategia stagionale</h3>
        <div style={{ display: 'flex', gap: 8, marginBottom: 16 }}>
          {(['promote','maintain','youth'] as const).map(s => (
            <button key={s} onClick={() => setStrategy(s)}
              style={{ ...btnSecondary, flex: 1, background: strategy === s ? '#eff6ff' : undefined,
                borderColor: strategy === s ? '#3b82f6' : undefined,
                color: strategy === s ? '#3b82f6' : undefined, fontWeight: strategy === s ? 600 : 400 }}>
              {STRATEGY_LABELS[s]}
            </button>
          ))}
        </div>
        <label style={labelStyle}>Note libere</label>
        <textarea value={notes} onChange={e => setNotes(e.target.value)}
          placeholder="Osservazioni, obiettivi specifici..."
          style={{ ...inputStyle, height: 80, resize: 'vertical' }} />
      </div>

      {saved && (
        <div style={{ ...sectionStyle, borderLeft: '4px solid #10b981' }}>
          <h3 style={{ margin: '0 0 8px', fontSize: 15, color: '#065f46' }}>Raccomandazione</h3>
          <p style={{ margin: 0, fontSize: 14, color: '#374151' }}>{saved.recommendation}</p>
        </div>
      )}

      <div style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: 32 }}>
        <button style={btnPrimary} disabled={saveMut.isPending} onClick={() => saveMut.mutate()}>
          {saveMut.isPending ? 'Salvataggio...' : 'Salva obiettivo'}
        </button>
      </div>

      {historyQ.data && historyQ.data.history.length > 1 && (
        <div style={sectionStyle}>
          <h3 style={{ margin: '0 0 16px', fontSize: 16 }}>Stagioni precedenti</h3>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
            <thead>
              <tr style={{ borderBottom: '2px solid #e5e7eb' }}>
                {['Stagione','Pos.','Punti','Serie','Strategia'].map(h => (
                  <th key={h} style={{ textAlign: 'left', padding: '6px 8px', color: '#6b7280' }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {historyQ.data.history.slice(1).map(r => (
                <tr key={r.id} style={{ borderBottom: '1px solid #f3f4f6' }}>
                  <td style={{ padding: '6px 8px', fontWeight: 600 }}>{r.season}</td>
                  <td style={{ padding: '6px 8px' }}>{r.league_position}</td>
                  <td style={{ padding: '6px 8px' }}>{r.league_points}</td>
                  <td style={{ padding: '6px 8px' }}>{r.league_series}</td>
                  <td style={{ padding: '6px 8px' }}>{STRATEGY_LABELS[r.strategy]}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
