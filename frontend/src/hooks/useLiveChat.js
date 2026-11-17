import { useCallback, useReducer } from 'react'

/** Chat is ephemeral: in-memory only, capped, never fetched on mount or reconnect. */
export const MAX_CHAT_MESSAGES = 200

export function chatReducer(state, action) {
  switch (action.type) {
    case 'received': {
      if (state.some((m) => m.id === action.message.id)) return state
      const next = [...state, action.message]
      return next.length > MAX_CHAT_MESSAGES ? next.slice(next.length - MAX_CHAT_MESSAGES) : next
    }
    case 'clear':
      return []
    default:
      return state
  }
}

export function useLiveChat() {
  const [messages, dispatch] = useReducer(chatReducer, [])
  const receive = useCallback((message) => dispatch({ type: 'received', message }), [])
  const clear = useCallback(() => dispatch({ type: 'clear' }), [])
  return { messages, receive, clear }
}
