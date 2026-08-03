import { useState } from 'react'

import LoginPage from './pages/LoginPage.jsx'
import TemplateListPage from './pages/TemplateListPage.jsx'
import { getCurrentUser, login } from './services/auth.js'
import { ApiError } from './services/api.js'

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
    <TemplateListPage
      accessToken={accessToken}
      currentUser={currentUser}
      onLogout={handleLogout}
    />
  )
}

export default App
