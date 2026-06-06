import { useState, useMemo } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid,
  Tooltip, Legend, ResponsiveContainer,
} from 'recharts'
import { getMatches } from '../api/matches'
import { HrfScanButton } from '../components/HrfScanButton'
import type { LineupEntry } from '../api/matches'

const card: React.CSSProperties = {
  background: '#fff',
  borderRadius: 8,
  border: '1px solid #e5e7eb',
  padding: '16px 20px',
  marginBottom: 24,
}

const LINE_ORDER = ['GK', 'Difesa', 'Centrocampo', 'Attacco', 'Panchina']

function groupByLine(lineup: LineupEntry[]): [string, LineupEntry[]][] {
  const groups: Record<string, LineupEntry[]> = {}
  for (const entry of lineup) {
    if (!groups[entry.line]) groups[entry.line] = []
    groups[entry.line].push(entry)
  }
  return LINE_ORDER.filter(l => groups[l]).map(l => [l, groups[l]])
}

export function Matches() {
  const qc = useQueryClient()
  const [selectedIdx, setSelectedIdx] = useState(0)

  const { data: matches = [], isLoading, error } = useQuery({
    queryKey: ['matches'],
    queryFn: getMatches,
  })

  const match = matches[selectedIdx]

  const chartData = useMemo(
    () => [...matches].reverse().map(m => ({
      label: `S${m.season} T${m.matchround}`,
      Punti: m.league.points,
      Posizione: m.league.position,
    })),
    [matches]
  )

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <h1 style={{ margin: 0 }}>Partite</h1>
        <HrfScanButton onScanned={() => {
          qc.invalidateQueries({ queryKey: ['matches'] })
        }} />
      </div>

      {isLoading && <p>Caricamento…</p>}
      {error && <p style={{ color: '#ef4444' }}>Errore: {(error as Error).message}</p>}

      {!isLoading && matches.length === 0 && (
        <p style={{ color: '#6b7280' }}>
          Nessuna partita trovata. Importa i file HRF per vedere le formazioni.
        </p>
      )}

      {match && (
        <div style={card}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 16, marginBottom: 16 }}>
            <button
              onClick={() => setSelectedIdx(i => i + 1)}
              disabled={selectedIdx >= matches.length - 1}
              style={{
                padding: '4px 12px', borderRadius: 6, border: '1px solid #d1d5db',
                background: '#fff', cursor: selectedIdx >= matches.length - 1 ? 'not-allowed' : 'pointer',
                color: selectedIdx >= matches.length - 1 ? '#d1d5db' : '#374151',
              }}
            >←</button>

            <span style={{ fontWeight: 600, fontSize: 15 }}>
              Stagione {match.season} — Turno {match.matchround}
            </span>
            <span style={{ color: '#9ca3af', fontSize: 13 }}>{match.snapshot_date}</span>

            <button
              onClick={() => setSelectedIdx(i => i - 1)}
              disabled={selectedIdx === 0}
              style={{
                padding: '4px 12px', borderRadius: 6, border: '1px solid #d1d5db',
                background: '#fff', cursor: selectedIdx === 0 ? 'not-allowed' : 'pointer',
                color: selectedIdx === 0 ? '#d1d5db' : '#374151',
              }}
            >→</button>
          </div>

          {match.lineup.length === 0 ? (
            <p style={{ color: '#9ca3af', fontSize: 13 }}>Formazione non disponibile.</p>
          ) : (
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
              <thead>
                <tr style={{ borderBottom: '1px solid #e5e7eb', color: '#9ca3af', textAlign: 'left' }}>
                  <th style={{ padding: '4px 8px', fontWeight: 500 }}>Reparto</th>
                  <th style={{ padding: '4px 8px', fontWeight: 500 }}>Posizione</th>
                  <th style={{ padding: '4px 8px', fontWeight: 500 }}>Giocatore</th>
                  <th style={{ padding: '4px 8px', fontWeight: 500, textAlign: 'right' }}>Voto</th>
                </tr>
              </thead>
              <tbody>
                {groupByLine(match.lineup).map(([line, entries]) =>
                  entries.map((e, i) => (
                    <tr key={`${e.position}-${e.player_id}`}
                        style={{ borderBottom: '1px solid #f3f4f6' }}>
                      <td style={{ padding: '5px 8px', color: '#6b7280' }}>
                        {i === 0 ? line : ''}
                      </td>
                      <td style={{ padding: '5px 8px', color: '#6b7280' }}>{e.position}</td>
                      <td style={{ padding: '5px 8px', fontWeight: 500 }}>{e.name}</td>
                      <td style={{ padding: '5px 8px', textAlign: 'right', color: e.rating != null ? '#374151' : '#d1d5db' }}>
                        {e.rating ?? '—'}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          )}
        </div>
      )}

      {chartData.length > 0 && (
        <div style={card}>
          <h2 style={{ margin: '0 0 16px', fontSize: 16 }}>Classifica nel tempo</h2>
          <ResponsiveContainer width="100%" height={260}>
            <LineChart data={chartData} margin={{ top: 5, right: 30, left: 0, bottom: 5 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f3f4f6" />
              <XAxis dataKey="label" tick={{ fontSize: 11 }} />
              <YAxis yAxisId="left" tick={{ fontSize: 11 }} />
              <YAxis yAxisId="right" orientation="right" reversed tick={{ fontSize: 11 }} />
              <Tooltip />
              <Legend />
              <Line yAxisId="left" type="monotone" dataKey="Punti"
                    stroke="#3b82f6" dot={{ r: 3 }} activeDot={{ r: 5 }} />
              <Line yAxisId="right" type="monotone" dataKey="Posizione"
                    stroke="#f59e0b" dot={{ r: 3 }} activeDot={{ r: 5 }} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  )
}
