import { useEffect, useRef, useState } from 'react'

import { confirmEmail } from '../services/auth.js'
import styles from './LoginPage.module.css'

function ConfirmEmailPage() {
  const token = new URLSearchParams(window.location.search).get('token') || ''
  const [state, setState] = useState(token ? 'confirming' : 'invalid')
  const hasRequested = useRef(false)

  useEffect(() => {
    if (!token || hasRequested.current) {
      return
    }

    // The token is single-use, so guard against a second call in strict mode.
    hasRequested.current = true
    let isCurrentRequest = true

    confirmEmail(token)
      .then(() => {
        if (isCurrentRequest) {
          setState('confirmed')
        }
      })
      .catch(() => {
        if (isCurrentRequest) {
          setState('invalid')
        }
      })

    return () => {
      isCurrentRequest = false
    }
  }, [token])

  return (
    <div className={styles.page}>
      <header className={styles.brand}>
        <span className={styles.brandMark} aria-hidden="true">DPP</span>
        <span className={styles.brandName}>Digital Product Passport</span>
      </header>

      <main className={styles.main}>
        <section className={styles.card} aria-labelledby="confirm-email-title">
          <h1 id="confirm-email-title">Confirm your email</h1>

          {state === 'confirming' && (
            <p className={styles.introduction} role="status">
              Confirming your email address…
            </p>
          )}

          {state === 'confirmed' && (
            <div className={styles.form}>
              <p className={styles.success} role="status">
                Your email address is confirmed. You can now sign in.
              </p>
              <a className={styles.secondaryLink} href="/">Go to sign in</a>
            </div>
          )}

          {state === 'invalid' && (
            <div className={styles.form}>
              <p className={styles.error} role="alert">
                This confirmation link is invalid or has expired.
              </p>
              <a className={styles.secondaryLink} href="/signup">
                Create a new account
              </a>
            </div>
          )}
        </section>
      </main>

      <footer className={styles.footer}>Product safety · Traceability · Trust</footer>
    </div>
  )
}

export default ConfirmEmailPage
