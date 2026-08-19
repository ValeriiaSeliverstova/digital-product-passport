import { useState } from 'react'

import { forgotPassword } from '../services/auth.js'
import styles from './LoginPage.module.css'

const SUCCESS_MESSAGE =
  'If an account with this email exists, password reset instructions have been sent.'

function ForgotPasswordPage() {
  const [email, setEmail] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [submitted, setSubmitted] = useState(false)
  const [error, setError] = useState('')

  async function handleSubmit(event) {
    event.preventDefault()
    setError('')
    setIsSubmitting(true)

    try {
      await forgotPassword(email)
      setSubmitted(true)
    } catch {
      setError('Unable to request a password reset. Please try again.')
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
        <section className={styles.card} aria-labelledby="forgot-password-title">
          <h1 id="forgot-password-title">Forgot password</h1>
          <p className={styles.introduction}>
            Enter your account email to receive a password reset link.
          </p>

          {submitted ? (
            <div className={styles.form}>
              <p className={styles.success} role="status">{SUCCESS_MESSAGE}</p>
              <a className={styles.secondaryLink} href="/">Back to sign in</a>
            </div>
          ) : (
            <form className={styles.form} onSubmit={handleSubmit}>
              <div className={styles.field}>
                <label htmlFor="reset-email">Email</label>
                <input
                  id="reset-email"
                  name="email"
                  type="email"
                  autoComplete="email"
                  autoCapitalize="none"
                  spellCheck="false"
                  value={email}
                  onChange={(event) => setEmail(event.target.value)}
                  required
                />
              </div>

              {error && <p className={styles.error} role="alert">{error}</p>}

              <button
                className={styles.submitButton}
                type="submit"
                disabled={isSubmitting}
              >
                {isSubmitting ? 'Sending…' : 'Send reset link'}
              </button>
              <a className={styles.secondaryLink} href="/">Back to sign in</a>
            </form>
          )}
        </section>
      </main>

      <footer className={styles.footer}>Product safety · Traceability · Trust</footer>
    </div>
  )
}

export default ForgotPasswordPage
