import { apiRequest } from './api.js'

/** Load one published passport. This public request does not need a token. */
export function getPublicPassport(publicId) {
  return apiRequest(`/api/passports/${encodeURIComponent(publicId)}`)
}

/** Submit a customer-support request for one published passport. */
export function submitSupportTicket(
  publicId,
  ticket,
  attachment,
  idempotencyKey,
) {
  const body = new FormData()
  Object.entries(ticket).forEach(([field, value]) => body.append(field, value))
  if (attachment) body.append('attachment', attachment)

  return apiRequest(
    `/api/passports/${encodeURIComponent(publicId)}/support-tickets`,
    {
      method: 'POST',
      headers: { 'Idempotency-Key': idempotencyKey },
      body,
    },
  )
}
