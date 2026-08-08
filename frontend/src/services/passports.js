import { apiRequest } from './api.js'

/** Load one published passport. This public request does not need a token. */
export function getPublicPassport(publicId) {
  return apiRequest(`/api/passports/${encodeURIComponent(publicId)}`)
}
