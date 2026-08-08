import { apiRequest } from './api.js'

/** List product models owned by the authenticated manufacturer. */
export function getProductModels(accessToken) {
  return apiRequest('/api/product-models', { token: accessToken })
}

/** Load one owned product model. */
export function getProductModel(accessToken, modelId) {
  return apiRequest(`/api/product-models/${modelId}`, { token: accessToken })
}

/** Register a product model using one exact active template version. */
export function createProductModel(accessToken, modelData) {
  return apiRequest('/api/product-models', {
    method: 'POST',
    token: accessToken,
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(modelData),
  })
}

/** Update only the editable product model information. */
export function updateProductModel(accessToken, modelId, modelData) {
  return apiRequest(`/api/product-models/${modelId}`, {
    method: 'PUT',
    token: accessToken,
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(modelData),
  })
}
