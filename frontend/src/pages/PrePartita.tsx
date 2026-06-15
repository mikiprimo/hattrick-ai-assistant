import { useState, useEffect } from 'react'
import { useQuery, useMutation } from '@tanstack/react-query'
import {
  getPrePartitaSquad, getFormationXP, getTacticXP, analyzeOpponent, saveAnalysis,
  type AnalysisResult,
} from '../api/pre_partita'

const FORMATIONS = ['4-4-2','3-5-2','4-3-3','3-4-3','5-4-1','4-5-1','5-3-2','5-2-3','5-5-0','2-5-3']
const TACTICS = ['Normal','Pressing','Contropiede','Attacco al Centro','Attacco sulle Fasce','Tiri da Fuori','Libertà d\'Inventiva']
const XP_LABELS = ['Insufficiente','Debole','Debole','Debole','Debole','Debole','Debole','Debole','Accettabile','Accettabile','Accettabile','Accettabile','Buono','Buono','Buono','Buono','Eccellente','Eccellente','Eccellente','Eccellente','Leggendario']

const ATTITUDE_LABELS: Record<string, string> = {
  normal: 'Normale', mots: 'Partita della Stagione', cool: 'Partitella',
}

const LINE_LABEL: Record<string, string> = {
  goalkeeper: 'Portiere', defense: 'Difesa', midfield: 'Centrocampo', attack: 'Attacco',
}

const TACTIC_TYPE_LABEL: Record<number, string> = {
  0: 'Normal', 1: 'Pressing', 2: 'Contropiede', 3: 'Attacco al Centro',
  4: 'Attacco sulle Fasce', 5: 'Tiri da Fuori', 6: 'Libertà d\'Inventiva',
}

type Step = 1 | 2 | 3

function StepHeader({ step }: { step: Step }) {
  return (
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
}

export function PrePartita() {
  const [step, setStep] = useState<Step>(1)

  const [spirit, setSpirit] = useState(10)
  const [confidence, setConfidence] = useState(10)
  const [formationXP, setFormationXP] = useState<Record<string, number>>({})
  const [tacticXP, setTacticXP] = useState<Record<string, number>>({})

  const [isHome, setIsHome] = useState(true)
  const [matchType, setMatchType] = useState<'league'|'cup'|'friendly'>('league')
  const [activeXmlTab, setActiveXmlTab] = useState<0|1|2>(0)
  const [matchdetailsXml, setMatchdetailsXml] = useState(['', '', ''])

  const [analysis, setAnalysis] = useState<AnalysisResult | null>(null)
  const [saved, setSaved] = useState(false)

  const squadQ = useQuery({ queryKey: ['pre-partita-squad'], queryFn: getPrePartitaSquad })
  const formationXPQ = useQuery({ queryKey: ['formation-xp'], queryFn: getFormationXP })
  const tacticXPQ = useQuery({ queryKey: ['tactic-xp'], queryFn: getTacticXP })

  useEffect(() => {
    if (formationXPQ.data) setFormationXP(formationXPQ.data.formation_xp)
  }, [formationXPQ.data])

  useEffect(() => {
    if (tacticXPQ.data) setTacticXP(tacticXPQ.data.tactic_xp)
  }, [tacticXPQ.data])

  const setXml = (idx: number, val: string) =>
    setMatchdetailsXml(prev => prev.map((x, i) => i === idx ? val : x))

  const analyzeMut = useMutation({
    mutationFn: () => analyzeOpponent({
      matchdetails_xml_1: matchdetailsXml[0],
      matchdetails_xml_2: matchdetailsXml[1] || undefined,
      matchdetails_xml_3: matchdetailsXml[2] || undefined,
      is_home: isHome,
      match_type: matchType,
      spirit,
      confidence,
      formation_xp: formationXP,
      tactic_xp: tacticXP,
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

  // ── Step 1: la tua squadra ───────────────────────────────────────────────
  if (step === 1) return (
    <div style={{ maxWidth: 700, margin: '0 auto' }}>
      <StepHeader step={step} />
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

      <div style={sectionStyle}>
        <h3 style={{ margin: '0 0 16px', fontSize: 16 }}>Esperienza per tattica</h3>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: 12 }}>
          {TACTICS.map(t => {
            const xp = tacticXP[t] ?? 0
            return (
              <div key={t}>
                <label style={labelStyle}>{t} — {XP_LABELS[xp] ?? xp}</label>
                <input type="range" min={0} max={20} value={xp}
                  onChange={e => setTacticXP(prev => ({ ...prev, [t]: +e.target.value }))}
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

  // ── Step 2: avversario ───────────────────────────────────────────────────
  if (step === 2) return (
    <div style={{ maxWidth: 700, margin: '0 auto' }}>
      <StepHeader step={step} />

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
        <h3 style={{ margin: '0 0 14px', fontSize: 16 }}>Campo</h3>
        <div style={{ display: 'flex', gap: 8 }}>
          {([true, false] as const).map(home => (
            <button key={String(home)} onClick={() => setIsHome(home)}
              style={{ ...btnSecondary, flex: 1, padding: '12px 0', fontSize: 15, fontWeight: 600,
                background: isHome === home ? (home ? '#eff6ff' : '#fef3c7') : undefined,
                borderColor: isHome === home ? (home ? '#3b82f6' : '#f59e0b') : undefined,
                color: isHome === home ? (home ? '#1d4ed8' : '#b45309') : undefined }}>
              {home ? '🏠 Casa' : '✈️ Trasferta'}
            </button>
          ))}
        </div>
        <p style={{ margin: '10px 0 0', fontSize: 12, color: '#9ca3af' }}>
          {isHome
            ? 'In casa: i rating avversari vengono deflazionati (×0.88) per il vantaggio campo.'
            : 'In trasferta: i rating avversari vengono gonfiati (×1.06) — giocano in casa loro.'}
        </p>
      </div>

      <div style={sectionStyle}>
        <h3 style={{ margin: '0 0 14px', fontSize: 16 }}>
          XML Matchdetails avversario
          <span style={{ fontSize: 12, fontWeight: 400, color: '#6b7280', marginLeft: 8 }}>
            (1–3 partite recenti)
          </span>
        </h3>

        {/* Tab bar */}
        <div style={{ display: 'flex', borderBottom: '1px solid #e5e7eb', marginBottom: 14, gap: 0 }}>
          {(['Partita 1 *', 'Partita 2', 'Partita 3'] as const).map((label, idx) => {
            const filled = !!matchdetailsXml[idx].trim()
            const active = activeXmlTab === idx
            return (
              <button key={idx} onClick={() => setActiveXmlTab(idx as 0|1|2)}
                style={{ background: 'none', border: 'none', cursor: 'pointer', padding: '8px 18px',
                  fontSize: 13, fontWeight: active ? 600 : 400,
                  color: active ? '#3b82f6' : filled ? '#059669' : '#6b7280',
                  borderBottom: `2px solid ${active ? '#3b82f6' : 'transparent'}`,
                  marginBottom: -1 }}>
                {filled && !active ? '✓ ' : ''}{label}
              </button>
            )
          })}
        </div>

        <textarea
          value={matchdetailsXml[activeXmlTab]}
          onChange={e => setXml(activeXmlTab, e.target.value)}
          placeholder={activeXmlTab === 0
            ? 'Incolla qui l\'XML matchdetails della partita più recente (obbligatorio)...'
            : `Incolla qui l\'XML matchdetails della ${activeXmlTab + 1}ª partita (opzionale)...`}
          style={{ ...inputStyle, height: 180, resize: 'vertical', fontFamily: 'monospace', fontSize: 12 }}
        />
        <p style={{ margin: '6px 0 0', fontSize: 12, color: '#9ca3af' }}>
          Fonte: CHPP → actionType=matchdetails&matchID=… — solo partite di campionato (MatchType=1).
          Più partite fornisci, più accurata è la media pesata dei rating.
        </p>
      </div>

      {analyzeMut.isError && (
        <div style={{ background: '#fef2f2', border: '1px solid #fca5a5', borderRadius: 6, padding: 12, marginBottom: 16, color: '#dc2626', fontSize: 13 }}>
          {String((analyzeMut.error as Error)?.message ?? 'Errore di analisi')}
        </div>
      )}

      <div style={{ display: 'flex', justifyContent: 'space-between' }}>
        <button style={btnSecondary} onClick={() => setStep(1)}>← Indietro</button>
        <button
          style={{ ...btnPrimary, opacity: !matchdetailsXml[0].trim() || analyzeMut.isPending ? 0.6 : 1 }}
          disabled={!matchdetailsXml[0].trim() || analyzeMut.isPending}
          onClick={() => analyzeMut.mutate()}>
          {analyzeMut.isPending ? 'Analisi in corso...' : 'Analizza partita →'}
        </button>
      </div>
    </div>
  )

  // ── Step 3: risultati ────────────────────────────────────────────────────
  if (!analysis) return null

  const { my_team, opponent, tactic_ranking, tactic_recommendation, sub_plan, attitude_orders, attitude, explanation } = analysis

  const allPlayers = squadQ.data?.players ?? []
  const startingIds = new Set(Object.values(my_team.lineup).flatMap(arr => arr.map(p => p.id)))
  const bench = allPlayers
    .filter(p => p.injury_days <= 0 && !startingIds.has(p.id))
    .sort((a, b) => b.role_rating - a.role_rating)

  const ratingBar = (val: number, max = 20) => (
    <div style={{ background: '#e5e7eb', borderRadius: 4, height: 8, width: '100%' }}>
      <div style={{ background: '#3b82f6', borderRadius: 4, height: 8, width: `${Math.min((val/max)*100, 100)}%` }} />
    </div>
  )

  return (
    <div style={{ maxWidth: 800, margin: '0 auto' }}>
      <StepHeader step={step} />

      {/* Sintesi */}
      <div style={{ ...sectionStyle, borderLeft: '4px solid #3b82f6' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 8 }}>
          <span style={{ fontSize: 28, fontWeight: 700, color: '#1d4ed8' }}>{my_team.best_formation}</span>
          <span style={{ fontSize: 13, background: my_team.xp_warning ? '#fef3c7' : '#d1fae5',
            color: my_team.xp_warning ? '#b45309' : '#065f46', borderRadius: 12, padding: '2px 10px' }}>
            XP {my_team.xp_level} {XP_LABELS[my_team.xp_level] ?? ''}
          </span>
          <span style={{ fontSize: 12, background: isHome ? '#eff6ff' : '#fef3c7',
            color: isHome ? '#1d4ed8' : '#b45309', borderRadius: 12, padding: '2px 10px' }}>
            {isHome ? '🏠 Casa' : '✈️ Trasferta'}
          </span>
          {my_team.xp_warning && my_team.xp_alternative && (
            <span style={{ fontSize: 12, color: '#b45309' }}>
              ⚠ Alternativa: {my_team.xp_alternative}
            </span>
          )}
        </div>
        <p style={{ margin: 0, fontSize: 14, color: '#374151' }}>{explanation}</p>
      </div>

      {/* Avversario */}
      <div style={sectionStyle}>
        <h3 style={{ margin: '0 0 14px', fontSize: 16 }}>
          Avversario: {opponent.team_name}
          <span style={{ fontSize: 12, fontWeight: 400, color: '#6b7280', marginLeft: 8 }}>
            {opponent.matches_used} partita{opponent.matches_used > 1 ? 'e' : ''} analizzata{opponent.matches_used > 1 ? 'e' : ''}
          </span>
        </h3>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16, marginBottom: 14 }}>
          <div>
            <span style={{ fontSize: 12, color: '#6b7280' }}>Modulo tipico</span>
            <div style={{ fontWeight: 700, fontSize: 18, color: '#111' }}>{opponent.typical_formation}</div>
          </div>
          <div>
            <span style={{ fontSize: 12, color: '#6b7280' }}>Tattica dominante</span>
            <div style={{ fontWeight: 700, fontSize: 15, color: '#111' }}>
              {opponent.dominant_tactic !== null
                ? TACTIC_TYPE_LABEL[opponent.dominant_tactic] ?? `Tipo ${opponent.dominant_tactic}`
                : 'Variabile'}
              {opponent.avg_tactic_skill > 0 && (
                <span style={{ fontWeight: 400, fontSize: 12, color: '#6b7280', marginLeft: 6 }}>
                  (XP {opponent.avg_tactic_skill.toFixed(0)})
                </span>
              )}
            </div>
          </div>
        </div>
        {opponent.recent_results.length > 0 && (
          <div>
            <span style={{ fontSize: 12, color: '#6b7280', display: 'block', marginBottom: 6 }}>Risultati recenti</span>
            <div style={{ display: 'flex', gap: 6 }}>
              {opponent.recent_results.map((r, i) => (
                <span key={i} style={{ fontSize: 13, fontWeight: 700, padding: '4px 10px', borderRadius: 6,
                  background: r.result === 'W' ? '#d1fae5' : r.result === 'D' ? '#fef3c7' : '#fee2e2',
                  color: r.result === 'W' ? '#065f46' : r.result === 'D' ? '#92400e' : '#991b1b' }}>
                  {r.result} {r.goals_for}–{r.goals_against}
                </span>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Formazione schierata */}
      <div style={sectionStyle}>
        <h3 style={{ margin: '0 0 16px', fontSize: 16 }}>Formazione schierata</h3>
        {(['goalkeeper','defense','midfield','attack'] as const).map(line => {
          const players = my_team.lineup[line] ?? []
          if (players.length === 0) return null
          return (
            <div key={line} style={{ display: 'flex', gap: 8, marginBottom: 10, alignItems: 'flex-start' }}>
              <span style={{ fontSize: 12, color: '#6b7280', width: 100, flexShrink: 0, paddingTop: 2 }}>{LINE_LABEL[line]}</span>
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

      {/* Panchina */}
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

      {/* Piano sostituzioni (dal backend) */}
      {sub_plan.length > 0 && (
        <div style={sectionStyle}>
          <h3 style={{ margin: '0 0 14px', fontSize: 16 }}>Piano sostituzioni</h3>
          <div style={{ fontSize: 12, color: '#6b7280', marginBottom: 10 }}>
            Basato sullo stamina dei titolari — adatta in base all'andamento.
          </div>
          {sub_plan.map((s, i) => (
            <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 10,
              padding: '10px 12px', borderRadius: 6, background: '#f9fafb', border: '1px solid #e5e7eb' }}>
              <span style={{ fontSize: 13, fontWeight: 600, color: '#6b7280', width: 60 }}>~{s.minute}'</span>
              <span style={{ fontSize: 13, color: '#dc2626', textDecoration: 'line-through' }}>{s.out_name}</span>
              <span style={{ fontSize: 11, background: '#fee2e2', color: '#dc2626', borderRadius: 4, padding: '1px 6px' }}>
                st.{s.out_stamina}
              </span>
              <span style={{ color: '#9ca3af', fontSize: 16 }}>→</span>
              <span style={{ fontSize: 13, fontWeight: 600, color: '#059669' }}>{s.in_name}</span>
            </div>
          ))}
        </div>
      )}

      {/* Ordini di atteggiamento condizionali */}
      {attitude_orders.length > 0 && (
        <div style={sectionStyle}>
          <h3 style={{ margin: '0 0 14px', fontSize: 16 }}>Ordini atteggiamento condizionali</h3>
          {attitude_orders.map((o, i) => (
            <div key={i} style={{ display: 'flex', alignItems: 'flex-start', gap: 12, marginBottom: 10,
              padding: '10px 12px', borderRadius: 6, background: '#f9fafb', border: '1px solid #e5e7eb' }}>
              <div style={{ minWidth: 80, textAlign: 'center', padding: '4px 8px', borderRadius: 6,
                background: '#e0f2fe', color: '#0369a1', fontWeight: 700, fontSize: 13 }}>
                {o.minute}'
              </div>
              <div style={{ flex: 1 }}>
                <div style={{ fontSize: 12, color: '#6b7280', marginBottom: 2 }}>
                  {o.condition.charAt(0).toUpperCase() + o.condition.slice(1)}
                </div>
                <div style={{ fontWeight: 600, fontSize: 14, color: '#111' }}>→ {o.attitude}</div>
                <div style={{ fontSize: 12, color: '#9ca3af', marginTop: 2 }}>{o.reason}</div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Rating per reparto */}
      <div style={sectionStyle}>
        <h3 style={{ margin: '0 0 16px', fontSize: 16 }}>Rating per reparto</h3>
        {(['goalkeeper','defense','midfield','attack'] as const).map(line => {
          const myVal = my_team.modified_ratings[line] ?? 0
          const oppRaw = opponent.chpp_ratings
          const oppVal = line === 'goalkeeper'
            ? (oppRaw['mid_def'] ?? 0) / 6
            : line === 'defense'
              ? ((oppRaw['mid_def'] ?? 0) + (oppRaw['right_def'] ?? 0) + (oppRaw['left_def'] ?? 0)) / 3 / 6
              : line === 'midfield'
                ? (oppRaw['midfield'] ?? 0) / 6
                : ((oppRaw['mid_att'] ?? 0) + (oppRaw['right_att'] ?? 0) + (oppRaw['left_att'] ?? 0)) / 3 / 6
          return (
            <div key={line} style={{ marginBottom: 12 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 13, marginBottom: 4 }}>
                <span style={{ color: '#374151' }}>{LINE_LABEL[line]}</span>
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

      {/* Tattica consigliata + ranking */}
      <div style={sectionStyle}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 16 }}>
          <h3 style={{ margin: 0, fontSize: 16 }}>Ranking tattiche</h3>
          <span style={{ fontSize: 13, background: '#eff6ff', color: '#1d4ed8', borderRadius: 12, padding: '2px 12px', fontWeight: 700 }}>
            ✓ {tactic_recommendation.recommended}
          </span>
        </div>
        {tactic_ranking.map((t, i) => {
          const isRec = t.name === tactic_recommendation.recommended
          return (
            <div key={t.name} style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 10,
              padding: '10px 12px', borderRadius: 6,
              background: isRec ? '#eff6ff' : '#f9fafb',
              border: isRec ? '1px solid #bfdbfe' : '1px solid #e5e7eb' }}>
              <span style={{ fontSize: 18, fontWeight: 700, color: isRec ? '#1d4ed8' : '#9ca3af', width: 24 }}>{i+1}</span>
              <div style={{ flex: 1 }}>
                <div style={{ fontWeight: isRec ? 700 : 500, fontSize: 14, color: '#111' }}>{t.name}</div>
                <div style={{ fontSize: 12, color: '#6b7280', marginTop: 2 }}>{t.explanation}</div>
              </div>
              <span style={{ fontSize: 13, fontWeight: 600, color: '#374151' }}>{t.score.toFixed(1)}</span>
            </div>
          )
        })}
      </div>

      {/* Atteggiamento */}
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
