import { apiRequest } from './api.js'

/** Load one published passport. This public request does not need a token. */
export function getPublicPassport(publicId) {
  return apiRequest(`/api/passports/${encodeURIComponent(publicId)}`)
}

/** Submit a customer-support request for one published passport. */
export function submitSupportTicket(publicId, ticket) {
  return apiRequest(
    `/api/passports/${encodeURIComponent(publicId)}/support-tickets`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(ticket),
    },
  )
}
