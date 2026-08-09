import { apiRequest } from './api.js'

/** List physical product items owned by the authenticated manufacturer. */
export function getProductItems(accessToken) {
  return apiRequest('/api/product-items', { token: accessToken })
}

/** Load one owned physical product and its passport values. */
export function getProductItem(accessToken, itemId) {
  return apiRequest(`/api/product-items/${itemId}`, { token: accessToken })
}

/** Register one physical product as a draft passport. */
export function createProductItem(accessToken, itemData) {
  return apiRequest('/api/product-items', {
    method: 'POST',
    token: accessToken,
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(itemData),
  })
}

/** Save draft values or move a product through its lifecycle. */
export function updateProductItem(accessToken, itemId, itemData) {
  return apiRequest(`/api/product-items/${itemId}`, {
    method: 'PUT',
    token: accessToken,
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(itemData),
  })
}

/** Generate a fresh printable SVG QR code for a published product item. */
export function getProductItemQrCode(accessToken, itemId) {
  return apiRequest(`/api/product-items/${itemId}/qr-code`, {
    token: accessToken,
    responseType: 'blob',
    headers: { Accept: 'image/svg+xml' },
  })
}

/** Load the complete lifecycle history visible to the manufacturer. */
export function getLifecycleEvents(accessToken, itemId) {
  return apiRequest(`/api/product-items/${itemId}/lifecycle-events`, {
    token: accessToken,
  })
}

/** Append one event to a published or retired product item. */
export function createLifecycleEvent(accessToken, itemId, eventData) {
  return apiRequest(`/api/product-items/${itemId}/lifecycle-events`, {
    method: 'POST',
    token: accessToken,
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(eventData),
  })
}
