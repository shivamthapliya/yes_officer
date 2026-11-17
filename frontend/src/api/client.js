import { API_HEADERS, API_ROOT, ENDPOINTS } from '../config/api'

export class ApiError extends Error {
  constructor({ status, code, message, details }) {
    super(message)
    this.status = status
    this.code = code
    this.details = details || {}
  }
}

const SESSION_ERRORS = new Set(['MISSING_TOKEN', 'INVALID_TOKEN'])
let refreshing = null
let onSessionExpired = () => {}

/** Called once by the auth provider so the client can sign the user out. */
export function setSessionExpiredHandler(handler) {
  onSessionExpired = handler
}

function buildUrl(path, params) {
  const url = new URL(`${API_ROOT}${path}`)
  Object.entries(params || {}).forEach(([k, v]) => {
    if (v !== undefined && v !== null && v !== '') url.searchParams.set(k, v)
  })
  return url.toString()
}

async function send(method, path, { body, params } = {}) {
  let response
  try {
    response = await fetch(buildUrl(path, params), {
      method,
      credentials: 'include',
      headers: { ...API_HEADERS, ...(body !== undefined ? { 'Content-Type': 'application/json' } : {}) },
      body: body !== undefined ? JSON.stringify(body) : undefined,
    })
  } catch {
    throw new ApiError({ status: 0, code: 'NETWORK', message: 'Can’t reach the server. Check your connection and try again.' })
  }
  if (response.status === 204) return null
  const data = await response.json().catch(() => null)
  if (!response.ok) {
    throw new ApiError({
      status: response.status,
      code: data?.error_code || 'HTTP_ERROR',
      message: data?.message || `Request failed (${response.status})`,
      details: data?.details,
    })
  }
  return data
}

function refreshSession() {
  refreshing ??= send('POST', ENDPOINTS.auth.refresh()).finally(() => {
    refreshing = null
  })
  return refreshing
}

/**
 * JSON request with cookie auth. On an expired access token it rotates the
 * session once and retries; if that fails the user is signed out.
 */
export async function request(method, path, options = {}) {
  try {
    return await send(method, path, options)
  } catch (error) {
    const isAuthCall = path.startsWith('/auth/')
    if (!(error instanceof ApiError) || error.status !== 401 || !SESSION_ERRORS.has(error.code) || isAuthCall) {
      throw error
    }
    try {
      await refreshSession()
    } catch {
      onSessionExpired()
      throw error
    }
    return send(method, path, options)
  }
}

export const api = {
  get: (path, params) => request('GET', path, { params }),
  post: (path, body) => request('POST', path, { body: body ?? {} }),
  patch: (path, body) => request('PATCH', path, { body }),
  put: (path, body) => request('PUT', path, { body }),
  delete: (path) => request('DELETE', path),
  refresh: refreshSession,
}
