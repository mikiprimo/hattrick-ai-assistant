import { useState, useEffect } from 'react'
import { useQuery, useMutation } from '@tanstack/react-query'
import {
  getPrePartitaSquad, getFormationXP, analyzeOpponent, saveAnalysis,
  type AnalysisResult,
} from '../api/pre_partita'

const FORMATIONS = ['4-4-2','3-5-2','4-3-3','3-4-3','5-4-1','4-5-1','5-3-2','5-2-3','5-5-0','2-5-3']
const XP_LABELS = ['Insufficiente','Debole','Debole','Debole','Debole','Debole','Debole','Debole','Accettabile','Accettabile','Accettabile','Accettabile','Buono','Buono','Buono','Buono','Eccellente','Eccellente','Eccellente','Eccellente','Leggendario']

type Step = 1 | 2 | 3

export function PrePartita() {
  const [step, setStep] = useState<Step>(1)

  const [spirit, setSpirit] = useState(10)
  const [confidence, setConfidence] = useState(10)
  const [formationXP, setFormationXP] = useState<Record<string, number>>({})

  const [playersXml, setPlayersXml] = useState('')
  const [matchesXml, setMatchesXml] = useState('')
  const [matchType, setMatchType] = useState<'league'|'cup'|'friendly'>('league')

  const [analysis, setAnalysis] = useState<AnalysisResult | null>(null)
  const [saved, setSaved] = useState(false)

  const squadQ = useQuery({ queryKey: ['pre-partita-squad'], queryFn: getPrePartitaSquad })
  const formationXPQ = useQuery({ queryKey: ['formation-xp'], queryFn: getFormationXP })

  useEffect(() => {
    if (formationXPQ.data) setFormationXP(formationXPQ.data.formation_xp)
  }, [formationXPQ.data])

  const analyzeMut = useMutation({
    mutationFn: () => analyzeOpponent({
      players_xml: playersXml,
      matches_xml: matchesXml,
      match_type: matchType,
      spirit,
      confidence,
      formation_xp: formationXP,
    }),
    onSuccess: (data: AnalysisResult) => { setAnalysis(data); setStep(3); setSaved(false) },
  })

  const saveMut = useMutation({
    mutationFn: () => saveAnalysis({
      analysis: analysis!,
      my_spirit: spirit,
      my_confidence: confidence,
      my_attitude: analysis!.attitude.attitude,
      match_type: matchType,
    }),
    onSuccess: () => setSaved(true),
  })

  const inputStyle: React.CSSProperties = {
    border: '1px solid #d1d5db', borderRadius: 6, padding: '6px 10px',
    fontSize: 14, width: '100%', boxSizing: 'border-box',
  }
  const labelStyle: React.CSSProperties = { fontSize: 13, color: '#6b7280', marginBottom: 4, display: 'block' }
  const sectionStyle: React.CSSProperties = { background: '#fff', borderRadius: 8, padding: 20, marginBottom: 16, boxShadow: '0 1px 3px rgba(0,0,0,.08)' }
  const btnPrimary: React.CSSProperties = { background: '#3b82f6', color: '#fff', border: 'none', borderRadius: 6, padding: '8px 20px', cursor: 'pointer', fontSize: 14, fontWeight: 600 }
  const btnSecondary: React.CSSProperties = { background: '#f3f4f6', color: '#374151', border: '1px solid #d1d5db', borderRadius: 6, padding: '8px 20px', cursor: 'pointer', fontSize: 14 }

  const StepHeader = () => (
    <div style={{ display: 'flex', gap: 0, marginBottom: 24 }}>
      {(['La tua squadra', 'Avversario', 'Analisi'] as const).map((label, i) => {
        const n = (i + 1) as Step
        const active = step === n
        const done = step > n
        return (
          <div key={n} style={{ flex: 1, textAlign: 'center', padding: '10px 0',
            borderBottom: `3px solid ${active ? '#3b82f6' : done ? '#10b981' : '#e5e7eb'}`,
            color: active ? '#3b82f6' : done ? '#10b981' : '#9ca3af',
            fontWeight: active ? 600 : 400, fontSize: 14 }}>
            {done ? '✓ ' : `${n}. `}{label}
          </div>
        )
      })}
    </div>
  )

  if (step === 1) return (
    <div style={{ maxWidth: 700, margin: '0 auto' }}>
      <StepHeader />
      <div style={sectionStyle}>
        <h3 style={{ margin: '0 0 16px', fontSize: 16 }}>Condizioni della squadra</h3>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
          <div>
            <label style={labelStyle}>Spirito di squadra (1–20): <strong>{spirit}</strong></label>
            <input type="range" min={1} max={20} value={spirit} onChange={e => setSpirit(+e.target.value)} style={{ width: '100%' }} />
          </div>
          <div>
            <label style={labelStyle}>Fiducia (1–20): <strong>{confidence}</strong></label>
            <input type="range" min={1} max={20} value={confidence} onChange={e => setConfidence(+e.target.value)} style={{ width: '100%' }} />
          </div>
        </div>
      </div>

      <div style={sectionStyle}>
        <h3 style={{ margin: '0 0 16px', fontSize: 16 }}>Esperienza per modulo</h3>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: 12 }}>
          {FORMATIONS.map(f => {
            const xp = formationXP[f] ?? 0
            return (
              <div key={f}>
                <label style={labelStyle}>{f} — {XP_LABELS[xp] ?? xp}</label>
                <input type="range" min={0} max={20} value={xp}
                  onChange={e => setFormationXP(prev => ({ ...prev, [f]: +e.target.value }))}
                  style={{ width: '100%' }} />
              </div>
            )
          })}
        </div>
      </div>

      {squadQ.data && (
        <div style={sectionStyle}>
          <h3 style={{ margin: '0 0 12px', fontSize: 16 }}>
            Giocatori disponibili ({squadQ.data.players.filter(p => p.injury_days <= 0).length} sani)
          </h3>
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
              <thead>
                <tr style={{ borderBottom: '2px solid #e5e7eb' }}>
                  {['Nome','Forma','Stamina','Ruolo','Rating'].map(h => (
                    <th key={h} style={{ textAlign: 'left', padding: '6px 8px', color: '#6b7280' }}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {squadQ.data.players.map(p => (
                  <tr key={p.id} style={{ borderBottom: '1px solid #f3f4f6', opacity: p.injury_days > 0 ? 0.4 : 1 }}>
                    <td style={{ padding: '6px 8px', fontWeight: 500 }}>{p.name}{p.injury_days > 0 ? ' 🤕' : ''}</td>
                    <td style={{ padding: '6px 8px' }}>{p.form}</td>
                    <td style={{ padding: '6px 8px' }}>{p.stamina}</td>
                    <td style={{ padding: '6px 8px' }}>{p.best_role}</td>
                    <td style={{ padding: '6px 8px' }}>{p.role_rating}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
        <button style={btnPrimary} onClick={() => setStep(2)}>Avanti: Avversario →</button>
      </div>
    </div>
  )

  if (step === 2) return (
    <div style={{ maxWidth: 700, margin: '0 auto' }}>
      <StepHeader />
      <div style={sectionStyle}>
        <h3 style={{ margin: '0 0 16px', fontSize: 16 }}>Tipo partita</h3>
        <div style={{ display: 'flex', gap: 8 }}>
          {(['league','cup','friendly'] as const).map(t => (
            <button key={t} onClick={() => setMatchType(t)}
              style={{ ...btnSecondary, background: matchType === t ? '#eff6ff' : undefined,
                borderColor: matchType === t ? '#3b82f6' : undefined,
                color: matchType === t ? '#3b82f6' : undefined }}>
              {t === 'league' ? 'Campionato' : t === 'cup' ? 'Coppa' : 'Amichevole'}
            </button>
          ))}
        </div>
      </div>

      <div style={sectionStyle}>
        <label style={{ ...labelStyle, marginBottom: 8, fontWeight: 600, color: '#111' }}>
          XML Rosa avversaria * (obbligatorio)
        </label>
        <textarea value={playersXml} onChange={e => setPlayersXml(e.target.value)}
          placeholder="Incolla qui l'XML CHPP della rosa avversaria..."
          style={{ ...inputStyle, height: 160, resize: 'vertical', fontFamily: 'monospace', fontSize: 12 }} />
      </div>

      <div style={sectionStyle}>
        <label style={{ ...labelStyle, marginBottom: 8, fontWeight: 600, color: '#111' }}>
          XML Partite recenti (opzionale)
        </label>
        <textarea value={matchesXml} onChange={e => setMatchesXml(e.target.value)}
          placeholder="Incolla qui l'XML CHPP delle partite recenti..."
          style={{ ...inputStyle, height: 100, resize: 'vertical', fontFamily: 'monospace', fontSize: 12 }} />
      </div>

      {analyzeMut.isError && (
        <div style={{ background: '#fef2f2', border: '1px solid #fca5a5', borderRadius: 6, padding: 12, marginBottom: 16, color: '#dc2626', fontSize: 13 }}>
          {String((analyzeMut.error as Error)?.message ?? 'Errore di analisi')}
        </div>
      )}

      <div style={{ display: 'flex', justifyContent: 'space-between' }}>
        <button style={btnSecondary} onClick={() => setStep(1)}>← Indietro</button>
        <button
          style={{ ...btnPrimary, opacity: !playersXml.trim() || analyzeMut.isPending ? 0.6 : 1 }}
          disabled={!playersXml.trim() || analyzeMut.isPending}
          onClick={() => analyzeMut.mutate()}>
          {analyzeMut.isPending ? 'Analisi in corso...' : 'Analizza partita →'}
        </button>
      </div>
    </div>
  )

  if (!analysis) return null

  const { my_team, opponent, tactic_ranking, attitude, explanation } = analysis

  const ATTITUDE_LABELS: Record<string, string> = {
    normal: 'Normale', mots: 'Partita della Stagione', cool: 'Partitella'
  }

  const LINE_LABEL: Record<string, string> = {
    goalkeeper: 'Portiere', defense: 'Difesa', midfield: 'Centrocampo', attack: 'Attacco'
  }

  // Collect starting XI ids from lineup
  const startingIds = new Set(
    Object.values(my_team.lineup).flatMap(arr => arr.map(p => p.id))
  )

  // Bench: available non-injured players not in starting XI
  const allPlayers = squadQ.data?.players ?? []
  const bench = allPlayers
    .filter(p => p.injury_days <= 0 && !startingIds.has(p.id))
    .sort((a, b) => b.role_rating - a.role_rating)

  // Substitution plan: starters with lowest stamina → best bench replacement by role
  const lineOrder = ['goalkeeper', 'defense', 'midfield', 'attack'] as const
  const starters = lineOrder.flatMap(line =>
    (my_team.lineup[line] ?? []).map(p => {
      const full = allPlayers.find(ap => ap.id === p.id)
      return { ...p, stamina: full?.stamina ?? 10, line }
    })
  )
  const subTargets = [...starters]
    .filter(p => p.line !== 'goalkeeper')
    .sort((a, b) => a.stamina - b.stamina)
    .slice(0, 3)

  const LINE_ROLES: Record<string, string[]> = {
    defense: ['CD', 'WB', 'W'],
    midfield: ['IM', 'W', 'WB'],
    attack: ['FW', 'IM'],
  }
  const usedBenchIds = new Set<number>()
  const subPlan = subTargets.map((out, i) => {
    const preferred = (LINE_ROLES[out.line] ?? [])
    const inPlayer = bench.find(b => !usedBenchIds.has(b.id) && preferred.includes(b.best_role))
      ?? bench.find(b => !usedBenchIds.has(b.id))
      ?? null
    if (inPlayer) usedBenchIds.add(inPlayer.id)
    return { out, inPlayer, minute: 60 + i * 10 }
  })

  const ratingBar = (val: number, max = 20) => (
    <div style={{ background: '#e5e7eb', borderRadius: 4, height: 8, width: '100%' }}>
      <div style={{ background: '#3b82f6', borderRadius: 4, height: 8, width: `${Math.min((val/max)*100, 100)}%` }} />
    </div>
  )

  return (
    <div style={{ maxWidth: 800, margin: '0 auto' }}>
      <StepHeader />

      <div style={{ ...sectionStyle, borderLeft: '4px solid #3b82f6' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 8 }}>
          <span style={{ fontSize: 28, fontWeight: 700, color: '#1d4ed8' }}>{my_team.best_formation}</span>
          <span style={{ fontSize: 13, background: my_team.xp_warning ? '#fef3c7' : '#d1fae5',
            color: my_team.xp_warning ? '#b45309' : '#065f46', borderRadius: 12, padding: '2px 10px' }}>
            XP {my_team.xp_level} {XP_LABELS[my_team.xp_level] ?? ''}
          </span>
          {my_team.xp_warning && my_team.xp_alternative && (
            <span style={{ fontSize: 12, color: '#b45309' }}>
              ⚠ Rischio confusione — alternativa: {my_team.xp_alternative}
            </span>
          )}
        </div>
        <p style={{ margin: 0, fontSize: 14, color: '#374151' }}>{explanation}</p>
      </div>

      <div style={sectionStyle}>
        <h3 style={{ margin: '0 0 16px', fontSize: 16 }}>Formazione schierata</h3>
        {(['goalkeeper','defense','midfield','attack'] as const).map(line => {
          const lineLabels: Record<string, string> = { goalkeeper: 'Portiere', defense: 'Difesa', midfield: 'Centrocampo', attack: 'Attacco' }
          const players = my_team.lineup[line] ?? []
          if (players.length === 0) return null
          return (
            <div key={line} style={{ display: 'flex', gap: 8, marginBottom: 10, alignItems: 'flex-start' }}>
              <span style={{ fontSize: 12, color: '#6b7280', width: 100, flexShrink: 0, paddingTop: 2 }}>{lineLabels[line]}</span>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                {players.map(p => (
                  <span key={p.id} style={{ background: '#eff6ff', border: '1px solid #bfdbfe', borderRadius: 6,
                    padding: '3px 10px', fontSize: 13, color: '#1d4ed8', fontWeight: 500 }}>
                    {p.name} <span style={{ color: '#6b7280', fontWeight: 400 }}>({p.rating})</span>
                  </span>
                ))}
              </div>
            </div>
          )
        })}
      </div>

      {bench.length > 0 && (
        <div style={sectionStyle}>
          <h3 style={{ margin: '0 0 14px', fontSize: 16 }}>Panchina ({bench.length})</h3>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
            {bench.map(p => (
              <span key={p.id} style={{ background: '#f9fafb', border: '1px solid #e5e7eb', borderRadius: 6,
                padding: '3px 10px', fontSize: 13, color: '#374151' }}>
                {p.name}
                <span style={{ color: '#6b7280', marginLeft: 6 }}>{p.best_role} · st.{p.stamina}</span>
              </span>
            ))}
          </div>
        </div>
      )}

      {subPlan.length > 0 && (
        <div style={sectionStyle}>
          <h3 style={{ margin: '0 0 14px', fontSize: 16 }}>Piano sostituzioni</h3>
          <div style={{ fontSize: 13, color: '#6b7280', marginBottom: 10 }}>
            Basato sullo stamina dei titolari — adatta in base all'andamento della partita.
          </div>
          {subPlan.map((sub, i) => (
            <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 10,
              padding: '10px 12px', borderRadius: 6, background: '#f9fafb', border: '1px solid #e5e7eb' }}>
              <span style={{ fontSize: 13, fontWeight: 600, color: '#6b7280', width: 60 }}>
                ~{sub.minute}'
              </span>
              <span style={{ fontSize: 13, color: '#dc2626', textDecoration: 'line-through' }}>
                {sub.out.name}
              </span>
              <span style={{ color: '#9ca3af' }}>
                <span style={{ fontSize: 11, background: '#fee2e2', color: '#dc2626', borderRadius: 4, padding: '1px 6px' }}>
                  st.{sub.out.stamina}
                </span>
              </span>
              <span style={{ color: '#9ca3af', fontSize: 16 }}>→</span>
              {sub.inPlayer ? (
                <>
                  <span style={{ fontSize: 13, fontWeight: 600, color: '#059669' }}>{sub.inPlayer.name}</span>
                  <span style={{ fontSize: 11, background: '#d1fae5', color: '#059669', borderRadius: 4, padding: '1px 6px' }}>
                    {sub.inPlayer.best_role} · st.{sub.inPlayer.stamina}
                  </span>
                </>
              ) : (
                <span style={{ fontSize: 13, color: '#9ca3af', fontStyle: 'italic' }}>nessun sostituto disponibile</span>
              )}
            </div>
          ))}
        </div>
      )}

      <div style={sectionStyle}>
        <h3 style={{ margin: '0 0 16px', fontSize: 16 }}>Rating per reparto</h3>
        {(['goalkeeper','defense','midfield','attack'] as const).map(line => {
          const myVal = my_team.modified_ratings[line] ?? 0
          const oppVal = opponent.line_ratings[line] ?? 0
          const labels: Record<string, string> = { goalkeeper: 'Portiere', defense: 'Difesa', midfield: 'Centrocampo', attack: 'Attacco' }
          return (
            <div key={line} style={{ marginBottom: 12 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 13, marginBottom: 4 }}>
                <span style={{ color: '#374151' }}>{labels[line]}</span>
                <span>
                  <span style={{ color: myVal >= oppVal ? '#059669' : '#dc2626', fontWeight: 600 }}>{myVal.toFixed(1)}</span>
                  <span style={{ color: '#9ca3af', margin: '0 6px' }}>vs</span>
                  <span style={{ color: '#6b7280' }}>{oppVal.toFixed(1)}</span>
                </span>
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 4 }}>
                {ratingBar(myVal)}
                {ratingBar(oppVal)}
              </div>
            </div>
          )
        })}
      </div>

      <div style={sectionStyle}>
        <h3 style={{ margin: '0 0 16px', fontSize: 16 }}>Ranking tattiche</h3>
        {tactic_ranking.map((t, i) => (
          <div key={t.name} style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 10,
            padding: '10px 12px', borderRadius: 6,
            background: i === 0 ? '#eff6ff' : '#f9fafb',
            border: i === 0 ? '1px solid #bfdbfe' : '1px solid #e5e7eb' }}>
            <span style={{ fontSize: 18, fontWeight: 700, color: i === 0 ? '#1d4ed8' : '#9ca3af', width: 24 }}>{i+1}</span>
            <div style={{ flex: 1 }}>
              <div style={{ fontWeight: i === 0 ? 700 : 500, fontSize: 14, color: '#111' }}>{t.name}</div>
              <div style={{ fontSize: 12, color: '#6b7280', marginTop: 2 }}>{t.explanation}</div>
            </div>
            <span style={{ fontSize: 13, fontWeight: 600, color: '#374151' }}>{t.score.toFixed(1)}</span>
          </div>
        ))}
      </div>

      <div style={{ ...sectionStyle, borderLeft: `4px solid ${attitude.attitude === 'mots' ? '#f59e0b' : attitude.attitude === 'cool' ? '#6b7280' : '#10b981'}` }}>
        <div style={{ fontSize: 12, color: '#6b7280', marginBottom: 4 }}>Atteggiamento consigliato</div>
        <div style={{ fontSize: 20, fontWeight: 700 }}>{ATTITUDE_LABELS[attitude.attitude]}</div>
        <div style={{ fontSize: 13, color: '#6b7280', marginTop: 4 }}>{attitude.reason}</div>
      </div>

      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <button style={btnSecondary} onClick={() => { setStep(1); setAnalysis(null) }}>← Nuova analisi</button>
        <button style={{ ...btnPrimary, opacity: saved ? 0.6 : 1 }}
          disabled={saved || saveMut.isPending}
          onClick={() => saveMut.mutate()}>
          {saved ? '✓ Analisi salvata' : 'Salva analisi'}
        </button>
      </div>
    </div>
  )
}
