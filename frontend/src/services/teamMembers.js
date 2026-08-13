import { apiRequest } from './api.js'

/** List service technicians owned by the current organization. */
export function getTeamMembers(accessToken) {
  return apiRequest('/api/organizations/me/team-members', {
    token: accessToken,
  })
}

/** Create a technician with an initial password chosen by the administrator. */
export function createTeamMember(accessToken, email, initialPassword) {
  return apiRequest('/api/organizations/me/team-members', {
    method: 'POST',
    token: accessToken,
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, initial_password: initialPassword }),
  })
}

/** Activate or deactivate one owned service-technician account. */
export function updateTeamMember(accessToken, memberId, status) {
  return apiRequest(`/api/organizations/me/team-members/${memberId}`, {
    method: 'PUT',
    token: accessToken,
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ status }),
  })
}
