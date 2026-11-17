import { useLayoutEffect, useRef } from 'react'

/**
 * Pushes an element down so its line box lands exactly on the next ruled line
 * of the enclosing `.index-card`. Content above it (option rows, wrapped
 * prompts) has arbitrary height, so a fixed margin can't keep text on the rules.
 * The element should use `line-height: var(--pitch)` and hold a single line.
 */
export function useSnapToRule(baseMargin = 0) {
  const ref = useRef(null)

  useLayoutEffect(() => {
    const el = ref.current
    const card = el?.closest('.index-card')
    if (!el || !card) return undefined

    const snap = () => {
      const styles = getComputedStyle(card)
      const pitch = parseFloat(styles.getPropertyValue('--pitch'))
      const ruledFrom = parseFloat(styles.getPropertyValue('--ruled-from'))
      if (!pitch || Number.isNaN(ruledFrom)) return
      // Text is centred in its line box; nudge the box so the baseline sits ~3px above the rule,
      // matching the prompt. Baseline ≈ half the leading + cap height (~0.7em).
      const fontSize = parseFloat(getComputedStyle(el).fontSize) || 14
      const baseline = (pitch + 0.7 * fontSize) / 2
      const nudge = Math.max(0, pitch - 4 - baseline)
      el.style.marginTop = `${baseMargin}px`
      const top = el.getBoundingClientRect().top - card.getBoundingClientRect().top
      const offset = (((ruledFrom + nudge - top) % pitch) + pitch) % pitch
      el.style.marginTop = `${baseMargin + offset}px`
    }

    snap()
    if (typeof ResizeObserver === 'undefined') return undefined
    const observer = new ResizeObserver(snap)
    observer.observe(card)
    return () => observer.disconnect()
  }, [baseMargin])

  return ref
}
