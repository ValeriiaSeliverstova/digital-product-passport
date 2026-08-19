import { useState } from 'react'

import { signup } from '../services/auth.js'
import styles from './LoginPage.module.css'

const MIN_PASSWORD_LENGTH = 12
const MAX_PASSWORD_LENGTH = 128

function SignupPage() {
  const [firstName, setFirstName] = useState('')
  const [lastName, setLastName] = useState('')
  const [email, setEmail] = useState('')
  const [organizationName, setOrganizationName] = useState('')
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [completed, setCompleted] = useState(false)
  const [error, setError] = useState('')

  async function handleSubmit(event) {
    event.preventDefault()
    setError('')

    if (
      !firstName.trim() ||
      !lastName.trim() ||
      !email.trim() ||
      !organizationName.trim()
    ) {
      setError('Please fill in every field.')
      return
    }
    if (password.length < MIN_PASSWORD_LENGTH) {
      setError(`Password must contain at least ${MIN_PASSWORD_LENGTH} characters.`)
      return
    }
    if (password !== confirmPassword) {
      setError('Passwords do not match.')
      return
    }

    setIsSubmitting(true)
    try {
      await signup({ firstName, lastName, email, password, organizationName })
      setCompleted(true)
    } catch (requestError) {
      // The API returns a clear message for a duplicate email; keep a safe
      // fallback for network problems and unexpected responses.
      setError(requestError.message || 'Unable to create the account.')
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
        <section className={styles.card} aria-labelledby="signup-title">
          <h1 id="signup-title">Create an account</h1>

          {completed ? (
            <div className={styles.form}>
              <p className={styles.success} role="status">
                Your account has been created. You can now sign in.
              </p>
              <a className={styles.secondaryLink} href="/">Go to sign in</a>
            </div>
          ) : (
            <form className={styles.form} onSubmit={handleSubmit}>
              <p className={styles.introduction}>
                Register your organization to start publishing product passports.
                Choose a password with at least {MIN_PASSWORD_LENGTH} characters.
              </p>

              <div className={styles.field}>
                <label htmlFor="first-name">First name</label>
                <input
                  id="first-name"
                  name="first-name"
                  type="text"
                  autoComplete="given-name"
                  maxLength={100}
                  value={firstName}
                  onChange={(event) => setFirstName(event.target.value)}
                  required
                />
              </div>

              <div className={styles.field}>
                <label htmlFor="last-name">Last name</label>
                <input
                  id="last-name"
                  name="last-name"
                  type="text"
                  autoComplete="family-name"
                  maxLength={100}
                  value={lastName}
                  onChange={(event) => setLastName(event.target.value)}
                  required
                />
              </div>

              <div className={styles.field}>
                <label htmlFor="signup-email">Email</label>
                <input
                  id="signup-email"
                  name="email"
                  type="email"
                  autoComplete="email"
                  autoCapitalize="none"
                  spellCheck="false"
                  maxLength={320}
                  value={email}
                  onChange={(event) => setEmail(event.target.value)}
                  required
                />
              </div>

              <div className={styles.field}>
                <label htmlFor="organization-name">Organization name</label>
                <input
                  id="organization-name"
                  name="organization-name"
                  type="text"
                  autoComplete="organization"
                  maxLength={255}
                  value={organizationName}
                  onChange={(event) => setOrganizationName(event.target.value)}
                  required
                />
              </div>

              <div className={styles.field}>
                <label htmlFor="signup-password">Password</label>
                <input
                  id="signup-password"
                  name="signup-password"
                  type="password"
                  autoComplete="new-password"
                  minLength={MIN_PASSWORD_LENGTH}
                  maxLength={MAX_PASSWORD_LENGTH}
                  value={password}
                  onChange={(event) => {
                    setPassword(event.target.value)
                    // Clear the alert while the user is correcting the problem.
                    setError('')
                  }}
                  aria-invalid={error ? 'true' : undefined}
                  aria-describedby={error ? 'signup-error' : undefined}
                  required
                />
              </div>

              <div className={styles.field}>
                <label htmlFor="signup-confirm-password">Confirm password</label>
                <input
                  id="signup-confirm-password"
                  name="signup-confirm-password"
                  type="password"
                  autoComplete="new-password"
                  minLength={MIN_PASSWORD_LENGTH}
                  maxLength={MAX_PASSWORD_LENGTH}
                  value={confirmPassword}
                  onChange={(event) => {
                    setConfirmPassword(event.target.value)
                    setError('')
                  }}
                  aria-invalid={error ? 'true' : undefined}
                  aria-describedby={error ? 'signup-error' : undefined}
                  required
                />
              </div>

              {error && (
                <p className={styles.error} id="signup-error" role="alert">
                  {error}
                </p>
              )}

              <button
                className={styles.submitButton}
                type="submit"
                disabled={isSubmitting}
              >
                {isSubmitting ? 'Creating account…' : 'Create account'}
              </button>
              <a className={styles.secondaryLink} href="/">
                Already have an account? Sign in
              </a>
            </form>
          )}
        </section>
      </main>

      <footer className={styles.footer}>Product safety · Traceability · Trust</footer>
    </div>
  )
}

export default SignupPage
