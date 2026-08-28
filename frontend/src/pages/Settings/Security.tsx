import { useState } from 'react'
import type { FormEvent } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { FiCheckCircle, FiLock } from 'react-icons/fi'
import { api, ApiError } from '../../api/client'
import { useAuth } from '../../api/AuthContext'
import styles from './Security.module.css'

export function SecuritySettings() {
  const { authMethod, refreshAuthConfig } = useAuth()
  const navigate = useNavigate()

  if (authMethod === 'loading') {
    return null
  }

  return (
    <div className={styles.page}>
      <h1 className={styles.title}>Security</h1>
      <section className={styles.card}>
        <h2 className={styles.cardTitle}>
          <FiLock /> Authentication method
        </h2>
        {authMethod === 'none' ? (
          <>
            <p className={styles.hint}>
              Evictarr currently has no login required - anyone who can reach this address can use it. Set a
              username and password below to require Basic (session login) authentication.
            </p>
            <EnableForm onEnabled={() => navigate('/login')} />
          </>
        ) : (
          <>
            <p className={styles.hint}>
              Evictarr currently requires a username and password to sign in. To change your password or manage two
              factor authentication, go to <Link to="/profile">My Profile</Link>.
            </p>
            <DisableForm onDisabled={refreshAuthConfig} />
          </>
        )}
      </section>
    </div>
  )
}

function EnableForm({ onEnabled }: { onEnabled: () => void }) {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)

  async function handleSubmit(event: FormEvent) {
    event.preventDefault()
    setError(null)
    if (!username || !password) {
      setError('Username and password are required')
      return
    }
    if (password !== confirmPassword) {
      setError('Passwords do not match')
      return
    }
    setSubmitting(true)
    try {
      await api.post('/api/auth/enable', { username, password })
      onEnabled()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Something went wrong')
      setSubmitting(false)
    }
  }

  return (
    <form onSubmit={handleSubmit} className={styles.form}>
      <label className={styles.label}>
        Username
        <input value={username} onChange={(e) => setUsername(e.target.value)} autoComplete="username" />
      </label>
      <label className={styles.label}>
        Password
        <input
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          autoComplete="new-password"
        />
      </label>
      <label className={styles.label}>
        Confirm password
        <input
          type="password"
          value={confirmPassword}
          onChange={(e) => setConfirmPassword(e.target.value)}
          autoComplete="new-password"
        />
      </label>
      {error && <div className={styles.error}>{error}</div>}
      <button type="submit" className={styles.submit} disabled={submitting}>
        Enable login
      </button>
    </form>
  )
}

function DisableForm({ onDisabled }: { onDisabled: () => Promise<void> }) {
  const [currentPassword, setCurrentPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [message, setMessage] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)

  async function handleSubmit(event: FormEvent) {
    event.preventDefault()
    setError(null)
    setMessage(null)
    setSubmitting(true)
    try {
      await api.post('/api/auth/disable', { current_password: currentPassword })
      setCurrentPassword('')
      setMessage('Login requirement turned off')
      await onDisabled()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Something went wrong')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <form onSubmit={handleSubmit} className={styles.form}>
      <label className={styles.label}>
        Current password
        <input
          type="password"
          value={currentPassword}
          onChange={(e) => setCurrentPassword(e.target.value)}
          autoComplete="current-password"
        />
      </label>
      {error && <div className={styles.error}>{error}</div>}
      {message && (
        <div className={styles.success}>
          <FiCheckCircle /> {message}
        </div>
      )}
      <button type="submit" className={styles.dangerButton} disabled={submitting}>
        Turn off login
      </button>
    </form>
  )
}
