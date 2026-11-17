import { act, render, renderHook, screen } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { ChatPanel } from '../components/ChatPanel'
import { chatReducer, MAX_CHAT_MESSAGES, useLiveChat } from '../hooks/useLiveChat'

const msg = (i) => ({ type: 'chat', id: `m${i}`, author_id: 'u', author_name: 'Sam', author_role: 'STUDENT', content: `hello ${i}` })

describe('live chat', () => {
  beforeEach(() => {
    vi.stubGlobal('fetch', vi.fn())
  })
  afterEach(() => vi.unstubAllGlobals())

  it('starts empty on mount and never fetches history', () => {
    const { result } = renderHook(() => useLiveChat())
    expect(result.current.messages).toEqual([])
    render(<ChatPanel messages={result.current.messages} onSend={() => true} status="open" online={1} currentUserId="u" />)
    expect(screen.getByText(/starts fresh whenever you reload/i)).toBeInTheDocument()
    expect(fetch).not.toHaveBeenCalled()
  })

  it('starts empty again after a remount (reload)', () => {
    const first = renderHook(() => useLiveChat())
    act(() => first.result.current.receive(msg(1)))
    expect(first.result.current.messages).toHaveLength(1)
    first.unmount()
    const second = renderHook(() => useLiveChat())
    expect(second.result.current.messages).toEqual([])
  })

  it(`keeps at most ${MAX_CHAT_MESSAGES} messages, dropping the oldest`, () => {
    let state = []
    for (let i = 0; i < MAX_CHAT_MESSAGES + 25; i += 1) state = chatReducer(state, { type: 'received', message: msg(i) })
    expect(state).toHaveLength(MAX_CHAT_MESSAGES)
    expect(state[0].id).toBe('m25')
    expect(state.at(-1).id).toBe(`m${MAX_CHAT_MESSAGES + 24}`)
  })

  it('ignores a duplicate delivery of the same message', () => {
    const state = chatReducer(chatReducer([], { type: 'received', message: msg(1) }), { type: 'received', message: msg(1) })
    expect(state).toHaveLength(1)
  })
})
