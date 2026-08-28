import { useState } from 'react'
import type { FormEvent } from 'react'
import { Navigate } from 'react-router-dom'
import { FiCheckCircle, FiShield } from 'react-icons/fi'
import { api, ApiError } from '../api/client'
import { useAuth } from '../api/AuthContext'
import type { MfaEnrollResponse } from '../api/types'
import styles from './Profile.module.css'

export function Profile() {
  const { session, authMethod, refreshSession } = useAuth()

  // Profile/MFA is meaningless with no login wall - guard against a direct
  // deep-link, since the nav entry is already hidden in this state.
  if (authMethod === 'none') {
    return <Navigate to="/" replace />
  }

  return (
    <div className={styles.page}>
      <h1 className={styles.title}>My Profile</h1>
      <ChangePasswordCard />
      <MfaCard mfaEnabled={session?.mfa_enabled ?? false} onChanged={refreshSession} />
    </div>
  )
}

function ChangePasswordCard() {
  const [currentPassword, setCurrentPassword] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [message, setMessage] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  async function handleSubmit(event: FormEvent) {
    event.preventDefault()
    setError(null)
    setMessage(null)
    if (newPassword !== confirmPassword) {
      setError('New passwords do not match')
      return
    }
    try {
      await api.post('/api/profile/change-password', {
        current_password: currentPassword,
        new_password: newPassword,
      })
      setMessage('Password updated')
      setCurrentPassword('')
      setNewPassword('')
      setConfirmPassword('')
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Something went wrong')
    }
  }

  return (
    <section className={styles.card}>
      <h2 className={styles.cardTitle}>Change password</h2>
      <form onSubmit={handleSubmit} className={styles.form}>
        <label className={styles.label}>
          Current password
          <input
            type="password"
            value={currentPassword}
            onChange={(e) => setCurrentPassword(e.target.value)}
          />
        </label>
        <label className={styles.label}>
          New password
          <input type="password" value={newPassword} onChange={(e) => setNewPassword(e.target.value)} />
        </label>
        <label className={styles.label}>
          Confirm new password
          <input
            type="password"
            value={confirmPassword}
            onChange={(e) => setConfirmPassword(e.target.value)}
          />
        </label>
        {error && <div className={styles.error}>{error}</div>}
        {message && (
          <div className={styles.success}>
            <FiCheckCircle /> {message}
          </div>
        )}
        <button type="submit" className={styles.submit}>
          Update password
        </button>
      </form>
    </section>
  )
}

function MfaCard({ mfaEnabled, onChanged }: { mfaEnabled: boolean; onChanged: () => Promise<void> }) {
  const [enrollment, setEnrollment] = useState<MfaEnrollResponse | null>(null)
  const [confirmCode, setConfirmCode] = useState('')
  const [disablePassword, setDisablePassword] = useState('')
  const [disableCode, setDisableCode] = useState('')
  const [error, setError] = useState<string | null>(null)

  async function startEnroll() {
    setError(null)
    try {
      const response = await api.post<MfaEnrollResponse>('/api/profile/mfa/enroll')
      setEnrollment(response)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Something went wrong')
    }
  }

  async function confirmEnroll(event: FormEvent) {
    event.preventDefault()
    if (!enrollment) return
    setError(null)
    try {
      await api.post('/api/profile/mfa/enroll/confirm', { secret: enrollment.secret, code: confirmCode })
      setEnrollment(null)
      setConfirmCode('')
      await onChanged()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Something went wrong')
    }
  }

  async function disable(event: FormEvent) {
    event.preventDefault()
    setError(null)
    try {
      await api.post('/api/profile/mfa/disable', { current_password: disablePassword, code: disableCode })
      setDisablePassword('')
      setDisableCode('')
      await onChanged()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Something went wrong')
    }
  }

  return (
    <section className={styles.card}>
      <h2 className={styles.cardTitle}>
        <FiShield /> Two factor authentication
      </h2>

      {mfaEnabled ? (
        <>
          <p className={styles.hint}>Two factor authentication is enabled on this account.</p>
          <form onSubmit={disable} className={styles.form}>
            <label className={styles.label}>
              Current password
              <input
                type="password"
                value={disablePassword}
                onChange={(e) => setDisablePassword(e.target.value)}
              />
            </label>
            <label className={styles.label}>
              Authenticator code
              <input
                inputMode="numeric"
                maxLength={6}
                value={disableCode}
                onChange={(e) => setDisableCode(e.target.value)}
              />
            </label>
            {error && <div className={styles.error}>{error}</div>}
            <button type="submit" className={styles.dangerButton}>
              Disable two factor authentication
            </button>
          </form>
        </>
      ) : enrollment ? (
        <form onSubmit={confirmEnroll} className={styles.form}>
          <p className={styles.hint}>Scan this code with your authenticator app, then enter the 6 digit code below.</p>
          <img
            className={styles.qr}
            src={`data:image/png;base64,${enrollment.qr_png_base64}`}
            alt="Authenticator QR code"
          />
          <div className={styles.secret}>{enrollment.secret}</div>
          <label className={styles.label}>
            Authenticator code
            <input
              autoFocus
              inputMode="numeric"
              maxLength={6}
              value={confirmCode}
              onChange={(e) => setConfirmCode(e.target.value)}
            />
          </label>
          {error && <div className={styles.error}>{error}</div>}
          <button type="submit" className={styles.submit}>
            Confirm and enable
          </button>
        </form>
      ) : (
        <>
          <p className={styles.hint}>Add an authenticator app as a second step when signing in.</p>
          {error && <div className={styles.error}>{error}</div>}
          <button onClick={startEnroll} className={styles.submit}>
            Enable two factor authentication
          </button>
        </>
      )}
    </section>
  )
}
