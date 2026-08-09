import { apiRequest } from './api.js'

/** List physical product items owned by the authenticated manufacturer. */
export function getProductItems(accessToken, filters) {
  const query = new URLSearchParams({
    page: String(filters.page),
    page_size: String(filters.pageSize),
  })
  if (filters.search) query.set('search', filters.search)
  if (filters.status) query.set('status', filters.status)
  if (filters.manufacturedFrom) {
    query.set('manufactured_from', filters.manufacturedFrom)
  }
  if (filters.manufacturedTo) {
    query.set('manufactured_to', filters.manufacturedTo)
  }
  return apiRequest(`/api/product-items?${query}`, { token: accessToken })
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
