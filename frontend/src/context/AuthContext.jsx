import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react'

import { setSessionExpiredHandler } from '../api/client'
import { authApi } from '../api/services'

const AuthContext = createContext(null)

// The session cookie is HttpOnly (and lives on the API's domain), so the page can't
// see it. This hint remembers that a sign-in happened, so signed-out visitors don't
// fire a /auth/me request that is certain to 401 (and log a console error).
const SESSION_HINT = 'yo.hasSession'
const hint = {
  get: () => {
    try {
      return localStorage.getItem(SESSION_HINT) === '1'
    } catch {
      return true // storage blocked: fall back to asking the server
    }
  },
  set: (on) => {
    try {
      if (on) localStorage.setItem(SESSION_HINT, '1')
      else localStorage.removeItem(SESSION_HINT)
    } catch {
      /* storage unavailable */
    }
  },
}

export function AuthProvider({ children }) {
  const [session, setSession] = useState(() =>
    hint.get() ? { status: 'loading', user: null, room: null } : { status: 'anonymous', user: null, room: null },
  )

  const apply = useCallback((data) => {
    hint.set(true)
    setSession({ status: 'authenticated', user: data.user, room: data.room })
    return data
  }, [])

  const signOutLocally = useCallback(() => {
    hint.set(false)
    setSession({ status: 'anonymous', user: null, room: null })
  }, [])

  // Stable identity: consumers list it in effect deps. Unchanged rooms keep the
  // same session object so they don't trigger a re-render (and refetch) loop.
  const setRoom = useCallback(
    (room) =>
      setSession((s) => (s.room?.id === room?.id && s.room?.name === room?.name ? s : { ...s, room })),
    [],
  )

  useEffect(() => {
    setSessionExpiredHandler(signOutLocally)
    if (hint.get()) authApi.me().then(apply).catch(signOutLocally)
  }, [apply, signOutLocally])

  const value = useMemo(
    () => ({
      ...session,
      login: (body) => authApi.login(body).then(apply),
      register: (body) => authApi.register(body).then(apply),
      logout: async () => {
        try {
          await authApi.logout()
        } finally {
          signOutLocally()
        }
      },
      setRoom,
    }),
    [session, apply, signOutLocally, setRoom],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used inside AuthProvider')
  return ctx
}
