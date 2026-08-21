import { useState } from 'react'

import { acceptInvitation } from '../services/auth.js'
import styles from './LoginPage.module.css'

const MIN_PASSWORD_LENGTH = 12
const MAX_PASSWORD_LENGTH = 128

function AcceptInvitationPage() {
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
      await acceptInvitation(token, newPassword)
      setCompleted(true)
    } catch {
      setError('This invitation link is invalid or has expired.')
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
        <section className={styles.card} aria-labelledby="invitation-title">
          <h1 id="invitation-title">Choose your password</h1>

          {completed ? (
            <div className={styles.form}>
              <p className={styles.success} role="status">
                Your password is set. You can now sign in.
              </p>
              <a className={styles.secondaryLink} href="/">Go to sign in</a>
            </div>
          ) : !token ? (
            <div className={styles.form}>
              <p className={styles.error} role="alert">
                This invitation link is invalid or has expired.
              </p>
            </div>
          ) : (
            <form className={styles.form} onSubmit={handleSubmit}>
              <p className={styles.introduction}>
                Set a password with at least {MIN_PASSWORD_LENGTH} characters to
                activate your service-technician account.
              </p>

              <div className={styles.field}>
                <label htmlFor="invitation-password">New password</label>
                <input
                  id="invitation-password"
                  name="invitation-password"
                  type="password"
                  autoComplete="new-password"
                  minLength={MIN_PASSWORD_LENGTH}
                  maxLength={MAX_PASSWORD_LENGTH}
                  value={newPassword}
                  onChange={(event) => {
                    setNewPassword(event.target.value)
                    setError('')
                  }}
                  required
                />
              </div>

              <div className={styles.field}>
                <label htmlFor="invitation-confirm">Confirm password</label>
                <input
                  id="invitation-confirm"
                  name="invitation-confirm"
                  type="password"
                  autoComplete="new-password"
                  minLength={MIN_PASSWORD_LENGTH}
                  maxLength={MAX_PASSWORD_LENGTH}
                  value={confirmPassword}
                  onChange={(event) => {
                    setConfirmPassword(event.target.value)
                    setError('')
                  }}
                  required
                />
              </div>

              {error && <p className={styles.error} role="alert">{error}</p>}

              <button
                className={styles.submitButton}
                type="submit"
                disabled={isSubmitting}
              >
                {isSubmitting ? 'Saving…' : 'Set password'}
              </button>
            </form>
          )}
        </section>
      </main>

      <footer className={styles.footer}>Product safety · Traceability · Trust</footer>
    </div>
  )
}

export default AcceptInvitationPage
