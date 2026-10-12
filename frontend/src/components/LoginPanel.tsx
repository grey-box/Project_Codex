import { useState, type FormEvent } from 'react'
import { loginUser } from '../services/api'

interface LoginPanelProps {
  onLogin: (token: string, role: string, email: string) => void
}

function LoginPanel({ onLogin }: LoginPanelProps) {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [isLoggingIn, setIsLoggingIn] = useState(false)

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()

    if (!email.trim() || !password) {
      setError('Email and password are required.')
      return
    }

    setIsLoggingIn(true)
    setError('')

    try {
      const response = await loginUser(email.trim(), password)

      onLogin(
        response.access_token,
        response.role,
        email.trim(),
      )

      setPassword('')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Login failed.')
    } finally {
      setIsLoggingIn(false)
    }
  }

  return (
    <section className="auth-panel">
      <h3>Account Login</h3>

      <form className="auth-form" onSubmit={handleSubmit}>
        <label htmlFor="login-email">Email</label>
        <input
          id="login-email"
          type="email"
          value={email}
          onChange={(event) => setEmail(event.target.value)}
          autoComplete="username"
          placeholder="Email address"
        />

        <label htmlFor="login-password">Password</label>
        <input
          id="login-password"
          type="password"
          value={password}
          onChange={(event) => setPassword(event.target.value)}
          autoComplete="current-password"
          placeholder="Password"
        />

        {error && (
          <div className="message message--error">
            {error}
          </div>
        )}

        <button type="submit" disabled={isLoggingIn}>
          {isLoggingIn ? 'Logging in...' : 'Login'}
        </button>
      </form>
    </section>
  )
}

export default LoginPanel
