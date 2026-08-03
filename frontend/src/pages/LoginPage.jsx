import { useState } from 'react'

import styles from './LoginPage.module.css'

function LoginPage({ onLogin }) {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [error, setError] = useState('')

  async function handleSubmit(event) {
    event.preventDefault()
    setError('')
    setIsSubmitting(true)

    try {
      await onLogin(email, password)
    } catch (loginError) {
      setError(loginError.message)
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <div className={styles.page}>
      <header className={styles.brand}>
        <span className={styles.brandMark} aria-hidden="true">
          DPP
        </span>
        <span className={styles.brandName}>Digital Product Passport</span>
      </header>

      <main className={styles.main}>
        <section className={styles.card} aria-labelledby="login-title">
          <h1 id="login-title">Manufacturer sign in</h1>
          <p className={styles.introduction}>
            Secure access for registered manufacturers
          </p>

          <form className={styles.form} onSubmit={handleSubmit}>
            <div className={styles.field}>
              <label htmlFor="email">Email</label>
              <input
                id="email"
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

            <div className={styles.field}>
              <label htmlFor="password">Password</label>
              <div className={styles.passwordControl}>
                <input
                  id="password"
                  name="password"
                  type={showPassword ? 'text' : 'password'}
                  autoComplete="current-password"
                  value={password}
                  onChange={(event) => setPassword(event.target.value)}
                  required
                />
                <button
                  className={styles.showPasswordButton}
                  type="button"
                  aria-pressed={showPassword}
                  onClick={() => setShowPassword((isVisible) => !isVisible)}
                >
                  {showPassword ? 'Hide' : 'Show'}
                </button>
              </div>
            </div>

            {error && (
              <p className={styles.error} role="alert">
                {error}
              </p>
            )}

            <button
              className={styles.submitButton}
              type="submit"
              disabled={isSubmitting}
            >
              {isSubmitting ? 'Signing in…' : 'Sign in'}
            </button>
          </form>
        </section>
      </main>

      <footer className={styles.footer}>
        Product safety · Traceability · Trust
      </footer>
    </div>
  )
}

export default LoginPage
