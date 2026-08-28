import styles from './Dashboard.module.css'

export function Dashboard() {
  return (
    <div className={styles.page}>
      <h1 className={styles.title}>Dashboard</h1>
      <p className={styles.hint}>
        Nothing to show yet. Once integrations and rules are configured, scan results will appear here.
      </p>
    </div>
  )
}
