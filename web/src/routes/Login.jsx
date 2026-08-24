import { useState } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import AuraField from '../components/AuraField'
import OrbitHub from '../components/OrbitHub'
import { signIn } from '../auth'
import { IconArrow, IconAlert } from '../components/Icons'

export default function Login({ onSignedIn }) {
  const nav = useNavigate()
  const loc = useLocation()
  const from = loc.state?.from || '/'   // land on the landing page; Ask is a click away

  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [show, setShow] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState(null)

  async function submit(e) {
    e.preventDefault()
    if (busy) return
    setBusy(true); setError(null)
    try {
      const session = await signIn(email, password)
      onSignedIn?.(session)
      nav(from, { replace: true })
    } catch (err) {
      setError(err.message)
      setPassword('')
      setBusy(false)
    }
  }

  return (
    <div className="login">
      <AuraField />

      <div className="login-in">
        <span className="login-pill">ModelBoard</span>

        <h1 className="login-title">
          Evidence you can<br />actually check
        </h1>

        <p className="login-sub">
          Every model in the window, every claim traced to the words an engineer
          published. Sign in to ask the board.
        </p>

        <OrbitHub />

        <form className="login-card" onSubmit={submit} noValidate>
          <label className="field">
            <span className="field-label">Email</span>
            <input
              type="email"
              autoComplete="username"
              inputMode="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="you@company.com"
              required
              autoFocus
            />
          </label>

          <label className="field">
            <span className="field-label">Password</span>
            <span className="field-wrap">
              <input
                type={show ? 'text' : 'password'}
                autoComplete="current-password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••••••"
                required
              />
              <button
                type="button"
                className="field-toggle"
                onClick={() => setShow((s) => !s)}
                aria-label={show ? 'Hide password' : 'Show password'}
              >
                {show ? 'Hide' : 'Show'}
              </button>
            </span>
          </label>

          {error && (
            <p className="login-error" role="alert">
              <IconAlert width={14} height={14} /> {error}
            </p>
          )}

          <button className="btn btn-primary btn-lg login-submit" type="submit" disabled={busy}>
            {busy ? <><span className="spin" /> Checking…</> : <>Sign in <IconArrow width={15} height={15} /></>}
          </button>
        </form>

        <p className="login-foot">
          Preview build · access is issued by the team
        </p>
      </div>
    </div>
  )
}
