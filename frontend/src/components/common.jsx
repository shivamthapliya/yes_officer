import { AlertCircle, Check, Eye, EyeOff, X } from 'lucide-react'
import { forwardRef, useEffect, useId, useRef, useState } from 'react'

/**
 * Password input with a show/hide toggle. `status` is an optional
 * { tone: 'ok' | 'error', text } line under the field; it replaces `hint`.
 */
export const PasswordField = forwardRef(function PasswordField(
  { label, hint, status, autoComplete, value, onChange, onBlur, minLength },
  ref,
) {
  const id = useId()
  const [visible, setVisible] = useState(false)
  const noteId = `${id}-note`
  const note = status || (hint ? { text: hint } : null)
  return (
    <div className="field">
      <label htmlFor={id}>{label}</label>
      <div className="password-wrap">
        <input
          ref={ref}
          id={id}
          className="input"
          type={visible ? 'text' : 'password'}
          autoComplete={autoComplete}
          minLength={minLength}
          required
          spellCheck={false}
          autoCapitalize="none"
          value={value}
          onChange={onChange}
          onBlur={onBlur}
          aria-invalid={status?.tone === 'error' || undefined}
          aria-describedby={note ? noteId : undefined}
        />
        <button
          type="button"
          className="password-toggle"
          aria-label={visible ? `Hide ${label.toLowerCase()}` : `Show ${label.toLowerCase()}`}
          aria-pressed={visible}
          aria-controls={id}
          onClick={() => setVisible((v) => !v)}
        >
          {visible ? <EyeOff size={18} aria-hidden="true" /> : <Eye size={18} aria-hidden="true" />}
        </button>
      </div>
      {note && (
        <small id={noteId} className="field-note" data-tone={note.tone} aria-live={status ? 'polite' : undefined}>
          {note.tone === 'ok' && <Check size={14} aria-hidden="true" />}
          {note.tone === 'error' && <X size={14} aria-hidden="true" />}
          {note.text}
        </small>
      )}
    </div>
  )
})

export function Spinner({ label = 'Loading' }) {
  return <span className="spinner" role="status" aria-label={label} />
}

export function LoadingBlock({ label = 'Loading…' }) {
  return (
    <div className="loading-block">
      <span className="spinner" aria-hidden="true" />
      <span>{label}</span>
    </div>
  )
}

export function ErrorAlert({ error, children }) {
  if (!error && !children) return null
  const problems = error?.details?.problems
  const fieldErrors = error?.details?.errors
  return (
    <div className="alert alert-error" role="alert">
      <AlertCircle size={18} aria-hidden="true" style={{ flex: 'none', marginTop: 2 }} />
      <div>
        {children || error.message}
        {problems?.length > 0 && (
          <ul>
            {problems.map((p) => (
              <li key={p}>{p}</li>
            ))}
          </ul>
        )}
        {fieldErrors?.length > 0 && (
          <ul>
            {fieldErrors.map((e) => (
              <li key={`${e.field}${e.reason}`}>{e.reason.replace(/^Value error, /, '')}</li>
            ))}
          </ul>
        )}
      </div>
    </div>
  )
}

export function StatusTag({ status }) {
  const label = { DRAFT: 'Draft', ACTIVE: 'Live', COMPLETED: 'Ended', CANCELLED: 'Cancelled' }[status] || status
  return (
    <span className="status-tag" data-status={status}>
      {label}
    </span>
  )
}

export function EmptyState({ icon: Icon, title, children, action }) {
  return (
    <div className="empty">
      {Icon && <Icon size={36} strokeWidth={1.5} aria-hidden="true" />}
      <h2>{title}</h2>
      {children && <p>{children}</p>}
      {action}
    </div>
  )
}

/** Native <dialog> confirm, used only for destructive or irreversible actions. */
export function ConfirmDialog({ open, title, children, confirmLabel, tone = 'danger', busy, onConfirm, onCancel }) {
  const ref = useRef(null)
  useEffect(() => {
    const dialog = ref.current
    if (!dialog) return
    if (open && !dialog.open) dialog.showModal()
    if (!open && dialog.open) dialog.close()
  }, [open])
  return (
    <dialog ref={ref} className="dialog" onCancel={(e) => { e.preventDefault(); onCancel() }} aria-labelledby="confirm-title">
      <div className="dialog-body">
        <h2 id="confirm-title">{title}</h2>
        <div className="muted">{children}</div>
      </div>
      <div className="dialog-actions">
        <button type="button" className="btn btn-ghost" onClick={onCancel} disabled={busy}>
          Keep going
        </button>
        <button type="button" className={`btn ${tone === 'danger' ? 'btn-danger' : 'btn-primary'}`} onClick={onConfirm} disabled={busy}>
          {busy && <span className="spinner" aria-hidden="true" />}
          {confirmLabel}
        </button>
      </div>
    </dialog>
  )
}
