import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react'

import { setSessionExpiredHandler } from '../api/client'
import { authApi } from '../api/services'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [session, setSession] = useState({ status: 'loading', user: null, room: null })

  const apply = useCallback((data) => {
    setSession({ status: 'authenticated', user: data.user, room: data.room })
    return data
  }, [])

  const signOutLocally = useCallback(() => setSession({ status: 'anonymous', user: null, room: null }), [])

  // Stable identity: consumers list it in effect deps. Unchanged rooms keep the
  // same session object so they don't trigger a re-render (and refetch) loop.
  const setRoom = useCallback(
    (room) =>
      setSession((s) => (s.room?.id === room?.id && s.room?.name === room?.name ? s : { ...s, room })),
    [],
  )

  useEffect(() => {
    setSessionExpiredHandler(signOutLocally)
    authApi.me().then(apply).catch(signOutLocally)
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
