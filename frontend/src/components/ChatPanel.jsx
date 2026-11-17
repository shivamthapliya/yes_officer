import { MessageSquare, Send } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'

const MAX_LENGTH = 500

export function ChatPanel({ messages, onSend, status, currentUserId, notice, online, className = '' }) {
  const [draft, setDraft] = useState('')
  const logRef = useRef(null)
  const stickToBottom = useRef(true)

  useEffect(() => {
    const el = logRef.current
    if (el && stickToBottom.current) el.scrollTop = el.scrollHeight
  }, [messages])

  const onScroll = () => {
    const el = logRef.current
    stickToBottom.current = el.scrollHeight - el.scrollTop - el.clientHeight < 40
  }

  const submit = (e) => {
    e.preventDefault()
    const text = draft.trim()
    if (!text) return
    if (onSend({ type: 'chat', content: text })) {
      setDraft('')
      stickToBottom.current = true
    }
  }

  const connected = status === 'open'

  return (
    <section className={`panel chat ${className}`} aria-labelledby="chat-title">
      <div className="panel-head">
        <MessageSquare size={18} aria-hidden="true" />
        <h2 id="chat-title">Class chat</h2>
        <span className="spacer" />
        <span className="meta">
          {connected
            ? `${online ?? 0} online`
            : { forbidden: 'no access', connecting: 'connecting…', closed: 'offline' }[status] ?? 'reconnecting…'}
        </span>
      </div>
      <div className="chat-log" ref={logRef} onScroll={onScroll} aria-live="polite" aria-relevant="additions">
        {messages.length === 0 ? (
          <p className="chat-empty">
            Messages appear here live. Chat isn’t saved: it starts fresh whenever you reload.
          </p>
        ) : (
          messages.map((m) => (
            <p key={m.id} className="chat-msg" data-role={m.author_role} data-mine={m.author_id === currentUserId}>
              <span className="who">{m.author_name}</span>
              {m.content}
            </p>
          ))
        )}
      </div>
      {notice && <p className="chat-note" role="alert">{notice}</p>}
      <form className="chat-form" onSubmit={submit}>
        <label htmlFor="chat-input" className="sr-only">
          Message the class
        </label>
        <input
          id="chat-input"
          className="input"
          placeholder={connected ? 'Message the class…' : 'Waiting for connection…'}
          value={draft}
          maxLength={MAX_LENGTH}
          onChange={(e) => setDraft(e.target.value)}
          disabled={!connected}
          autoComplete="off"
        />
        <button type="submit" className="btn btn-primary btn-icon" disabled={!connected || !draft.trim()} aria-label="Send message">
          <Send size={17} aria-hidden="true" />
        </button>
      </form>
    </section>
  )
}
