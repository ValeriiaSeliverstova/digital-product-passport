import { apiRequest } from './api.js'

/** Update the organization owned by the authenticated manufacturer. */
export function updateCurrentOrganization(accessToken, organizationData) {
  return apiRequest('/api/organizations/me', {
    method: 'PUT',
    token: accessToken,
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(organizationData),
  })
}
