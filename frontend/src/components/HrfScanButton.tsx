import { useState } from 'react'
import { scanHrf } from '../api/hrf'

interface Props {
  onScanned?: () => void
}

export function HrfScanButton({ onScanned }: Props) {
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<{ scanned_at: string; files_imported: number } | null>(null)
  const [error, setError] = useState<string | null>(null)

  async function handleScan() {
    setLoading(true)
    setError(null)
    try {
      const r = await scanHrf()
      setResult({ scanned_at: r.scanned_at, files_imported: r.files_imported })
      onScanned?.()
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Errore')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
      <button
        onClick={handleScan}
        disabled={loading}
        style={{
          padding: '6px 14px',
          background: loading ? '#93c5fd' : '#3b82f6',
          color: '#fff',
          border: 'none',
          borderRadius: 6,
          cursor: loading ? 'not-allowed' : 'pointer',
          fontSize: 13,
        }}
      >
        {loading ? 'Importazione…' : 'Importa HRF'}
      </button>
      {result && (
        <span style={{ fontSize: 12, color: '#6b7280' }}>
          {result.files_imported} file — {new Date(result.scanned_at).toLocaleString('it-IT')}
        </span>
      )}
      {error && <span style={{ fontSize: 12, color: '#ef4444' }}>{error}</span>}
    </div>
  )
}
