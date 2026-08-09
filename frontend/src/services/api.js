const API_URL = (import.meta.env.VITE_API_URL || 'http://localhost:8000').replace(
  /\/$/,
  '',
)

/** Build a URL for browser-loaded resources such as organization logos. */
export function apiUrl(path) {
  return `${API_URL}${path}`
}

export class ApiError extends Error {
  constructor(status, message) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

/** Send one request and convert unsuccessful responses into a consistent error. */
export async function apiRequest(path, options = {}) {
  const { token, headers, responseType = 'json', ...requestOptions } = options
  const requestHeaders = {
    Accept: 'application/json',
    ...headers,
  }

  if (token) {
    requestHeaders.Authorization = `Bearer ${token}`
  }

  const response = await fetch(`${API_URL}${path}`, {
    ...requestOptions,
    headers: requestHeaders,
  })

  if (!response.ok) {
    let message = 'The request could not be completed.'

    try {
      const responseBody = await response.json()
      if (typeof responseBody.detail === 'string') {
        message = responseBody.detail
      }
    } catch {
      // Some error responses may not contain JSON, so keep the safe fallback.
    }

    throw new ApiError(response.status, message)
  }

  if (response.status === 204) {
    return null
  }

  if (responseType === 'blob') {
    return response.blob()
  }

  return response.json()
}
