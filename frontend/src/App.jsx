import { useCallback, useState } from 'react'

import CreateTemplatePage from './pages/CreateTemplatePage.jsx'
import EditTemplatePage from './pages/EditTemplatePage.jsx'
import LoginPage from './pages/LoginPage.jsx'
import TemplateListPage from './pages/TemplateListPage.jsx'
import { getCurrentUser, login } from './services/auth.js'
import { ApiError } from './services/api.js'

function App() {
  const [accessToken, setAccessToken] = useState(null)
  const [currentUser, setCurrentUser] = useState(null)
  const [currentPage, setCurrentPage] = useState('templates')
  const [selectedTemplateId, setSelectedTemplateId] = useState(null)
  const [notice, setNotice] = useState('')

  async function handleLogin(email, password) {
    try {
      const tokenResponse = await login(email, password)
      const user = await getCurrentUser(tokenResponse.access_token)

      // The short-lived token stays only in React memory, never localStorage.
      setAccessToken(tokenResponse.access_token)
      setCurrentUser(user)
      setCurrentPage('templates')
      setSelectedTemplateId(null)
      setNotice('')
    } catch (error) {
      if (error instanceof ApiError && [401, 422].includes(error.status)) {
        throw new Error('Email or password is incorrect.')
      }

      throw new Error('Unable to sign in. Check your connection and try again.')
    }
  }

  const handleLogout = useCallback(() => {
    setAccessToken(null)
    setCurrentUser(null)
    setCurrentPage('templates')
    setSelectedTemplateId(null)
    setNotice('')
  }, [])

  if (!accessToken || !currentUser) {
    return <LoginPage onLogin={handleLogin} />
  }

  if (currentPage === 'create-template') {
    return (
      <CreateTemplatePage
        accessToken={accessToken}
        currentUser={currentUser}
        onCancel={() => setCurrentPage('templates')}
        onCreated={(template) => {
          setSelectedTemplateId(template.id)
          setNotice(`“${template.name}” was created as a draft.`)
          setCurrentPage('edit-template')
        }}
        onLogout={handleLogout}
      />
    )
  }

  if (currentPage === 'edit-template' && selectedTemplateId) {
    return (
      <EditTemplatePage
        accessToken={accessToken}
        currentUser={currentUser}
        templateId={selectedTemplateId}
        onBack={() => {
          setSelectedTemplateId(null)
          setCurrentPage('templates')
        }}
        onLogout={handleLogout}
        onSelectVersion={setSelectedTemplateId}
      />
    )
  }

  return (
    <TemplateListPage
      accessToken={accessToken}
      currentUser={currentUser}
      notice={notice}
      onCreateTemplate={() => {
        setNotice('')
        setCurrentPage('create-template')
      }}
      onEditTemplate={(templateId) => {
        setNotice('')
        setSelectedTemplateId(templateId)
        setCurrentPage('edit-template')
      }}
      onLogout={handleLogout}
    />
  )
}

export default App
