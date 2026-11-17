import { act, renderHook } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { MIN_DISPLAY_MS, useInsightsDisplay } from '../hooks/useInsightsDisplay'

const snap = (version) => ({ version, insights: [] })

describe('useInsightsDisplay', () => {
  beforeEach(() => vi.useFakeTimers())
  afterEach(() => vi.useRealTimers())

  it('shows the first snapshot immediately', () => {
    const { result } = renderHook(() => useInsightsDisplay())
    act(() => result.current.push(snap(1)))
    expect(result.current.displayed.version).toBe(1)
  })

  it('holds each snapshot for the minimum time and shows only the newest pending one', () => {
    const { result } = renderHook(() => useInsightsDisplay())
    act(() => result.current.push(snap(1)))
    act(() => {
      vi.advanceTimersByTime(1000)
      result.current.push(snap(2))
      result.current.push(snap(3))
    })
    expect(result.current.displayed.version).toBe(1)
    expect(result.current.hasPending).toBe(true)
    act(() => vi.advanceTimersByTime(MIN_DISPLAY_MS - 1000 - 1))
    expect(result.current.displayed.version).toBe(1)
    act(() => vi.advanceTimersByTime(1))
    expect(result.current.displayed.version).toBe(3)
    expect(result.current.hasPending).toBe(false)
  })

  it('ignores stale or repeated versions so the panel never rolls back', () => {
    const { result } = renderHook(() => useInsightsDisplay())
    act(() => result.current.push(snap(5)))
    act(() => {
      vi.advanceTimersByTime(MIN_DISPLAY_MS)
      result.current.push(snap(4))
      result.current.push(snap(5))
    })
    expect(result.current.displayed.version).toBe(5)
    expect(result.current.hasPending).toBe(false)
  })

  it('reset replaces the display immediately (scope change)', () => {
    const { result } = renderHook(() => useInsightsDisplay())
    act(() => result.current.push(snap(2)))
    act(() => result.current.reset(snap(2)))
    expect(result.current.displayed.version).toBe(2)
  })
})
