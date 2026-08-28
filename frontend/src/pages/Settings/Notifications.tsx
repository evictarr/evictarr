import { useEffect, useState } from 'react'
import { FiCheckCircle, FiXCircle } from 'react-icons/fi'
import { api, ApiError } from '../../api/client'
import type { NotificationConfig, NotificationProviderName } from '../../api/types'
import styles from './Notifications.module.css'

const PROVIDER_LABELS: Record<NotificationProviderName, string> = {
  discord: 'Discord',
  telegram: 'Telegram',
}

export function NotificationsSettings() {
  const [configs, setConfigs] = useState<NotificationConfig[] | null>(null)

  async function load() {
    const data = await api.get<NotificationConfig[]>('/api/notifications/config')
    setConfigs(data)
  }

  useEffect(() => {
    load()
  }, [])

  if (!configs) {
    return null
  }

  return (
    <div className={styles.page}>
      <h1 className={styles.title}>Notifications</h1>
      <p className={styles.hint}>
        Get notified when something is queued for deletion, actually deleted, or after each scheduled scan.
      </p>
      <div className={styles.grid}>
        {configs.map((config) => (
          <ProviderCard key={config.provider} config={config} onSaved={load} />
        ))}
      </div>
    </div>
  )
}

function ProviderCard({ config, onSaved }: { config: NotificationConfig; onSaved: () => Promise<void> }) {
  const [enabled, setEnabled] = useState(config.enabled)
  const [webhookUrl, setWebhookUrl] = useState('')
  const [botToken, setBotToken] = useState('')
  const [chatId, setChatId] = useState((config.config_summary.chat_id as string) ?? '')
  const [notifyOnStage, setNotifyOnStage] = useState(config.notify_on_stage)
  const [notifyOnExecute, setNotifyOnExecute] = useState(config.notify_on_execute)
  const [notifyDailySummary, setNotifyDailySummary] = useState(config.notify_daily_summary)
  const [saving, setSaving] = useState(false)
  const [testing, setTesting] = useState(false)
  const [testResult, setTestResult] = useState<{ ok: boolean; detail: string } | null>(null)
  const [error, setError] = useState<string | null>(null)

  async function handleSave() {
    setSaving(true)
    setError(null)
    try {
      const configPayload =
        config.provider === 'discord' ? { webhook_url: webhookUrl || undefined } : { bot_token: botToken || undefined, chat_id: chatId || undefined }
      await api.put(`/api/notifications/config/${config.provider}`, {
        enabled,
        config: configPayload,
        notify_on_stage: notifyOnStage,
        notify_on_execute: notifyOnExecute,
        notify_daily_summary: notifyDailySummary,
      })
      setWebhookUrl('')
      setBotToken('')
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
      const result = await api.post<{ ok: boolean; detail: string }>(`/api/notifications/config/${config.provider}/test`)
      setTestResult(result)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Something went wrong')
    } finally {
      setTesting(false)
    }
  }

  return (
    <section className={styles.card}>
      <h2 className={styles.cardTitle}>{PROVIDER_LABELS[config.provider]}</h2>

      {config.provider === 'discord' ? (
        <label className={styles.label}>
          Webhook URL
          <input
            value={webhookUrl}
            onChange={(e) => setWebhookUrl(e.target.value)}
            placeholder={config.config_summary.webhook_url_set ? 'Unchanged' : 'https://discord.com/api/webhooks/...'}
          />
        </label>
      ) : (
        <>
          <label className={styles.label}>
            Bot token
            <input
              type="password"
              value={botToken}
              onChange={(e) => setBotToken(e.target.value)}
              placeholder={config.config_summary.bot_token_set ? 'Unchanged' : 'Not set'}
            />
          </label>
          <label className={styles.label}>
            Chat ID
            <input value={chatId} onChange={(e) => setChatId(e.target.value)} />
          </label>
        </>
      )}

      <div className={styles.checkboxGroup}>
        <label className={styles.checkboxLabel}>
          <input type="checkbox" checked={enabled} onChange={(e) => setEnabled(e.target.checked)} />
          Enabled
        </label>
        <label className={styles.checkboxLabel}>
          <input type="checkbox" checked={notifyOnStage} onChange={(e) => setNotifyOnStage(e.target.checked)} />
          Notify when something is queued
        </label>
        <label className={styles.checkboxLabel}>
          <input type="checkbox" checked={notifyOnExecute} onChange={(e) => setNotifyOnExecute(e.target.checked)} />
          Notify when something is deleted
        </label>
        <label className={styles.checkboxLabel}>
          <input
            type="checkbox"
            checked={notifyDailySummary}
            onChange={(e) => setNotifyDailySummary(e.target.checked)}
          />
          Notify with a scan summary
        </label>
      </div>

      {error && <div className={styles.error}>{error}</div>}

      <div className={styles.actions}>
        <button type="button" className={styles.primaryButton} onClick={handleSave} disabled={saving}>
          Save
        </button>
        <button type="button" className={styles.secondaryButton} onClick={handleTest} disabled={testing}>
          Send test
        </button>
      </div>

      {testResult && (
        <div className={testResult.ok ? styles.success : styles.error}>
          {testResult.ok ? <FiCheckCircle /> : <FiXCircle />} {testResult.detail}
        </div>
      )}
    </section>
  )
}
