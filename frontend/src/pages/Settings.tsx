import { useState, useEffect, FormEvent } from 'react'
import { useSearchParams } from 'react-router-dom'
import { useQueryClient } from '@tanstack/react-query'
import { getSettings } from '../api/settings'
import { initiateOAuth } from '../api/auth'
import { getHrfSettings, saveHrfSettings } from '../api/hrf'
import { HrfScanButton } from '../components/HrfScanButton'

export function Settings() {
  const [searchParams, setSearchParams] = useSearchParams()
  const justAuthorized = searchParams.get('authorized') === 'true'
  const qc = useQueryClient()

  const [consumerKey, setConsumerKey] = useState('')
  const [consumerSecret, setConsumerSecret] = useState('')
  const [oauthComplete, setOauthComplete] = useState(false)
  const [chppLoading, setChppLoading] = useState(false)
  const [chppError, setChppError] = useState<string | null>(null)

  const [hrfFolder, setHrfFolder] = useState('')
  const [hrfSaved, setHrfSaved] = useState(false)
  const [hrfError, setHrfError] = useState<string | null>(null)
  const [hrfLoading, setHrfLoading] = useState(false)

  useEffect(() => {
    getSettings().then((s) => {
      if (s.configured) {
        setConsumerKey(s.consumer_key ?? '')
        setOauthComplete(s.oauth_complete ?? false)
      }
    })
    if (justAuthorized) {
      setOauthComplete(true)
      setSearchParams({}, { replace: true })
    }
    getHrfSettings()
      .then((s) => setHrfFolder(s.hrf_folder_path))
      .catch(() => {})
  }, [])

  async function handleSaveHrf(e: FormEvent) {
    e.preventDefault()
    setHrfLoading(true)
    setHrfError(null)
    try {
      await saveHrfSettings({ hrf_folder_path: hrfFolder, team_id: null, enabled: true })
      setHrfSaved(true)
      setTimeout(() => setHrfSaved(false), 3000)
    } catch (err: unknown) {
      setHrfError(err instanceof Error ? err.message : 'Errore')
    } finally {
      setHrfLoading(false)
    }
  }

  async function handleAuthorize(e: FormEvent) {
    e.preventDefault()
    if (!consumerKey || !consumerSecret) {
      setChppError('Inserisci consumer key e consumer secret.')
      return
    }
    setChppLoading(true)
    setChppError(null)
    try {
      const { auth_url } = await initiateOAuth(consumerKey, consumerSecret)
      window.location.href = auth_url
    } catch (err: unknown) {
      setChppError(err instanceof Error ? err.message : 'Errore durante la richiesta token')
      setChppLoading(false)
    }
  }

  return (
    <div style={{ maxWidth: 520 }}>
      <h1 style={{ marginTop: 0 }}>Impostazioni</h1>

      <section style={{ marginBottom: 32 }}>
        <h2 style={{ fontSize: 18, marginTop: 0, marginBottom: 16 }}>Importazione HRF</h2>
        <form onSubmit={handleSaveHrf}>
          <div style={{ marginBottom: 14 }}>
            <label style={{ display: 'block', marginBottom: 4, fontWeight: 500, fontSize: 14 }}>
              Cartella file HRF
            </label>
            <input
              type="text"
              value={hrfFolder}
              onChange={(e) => setHrfFolder(e.target.value)}
              placeholder="/program/ho/"
              style={inputStyle}
            />
          </div>
          <div style={{ display: 'flex', gap: 12, alignItems: 'center', marginBottom: 16 }}>
            <button type="submit" disabled={hrfLoading} style={buttonStyle(hrfLoading)}>
              {hrfLoading ? 'Salvataggio…' : 'Salva percorso'}
            </button>
            {hrfSaved && <span style={{ fontSize: 12, color: '#16a34a' }}>✓ Salvato</span>}
            {hrfError && <span style={{ fontSize: 12, color: '#ef4444' }}>{hrfError}</span>}
          </div>
        </form>
        <HrfScanButton onScanned={() => {
          qc.invalidateQueries({ queryKey: ['squad'] })
          qc.invalidateQueries({ queryKey: ['training'] })
        }} />
      </section>

      <details>
        <summary
          style={{ cursor: 'pointer', color: '#6b7280', fontSize: 14, userSelect: 'none', marginBottom: 4 }}
        >
          Configurazione CHPP (avanzata)
        </summary>
        <div style={{ marginTop: 16 }}>
          {oauthComplete ? (
            <div
              style={{
                padding: '16px 20px',
                background: '#f0fdf4',
                border: '1px solid #bbf7d0',
                borderRadius: 8,
                marginBottom: 24,
              }}
            >
              <div style={{ fontWeight: 600, color: '#15803d' }}>✓ Autorizzato con Hattrick</div>
              <div style={{ fontSize: 13, color: '#16a34a', marginTop: 4 }}>
                I token CHPP sono salvati.
              </div>
            </div>
          ) : (
            <div
              style={{
                padding: '16px 20px',
                background: '#fefce8',
                border: '1px solid #fde047',
                borderRadius: 8,
                marginBottom: 24,
              }}
            >
              <div style={{ fontWeight: 600, color: '#854d0e' }}>⏳ Non ancora autorizzato</div>
              <div style={{ fontSize: 13, color: '#92400e', marginTop: 4 }}>
                Richiedi l&apos;accesso CHPP su{' '}
                <a href="https://chpp.hattrick.org/" target="_blank" rel="noreferrer">
                  chpp.hattrick.org
                </a>
                , poi inserisci le credenziali qui sotto.
              </div>
            </div>
          )}

          <form onSubmit={handleAuthorize}>
            <h2 style={{ fontSize: 16, marginBottom: 16 }}>Credenziali applicazione</h2>
            <div style={{ marginBottom: 14 }}>
              <label style={{ display: 'block', marginBottom: 4, fontWeight: 500, fontSize: 14 }}>
                Consumer Key
              </label>
              <input
                type="text"
                value={consumerKey}
                onChange={(e) => setConsumerKey(e.target.value)}
                style={inputStyle}
              />
            </div>
            <div style={{ marginBottom: 20 }}>
              <label style={{ display: 'block', marginBottom: 4, fontWeight: 500, fontSize: 14 }}>
                Consumer Secret
              </label>
              <input
                type="password"
                value={consumerSecret}
                onChange={(e) => setConsumerSecret(e.target.value)}
                style={inputStyle}
              />
            </div>
            <button type="submit" disabled={chppLoading} style={buttonStyle(chppLoading)}>
              {chppLoading ? 'Connessione a Hattrick…' : 'Autorizza con Hattrick →'}
            </button>
            {chppError && (
              <p style={{ marginTop: 10, color: '#ef4444', fontSize: 13 }}>{chppError}</p>
            )}
          </form>

          <div
            style={{
              marginTop: 32,
              padding: '14px 16px',
              background: '#f8fafc',
              borderRadius: 6,
              fontSize: 12,
              color: '#64748b',
            }}
          >
            <strong>Come funziona:</strong> Cliccando il bottone, verrai reindirizzato su Hattrick
            per autorizzare l&apos;accesso. Dopo l&apos;autorizzazione tornerai automaticamente qui
            con i token salvati.
          </div>
        </div>
      </details>
    </div>
  )
}

const inputStyle: React.CSSProperties = {
  width: '100%',
  padding: '8px 10px',
  border: '1px solid #d1d5db',
  borderRadius: 6,
  fontSize: 14,
  boxSizing: 'border-box',
}

function buttonStyle(disabled: boolean): React.CSSProperties {
  return {
    padding: '9px 20px',
    background: disabled ? '#93c5fd' : '#3b82f6',
    color: '#fff',
    border: 'none',
    borderRadius: 6,
    cursor: disabled ? 'not-allowed' : 'pointer',
    fontSize: 14,
    fontWeight: 500,
  }
}
