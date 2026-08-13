import { apiRequest } from './api.js'

/** Verify an emailed tracking code and load the customer-safe ticket status. */
export function trackSupportTicket(ticketId, trackingCode) {
  return apiRequest(`/api/support-tickets/${encodeURIComponent(ticketId)}/track`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ tracking_code: trackingCode }),
  })
}
