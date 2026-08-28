import { useEffect, useState } from 'react'
import { FiAlertTriangle, FiCheckCircle, FiChevronDown, FiChevronRight, FiXCircle } from 'react-icons/fi'
import { api } from '../api/client'
import type { ActionLogEntry, EventLevel, Run, RunEvent } from '../api/types'
import styles from './History.module.css'

type Tab = 'scans' | 'deletions'

export function History() {
  const [tab, setTab] = useState<Tab>('scans')

  return (
    <div className={styles.page}>
      <h1 className={styles.title}>History</h1>

      <div className={styles.tabs}>
        <button
          type="button"
          className={tab === 'scans' ? styles.tabActive : styles.tab}
          onClick={() => setTab('scans')}
        >
          Scans
        </button>
        <button
          type="button"
          className={tab === 'deletions' ? styles.tabActive : styles.tab}
          onClick={() => setTab('deletions')}
        >
          Deletions
        </button>
      </div>

      {tab === 'scans' ? <ScansTab /> : <DeletionsTab />}
    </div>
  )
}

function ScansTab() {
  const [runs, setRuns] = useState<Run[] | null>(null)
  const [expandedRunId, setExpandedRunId] = useState<number | null>(null)

  useEffect(() => {
    api.get<Run[]>('/api/runs').then(setRuns)
  }, [])

  if (!runs) {
    return null
  }

  return (
    <div className={styles.list}>
      {runs.length === 0 && <p className={styles.hint}>No scans have run yet.</p>}
      {runs.map((run) => (
        <RunRow
          key={run.id}
          run={run}
          expanded={expandedRunId === run.id}
          onToggle={() => setExpandedRunId(expandedRunId === run.id ? null : run.id)}
        />
      ))}
    </div>
  )
}

function RunRow({ run, expanded, onToggle }: { run: Run; expanded: boolean; onToggle: () => void }) {
  const [events, setEvents] = useState<RunEvent[] | null>(null)

  useEffect(() => {
    if (expanded && events === null) {
      api.get<RunEvent[]>(`/api/runs/${run.id}/events`).then(setEvents)
    }
  }, [expanded, events, run.id])

  return (
    <div className={styles.card}>
      <button type="button" className={styles.cardHeader} onClick={onToggle}>
        {expanded ? <FiChevronDown /> : <FiChevronRight />}
        <span className={styles.runType}>{run.run_type}</span>
        <span className={styles.timestamp}>{new Date(run.started_at).toLocaleString()}</span>
        <span className={styles.status} data-status={run.status}>
          {run.status}
        </span>
        <span className={styles.counts}>
          {run.items_scanned} scanned - {run.items_matched} matched - {run.items_skipped} skipped
        </span>
      </button>

      {expanded && (
        <div className={styles.events}>
          {events === null && <p className={styles.hint}>Loading...</p>}
          {events?.length === 0 && <p className={styles.hint}>No notable events for this run.</p>}
          {events?.map((event) => (
            <EventRow key={event.id} event={event} />
          ))}
        </div>
      )}
    </div>
  )
}

const LEVEL_ICON: Record<EventLevel, React.ReactNode> = {
  match: <FiCheckCircle />,
  skip: <FiXCircle />,
  error: <FiAlertTriangle />,
}

function EventRow({ event }: { event: RunEvent }) {
  return (
    <div className={styles.event} data-level={event.level}>
      {LEVEL_ICON[event.level]}
      <span className={styles.eventTitle}>{event.media_title ?? 'General'}</span>
      <span className={styles.eventReason}>{event.reason}</span>
    </div>
  )
}

function DeletionsTab() {
  const [entries, setEntries] = useState<ActionLogEntry[] | null>(null)

  useEffect(() => {
    api.get<ActionLogEntry[]>('/api/action-log').then(setEntries)
  }, [])

  if (!entries) {
    return null
  }

  return (
    <div className={styles.list}>
      {entries.length === 0 && <p className={styles.hint}>Nothing has been deleted yet.</p>}
      {entries.map((entry) => (
        <div key={entry.id} className={styles.card}>
          <div className={styles.deletionRow}>
            <span className={styles.overallStatus} data-status={entry.overall_status}>
              {entry.overall_status === 'success' ? <FiCheckCircle /> : <FiAlertTriangle />}
            </span>
            <span className={styles.eventTitle}>{entry.pending_deletion.title}</span>
            <span className={styles.timestamp}>{new Date(entry.executed_at).toLocaleString()}</span>
            <span className={styles.counts}>
              Seerr: {entry.seerr_status ?? 'n/a'} - Radarr/Sonarr: {entry.radarr_sonarr_status ?? 'n/a'}
            </span>
          </div>
        </div>
      ))}
    </div>
  )
}
