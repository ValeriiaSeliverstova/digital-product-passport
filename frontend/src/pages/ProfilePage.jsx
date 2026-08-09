import { useState } from 'react'

import AppHeader from '../components/AppHeader.jsx'
import { ApiError } from '../services/api.js'
import { changePassword } from '../services/auth.js'
import {
  deleteOrganizationLogo,
  organizationLogoUrl,
  updateCurrentOrganization,
  uploadOrganizationLogo,
} from '../services/organizations.js'
import styles from './ProfilePage.module.css'

const MIN_PASSWORD_LENGTH = 12
const ORGANIZATION_FIELDS = [
  'name',
  'country',
  'address_line_1',
  'address_line_2',
  'city',
  'postal_code',
  'contact_email',
  'phone',
  'website',
]

function organizationFormValues(organization) {
  return Object.fromEntries(
    ORGANIZATION_FIELDS.map((field) => [field, organization?.[field] || '']),
  )
}

function ProfilePage({
  accessToken,
  currentUser,
  onLogout,
  onNavigate,
  onOrganizationUpdated,
}) {
  const [organizationForm, setOrganizationForm] = useState(
    organizationFormValues(currentUser.organization),
  )
  const [isSavingOrganization, setIsSavingOrganization] = useState(false)
  const [organizationError, setOrganizationError] = useState('')
  const [organizationNotice, setOrganizationNotice] = useState('')
  const [isUpdatingLogo, setIsUpdatingLogo] = useState(false)
  const [currentPassword, setCurrentPassword] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [showPasswords, setShowPasswords] = useState(false)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')

  const hasOrganizationChanges = ORGANIZATION_FIELDS.some(
    (field) =>
      organizationForm[field].trim() !==
      (currentUser.organization?.[field] || ''),
  )

  function updateOrganizationField(field, value) {
    setOrganizationForm((current) => ({ ...current, [field]: value }))
  }

  async function handleLogoUpload(event) {
    const logo = event.target.files?.[0]
    event.target.value = ''
    if (!logo) return

    setOrganizationError('')
    setOrganizationNotice('')
    if (logo.size > 2 * 1024 * 1024) {
      setOrganizationError('Organization logo must not exceed 2 MB.')
      return
    }

    setIsUpdatingLogo(true)
    try {
      const organization = await uploadOrganizationLogo(accessToken, logo)
      onOrganizationUpdated(organization)
      setOrganizationNotice('Organization logo was updated.')
    } catch (uploadError) {
      if (uploadError instanceof ApiError && uploadError.status === 401) {
        onLogout()
        return
      }
      setOrganizationError(
        uploadError instanceof ApiError
          ? uploadError.message
          : 'Unable to upload the organization logo.',
      )
    } finally {
      setIsUpdatingLogo(false)
    }
  }

  async function handleLogoDelete() {
    setIsUpdatingLogo(true)
    setOrganizationError('')
    setOrganizationNotice('')
    try {
      await deleteOrganizationLogo(accessToken)
      onOrganizationUpdated({
        ...currentUser.organization,
        has_logo: false,
        logo_updated_at: null,
      })
      setOrganizationNotice('Organization logo was deleted.')
    } catch (deleteError) {
      if (deleteError instanceof ApiError && deleteError.status === 401) {
        onLogout()
        return
      }
      setOrganizationError('Unable to delete the organization logo.')
    } finally {
      setIsUpdatingLogo(false)
    }
  }

  async function handleOrganizationUpdate(event) {
    event.preventDefault()
    const normalizedOrganization = Object.fromEntries(
      ORGANIZATION_FIELDS.map((field) => {
        const value = organizationForm[field].trim()
        return [field, field === 'name' ? value : value || null]
      }),
    )
    setOrganizationError('')
    setOrganizationNotice('')

    if (!normalizedOrganization.name) {
      setOrganizationError('Organization name is required.')
      return
    }

    setIsSavingOrganization(true)

    try {
      const organization = await updateCurrentOrganization(
        accessToken,
        normalizedOrganization,
      )
      setOrganizationForm(organizationFormValues(organization))
      onOrganizationUpdated(organization)
      setOrganizationNotice('Organization details were updated.')
    } catch (updateError) {
      if (updateError instanceof ApiError && updateError.status === 401) {
        onLogout()
        return
      }

      setOrganizationError(
        updateError instanceof ApiError
          ? updateError.message
          : 'Unable to update the organization. Check your connection and try again.',
      )
    } finally {
      setIsSavingOrganization(false)
    }
  }

  async function handlePasswordChange(event) {
    event.preventDefault()
    setError('')
    setNotice('')

    if (newPassword.length < MIN_PASSWORD_LENGTH) {
      setError(`New password must contain at least ${MIN_PASSWORD_LENGTH} characters.`)
      return
    }

    if (newPassword !== confirmPassword) {
      setError('New password and confirmation do not match.')
      return
    }

    setIsSubmitting(true)

    try {
      await changePassword(accessToken, currentPassword, newPassword)
      setCurrentPassword('')
      setNewPassword('')
      setConfirmPassword('')
      setNotice('Your password was changed successfully.')
    } catch (changeError) {
      if (changeError instanceof ApiError && changeError.status === 401) {
        onLogout()
        return
      }

      if (changeError instanceof ApiError && changeError.status === 400) {
        setError(changeError.message)
        return
      }

      setError('Unable to change the password. Check your connection and try again.')
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <div className={styles.page}>
      <AppHeader
        currentSection="profile"
        currentUser={currentUser}
        onLogout={onLogout}
        onNavigate={onNavigate}
      />

      <main className={styles.main}>
        <div className={styles.heading}>
          <h1>Profile</h1>
          <p>Review your organization, account information, and password.</p>
        </div>

        <section className={styles.card} aria-labelledby="account-heading">
          <h2 id="account-heading">Account details</h2>
          <dl className={styles.details}>
            <div>
              <dt>Email</dt>
              <dd>{currentUser.email}</dd>
            </div>
          </dl>

          {currentUser.organization ? (
            <>
              <div className={styles.logoEditor}>
                {currentUser.organization.has_logo ? (
                  <img
                    className={styles.logoPreview}
                    src={organizationLogoUrl(currentUser.organization)}
                    alt={`${currentUser.organization.name} logo`}
                  />
                ) : (
                  <span className={styles.logoFallback} aria-hidden="true">
                    DPP
                  </span>
                )}
                <div>
                  <h3>Organization logo</h3>
                  <p>PNG, JPEG, or WebP. Maximum size 2 MB.</p>
                  <div className={styles.logoActions}>
                    <label className={styles.logoUploadButton}>
                      {isUpdatingLogo ? 'Updating…' : 'Choose image'}
                      <input
                        type="file"
                        accept="image/png,image/jpeg,image/webp"
                        onChange={handleLogoUpload}
                        disabled={isUpdatingLogo}
                      />
                    </label>
                    {currentUser.organization.has_logo && (
                      <button
                        className={styles.logoDeleteButton}
                        type="button"
                        onClick={handleLogoDelete}
                        disabled={isUpdatingLogo}
                      >
                        Delete logo
                      </button>
                    )}
                  </div>
                </div>
              </div>

              <form
                className={styles.organizationForm}
                onSubmit={handleOrganizationUpdate}
              >
              <div className={`${styles.field} ${styles.fullWidthField}`}>
                <label htmlFor="organization-name">Organization name</label>
                <input
                  id="organization-name"
                  autoComplete="organization"
                  maxLength={255}
                  value={organizationForm.name}
                  onChange={(event) =>
                    updateOrganizationField('name', event.target.value)
                  }
                  required
                />
              </div>

              <div className={styles.field}>
                <label htmlFor="organization-country">Country (optional)</label>
                <input
                  id="organization-country"
                  autoComplete="country-name"
                  maxLength={100}
                  value={organizationForm.country}
                  onChange={(event) =>
                    updateOrganizationField('country', event.target.value)
                  }
                />
              </div>

              <div className={styles.field}>
                <label htmlFor="organization-city">City (optional)</label>
                <input
                  id="organization-city"
                  autoComplete="address-level2"
                  maxLength={100}
                  value={organizationForm.city}
                  onChange={(event) =>
                    updateOrganizationField('city', event.target.value)
                  }
                />
              </div>

              <div className={styles.field}>
                <label htmlFor="organization-address-1">
                  Address line 1 (optional)
                </label>
                <input
                  id="organization-address-1"
                  autoComplete="address-line1"
                  maxLength={255}
                  value={organizationForm.address_line_1}
                  onChange={(event) =>
                    updateOrganizationField('address_line_1', event.target.value)
                  }
                />
              </div>

              <div className={styles.field}>
                <label htmlFor="organization-address-2">
                  Address line 2 (optional)
                </label>
                <input
                  id="organization-address-2"
                  autoComplete="address-line2"
                  maxLength={255}
                  value={organizationForm.address_line_2}
                  onChange={(event) =>
                    updateOrganizationField('address_line_2', event.target.value)
                  }
                />
              </div>

              <div className={styles.field}>
                <label htmlFor="organization-postal-code">
                  Postal code (optional)
                </label>
                <input
                  id="organization-postal-code"
                  autoComplete="postal-code"
                  maxLength={30}
                  value={organizationForm.postal_code}
                  onChange={(event) =>
                    updateOrganizationField('postal_code', event.target.value)
                  }
                />
              </div>

              <div className={styles.field}>
                <label htmlFor="organization-email">Contact email (optional)</label>
                <input
                  id="organization-email"
                  type="email"
                  autoComplete="email"
                  maxLength={320}
                  value={organizationForm.contact_email}
                  onChange={(event) =>
                    updateOrganizationField('contact_email', event.target.value)
                  }
                />
              </div>

              <div className={styles.field}>
                <label htmlFor="organization-phone">Phone (optional)</label>
                <input
                  id="organization-phone"
                  type="tel"
                  autoComplete="tel"
                  maxLength={50}
                  value={organizationForm.phone}
                  onChange={(event) =>
                    updateOrganizationField('phone', event.target.value)
                  }
                />
              </div>

              <div className={`${styles.field} ${styles.fullWidthField}`}>
                <label htmlFor="organization-website">Website (optional)</label>
                <input
                  id="organization-website"
                  type="url"
                  autoComplete="url"
                  maxLength={2048}
                  placeholder="https://example.com"
                  value={organizationForm.website}
                  onChange={(event) =>
                    updateOrganizationField('website', event.target.value)
                  }
                />
              </div>

              {organizationNotice && (
                <p
                  className={`${styles.formMessage} ${styles.notice}`}
                  role="status"
                >
                  {organizationNotice}
                </p>
              )}
              {organizationError && (
                <p className={`${styles.formMessage} ${styles.error}`} role="alert">
                  {organizationError}
                </p>
              )}

              <button
                className={`${styles.submitButton} ${styles.organizationSubmit}`}
                type="submit"
                disabled={isSavingOrganization || !hasOrganizationChanges}
              >
                {isSavingOrganization ? 'Saving…' : 'Save organization details'}
              </button>
              </form>
            </>
          ) : (
            <p className={styles.unassignedOrganization}>
              No organization is assigned to this account.
            </p>
          )}
        </section>

        <section className={styles.card} aria-labelledby="password-heading">
          <div className={styles.sectionHeading}>
            <h2 id="password-heading">Change password</h2>
            <p>Use at least {MIN_PASSWORD_LENGTH} characters for the new password.</p>
          </div>

          {notice && (
            <p className={styles.notice} role="status">
              {notice}
            </p>
          )}
          {error && (
            <p className={styles.error} role="alert">
              {error}
            </p>
          )}

          <form className={styles.form} onSubmit={handlePasswordChange}>
            <div className={styles.field}>
              <label htmlFor="current-password">Current password</label>
              <input
                id="current-password"
                type={showPasswords ? 'text' : 'password'}
                autoComplete="current-password"
                value={currentPassword}
                onChange={(event) => setCurrentPassword(event.target.value)}
                required
              />
            </div>

            <div className={styles.field}>
              <label htmlFor="new-password">New password</label>
              <input
                id="new-password"
                type={showPasswords ? 'text' : 'password'}
                autoComplete="new-password"
                minLength={MIN_PASSWORD_LENGTH}
                maxLength={128}
                value={newPassword}
                onChange={(event) => setNewPassword(event.target.value)}
                required
              />
            </div>

            <div className={styles.field}>
              <label htmlFor="confirm-password">Confirm new password</label>
              <input
                id="confirm-password"
                type={showPasswords ? 'text' : 'password'}
                autoComplete="new-password"
                minLength={MIN_PASSWORD_LENGTH}
                maxLength={128}
                value={confirmPassword}
                onChange={(event) => setConfirmPassword(event.target.value)}
                required
              />
            </div>

            <label className={styles.showPasswords}>
              <input
                type="checkbox"
                checked={showPasswords}
                onChange={(event) => setShowPasswords(event.target.checked)}
              />
              Show passwords
            </label>

            <button
              className={styles.submitButton}
              type="submit"
              disabled={isSubmitting}
            >
              {isSubmitting ? 'Changing password…' : 'Change password'}
            </button>
          </form>
        </section>
      </main>
    </div>
  )
}

export default ProfilePage
