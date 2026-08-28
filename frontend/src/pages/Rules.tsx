import { useEffect, useState } from 'react'
import type { FormEvent } from 'react'
import { FiEdit2, FiLoader, FiPlay, FiPlus, FiTrash2 } from 'react-icons/fi'
import { api, ApiError } from '../api/client'
import type { Rule, RuleFormValues, RuleType, SeriesGranularity, ThresholdUnit } from '../api/types'
import styles from './Rules.module.css'

const RULE_TYPE_LABELS: Record<RuleType, string> = {
  movie_watched_cleanup: 'Movie watched cleanup',
  series_watched_cleanup: 'Series or season watched cleanup',
  stale_request_cleanup: 'Stale request cleanup',
}

const GRANULARITY_LABELS: Record<SeriesGranularity, string> = {
  series: 'Whole series',
  season: 'Individual season',
}

const EMPTY_FORM: RuleFormValues = {
  name: '',
  rule_type: 'movie_watched_cleanup',
  threshold_value: 30,
  threshold_unit: 'days',
  granularity: null,
  exempt_favorite: true,
  enabled: true,
}

export function Rules() {
  const [rules, setRules] = useState<Rule[] | null>(null)
  const [editing, setEditing] = useState<Rule | 'new' | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [runningRuleId, setRunningRuleId] = useState<number | null>(null)

  async function load() {
    const data = await api.get<Rule[]>('/api/rules')
    setRules(data)
  }

  useEffect(() => {
    load()
  }, [])

  async function handleDelete(rule: Rule) {
    setError(null)
    try {
      await api.delete(`/api/rules/${rule.id}`)
      await load()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Something went wrong')
    }
  }

  async function handleToggle(rule: Rule) {
    setError(null)
    try {
      await api.post(`/api/rules/${rule.id}/toggle`)
      await load()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Something went wrong')
    }
  }

  async function handleRunNow(rule: Rule) {
    setError(null)
    setRunningRuleId(rule.id)
    try {
      await api.post('/api/runs/run-now', { rule_ids: [rule.id] })
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Something went wrong')
    } finally {
      setRunningRuleId(null)
    }
  }

  if (!rules) {
    return null
  }

  return (
    <div className={styles.page}>
      <div className={styles.headerRow}>
        <h1 className={styles.title}>Rules</h1>
        <button type="button" className={styles.primaryButton} onClick={() => setEditing('new')}>
          <FiPlus /> New rule
        </button>
      </div>

      {error && <div className={styles.error}>{error}</div>}

      {editing && (
        <RuleForm
          rule={editing === 'new' ? null : editing}
          onDone={async () => {
            setEditing(null)
            await load()
          }}
          onCancel={() => setEditing(null)}
        />
      )}

      <div className={styles.list}>
        {rules.length === 0 && <p className={styles.hint}>No rules yet. Add one to start cleaning up your library.</p>}
        {rules.map((rule) => (
          <div key={rule.id} className={styles.card}>
            <div className={styles.cardMain}>
              <div className={styles.cardTitleRow}>
                <span className={styles.cardTitle}>{rule.name}</span>
                {!rule.enabled && <span className={styles.disabledBadge}>Disabled</span>}
              </div>
              <div className={styles.cardMeta}>
                {RULE_TYPE_LABELS[rule.rule_type]}
                {rule.granularity && ` - ${GRANULARITY_LABELS[rule.granularity]}`}
                {' - after '}
                {rule.threshold_value} {rule.threshold_unit}
              </div>
            </div>
            <div className={styles.cardActions}>
              <button
                type="button"
                className={styles.iconButton}
                title={runningRuleId === rule.id ? 'Running...' : 'Run this rule now'}
                onClick={() => handleRunNow(rule)}
                disabled={runningRuleId === rule.id}
              >
                {runningRuleId === rule.id ? <FiLoader className={styles.spin} /> : <FiPlay />}
              </button>
              <button type="button" className={styles.iconButton} title="Edit" onClick={() => setEditing(rule)}>
                <FiEdit2 />
              </button>
              <button
                type="button"
                className={styles.iconButton}
                title="Delete"
                onClick={() => handleDelete(rule)}
              >
                <FiTrash2 />
              </button>
              <label className={styles.switch}>
                <input type="checkbox" checked={rule.enabled} onChange={() => handleToggle(rule)} />
                <span className={styles.slider} />
              </label>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

function RuleForm({
  rule,
  onDone,
  onCancel,
}: {
  rule: Rule | null
  onDone: () => Promise<void>
  onCancel: () => void
}) {
  const [values, setValues] = useState<RuleFormValues>(
    rule
      ? {
          name: rule.name,
          rule_type: rule.rule_type,
          threshold_value: rule.threshold_value,
          threshold_unit: rule.threshold_unit,
          granularity: rule.granularity,
          exempt_favorite: true,
          enabled: rule.enabled,
        }
      : EMPTY_FORM,
  )
  const [error, setError] = useState<string | null>(null)
  const [saving, setSaving] = useState(false)

  async function handleSubmit(event: FormEvent) {
    event.preventDefault()
    setError(null)
    setSaving(true)
    try {
      const payload = {
        name: values.name,
        threshold_value: values.threshold_value,
        threshold_unit: values.threshold_unit,
        granularity: values.rule_type === 'series_watched_cleanup' ? values.granularity : null,
        exempt_favorite: true,
        enabled: values.enabled,
      }
      if (rule) {
        await api.put(`/api/rules/${rule.id}`, payload)
      } else {
        await api.post('/api/rules', { ...payload, rule_type: values.rule_type })
      }
      await onDone()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Something went wrong')
    } finally {
      setSaving(false)
    }
  }

  return (
    <form onSubmit={handleSubmit} className={styles.form}>
      <label className={styles.label}>
        Name
        <input value={values.name} onChange={(e) => setValues({ ...values, name: e.target.value })} required />
      </label>

      <label className={styles.label}>
        Rule type
        <select
          value={values.rule_type}
          disabled={rule !== null}
          onChange={(e) =>
            setValues({
              ...values,
              rule_type: e.target.value as RuleType,
              granularity: e.target.value === 'series_watched_cleanup' ? 'season' : null,
            })
          }
        >
          {Object.entries(RULE_TYPE_LABELS).map(([value, label]) => (
            <option key={value} value={value}>
              {label}
            </option>
          ))}
        </select>
      </label>

      {values.rule_type === 'series_watched_cleanup' && (
        <label className={styles.label}>
          Granularity
          <select
            value={values.granularity ?? 'season'}
            onChange={(e) => setValues({ ...values, granularity: e.target.value as SeriesGranularity })}
          >
            {Object.entries(GRANULARITY_LABELS).map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </select>
        </label>
      )}

      <div className={styles.inline}>
        <label className={styles.label}>
          After
          <input
            type="number"
            min={1}
            value={values.threshold_value}
            onChange={(e) => setValues({ ...values, threshold_value: Number(e.target.value) })}
          />
        </label>
        <label className={styles.label}>
          &nbsp;
          <select
            value={values.threshold_unit}
            onChange={(e) => setValues({ ...values, threshold_unit: e.target.value as ThresholdUnit })}
          >
            {(['hours', 'days', 'weeks', 'months', 'years'] as ThresholdUnit[]).map((unit) => (
              <option key={unit} value={unit}>
                {unit}
              </option>
            ))}
          </select>
        </label>
      </div>

      <p className={styles.hint}>Anything marked as favorite in Jellyfin is always kept, no matter what.</p>

      <label className={styles.checkboxLabel}>
        <input
          type="checkbox"
          checked={values.enabled}
          onChange={(e) => setValues({ ...values, enabled: e.target.checked })}
        />
        Enabled
      </label>

      {error && <div className={styles.error}>{error}</div>}

      <div className={styles.actions}>
        <button type="submit" className={styles.primaryButton} disabled={saving}>
          Save
        </button>
        <button type="button" className={styles.secondaryButton} onClick={onCancel}>
          Cancel
        </button>
      </div>
    </form>
  )
}
