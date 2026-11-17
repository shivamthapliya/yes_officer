import { DoorOpen, GraduationCap } from 'lucide-react'
import { useRef, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'

import { ErrorAlert, PasswordField } from '../../components/common'
import { useAuth } from '../../context/AuthContext'
import { AuthLayout } from './AuthLayout'

const ROLES = [
  { value: 'STUDENT', label: 'I’m a student', hint: 'Join your teacher’s room and answer live polls', icon: GraduationCap },
  { value: 'TEACHER', label: 'I’m a teacher', hint: 'Get your own room and run polls', icon: DoorOpen },
]

export function RegisterPage() {
  const { register } = useAuth()
  const navigate = useNavigate()
  const [form, setForm] = useState({ full_name: '', email: '', password: '', role: 'STUDENT', room_name: '' })
  const [error, setError] = useState(null)
  const [busy, setBusy] = useState(false)
  const [confirm, setConfirm] = useState('')
  const [confirmTouched, setConfirmTouched] = useState(false)
  const confirmRef = useRef(null)
  const set = (key) => (e) => setForm({ ...form, [key]: e.target.value })

  const matches = confirm.length > 0 && confirm === form.password
  // Judge a mismatch once the user has left the field or typed as much as the password.
  const showMismatch = confirm.length > 0 && !matches && (confirmTouched || confirm.length >= form.password.length)
  const confirmStatus = matches
    ? { tone: 'ok', text: 'Passwords match.' }
    : showMismatch
      ? { tone: 'error', text: 'Passwords don’t match.' }
      : null

  const submit = async (e) => {
    e.preventDefault()
    if (!matches) {
      setConfirmTouched(true)
      confirmRef.current?.focus()
      return
    }
    setBusy(true)
    setError(null)
    try {
      const body = { ...form, room_name: form.role === 'TEACHER' && form.room_name.trim() ? form.room_name : null }
      const data = await register(body)
      navigate(data.user.role === 'TEACHER' ? '/teach' : '/rooms', { replace: true })
    } catch (err) {
      setError(err)
      setBusy(false)
    }
  }

  return (
    <AuthLayout title="Create your account">
      <form onSubmit={submit} className="stack" noValidate>
        <ErrorAlert error={error} />
        <fieldset className="role-pick">
          <legend className="sr-only">Account type</legend>
          {ROLES.map(({ value, label, hint, icon: Icon }) => (
            <label key={value} className="role-option" data-checked={form.role === value}>
              <input type="radio" name="role" value={value} checked={form.role === value} onChange={set('role')} />
              <Icon size={20} aria-hidden="true" />
              <span>
                <strong>{label}</strong>
                <small>{hint}</small>
              </span>
            </label>
          ))}
        </fieldset>
        <label className="field">
          <span>Full name</span>
          <input className="input" autoComplete="name" required maxLength={120} value={form.full_name} onChange={set('full_name')} />
          <small>Shown to your class in chat and results.</small>
        </label>
        <label className="field">
          <span>Email</span>
          <input className="input" type="email" autoComplete="email" required value={form.email} onChange={set('email')} />
        </label>
        <PasswordField
          label="Password"
          hint="At least 8 characters."
          autoComplete="new-password"
          minLength={8}
          value={form.password}
          onChange={set('password')}
        />
        <PasswordField
          ref={confirmRef}
          label="Confirm password"
          autoComplete="new-password"
          value={confirm}
          onChange={(e) => setConfirm(e.target.value)}
          onBlur={() => setConfirmTouched(true)}
          status={confirmStatus}
        />
        {form.role === 'TEACHER' && (
          <label className="field">
            <span>Room name (optional)</span>
            <input
              className="input"
              maxLength={120}
              placeholder={form.full_name ? `${form.full_name}’s Room` : 'e.g. Year 10 Biology'}
              value={form.room_name}
              onChange={set('room_name')}
            />
            <small>Every teacher gets one permanent room. You can rename it later.</small>
          </label>
        )}
        <button
          type="submit"
          className="btn btn-primary"
          disabled={busy || !form.full_name.trim() || !form.email || form.password.length < 8 || !matches}
        >
          {busy && <span className="spinner" aria-hidden="true" />}
          Create account
        </button>
        <p className="muted">
          Already have an account? <Link to="/login">Sign in</Link>
        </p>
      </form>
    </AuthLayout>
  )
}
