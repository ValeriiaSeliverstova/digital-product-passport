import { useState } from 'react'

import AppHeader from '../components/AppHeader.jsx'
import { ApiError } from '../services/api.js'
import { changePassword } from '../services/auth.js'
import styles from './ProfilePage.module.css'

const MIN_PASSWORD_LENGTH = 12

function ProfilePage({ accessToken, currentUser, onLogout, onNavigate }) {
  const [currentPassword, setCurrentPassword] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [showPasswords, setShowPasswords] = useState(false)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')

  async function handlePasswordChange(event) {
    event.preventDefault()
    setError('')
    setNotice('')

    if (newPassword.length < MIN_PASSWORD_LENGTH) {
      setError(`New password must contain at least ${MIN_PASSWORD_LENGTH} characters.`)
      return
    }

    if (newPassword !== confirmPassword) {
      setError('New password and confirmation do not match.')
      return
    }

    setIsSubmitting(true)

    try {
      await changePassword(accessToken, currentPassword, newPassword)
      setCurrentPassword('')
      setNewPassword('')
      setConfirmPassword('')
      setNotice('Your password was changed successfully.')
    } catch (changeError) {
      if (changeError instanceof ApiError && changeError.status === 401) {
        onLogout()
        return
      }

      if (changeError instanceof ApiError && changeError.status === 400) {
        setError(changeError.message)
        return
      }

      setError('Unable to change the password. Check your connection and try again.')
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <div className={styles.page}>
      <AppHeader
        currentSection="profile"
        currentUser={currentUser}
        onLogout={onLogout}
        onNavigate={onNavigate}
      />

      <main className={styles.main}>
        <div className={styles.heading}>
          <h1>Profile</h1>
          <p>Review your account information and update your password.</p>
        </div>

        <section className={styles.card} aria-labelledby="account-heading">
          <h2 id="account-heading">Account details</h2>
          <dl className={styles.details}>
            <div>
              <dt>Email</dt>
              <dd>{currentUser.email}</dd>
            </div>
            <div>
              <dt>Organization</dt>
              <dd>{currentUser.organization?.name || 'Not assigned'}</dd>
            </div>
          </dl>
        </section>

        <section className={styles.card} aria-labelledby="password-heading">
          <div className={styles.sectionHeading}>
            <h2 id="password-heading">Change password</h2>
            <p>Use at least {MIN_PASSWORD_LENGTH} characters for the new password.</p>
          </div>

          {notice && (
            <p className={styles.notice} role="status">
              {notice}
            </p>
          )}
          {error && (
            <p className={styles.error} role="alert">
              {error}
            </p>
          )}

          <form className={styles.form} onSubmit={handlePasswordChange}>
            <div className={styles.field}>
              <label htmlFor="current-password">Current password</label>
              <input
                id="current-password"
                type={showPasswords ? 'text' : 'password'}
                autoComplete="current-password"
                value={currentPassword}
                onChange={(event) => setCurrentPassword(event.target.value)}
                required
              />
            </div>

            <div className={styles.field}>
              <label htmlFor="new-password">New password</label>
              <input
                id="new-password"
                type={showPasswords ? 'text' : 'password'}
                autoComplete="new-password"
                minLength={MIN_PASSWORD_LENGTH}
                maxLength={128}
                value={newPassword}
                onChange={(event) => setNewPassword(event.target.value)}
                required
              />
            </div>

            <div className={styles.field}>
              <label htmlFor="confirm-password">Confirm new password</label>
              <input
                id="confirm-password"
                type={showPasswords ? 'text' : 'password'}
                autoComplete="new-password"
                minLength={MIN_PASSWORD_LENGTH}
                maxLength={128}
                value={confirmPassword}
                onChange={(event) => setConfirmPassword(event.target.value)}
                required
              />
            </div>

            <label className={styles.showPasswords}>
              <input
                type="checkbox"
                checked={showPasswords}
                onChange={(event) => setShowPasswords(event.target.checked)}
              />
              Show passwords
            </label>

            <button
              className={styles.submitButton}
              type="submit"
              disabled={isSubmitting}
            >
              {isSubmitting ? 'Changing password…' : 'Change password'}
            </button>
          </form>
        </section>
      </main>
    </div>
  )
}

export default ProfilePage
