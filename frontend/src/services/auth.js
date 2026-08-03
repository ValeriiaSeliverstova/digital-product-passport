import { apiRequest } from './api.js'

/** Exchange manufacturer credentials for a short-lived access token. */
export function login(email, password) {
  const formData = new URLSearchParams({
    grant_type: 'password',
    username: email.trim(),
    password,
  })

  return apiRequest('/api/auth/login', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/x-www-form-urlencoded',
    },
    body: formData,
  })
}

/** Load the safe user profile associated with an access token. */
export function getCurrentUser(accessToken) {
  return apiRequest('/api/users/me', { token: accessToken })
}
