import { useEffect, useState } from 'react'

/**
 * Seconds remaining until `deadlineIso`, corrected by the server clock offset
 * (serverTimeIso is the server's "now" when the state was fetched).
 */
export function useCountdown(deadlineIso, serverTimeIso) {
  const [offset, setOffset] = useState(0)
  const [now, setNow] = useState(() => Date.now())

  useEffect(() => {
    if (serverTimeIso) setOffset(new Date(serverTimeIso).getTime() - Date.now())
  }, [serverTimeIso])

  useEffect(() => {
    if (!deadlineIso) return undefined
    const id = setInterval(() => setNow(Date.now()), 250)
    return () => clearInterval(id)
  }, [deadlineIso])

  if (!deadlineIso) return { remainingMs: null, seconds: null, label: '--:--' }
  const remainingMs = Math.max(0, new Date(deadlineIso).getTime() - (now + offset))
  const seconds = Math.ceil(remainingMs / 1000)
  const label = `${String(Math.floor(seconds / 60)).padStart(2, '0')}:${String(seconds % 60).padStart(2, '0')}`
  return { remainingMs, seconds, label }
}
