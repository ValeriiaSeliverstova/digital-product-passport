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

/** Request reset instructions without exposing whether the account exists. */
export function forgotPassword(email) {
  return apiRequest('/api/auth/forgot-password', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ email: email.trim() }),
  })
}

/** Replace a password using the private token from the reset email. */
export function resetPassword(token, newPassword) {
  return apiRequest('/api/auth/reset-password', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ token, new_password: newPassword }),
  })
}

/** Load the safe user profile associated with an access token. */
export function getCurrentUser(accessToken) {
  return apiRequest('/api/users/me', { token: accessToken })
}

/** Verify the existing password before replacing it for the current user. */
export function changePassword(accessToken, currentPassword, newPassword) {
  return apiRequest('/api/users/me/password', {
    method: 'PUT',
    token: accessToken,
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      current_password: currentPassword,
      new_password: newPassword,
    }),
  })
}
