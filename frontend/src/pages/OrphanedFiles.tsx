import { useEffect, useState } from 'react'
import { FiCheck, FiSearch } from 'react-icons/fi'
import { api, ApiError } from '../api/client'
import type { OrphanedFile } from '../api/types'
import styles from './OrphanedFiles.module.css'

function formatSize(bytes: number): string {
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`
  if (bytes < 1024 * 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(0)} MB`
  return `${(bytes / (1024 * 1024 * 1024)).toFixed(1)} GB`
}

export function OrphanedFiles() {
  const [items, setItems] = useState<OrphanedFile[] | null>(null)
  const [scanning, setScanning] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [message, setMessage] = useState<string | null>(null)

  async function load() {
    const data = await api.get<OrphanedFile[]>('/api/orphaned-files?status=open')
    setItems(data)
  }

  useEffect(() => {
    load()
  }, [])

  async function handleScan() {
    setScanning(true)
    setError(null)
    setMessage(null)
    try {
      const result = await api.post<{ found: number }>('/api/orphaned-files/scan')
      setMessage(result.found === 0 ? 'No new orphaned files found' : `Found ${result.found} new orphaned file(s)`)
      await load()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Something went wrong')
    } finally {
      setScanning(false)
    }
  }

  async function handleClear(item: OrphanedFile) {
    setError(null)
    try {
      await api.post(`/api/orphaned-files/${item.id}/clear`)
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
      <div className={styles.headerRow}>
        <h1 className={styles.title}>Orphaned files</h1>
        <button type="button" className={styles.primaryButton} onClick={handleScan} disabled={scanning}>
          <FiSearch /> Scan now
        </button>
      </div>
      <p className={styles.hint}>
        Files on disk that Radarr or Sonarr no longer track - left behind by a manual deletion or a failed import.
        This is a read-only report, nothing here is deleted automatically. Review and clear each one yourself.
      </p>

      {error && <div className={styles.error}>{error}</div>}
      {message && <div className={styles.success}>{message}</div>}

      {items.length === 0 && <p className={styles.hint}>Nothing to review right now.</p>}

      <div className={styles.list}>
        {items.map((item) => (
          <div key={item.id} className={styles.card}>
            <div className={styles.cardMain}>
              <span className={styles.cardPath}>{item.path}</span>
              <span className={styles.cardMeta}>
                {item.service_context} - {formatSize(item.size_bytes)}
              </span>
            </div>
            <button type="button" className={styles.clearButton} onClick={() => handleClear(item)}>
              <FiCheck /> Clear
            </button>
          </div>
        ))}
      </div>
    </div>
  )
}
