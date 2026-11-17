import { useCallback, useEffect, useRef, useState } from 'react'

export const MIN_DISPLAY_MS = 6000

/**
 * Presentation-only coalescing for AI insight snapshots ({ version, ... }).
 * - Snapshots with a version not newer than the latest seen are ignored, so
 *   out-of-order delivery can never roll the panel back.
 * - The visible snapshot stays up at least MIN_DISPLAY_MS; updates arriving in
 *   that window replace a single pending slot, shown when the window ends.
 * - `reset` replaces everything at once (scope change, poll change).
 */
export function useInsightsDisplay(minDisplayMs = MIN_DISPLAY_MS) {
  const [displayed, setDisplayed] = useState(null)
  const [hasPending, setHasPending] = useState(false)
  const latestVersion = useRef(-1)
  const shownAt = useRef(0)
  const pending = useRef(null)
  const timer = useRef(null)

  const show = useCallback((snapshot) => {
    shownAt.current = Date.now()
    pending.current = null
    setHasPending(false)
    setDisplayed(snapshot)
  }, [])

  const push = useCallback(
    (snapshot) => {
      if (!snapshot || snapshot.version <= latestVersion.current) return
      latestVersion.current = snapshot.version
      const elapsed = Date.now() - shownAt.current
      if (shownAt.current === 0 || elapsed >= minDisplayMs) {
        clearTimeout(timer.current)
        timer.current = null
        show(snapshot)
        return
      }
      pending.current = snapshot
      setHasPending(true)
      if (!timer.current) {
        timer.current = setTimeout(() => {
          timer.current = null
          if (pending.current) show(pending.current)
        }, minDisplayMs - elapsed)
      }
    },
    [minDisplayMs, show],
  )

  const reset = useCallback(
    (snapshot = null) => {
      clearTimeout(timer.current)
      timer.current = null
      latestVersion.current = snapshot ? snapshot.version : -1
      pending.current = null
      setHasPending(false)
      shownAt.current = snapshot ? Date.now() : 0
      setDisplayed(snapshot)
    },
    [],
  )

  useEffect(() => () => clearTimeout(timer.current), [])

  return { displayed, hasPending, push, reset, latestVersion }
}
