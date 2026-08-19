import { useState } from 'react'

import { resetPassword } from '../services/auth.js'
import styles from './LoginPage.module.css'

const MIN_PASSWORD_LENGTH = 12
const MAX_PASSWORD_LENGTH = 128

function ResetPasswordPage() {
  const token = new URLSearchParams(window.location.search).get('token') || ''
  const [newPassword, setNewPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [completed, setCompleted] = useState(false)
  const [error, setError] = useState('')

  async function handleSubmit(event) {
    event.preventDefault()
    setError('')

    if (newPassword.length < MIN_PASSWORD_LENGTH) {
      setError(`Password must contain at least ${MIN_PASSWORD_LENGTH} characters.`)
      return
    }
    if (newPassword !== confirmPassword) {
      setError('Passwords do not match.')
      return
    }

    setIsSubmitting(true)
    try {
      await resetPassword(token, newPassword)
      setCompleted(true)
    } catch {
      setError('This password reset link is invalid or has expired.')
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <div className={styles.page}>
      <header className={styles.brand}>
        <span className={styles.brandMark} aria-hidden="true">DPP</span>
        <span className={styles.brandName}>Digital Product Passport</span>
      </header>

      <main className={styles.main}>
        <section className={styles.card} aria-labelledby="reset-password-title">
          <h1 id="reset-password-title">Reset password</h1>

          {completed ? (
            <div className={styles.form}>
              <p className={styles.success} role="status">
                Your password has been reset successfully.
              </p>
              <a className={styles.secondaryLink} href="/">Back to sign in</a>
            </div>
          ) : !token ? (
            <div className={styles.form}>
              <p className={styles.error} role="alert">
                This password reset link is invalid or has expired.
              </p>
              <a className={styles.secondaryLink} href="/forgot-password">
                Request a new reset link
              </a>
            </div>
          ) : (
            <form className={styles.form} onSubmit={handleSubmit}>
              <p className={styles.introduction}>
                Choose a new password with at least {MIN_PASSWORD_LENGTH} characters.
              </p>
              <div className={styles.field}>
                <label htmlFor="new-password">New password</label>
                <input
                  id="new-password"
                  name="new-password"
                  type="password"
                  autoComplete="new-password"
                  minLength={MIN_PASSWORD_LENGTH}
                  maxLength={MAX_PASSWORD_LENGTH}
                  value={newPassword}
                  onChange={(event) => setNewPassword(event.target.value)}
                  required
                />
              </div>
              <div className={styles.field}>
                <label htmlFor="confirm-password">Confirm password</label>
                <input
                  id="confirm-password"
                  name="confirm-password"
                  type="password"
                  autoComplete="new-password"
                  minLength={MIN_PASSWORD_LENGTH}
                  maxLength={MAX_PASSWORD_LENGTH}
                  value={confirmPassword}
                  onChange={(event) => setConfirmPassword(event.target.value)}
                  required
                />
              </div>

              {error && <p className={styles.error} role="alert">{error}</p>}

              <button
                className={styles.submitButton}
                type="submit"
                disabled={isSubmitting}
              >
                {isSubmitting ? 'Resetting…' : 'Reset password'}
              </button>
            </form>
          )}
        </section>
      </main>

      <footer className={styles.footer}>Product safety · Traceability · Trust</footer>
    </div>
  )
}

export default ResetPasswordPage
