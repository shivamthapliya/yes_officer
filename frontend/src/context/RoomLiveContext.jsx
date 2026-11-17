import { createContext, useCallback, useContext, useEffect, useMemo, useRef } from 'react'

import { useLiveChat } from '../hooks/useLiveChat'
import { useRoomSocket } from '../realtime/useRoomSocket'

const RoomLiveContext = createContext(null)

/**
 * One WebSocket per room: chat lives here (in memory only) and every other
 * server event fans out to subscribers registered with useRoomEvent.
 */
export function RoomLiveProvider({ roomId, children }) {
  const { messages, receive } = useLiveChat()
  const listeners = useRef(new Set())
  const reconnectListeners = useRef(new Set())

  const onEvent = useCallback(
    (event) => {
      if (event.type === 'chat') receive(event)
      listeners.current.forEach((fn) => fn(event))
    },
    [receive],
  )
  const onReconnect = useCallback(() => reconnectListeners.current.forEach((fn) => fn()), [])

  const { status, online, send } = useRoomSocket(roomId, { onEvent, onReconnect })

  const subscribe = useCallback((fn) => {
    listeners.current.add(fn)
    return () => listeners.current.delete(fn)
  }, [])
  const subscribeReconnect = useCallback((fn) => {
    reconnectListeners.current.add(fn)
    return () => reconnectListeners.current.delete(fn)
  }, [])

  const value = useMemo(
    () => ({ roomId, status, online, send, messages, subscribe, subscribeReconnect }),
    [roomId, status, online, send, messages, subscribe, subscribeReconnect],
  )
  return <RoomLiveContext.Provider value={value}>{children}</RoomLiveContext.Provider>
}

export function useRoomLive() {
  const ctx = useContext(RoomLiveContext)
  if (!ctx) throw new Error('useRoomLive must be used inside RoomLiveProvider')
  return ctx
}

/** Subscribe to room events; the latest handler is always used. */
export function useRoomEvent(handler, onReconnect) {
  const { subscribe, subscribeReconnect } = useRoomLive()
  const ref = useRef({ handler, onReconnect })
  ref.current = { handler, onReconnect }
  useEffect(() => subscribe((e) => ref.current.handler?.(e)), [subscribe])
  useEffect(() => subscribeReconnect(() => ref.current.onReconnect?.()), [subscribeReconnect])
}
