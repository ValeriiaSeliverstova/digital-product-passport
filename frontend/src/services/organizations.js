import { apiRequest, apiUrl } from './api.js'

/** Update the organization owned by the authenticated manufacturer. */
export function updateCurrentOrganization(accessToken, organizationData) {
  return apiRequest('/api/organizations/me', {
    method: 'PUT',
    token: accessToken,
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(organizationData),
  })
}

/** Upload a PNG, JPEG, or WebP organization logo. */
export function uploadOrganizationLogo(accessToken, logo) {
  const body = new FormData()
  body.append('logo', logo)
  return apiRequest('/api/organizations/me/logo', {
    method: 'PUT',
    token: accessToken,
    body,
  })
}

/** Delete the authenticated organization's current logo. */
export function deleteOrganizationLogo(accessToken) {
  return apiRequest('/api/organizations/me/logo', {
    method: 'DELETE',
    token: accessToken,
  })
}

/** Build a cache-safe public URL for an organization's current logo. */
export function organizationLogoUrl(organization) {
  if (!organization?.has_logo) return ''
  const version = organization.logo_updated_at
    ? `?v=${encodeURIComponent(organization.logo_updated_at)}`
    : ''
  return apiUrl(`/api/organizations/${organization.id}/logo${version}`)
}
