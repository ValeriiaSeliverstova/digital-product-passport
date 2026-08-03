import { useState } from 'react'

import LoginPage from './pages/LoginPage.jsx'
import { getCurrentUser, login } from './services/auth.js'
import { ApiError } from './services/api.js'
import styles from './App.module.css'

function App() {
  const [accessToken, setAccessToken] = useState(null)
  const [currentUser, setCurrentUser] = useState(null)

  async function handleLogin(email, password) {
    try {
      const tokenResponse = await login(email, password)
      const user = await getCurrentUser(tokenResponse.access_token)

      // The short-lived token stays only in React memory, never localStorage.
      setAccessToken(tokenResponse.access_token)
      setCurrentUser(user)
    } catch (error) {
      if (error instanceof ApiError && [401, 422].includes(error.status)) {
        throw new Error('Email or password is incorrect.')
      }

      throw new Error('Unable to sign in. Check your connection and try again.')
    }
  }

  function handleLogout() {
    setAccessToken(null)
    setCurrentUser(null)
  }

  if (!accessToken || !currentUser) {
    return <LoginPage onLogin={handleLogin} />
  }

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <span className={styles.brand}>Digital Product Passport</span>
        <button
          className={styles.logoutButton}
          type="button"
          onClick={handleLogout}
        >
          Logout
        </button>
      </header>

      <main>
        <section className={styles.content} aria-labelledby="page-title">
          <h1 id="page-title">Welcome</h1>
          <dl className={styles.userDetails}>
            <div>
              <dt>Email</dt>
              <dd>{currentUser.email}</dd>
            </div>
            <div>
              <dt>Role</dt>
              <dd>{currentUser.role.name}</dd>
            </div>
          </dl>
        </section>
      </main>
    </div>
  )
}

export default App
