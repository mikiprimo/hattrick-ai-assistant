import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import {
  createColumnHelper,
  flexRender,
  getCoreRowModel,
  getSortedRowModel,
  useReactTable,
  type SortingState,
} from '@tanstack/react-table'
import { getSquad, type Player } from '../api/squad'
import { SkillBar } from '../components/SkillBar'
import { SyncButton } from '../components/SyncButton'
import { HrfScanButton } from '../components/HrfScanButton'

const col = createColumnHelper<Player>()

const columns = [
  col.accessor((p) => `${p.first_name} ${p.last_name}`, {
    id: 'name',
    header: 'Nome',
    cell: (info) => {
      const player = info.row.original
      return (
        <Link
          to={`/players/${player.id}`}
          style={{ color: '#3b82f6', textDecoration: 'none', fontWeight: 500 }}
        >
          {player.first_name} {player.last_name}
        </Link>
      )
    },
  }),
  col.accessor('age', { header: 'Età' }),
  col.accessor('form', { header: 'Forma' }),
  col.accessor('tsi', {
    header: 'TSI',
    cell: (info) => info.getValue().toLocaleString('it-IT'),
  }),
  col.accessor('stamina', {
    header: 'Sta.',
    cell: (info) => <SkillBar value={info.getValue()} />,
  }),
  col.accessor('goalkeeper', {
    header: 'Por.',
    cell: (info) => <SkillBar value={info.getValue()} />,
  }),
  col.accessor('defending', {
    header: 'Dif.',
    cell: (info) => <SkillBar value={info.getValue()} />,
  }),
  col.accessor('playmaking', {
    header: 'Cen.',
    cell: (info) => <SkillBar value={info.getValue()} />,
  }),
  col.accessor('winger', {
    header: 'Ala',
    cell: (info) => <SkillBar value={info.getValue()} />,
  }),
  col.accessor('passing', {
    header: 'Pas.',
    cell: (info) => <SkillBar value={info.getValue()} />,
  }),
  col.accessor('scoring', {
    header: 'Att.',
    cell: (info) => <SkillBar value={info.getValue()} />,
  }),
  col.accessor('set_pieces', {
    header: 'Cal.',
    cell: (info) => <SkillBar value={info.getValue()} />,
  }),
  col.accessor('salary', {
    header: 'Stipendio',
    cell: (info) => `€${info.getValue().toLocaleString('it-IT')}`,
  }),
  col.accessor('injury_days', {
    header: 'Infort.',
    cell: (info) => {
      const v = info.getValue()
      return v === -1 ? '—' : <span style={{ color: '#ef4444' }}>{v}w</span>
    },
  }),
]

export function Squad() {
  const qc = useQueryClient()
  const [sorting, setSorting] = useState<SortingState>([])
  const { data: players = [], isLoading, error } = useQuery({
    queryKey: ['squad'],
    queryFn: getSquad,
  })

  const table = useReactTable({
    data: players,
    columns,
    state: { sorting },
    onSortingChange: setSorting,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
  })

  return (
    <div>
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          marginBottom: 16,
        }}
      >
        <h1 style={{ margin: 0 }}>Rosa ({players.length})</h1>
        <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
          <HrfScanButton onScanned={() => qc.invalidateQueries({ queryKey: ['squad'] })} />
          <SyncButton entity="squad" onSynced={() => qc.invalidateQueries({ queryKey: ['squad'] })} />
        </div>
      </div>

      {isLoading && <p>Caricamento…</p>}
      {error && <p style={{ color: '#ef4444' }}>Errore: {(error as Error).message}</p>}

      {!isLoading && players.length === 0 && (
        <p style={{ color: '#6b7280' }}>
          Nessun giocatore. Importa un file HRF o configura CHPP e clicca Sincronizza.
        </p>
      )}

      {players.length > 0 && (
        <div style={{ overflowX: 'auto' }}>
          <table
            style={{
              width: '100%',
              borderCollapse: 'collapse',
              background: '#fff',
              borderRadius: 8,
              overflow: 'hidden',
            }}
          >
            <thead>
              {table.getHeaderGroups().map((hg) => (
                <tr key={hg.id}>
                  {hg.headers.map((h) => (
                    <th
                      key={h.id}
                      onClick={h.column.getToggleSortingHandler()}
                      style={{
                        padding: '10px 12px',
                        textAlign: 'left',
                        borderBottom: '2px solid #e5e7eb',
                        cursor: h.column.getCanSort() ? 'pointer' : 'default',
                        whiteSpace: 'nowrap',
                        fontSize: 13,
                        color: '#6b7280',
                        userSelect: 'none',
                      }}
                    >
                      {flexRender(h.column.columnDef.header, h.getContext())}
                      {h.column.getIsSorted() === 'asc'
                        ? ' ↑'
                        : h.column.getIsSorted() === 'desc'
                        ? ' ↓'
                        : ''}
                    </th>
                  ))}
                </tr>
              ))}
            </thead>
            <tbody>
              {table.getRowModel().rows.map((row, i) => (
                <tr
                  key={row.id}
                  style={{ background: i % 2 === 0 ? '#fff' : '#f9fafb' }}
                >
                  {row.getVisibleCells().map((cell) => (
                    <td key={cell.id} style={{ padding: '8px 12px', fontSize: 13 }}>
                      {flexRender(cell.column.columnDef.cell, cell.getContext())}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
