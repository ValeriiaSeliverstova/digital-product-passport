import { useEffect, useState } from 'react'

import AppHeader from '../components/AppHeader.jsx'
import { ApiError } from '../services/api.js'
import {
  createTeamMember,
  getTeamMembers,
  updateTeamMember,
} from '../services/teamMembers.js'
import styles from './TeamMemberPage.module.css'

const MIN_PASSWORD_LENGTH = 12

function TeamMemberPage({
  accessToken,
  currentUser,
  onLogout,
  onNavigate,
}) {
  const [members, setMembers] = useState([])
  const [email, setEmail] = useState('')
  const [initialPassword, setInitialPassword] = useState('')
  const [loadState, setLoadState] = useState('loading')
  const [isCreating, setIsCreating] = useState(false)
  const [updatingMemberId, setUpdatingMemberId] = useState(null)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')

  useEffect(() => {
    let isCurrentRequest = true

    getTeamMembers(accessToken)
      .then((data) => {
        if (!isCurrentRequest) return
        setMembers(data)
        setLoadState('success')
      })
      .catch((loadError) => {
        if (!isCurrentRequest) return
        if (loadError instanceof ApiError && loadError.status === 401) {
          onLogout()
          return
        }
        setLoadState('error')
      })

    return () => {
      isCurrentRequest = false
    }
  }, [accessToken, onLogout])

  async function handleCreate(event) {
    event.preventDefault()
    setError('')
    setNotice('')
    if (initialPassword.length < MIN_PASSWORD_LENGTH) {
      setError(`Initial password must contain at least ${MIN_PASSWORD_LENGTH} characters.`)
      return
    }

    setIsCreating(true)
    try {
      const member = await createTeamMember(
        accessToken,
        email.trim(),
        initialPassword,
      )
      setMembers((current) =>
        [...current, member].sort((first, second) =>
          first.email.localeCompare(second.email),
        ),
      )
      setEmail('')
      setInitialPassword('')
      setNotice('Service technician account was created.')
    } catch (createError) {
      if (createError instanceof ApiError && createError.status === 401) {
        onLogout()
        return
      }
      setError(
        createError instanceof ApiError
          ? createError.message
          : 'The technician account could not be created.',
      )
    } finally {
      setIsCreating(false)
    }
  }

  async function toggleMember(member) {
    const nextStatus = member.status === 'active' ? 'inactive' : 'active'
    setUpdatingMemberId(member.id)
    setError('')
    setNotice('')
    try {
      const updated = await updateTeamMember(
        accessToken,
        member.id,
        nextStatus,
      )
      setMembers((current) =>
        current.map((candidate) =>
          candidate.id === updated.id ? updated : candidate,
        ),
      )
      setNotice(
        nextStatus === 'active'
          ? 'Technician account was activated.'
          : 'Technician account was deactivated.',
      )
    } catch (updateError) {
      if (updateError instanceof ApiError && updateError.status === 401) {
        onLogout()
        return
      }
      setError('The technician account could not be updated.')
    } finally {
      setUpdatingMemberId(null)
    }
  }

  return (
    <div className={styles.page}>
      <AppHeader
        currentSection="team-members"
        currentUser={currentUser}
        onLogout={onLogout}
        onNavigate={onNavigate}
      />
      <main className={styles.main}>
        <header className={styles.heading}>
          <h1>Team members</h1>
          <p>Add service technicians who can register products and lifecycle events.</p>
        </header>

        {notice && <p className={styles.notice} role="status">{notice}</p>}
        {error && <p className={styles.error} role="alert">{error}</p>}

        <section className={styles.card} aria-labelledby="add-technician-heading">
          <h2 id="add-technician-heading">Add service technician</h2>
          <form className={styles.form} onSubmit={handleCreate}>
            <div>
              <label htmlFor="technician-email">Email</label>
              <input
                id="technician-email"
                type="email"
                maxLength={320}
                value={email}
                onChange={(event) => setEmail(event.target.value)}
                required
              />
            </div>
            <div>
              <label htmlFor="technician-password">Initial password</label>
              <input
                id="technician-password"
                type="password"
                autoComplete="new-password"
                minLength={MIN_PASSWORD_LENGTH}
                maxLength={128}
                value={initialPassword}
                onChange={(event) => setInitialPassword(event.target.value)}
                required
              />
              <p>Share it privately. The technician can change it after signing in.</p>
            </div>
            <button type="submit" disabled={isCreating}>
              {isCreating ? 'Creating…' : 'Add technician'}
            </button>
          </form>
        </section>

        <section className={styles.card} aria-labelledby="technicians-heading">
          <h2 id="technicians-heading">Service technicians</h2>
          {loadState === 'loading' && <p>Loading team members…</p>}
          {loadState === 'error' && (
            <p role="alert">Team members could not be loaded.</p>
          )}
          {loadState === 'success' && members.length === 0 && (
            <p>No service technicians have been added yet.</p>
          )}
          {loadState === 'success' && members.length > 0 && (
            <ul className={styles.memberList}>
              {members.map((member) => (
                <li key={member.id}>
                  <div>
                    <strong>{member.email}</strong>
                    <span>{member.status === 'active' ? 'Active' : 'Inactive'}</span>
                  </div>
                  <button
                    className={member.status === 'active'
                      ? styles.deactivateButton
                      : styles.activateButton}
                    type="button"
                    disabled={updatingMemberId === member.id}
                    onClick={() => toggleMember(member)}
                  >
                    {updatingMemberId === member.id
                      ? 'Updating…'
                      : member.status === 'active'
                        ? 'Deactivate'
                        : 'Activate'}
                  </button>
                </li>
              ))}
            </ul>
          )}
        </section>
      </main>
    </div>
  )
}

export default TeamMemberPage
