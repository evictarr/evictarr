import { useState } from 'react'
import type { FormEvent } from 'react'
import { FiLock, FiShield, FiUser } from 'react-icons/fi'
import { useAuth, ApiError } from '../api/AuthContext'
import styles from './Login.module.css'

export function Login() {
  const { status, login, verifyMfa } = useAuth()
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [code, setCode] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)

  async function handleLogin(event: FormEvent) {
    event.preventDefault()
    setError(null)
    setSubmitting(true)
    try {
      await login(username, password)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Something went wrong')
    } finally {
      setSubmitting(false)
    }
  }

  async function handleMfaVerify(event: FormEvent) {
    event.preventDefault()
    setError(null)
    setSubmitting(true)
    try {
      await verifyMfa(code)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Something went wrong')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className={styles.page}>
      <div className={styles.card}>
        <div className={styles.brand}>
          <img src="/logo.svg" alt="" className={styles.logo} />
          Evictarr
        </div>

        {status === 'mfa-pending' ? (
          <form onSubmit={handleMfaVerify} className={styles.form}>
            <p className={styles.subtitle}>Enter the 6 digit code from your authenticator app</p>
            <label className={styles.field}>
              <FiShield />
              <input
                autoFocus
                inputMode="numeric"
                maxLength={6}
                placeholder="123456"
                value={code}
                onChange={(e) => setCode(e.target.value)}
              />
            </label>
            {error && <div className={styles.error}>{error}</div>}
            <button type="submit" disabled={submitting} className={styles.submit}>
              Verify
            </button>
          </form>
        ) : (
          <form onSubmit={handleLogin} className={styles.form}>
            <label className={styles.field}>
              <FiUser />
              <input
                autoFocus
                placeholder="Username"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
              />
            </label>
            <label className={styles.field}>
              <FiLock />
              <input
                type="password"
                placeholder="Password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
              />
            </label>
            {error && <div className={styles.error}>{error}</div>}
            <button type="submit" disabled={submitting} className={styles.submit}>
              Sign in
            </button>
          </form>
        )}
      </div>
    </div>
  )
}
