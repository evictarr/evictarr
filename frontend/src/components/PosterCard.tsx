import { useState } from 'react'
import styles from './PosterCard.module.css'

export function PosterCard({
  posterId,
  title,
  statusLine,
}: {
  posterId: string | null
  title: string
  statusLine: string
}) {
  const [imgFailed, setImgFailed] = useState(false)

  return (
    <div className={styles.card}>
      {posterId && !imgFailed ? (
        <img
          className={styles.poster}
          src={`/api/media/poster/${posterId}`}
          alt={title}
          onError={() => setImgFailed(true)}
        />
      ) : (
        <div className={styles.posterPlaceholder} aria-hidden="true" />
      )}
      <div className={styles.title}>{title}</div>
      <div className={styles.statusLine}>{statusLine}</div>
    </div>
  )
}
