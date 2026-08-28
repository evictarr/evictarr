import { useEffect, useState } from 'react'
import { FiCheckCircle, FiXCircle } from 'react-icons/fi'
import { api, ApiError } from '../../api/client'
import type { Integration, JellyfinUser, ServiceName } from '../../api/types'
import styles from './Integrations.module.css'

const SERVICE_LABELS: Record<ServiceName, string> = {
  jellyfin: 'Jellyfin',
  seerr: 'Seerr',
  radarr: 'Radarr',
  sonarr: 'Sonarr',
}

export function IntegrationsSettings() {
  const [integrations, setIntegrations] = useState<Integration[] | null>(null)

  async function load() {
    const data = await api.get<Integration[]>('/api/integrations')
    setIntegrations(data)
  }

  useEffect(() => {
    load()
  }, [])

  if (!integrations) {
    return null
  }

  return (
    <div className={styles.page}>
      <h1 className={styles.title}>Integrations</h1>
      <p className={styles.hint}>
        Connect Evictarr to the services it manages. Base URL should include the scheme, for example
        http://jellyfin:8096.
      </p>
      <div className={styles.grid}>
        {integrations.map((integration) => (
          <IntegrationCard key={integration.service} integration={integration} onSaved={load} />
        ))}
      </div>
    </div>
  )
}

function IntegrationCard({ integration, onSaved }: { integration: Integration; onSaved: () => Promise<void> }) {
  const [baseUrl, setBaseUrl] = useState(integration.base_url ?? '')
  const [apiKey, setApiKey] = useState('')
  const [enabled, setEnabled] = useState(integration.enabled)
  const [jellyfinUserId, setJellyfinUserId] = useState((integration.extra_config.jellyfin_user_id as string) ?? '')
  const [jellyfinUsers, setJellyfinUsers] = useState<JellyfinUser[] | null>(null)
  const [saving, setSaving] = useState(false)
  const [testing, setTesting] = useState(false)
  const [testResult, setTestResult] = useState<{ ok: boolean; detail: string } | null>(null)
  const [error, setError] = useState<string | null>(null)

  async function handleSave() {
    setSaving(true)
    setError(null)
    try {
      const extraConfig =
        integration.service === 'jellyfin' && jellyfinUserId ? { jellyfin_user_id: jellyfinUserId } : {}
      await api.put(`/api/integrations/${integration.service}`, {
        base_url: baseUrl || null,
        api_key: apiKey || undefined,
        extra_config: extraConfig,
        enabled,
      })
      setApiKey('')
      await onSaved()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Something went wrong')
    } finally {
      setSaving(false)
    }
  }

  async function handleTest() {
    setTesting(true)
    setError(null)
    try {
      const result = await api.post<{ ok: boolean; detail: string }>(`/api/integrations/${integration.service}/test`)
      setTestResult(result)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Something went wrong')
    } finally {
      setTesting(false)
    }
  }

  async function handleLoadUsers() {
    setError(null)
    try {
      const users = await api.get<JellyfinUser[]>('/api/integrations/jellyfin/users')
      setJellyfinUsers(users)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Something went wrong')
    }
  }

  return (
    <section className={styles.card}>
      <h2 className={styles.cardTitle}>{SERVICE_LABELS[integration.service]}</h2>

      <label className={styles.label}>
        Base URL
        <input value={baseUrl} onChange={(e) => setBaseUrl(e.target.value)} placeholder="http://" />
      </label>

      <label className={styles.label}>
        API key
        <input
          type="password"
          value={apiKey}
          onChange={(e) => setApiKey(e.target.value)}
          placeholder={integration.has_api_key ? 'Unchanged' : 'Not set'}
        />
      </label>

      {integration.service === 'jellyfin' && (
        <label className={styles.label}>
          Jellyfin user to track
          <div className={styles.inline}>
            <select value={jellyfinUserId} onChange={(e) => setJellyfinUserId(e.target.value)}>
              <option value="">Not selected</option>
              {jellyfinUsers?.map((u) => (
                <option key={u.id} value={u.id}>
                  {u.name}
                </option>
              ))}
            </select>
            <button type="button" className={styles.secondaryButton} onClick={handleLoadUsers}>
              Load users
            </button>
          </div>
        </label>
      )}

      <label className={styles.checkboxLabel}>
        <input type="checkbox" checked={enabled} onChange={(e) => setEnabled(e.target.checked)} />
        Enabled
      </label>

      {error && <div className={styles.error}>{error}</div>}

      <div className={styles.actions}>
        <button type="button" className={styles.primaryButton} onClick={handleSave} disabled={saving}>
          Save
        </button>
        <button type="button" className={styles.secondaryButton} onClick={handleTest} disabled={testing}>
          Test connection
        </button>
      </div>

      {testResult && (
        <div className={testResult.ok ? styles.success : styles.error}>
          {testResult.ok ? <FiCheckCircle /> : <FiXCircle />} {testResult.detail}
        </div>
      )}

      {integration.last_test_at && !testResult && (
        <div className={integration.last_test_status === 'ok' ? styles.success : styles.error}>
          {integration.last_test_status === 'ok' ? <FiCheckCircle /> : <FiXCircle />} {integration.last_test_detail}
        </div>
      )}
    </section>
  )
}
