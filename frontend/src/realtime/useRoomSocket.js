import { useCallback, useEffect, useRef, useState } from 'react'

import { api } from '../api/client'
import { WS_ENDPOINTS } from '../config/api'

const PING_MS = 25_000
const MAX_BACKOFF_MS = 10_000
const CLOSE_UNAUTHORIZED = 4401
const CLOSE_FORBIDDEN = 4403

/**
 * Room WebSocket with automatic reconnect.
 * status: connecting | open | reconnecting | forbidden | closed
 * `onEvent` receives every server event; `onReconnect` fires after a
 * reconnect so callers can re-fetch authoritative state (never chat history).
 */
export function useRoomSocket(roomId, { onEvent, onReconnect } = {}) {
  const [status, setStatus] = useState('connecting')
  const [online, setOnline] = useState([])
  const socketRef = useRef(null)
  const handlers = useRef({ onEvent, onReconnect })
  handlers.current = { onEvent, onReconnect }

  useEffect(() => {
    if (!roomId) return undefined
    let disposed = false
    let attempt = 0
    let pingTimer
    let retryTimer
    let hasOpened = false

    const connect = () => {
      setStatus(hasOpened ? 'reconnecting' : 'connecting')
      const ws = new WebSocket(WS_ENDPOINTS.room(roomId))
      socketRef.current = ws

      ws.onopen = () => {
        const reconnected = hasOpened
        hasOpened = true
        attempt = 0
        setStatus('open')
        pingTimer = setInterval(() => ws.readyState === WebSocket.OPEN && ws.send('{"type":"ping"}'), PING_MS)
        if (reconnected) handlers.current.onReconnect?.()
      }
      ws.onmessage = (message) => {
        let event
        try {
          event = JSON.parse(message.data)
        } catch {
          return
        }
        if (event.type === 'pong') return
        if (event.type === 'presence') setOnline(event.users || [])
        handlers.current.onEvent?.(event)
      }
      ws.onclose = async (closeEvent) => {
        clearInterval(pingTimer)
        if (disposed) return
        if (closeEvent.code === CLOSE_FORBIDDEN) {
          setStatus('forbidden')
          return
        }
        if (closeEvent.code === CLOSE_UNAUTHORIZED) {
          try {
            await api.refresh()
          } catch {
            setStatus('closed')
            return
          }
        }
        attempt += 1
        setStatus('reconnecting')
        retryTimer = setTimeout(connect, Math.min(MAX_BACKOFF_MS, 500 * 2 ** attempt))
      }
    }

    connect()
    return () => {
      disposed = true
      clearInterval(pingTimer)
      clearTimeout(retryTimer)
      const ws = socketRef.current
      socketRef.current = null
      if (ws?.readyState === WebSocket.CONNECTING) {
        // Closing mid-handshake logs a browser warning (every StrictMode remount); close once open instead.
        ws.onmessage = null
        ws.onopen = () => ws.close(1000)
      } else {
        ws?.close(1000)
      }
    }
  }, [roomId])

  const send = useCallback((payload) => {
    const ws = socketRef.current
    if (!ws || ws.readyState !== WebSocket.OPEN) return false
    ws.send(JSON.stringify(payload))
    return true
  }, [])

  return { status, online, send }
}
