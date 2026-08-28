// frontend/src/pages/Dashboard.tsx
import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api, ApiError } from '../api/client'
import type { PendingDeletion, WatchedStatusResponse } from '../api/types'
import { PosterCard } from '../components/PosterCard'
import styles from './Dashboard.module.css'

const MEDIA_TYPE_LABELS: Record<string, string> = {
  movie: 'Movie',
  series: 'Series',
  season: 'Season',
}

function daysAgo(iso: string | null): string {
  if (!iso) return 'watched'
  const days = Math.floor((Date.now() - new Date(iso).getTime()) / 86400000)
  if (days <= 0) return 'watched today'
  if (days === 1) return 'watched 1 day ago'
  return `watched ${days} days ago`
}

function remainingText(hours: number | null): string {
  if (hours === null) return ''
  if (hours < 1) return 'due within the hour'
  const days = Math.floor(hours / 24)
  if (days >= 1) return `${days}d left`
  return `${Math.round(hours)}h left`
}

function pendingCountdown(executeAfter: string): string {
  const diffMs = new Date(executeAfter).getTime() - Date.now()
  if (diffMs <= 0) return 'due now'
  const hours = Math.floor(diffMs / 3600000)
  const minutes = Math.floor((diffMs % 3600000) / 60000)
  if (hours > 0) return `in ${hours}h ${minutes}m`
  return `in ${minutes}m`
}

export function Dashboard() {
  const [watchedStatus, setWatchedStatus] = useState<WatchedStatusResponse | null>(null)
  const [watchedError, setWatchedError] = useState<string | null>(null)
  const [watchedLoading, setWatchedLoading] = useState(true)
  const [pending, setPending] = useState<PendingDeletion[] | null>(null)
  const [pendingError, setPendingError] = useState<string | null>(null)
  const [pendingLoading, setPendingLoading] = useState(true)

  useEffect(() => {
    api
      .get<WatchedStatusResponse>('/api/dashboard/watched-status')
      .then(setWatchedStatus)
      .catch((err) => setWatchedError(err instanceof ApiError ? err.message : 'Something went wrong'))
      .finally(() => setWatchedLoading(false))

    api
      .get<PendingDeletion[]>('/api/pending-deletions?status=pending')
      .then(setPending)
      .catch((err) => setPendingError(err instanceof ApiError ? err.message : 'Something went wrong'))
      .finally(() => setPendingLoading(false))
  }, [])

  if (watchedLoading || pendingLoading) {
    return (
      <div className={styles.page}>
        <h1 className={styles.title}>Dashboard</h1>
        <p className={styles.hint}>Loading...</p>
      </div>
    )
  }

  const approaching = watchedStatus?.approaching ?? []
  const exempt = watchedStatus?.exempt ?? []
  const pendingPreview = (pending ?? []).slice(0, 6)

  return (
    <div className={styles.page}>
      <h1 className={styles.title}>Dashboard</h1>

      <section className={styles.section}>
        <h2 className={styles.sectionTitle}>Approaching cleanup</h2>
        {watchedError && <p className={styles.error}>{watchedError}</p>}
        {!watchedError && approaching.length === 0 && (
          <p className={styles.hint}>Nothing approaching cleanup right now.</p>
        )}
        <div className={styles.grid}>
          {approaching.map((item) => (
            <PosterCard
              key={`${item.rule_id}-${item.jellyfin_item_id}`}
              posterId={item.jellyfin_item_id}
              title={item.title}
              statusLine={`${item.rule_name} · ${remainingText(item.hours_remaining)}`}
            />
          ))}
        </div>
      </section>

      <section className={styles.section}>
        <h2 className={styles.sectionTitle}>Exempt (favorited)</h2>
        {!watchedError && exempt.length === 0 && <p className={styles.hint}>Nothing exempted right now.</p>}
        <div className={styles.grid}>
          {exempt.map((item) => (
            <PosterCard
              key={`${item.rule_id}-${item.jellyfin_item_id}`}
              posterId={item.jellyfin_item_id}
              title={item.title}
              statusLine={`${daysAgo(item.watched_at)} · favorited`}
            />
          ))}
        </div>
      </section>

      <section className={styles.section}>
        <div className={styles.sectionHeaderRow}>
          <h2 className={styles.sectionTitle}>Pending deletion</h2>
          <Link to="/pending-deletions" className={styles.viewAllLink}>
            View all &rarr;
          </Link>
        </div>
        {pendingError && <p className={styles.error}>{pendingError}</p>}
        {!pendingError && pendingPreview.length === 0 && (
          <p className={styles.hint}>Nothing is queued for deletion right now.</p>
        )}
        <div className={styles.grid}>
          {pendingPreview.map((item) => (
            <PosterCard
              key={item.id}
              posterId={(item.external_ids.jellyfin_item_id as string | undefined) ?? null}
              title={item.title}
              statusLine={`${MEDIA_TYPE_LABELS[item.media_type]} · ${pendingCountdown(item.execute_after)}`}
            />
          ))}
        </div>
      </section>
    </div>
  )
}
