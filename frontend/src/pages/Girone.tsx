import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { getLatestLeague } from '../api/matches'
import { getRivals, createRival, importRivalXml, setRivalRatings, deleteRival } from '../api/rivals'

const sec: React.CSSProperties = {
  background: '#fff', borderRadius: 8, padding: 20, marginBottom: 16,
  boxShadow: '0 1px 3px rgba(0,0,0,.08)',
}
const inp: React.CSSProperties = {
  border: '1px solid #d1d5db', borderRadius: 6, padding: '6px 10px',
  fontSize: 14, width: '100%', boxSizing: 'border-box',
}
const btnP: React.CSSProperties = {
  background: '#3b82f6', color: '#fff', border: 'none', borderRadius: 6,
  padding: '7px 16px', cursor: 'pointer', fontSize: 13, fontWeight: 600,
}
const btnD: React.CSSProperties = {
  background: '#fee2e2', color: '#dc2626', border: 'none', borderRadius: 6,
  padding: '5px 10px', cursor: 'pointer', fontSize: 12,
}

export function Girone() {
  const qc = useQueryClient()
  const leagueQ = useQuery({ queryKey: ['latest-league'], queryFn: getLatestLeague })
  const rivalsQ = useQuery({ queryKey: ['rivals'], queryFn: getRivals })

  const [newId, setNewId] = useState('')
  const [newName, setNewName] = useState('')
  const [xmlMap, setXmlMap] = useState<Record<number, string>>({})
  const [ratingMap, setRatingMap] = useState<Record<number, { defense: string; midfield: string; attack: string }>>({})
  const [expandedId, setExpandedId] = useState<number | null>(null)

  const series = leagueQ.data?.league_series ?? ''
  const season = leagueQ.data?.season ?? 0

  const createMut = useMutation({
    mutationFn: () => createRival({
      team_id: parseInt(newId), team_name: newName, league_series: series, season,
    }),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['rivals'] }); setNewId(''); setNewName('') },
  })

  const xmlMut = useMutation({
    mutationFn: ({ team_id, xml }: { team_id: number; xml: string }) => importRivalXml(team_id, xml),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['rivals'] }),
  })

  const ratingMut = useMutation({
    mutationFn: ({ team_id, r }: { team_id: number; r: { defense: string; midfield: string; attack: string } }) =>
      setRivalRatings(team_id, {
        defense: parseFloat(r.defense) || undefined,
        midfield: parseFloat(r.midfield) || undefined,
        attack: parseFloat(r.attack) || undefined,
      }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['rivals'] }),
  })

  const deleteMut = useMutation({
    mutationFn: (team_id: number) => deleteRival(team_id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['rivals'] }),
  })

  const rivals = rivalsQ.data ?? []

  return (
    <div style={{ maxWidth: 800, margin: '0 auto' }}>
      <h2 style={{ fontSize: 20, fontWeight: 700, marginBottom: 4 }}>Girone</h2>
      {series && (
        <p style={{ fontSize: 14, color: '#6b7280', marginBottom: 20 }}>
          Serie: <strong>{series}</strong> · Stagione {season}
        </p>
      )}

      {/* Aggiungi squadra */}
      <div style={sec}>
        <h3 style={{ margin: '0 0 12px', fontSize: 15 }}>Aggiungi squadra rivale</h3>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 2fr auto', gap: 8, alignItems: 'end' }}>
          <div>
            <label style={{ fontSize: 12, color: '#6b7280', display: 'block', marginBottom: 4 }}>Team ID</label>
            <input style={inp} type="number" value={newId} onChange={e => setNewId(e.target.value)} placeholder="123456" />
          </div>
          <div>
            <label style={{ fontSize: 12, color: '#6b7280', display: 'block', marginBottom: 4 }}>Nome squadra</label>
            <input style={inp} type="text" value={newName} onChange={e => setNewName(e.target.value)} placeholder="FC Avversario" />
          </div>
          <button style={btnP} disabled={!newId || !newName || createMut.isPending}
            onClick={() => createMut.mutate()}>
            Aggiungi
          </button>
        </div>
      </div>

      {/* Lista rivali */}
      {rivals.length === 0 && (
        <p style={{ color: '#9ca3af', fontSize: 14, textAlign: 'center', padding: 32 }}>
          Nessuna squadra rivale registrata.
        </p>
      )}
      {rivals.map(t => {
        const expanded = expandedId === t.team_id
        const xml = xmlMap[t.team_id] ?? ''
        const r = ratingMap[t.team_id] ?? { defense: '', midfield: '', attack: '' }
        const mr = t.manual_ratings
        return (
          <div key={t.team_id} style={{ ...sec, border: expanded ? '1px solid #bfdbfe' : undefined }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div>
                <span style={{ fontWeight: 600, fontSize: 15 }}>{t.team_name}</span>
                <span style={{ fontSize: 12, color: '#9ca3af', marginLeft: 8 }}>#{t.team_id}</span>
                {t.player_count > 0 && (
                  <span style={{ fontSize: 12, color: '#059669', marginLeft: 8 }}>
                    {t.player_count} giocatori
                  </span>
                )}
                {mr && (mr.defense || mr.midfield || mr.attack) && (
                  <span style={{ fontSize: 12, color: '#7c3aed', marginLeft: 8 }}>
                    Dif {mr.defense?.toFixed(1)} · Cen {mr.midfield?.toFixed(1)} · Att {mr.attack?.toFixed(1)}
                  </span>
                )}
              </div>
              <div style={{ display: 'flex', gap: 6 }}>
                <button style={{ ...btnP, background: expanded ? '#e0e7ff' : '#3b82f6',
                  color: expanded ? '#3730a3' : '#fff' }}
                  onClick={() => setExpandedId(expanded ? null : t.team_id)}>
                  {expanded ? 'Chiudi' : 'Gestisci'}
                </button>
                <button style={btnD} onClick={() => deleteMut.mutate(t.team_id)}>Elimina</button>
              </div>
            </div>

            {expanded && (
              <div style={{ marginTop: 16, display: 'grid', gap: 16 }}>
                {/* Import XML */}
                <div>
                  <label style={{ fontSize: 13, fontWeight: 600, display: 'block', marginBottom: 6 }}>
                    Importa giocatori (incolla XML CHPP)
                  </label>
                  <textarea value={xml}
                    onChange={e => setXmlMap(m => ({ ...m, [t.team_id]: e.target.value }))}
                    placeholder="Incolla il contenuto del file XML della squadra avversaria..."
                    style={{ ...inp, height: 100, resize: 'vertical', fontFamily: 'monospace', fontSize: 12 }} />
                  <button style={{ ...btnP, marginTop: 6 }}
                    disabled={!xml || xmlMut.isPending}
                    onClick={() => xmlMut.mutate({ team_id: t.team_id, xml })}>
                    Importa giocatori
                  </button>
                </div>

                {/* Rating manuali */}
                <div>
                  <label style={{ fontSize: 13, fontWeight: 600, display: 'block', marginBottom: 6 }}>
                    Rating manuali (opzionali — sovrascrivono XML)
                  </label>
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr auto', gap: 8, alignItems: 'end' }}>
                    {(['defense', 'midfield', 'attack'] as const).map(f => (
                      <div key={f}>
                        <label style={{ fontSize: 12, color: '#6b7280', display: 'block', marginBottom: 4 }}>
                          {f === 'defense' ? 'Difesa' : f === 'midfield' ? 'Centrocampo' : 'Attacco'}
                        </label>
                        <input style={inp} type="number" step="0.1" min="0" max="20"
                          value={r[f]}
                          onChange={e => setRatingMap(m => ({ ...m, [t.team_id]: { ...r, [f]: e.target.value } }))}
                          placeholder={mr?.[f]?.toFixed(1) ?? '—'} />
                      </div>
                    ))}
                    <button style={btnP}
                      disabled={ratingMut.isPending}
                      onClick={() => ratingMut.mutate({ team_id: t.team_id, r })}>
                      Salva
                    </button>
                  </div>
                </div>
              </div>
            )}
          </div>
        )
      })}
    </div>
  )
}
