import { useState, useEffect } from 'react'
import { getHrfSettings, saveHrfSettings } from '../api/hrf'
import { HrfScanButton } from '../components/HrfScanButton'

export function Settings() {
  const [hrfFolder, setHrfFolder] = useState('')
  const [saved, setSaved] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    getHrfSettings().then(s => setHrfFolder(s.hrf_folder_path)).catch(() => {})
  }, [])

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setError(null)
    try {
      await saveHrfSettings({ hrf_folder_path: hrfFolder, team_id: null, enabled: true })
      setSaved(true)
      setTimeout(() => setSaved(false), 2000)
    } catch {
      setError('Errore nel salvataggio del percorso HRF')
    } finally {
      setLoading(false)
    }
  }

  const inputStyle: React.CSSProperties = { border: '1px solid #d1d5db', borderRadius: 6, padding: '6px 10px', fontSize: 14, width: '100%', boxSizing: 'border-box' }
  const sectionStyle: React.CSSProperties = { background: '#fff', borderRadius: 8, padding: 20, marginBottom: 16, boxShadow: '0 1px 3px rgba(0,0,0,.08)' }

  return (
    <div style={{ maxWidth: 560, margin: '0 auto' }}>
      <h2 style={{ fontSize: 20, fontWeight: 700, marginBottom: 20 }}>Impostazioni</h2>
      <div style={sectionStyle}>
        <h3 style={{ margin: '0 0 16px', fontSize: 16 }}>Cartella HRF</h3>
        <form onSubmit={handleSave}>
          <label style={{ fontSize: 13, color: '#6b7280', marginBottom: 4, display: 'block' }}>
            Percorso cartella HRF (dove HattrickOrganizer salva i file .hrf)
          </label>
          <input type="text" value={hrfFolder} onChange={e => setHrfFolder(e.target.value)}
            placeholder="/home/user/HRF" style={{ ...inputStyle, marginBottom: 12 }} />
          {error && <div style={{ color: '#dc2626', fontSize: 13, marginBottom: 8 }}>{error}</div>}
          <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
            <button type="submit" disabled={loading}
              style={{ background: '#3b82f6', color: '#fff', border: 'none', borderRadius: 6, padding: '8px 20px', cursor: 'pointer', fontSize: 14 }}>
              {loading ? 'Salvataggio...' : saved ? '✓ Salvato' : 'Salva'}
            </button>
            <HrfScanButton />
          </div>
        </form>
      </div>
    </div>
  )
}
