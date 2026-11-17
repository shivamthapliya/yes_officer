import { useState } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'

import { ErrorAlert, PasswordField } from '../../components/common'
import { useAuth } from '../../context/AuthContext'
import { AuthLayout } from './AuthLayout'

export function LoginPage() {
  const { login } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const [form, setForm] = useState({ email: '', password: '' })
  const [error, setError] = useState(null)
  const [busy, setBusy] = useState(false)

  const submit = async (e) => {
    e.preventDefault()
    setBusy(true)
    setError(null)
    try {
      const data = await login(form)
      const fallback = data.user.role === 'TEACHER' ? '/teach' : '/rooms'
      navigate(location.state?.from || fallback, { replace: true })
    } catch (err) {
      setError(err)
      setBusy(false)
    }
  }

  return (
    <AuthLayout title="Sign in">
      <form onSubmit={submit} className="stack" noValidate>
        <ErrorAlert error={error} />
        <label className="field">
          <span>Email</span>
          <input
            className="input"
            type="email"
            autoComplete="email"
            required
            value={form.email}
            onChange={(e) => setForm({ ...form, email: e.target.value })}
          />
        </label>
        <PasswordField
          label="Password"
          autoComplete="current-password"
          value={form.password}
          onChange={(e) => setForm({ ...form, password: e.target.value })}
        />
        <button type="submit" className="btn btn-primary" disabled={busy || !form.email || !form.password}>
          {busy && <span className="spinner" aria-hidden="true" />}
          Sign in
        </button>
        <p className="muted">
          New here? <Link to="/register">Create an account</Link>
        </p>
      </form>
    </AuthLayout>
  )
}
