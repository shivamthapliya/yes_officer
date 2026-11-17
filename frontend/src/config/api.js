/**
 * The single place where backend locations are defined.
 *
 * To point the app at another backend, change VITE_API_BASE_URL in `.env`
 * (or the deploy environment). Nothing else in the codebase knows a URL.
 */

const trimSlash = (value) => value.replace(/\/+$/, '')

export const API_BASE_URL = trimSlash(import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000')
export const API_PREFIX = '/api'
export const API_ROOT = `${API_BASE_URL}${API_PREFIX}`

/**
 * Headers sent with every REST call. ngrok's free domains answer browser
 * requests with an HTML warning page unless this header is present.
 */
export const API_HEADERS = /\.ngrok(-free)?\.(app|dev|io)$/.test(new URL(API_BASE_URL).hostname)
  ? { 'ngrok-skip-browser-warning': 'true' }
  : {}

export const WS_BASE_URL = trimSlash(
  import.meta.env.VITE_WS_BASE_URL || API_BASE_URL.replace(/^http(s?):\/\//, (_, s) => `ws${s}://`),
)

/** Every REST endpoint, as path builders relative to API_ROOT. */
export const ENDPOINTS = {
  auth: {
    register: () => '/auth/register',
    login: () => '/auth/login',
    refresh: () => '/auth/refresh',
    logout: () => '/auth/logout',
    me: () => '/auth/me',
  },
  rooms: {
    list: () => '/rooms',
    mine: () => '/rooms/mine',
    joined: () => '/rooms/joined',
    detail: (roomId) => `/rooms/${roomId}`,
    join: (roomId) => `/rooms/${roomId}/join`,
    participants: (roomId) => `/rooms/${roomId}/participants`,
    activePoll: (roomId) => `/rooms/${roomId}/active-poll`,
    polls: (roomId) => `/rooms/${roomId}/polls`,
  },
  polls: {
    detail: (pollId) => `/polls/${pollId}`,
    questions: (pollId) => `/polls/${pollId}/questions`,
    questionOrder: (pollId) => `/polls/${pollId}/questions/order`,
    question: (questionId) => `/questions/${questionId}`,
    start: (pollId) => `/polls/${pollId}/start`,
    nextQuestion: (pollId) => `/polls/${pollId}/next-question`,
    end: (pollId) => `/polls/${pollId}/end`,
    cancel: (pollId) => `/polls/${pollId}/cancel`,
    live: (pollId) => `/polls/${pollId}/live`,
    answers: (pollId) => `/polls/${pollId}/answers`,
    results: (pollId) => `/polls/${pollId}/results`,
    insights: (pollId) => `/polls/${pollId}/insights`,
    studentInsights: (pollId, studentId) => `/polls/${pollId}/students/${studentId}/insights`,
  },
  history: {
    myPolls: () => '/me/polls',
    review: (pollId) => `/me/polls/${pollId}/review`,
  },
}

/** WebSocket endpoints, as absolute URLs. */
export const WS_ENDPOINTS = {
  room: (roomId) => `${WS_BASE_URL}${API_PREFIX}/ws/rooms/${roomId}`,
}
