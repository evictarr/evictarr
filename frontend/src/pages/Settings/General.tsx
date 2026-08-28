import { useEffect, useState } from 'react'
import type { FormEvent } from 'react'
import { FiCheckCircle } from 'react-icons/fi'
import { api, ApiError } from '../../api/client'
import type { AppSettings } from '../../api/types'
import styles from './General.module.css'

export function GeneralSettings() {
  const [values, setValues] = useState<AppSettings | null>(null)
  const [message, setMessage] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    api.get<AppSettings>('/api/settings').then((data) => setValues({ ...data, scheduler_time: data.scheduler_time.slice(0, 5) }))
  }, [])

  async function handleSubmit(event: FormEvent) {
    event.preventDefault()
    if (!values) return
    setError(null)
    setMessage(null)
    setSaving(true)
    try {
      const payload = { ...values, scheduler_time: `${values.scheduler_time}:00` }
      const saved = await api.put<AppSettings>('/api/settings', payload)
      setValues({ ...saved, scheduler_time: saved.scheduler_time.slice(0, 5) })
      setMessage('Settings saved')
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Something went wrong')
    } finally {
      setSaving(false)
    }
  }

  if (!values) {
    return null
  }

  return (
    <div className={styles.page}>
      <h1 className={styles.title}>General</h1>
      <form onSubmit={handleSubmit} className={styles.form}>
        <label className={styles.label}>
          Daily scan time
          <input
            type="time"
            value={values.scheduler_time}
            onChange={(e) => setValues({ ...values, scheduler_time: e.target.value })}
          />
        </label>

        <label className={styles.label}>
          Timezone
          <input
            value={values.timezone}
            onChange={(e) => setValues({ ...values, timezone: e.target.value })}
            placeholder="e.g. Europe/Chisinau"
          />
        </label>

        <label className={styles.label}>
          Grace period before deletion (hours)
          <input
            type="number"
            min={0}
            value={values.default_grace_period_hours}
            onChange={(e) => setValues({ ...values, default_grace_period_hours: Number(e.target.value) })}
          />
        </label>

        <label className={styles.label}>
          Deletion check interval (minutes)
          <input
            type="number"
            min={1}
            value={values.executor_interval_minutes}
            onChange={(e) => setValues({ ...values, executor_interval_minutes: Number(e.target.value) })}
          />
        </label>

        <label className={styles.label}>
          Keep history for (days)
          <input
            type="number"
            min={1}
            value={values.log_retention_days}
            onChange={(e) => setValues({ ...values, log_retention_days: Number(e.target.value) })}
          />
        </label>

        {error && <div className={styles.error}>{error}</div>}
        {message && (
          <div className={styles.success}>
            <FiCheckCircle /> {message}
          </div>
        )}

        <button type="submit" className={styles.submit} disabled={saving}>
          Save
        </button>
      </form>
    </div>
  )
}
