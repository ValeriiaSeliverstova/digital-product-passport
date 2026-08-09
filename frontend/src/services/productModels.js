import { apiRequest, apiUrl } from './api.js'

/** List product models owned by the authenticated manufacturer. */
export function getProductModels(accessToken) {
  return apiRequest('/api/product-models', { token: accessToken })
}

/** Load one filtered page of product-model cards. */
export function getProductModelPage(accessToken, filters) {
  const query = new URLSearchParams({
    page: String(filters.page),
    page_size: String(filters.pageSize),
  })
  if (filters.search) query.set('search', filters.search)
  if (filters.categoryId) query.set('category_id', filters.categoryId)
  if (filters.status) query.set('status', filters.status)

  return apiRequest(`/api/product-models/page?${query}`, { token: accessToken })
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

/** Upload or replace a product model's public image. */
export function uploadProductModelImage(accessToken, modelId, image) {
  const body = new FormData()
  body.append('image', image)
  return apiRequest(`/api/product-models/${modelId}/image`, {
    method: 'PUT',
    token: accessToken,
    body,
  })
}

/** Delete a product model's image. */
export function deleteProductModelImage(accessToken, modelId) {
  return apiRequest(`/api/product-models/${modelId}/image`, {
    method: 'DELETE',
    token: accessToken,
  })
}

/** Build a cache-safe image URL from product-model response data. */
export function productModelImageUrl(productModel) {
  if (!productModel?.has_image) return ''
  const version = productModel.image_updated_at
    ? `?v=${encodeURIComponent(productModel.image_updated_at)}`
    : ''
  return apiUrl(`/api/product-models/${productModel.id}/image${version}`)
}
