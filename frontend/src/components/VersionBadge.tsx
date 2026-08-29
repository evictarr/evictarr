import { useEffect, useState } from 'react'
import { api } from '../api/client'
import type { VersionResponse } from '../api/types'
import styles from './VersionBadge.module.css'

const REPO = 'evictarr/evictarr'

interface GithubRelease {
  tag_name: string
  html_url: string
}

type Status = 'loading' | 'latest' | 'update-available' | 'unknown'

export function VersionBadge() {
  const [version, setVersion] = useState<string | null>(null)
  const [status, setStatus] = useState<Status>('loading')
  const [releaseUrl, setReleaseUrl] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false

    api
      .get<VersionResponse>('/api/version')
      .then((res) => {
        if (cancelled) return
        setVersion(res.version)

        // Public, unauthenticated GitHub endpoint - fetched directly from
        // the browser rather than through the backend, since it needs no
        // credentials and this keeps the backend from needing outbound
        // internet access just to render a badge.
        return fetch(`https://api.github.com/repos/${REPO}/releases/latest`)
          .then((r) => (r.ok ? (r.json() as Promise<GithubRelease>) : Promise.reject(new Error('bad response'))))
          .then((release) => {
            if (cancelled) return
            setReleaseUrl(release.html_url)
            const latest = release.tag_name.replace(/^v/, '')
            setStatus(latest === res.version ? 'latest' : 'update-available')
          })
      })
      .catch(() => {
        if (!cancelled) setStatus('unknown')
      })

    return () => {
      cancelled = true
    }
  }, [])

  if (!version) {
    return null
  }

  const badgeClass =
    status === 'latest' ? styles.latest : status === 'update-available' ? styles.updateAvailable : styles.unknown

  const label = status === 'update-available' ? `v${version} · update available` : `v${version}`

  if (!releaseUrl) {
    return (
      <span className={`${styles.badge} ${badgeClass}`} title="Current version">
        {label}
      </span>
    )
  }

  return (
    <a
      className={`${styles.badge} ${badgeClass}`}
      href={releaseUrl}
      target="_blank"
      rel="noopener noreferrer"
      title={status === 'update-available' ? 'A newer release is available - click to view it' : 'You are on the latest release'}
    >
      {label}
    </a>
  )
}
