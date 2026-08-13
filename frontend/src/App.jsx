import { useCallback, useState } from 'react'

import CreateTemplatePage from './pages/CreateTemplatePage.jsx'
import EditTemplatePage from './pages/EditTemplatePage.jsx'
import LoginPage from './pages/LoginPage.jsx'
import ProfilePage from './pages/ProfilePage.jsx'
import ProductItemFormPage from './pages/ProductItemFormPage.jsx'
import ProductItemListPage from './pages/ProductItemListPage.jsx'
import ProductModelFormPage from './pages/ProductModelFormPage.jsx'
import ProductModelListPage from './pages/ProductModelListPage.jsx'
import PublicPassportPage from './pages/PublicPassportPage.jsx'
import PublicSupportTicketPage from './pages/PublicSupportTicketPage.jsx'
import TemplateListPage from './pages/TemplateListPage.jsx'
import TeamMemberPage from './pages/TeamMemberPage.jsx'
import { getCurrentUser, login } from './services/auth.js'
import { ApiError } from './services/api.js'

function App() {
  const [accessToken, setAccessToken] = useState(null)
  const [currentUser, setCurrentUser] = useState(null)
  const [currentPage, setCurrentPage] = useState('templates')
  const [selectedTemplateId, setSelectedTemplateId] = useState(null)
  const [selectedProductModelId, setSelectedProductModelId] = useState(null)
  const [selectedProductItemId, setSelectedProductItemId] = useState(null)
  const [notice, setNotice] = useState('')
  const publicPassportMatch = window.location.pathname.match(
    /^\/passport\/([^/]+)\/?$/,
  )
  const publicPassportId = publicPassportMatch?.[1]
  const publicSupportTicketMatch = window.location.pathname.match(
    /^\/support-ticket\/(\d+)\/?$/,
  )
  const publicSupportTicketId = publicSupportTicketMatch?.[1]
  const isPublicSupportTracker = /^\/support-ticket\/?$/.test(
    window.location.pathname,
  )

  async function handleLogin(email, password) {
    try {
      const tokenResponse = await login(email, password)
      const user = await getCurrentUser(tokenResponse.access_token)

      // The short-lived token stays only in React memory, never localStorage.
      setAccessToken(tokenResponse.access_token)
      setCurrentUser(user)
      setCurrentPage(
        user.role.name === 'service_technician' ? 'product-items' : 'templates',
      )
      setSelectedTemplateId(null)
      setSelectedProductModelId(null)
      setSelectedProductItemId(null)
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
    setSelectedProductModelId(null)
    setSelectedProductItemId(null)
    setNotice('')
  }, [])

  function handleNavigate(section) {
    setCurrentPage(section)
    setSelectedTemplateId(null)
    setSelectedProductModelId(null)
    setSelectedProductItemId(null)
    setNotice('')
  }

  function handleOrganizationUpdated(organization) {
    setCurrentUser((user) => ({
      ...user,
      organization_id: organization.id,
      organization,
    }))
  }

  // Public QR links bypass the manufacturer sign-in screen.
  if (publicPassportId) {
    return <PublicPassportPage publicId={publicPassportId} />
  }

  if (publicSupportTicketId || isPublicSupportTracker) {
    return <PublicSupportTicketPage ticketId={publicSupportTicketId} />
  }

  if (!accessToken || !currentUser) {
    return <LoginPage onLogin={handleLogin} />
  }

  if (currentPage === 'profile') {
    return (
      <ProfilePage
        accessToken={accessToken}
        currentUser={currentUser}
        onLogout={handleLogout}
        onNavigate={handleNavigate}
        onOrganizationUpdated={handleOrganizationUpdated}
      />
    )
  }

  if (
    currentPage === 'team-members' &&
    currentUser.role.name === 'manufacturer_user'
  ) {
    return (
      <TeamMemberPage
        accessToken={accessToken}
        currentUser={currentUser}
        onLogout={handleLogout}
        onNavigate={handleNavigate}
      />
    )
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
        onNavigate={handleNavigate}
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
        onNavigate={handleNavigate}
        onSelectVersion={setSelectedTemplateId}
      />
    )
  }

  if (currentPage === 'create-product-model') {
    return (
      <ProductModelFormPage
        accessToken={accessToken}
        currentUser={currentUser}
        onBack={() => setCurrentPage('product-models')}
        onLogout={handleLogout}
        onNavigate={handleNavigate}
        onSaved={(model) => {
          setNotice(`“${model.name}” was created.`)
          setCurrentPage('product-models')
        }}
      />
    )
  }

  if (currentPage === 'edit-product-model' && selectedProductModelId) {
    return (
      <ProductModelFormPage
        accessToken={accessToken}
        currentUser={currentUser}
        modelId={selectedProductModelId}
        onBack={() => setCurrentPage('product-models')}
        onLogout={handleLogout}
        onNavigate={handleNavigate}
        onSaved={(model) => {
          setNotice(`Changes to “${model.name}” were saved.`)
          setCurrentPage('product-models')
        }}
      />
    )
  }

  if (currentPage === 'product-models') {
    return (
      <ProductModelListPage
        accessToken={accessToken}
        currentUser={currentUser}
        notice={notice}
        onCreate={() => {
          setNotice('')
          setCurrentPage('create-product-model')
        }}
        onEdit={(modelId) => {
          setNotice('')
          setSelectedProductModelId(modelId)
          setCurrentPage('edit-product-model')
        }}
        onLogout={handleLogout}
        onNavigate={handleNavigate}
      />
    )
  }

  if (currentPage === 'create-product-item') {
    return (
      <ProductItemFormPage
        accessToken={accessToken}
        currentUser={currentUser}
        onBack={() => setCurrentPage('product-items')}
        onCreated={(item) => {
          setSelectedProductItemId(item.id)
          setNotice('Product item was created as a draft.')
          setCurrentPage('edit-product-item')
        }}
        onLogout={handleLogout}
        onNavigate={handleNavigate}
      />
    )
  }

  if (currentPage === 'edit-product-item' && selectedProductItemId) {
    return (
      <ProductItemFormPage
        accessToken={accessToken}
        currentUser={currentUser}
        itemId={selectedProductItemId}
        initialNotice={notice}
        onBack={() => {
          setNotice('')
          setCurrentPage('product-items')
        }}
        onLogout={handleLogout}
        onNavigate={handleNavigate}
      />
    )
  }

  if (currentPage === 'product-items') {
    return (
      <ProductItemListPage
        accessToken={accessToken}
        currentUser={currentUser}
        notice={notice}
        onCreate={() => {
          setNotice('')
          setCurrentPage('create-product-item')
        }}
        onEdit={(itemId) => {
          setNotice('')
          setSelectedProductItemId(itemId)
          setCurrentPage('edit-product-item')
        }}
        onLogout={handleLogout}
        onNavigate={handleNavigate}
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
      onNavigate={handleNavigate}
    />
  )
}

export default App
