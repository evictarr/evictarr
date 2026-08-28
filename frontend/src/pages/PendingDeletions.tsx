import { useEffect, useState } from 'react'
import { FiClock, FiXCircle } from 'react-icons/fi'
import { api, ApiError } from '../api/client'
import type { PendingDeletion } from '../api/types'
import styles from './PendingDeletions.module.css'

const MEDIA_TYPE_LABELS: Record<string, string> = {
  movie: 'Movie',
  series: 'Series',
  season: 'Season',
}

function timeRemaining(executeAfter: string): string {
  const diffMs = new Date(executeAfter).getTime() - Date.now()
  if (diffMs <= 0) return 'due now'
  const hours = Math.floor(diffMs / 3600000)
  const minutes = Math.floor((diffMs % 3600000) / 60000)
  if (hours > 0) return `in ${hours}h ${minutes}m`
  return `in ${minutes}m`
}

export function PendingDeletions() {
  const [items, setItems] = useState<PendingDeletion[] | null>(null)
  const [error, setError] = useState<string | null>(null)

  async function load() {
    const data = await api.get<PendingDeletion[]>('/api/pending-deletions?status=pending')
    setItems(data)
  }

  useEffect(() => {
    load()
  }, [])

  async function handleCancel(item: PendingDeletion) {
    setError(null)
    try {
      await api.post(`/api/pending-deletions/${item.id}/cancel`, { reason: 'cancelled from UI' })
      await load()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Something went wrong')
    }
  }

  if (!items) {
    return null
  }

  return (
    <div className={styles.page}>
      <h1 className={styles.title}>Pending deletions</h1>
      <p className={styles.hint}>
        Items matched by a rule wait here before anything is deleted. Cancel anything you want to keep before its
        timer runs out.
      </p>

      {error && <div className={styles.error}>{error}</div>}

      {items.length === 0 && <p className={styles.hint}>Nothing is queued for deletion right now.</p>}

      <div className={styles.list}>
        {items.map((item) => (
          <div key={item.id} className={styles.card}>
            <div className={styles.cardMain}>
              <span className={styles.cardTitle}>{item.title}</span>
              <span className={styles.cardMeta}>
                {MEDIA_TYPE_LABELS[item.media_type]}
                {' - '}
                <FiClock className={styles.clockIcon} /> {timeRemaining(item.execute_after)}
              </span>
            </div>
            <button type="button" className={styles.cancelButton} onClick={() => handleCancel(item)}>
              <FiXCircle /> Cancel
            </button>
          </div>
        ))}
      </div>
    </div>
  )
}
