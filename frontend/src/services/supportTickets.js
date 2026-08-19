import { apiRequest } from './api.js'

/** Verify an emailed tracking code and load the customer-safe ticket status. */
export function trackSupportTicket(ticketId, trackingCode, productPublicId) {
  return apiRequest(`/api/support-tickets/${encodeURIComponent(ticketId)}/track`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      tracking_code: trackingCode,
      ...(productPublicId && { product_public_id: productPublicId }),
    }),
  })
}

/** Add a customer reply to the Azure ticket after verifying its private code. */
export function replyToSupportTicket(
  ticketId,
  trackingCode,
  message,
  productPublicId,
) {
  return apiRequest(`/api/support-tickets/${encodeURIComponent(ticketId)}/comments`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      tracking_code: trackingCode,
      message,
      ...(productPublicId && { product_public_id: productPublicId }),
    }),
  })
}
