import { useState, type FormEvent } from 'react'
import { useGoogleLogin } from '@react-oauth/google'
import { useAuth } from '../context/AuthContext'
import './AuthPage.css'

interface AuthPageProps {
  initialTab?: 'login' | 'register'
  onBack?: () => void
  onComplete?: () => void
}

function BookBrandIcon() {
  return (
    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z" />
      <path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z" />
    </svg>
  )
}

function EyeIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
      <circle cx="12" cy="12" r="3" />
    </svg>
  )
}

function EyeOffIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24" />
      <line x1="1" y1="1" x2="23" y2="23" />
    </svg>
  )
}

function SocialTargetIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <circle cx="12" cy="12" r="10" />
      <line x1="15" y1="9" x2="9" y2="15" />
      <line x1="9" y1="9" x2="15" y2="15" />
    </svg>
  )
}

export function AuthPage({ initialTab = 'login', onBack, onComplete }: AuthPageProps) {
  const { loginWithGoogle, loginWithEmail, registerWithEmail } = useAuth()
  const [mode, setMode] = useState<'login' | 'register'>(initialTab)

  const [fullName, setFullName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')

  const [showPassword, setShowPassword] = useState(false)
  const [showConfirmPassword, setShowConfirmPassword] = useState(false)

  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const googleLogin = useGoogleLogin({
    onSuccess: async (tokenResponse) => {
      setLoading(true)
      setError(null)
      try {
        await loginWithGoogle(tokenResponse.access_token || '')
        if (onComplete) onComplete()
      } catch (err: any) {
        setError(err.message || 'Google sign in failed. Please try again.')
      } finally {
        setLoading(false)
      }
    },
    onError: () => {
      setError('Google sign-in was cancelled or encountered an error.')
    },
  })

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    setError(null)

    if (mode === 'register') {
      if (!fullName.trim()) {
        setError('Please enter your full name.')
        return
      }
      if (password.length < 6) {
        setError('Password must be at least 6 characters.')
        return
      }
      if (password !== confirmPassword) {
        setError('Passwords do not match. Please verify.')
        return
      }
    }

    setLoading(true)
    try {
      if (mode === 'login') {
        await loginWithEmail(email, password)
      } else {
        await registerWithEmail({
          email,
          password,
          full_name: fullName,
          grade: 11,
        })
      }
      if (onComplete) onComplete()
    } catch (err: any) {
      setError(err.message || 'Sign in failed. Check your credentials and try again.')
    } finally {
      setLoading(false)
    }
  }

  const switchMode = (newMode: 'login' | 'register') => {
    setMode(newMode)
    setError(null)
    setPassword('')
    setConfirmPassword('')
  }

  return (
    <div className="auth-screen-container">
      <div className="auth-ambient-glow" />

      <div className="auth-card-box">
        {/* Header */}
        <div className="auth-card-header">
          <div className="auth-brand-logo">
            <span className="auth-brand-logo-icon">
              <BookBrandIcon />
            </span>
            <span>Paperwise</span>
          </div>
          <p className="auth-card-subtitle">
            {mode === 'login'
              ? 'Welcome back. Log in to resume study.'
              : 'Create an account to begin focused exam study.'}
          </p>
        </div>

        {/* Error Alert */}
        {error && (
          <div className="auth-alert-error" role="alert">
            {error}
          </div>
        )}

        {/* Form Fields */}
        <form className="auth-form" onSubmit={handleSubmit}>
          {mode === 'register' && (
            <div className="auth-field-group">
              <label htmlFor="auth-full-name" className="auth-field-label">
                FULL NAME
              </label>
              <div className="auth-input-wrapper">
                <input
                  id="auth-full-name"
                  type="text"
                  className="auth-input"
                  placeholder="John Doe"
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                  required
                  autoComplete="name"
                />
              </div>
            </div>
          )}

          <div className="auth-field-group">
            <label htmlFor="auth-email-input" className="auth-field-label">
              EMAIL ADDRESS
            </label>
            <div className="auth-input-wrapper">
              <input
                id="auth-email-input"
                type="email"
                className="auth-input"
                placeholder="johndoe@stanford.edu"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                autoComplete="email"
              />
            </div>
          </div>

          <div className="auth-field-group">
            <label htmlFor="auth-password-input" className="auth-field-label">
              PASSWORD
            </label>
            <div className="auth-input-wrapper">
              <input
                id="auth-password-input"
                type={showPassword ? 'text' : 'password'}
                className="auth-input has-eye"
                placeholder="••••••••"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                autoComplete={mode === 'login' ? 'current-password' : 'new-password'}
                minLength={6}
              />
              <button
                type="button"
                className="auth-eye-btn"
                onClick={() => setShowPassword(!showPassword)}
                aria-label={showPassword ? 'Hide password' : 'Show password'}
              >
                {showPassword ? <EyeOffIcon /> : <EyeIcon />}
              </button>
            </div>
          </div>

          {mode === 'register' && (
            <div className="auth-field-group">
              <label htmlFor="auth-confirm-password" className="auth-field-label">
                CONFIRM PASSWORD
              </label>
              <div className="auth-input-wrapper">
                <input
                  id="auth-confirm-password"
                  type={showConfirmPassword ? 'text' : 'password'}
                  className="auth-input has-eye"
                  placeholder="••••••••"
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  required
                  autoComplete="new-password"
                  minLength={6}
                />
                <button
                  type="button"
                  className="auth-eye-btn"
                  onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                  aria-label={showConfirmPassword ? 'Hide password' : 'Show password'}
                >
                  {showConfirmPassword ? <EyeOffIcon /> : <EyeIcon />}
                </button>
              </div>
            </div>
          )}

          {mode === 'login' && (
            <button
              type="button"
              className="auth-forgot-password-link"
              onClick={() => setError('Password reset instructions will be sent to your email.')}
            >
              Forgot password?
            </button>
          )}

          <button
            type="submit"
            className="auth-submit-btn"
            disabled={loading}
          >
            {loading
              ? 'Please wait...'
              : mode === 'login'
                ? 'Sign In'
                : 'Create Account'}
          </button>
        </form>

        {/* Divider */}
        <div className="auth-divider-wrap">
          <span className="auth-divider-text">
            {mode === 'login' ? 'OR CONTINUE WITH' : 'OR SIGN UP WITH'}
          </span>
        </div>

        {/* Google Social Action Button */}
        <button
          type="button"
          className="auth-social-btn"
          onClick={() => googleLogin()}
          disabled={loading}
        >
          <span className="auth-google-icon">
            <SocialTargetIcon />
          </span>
          <span>{mode === 'login' ? 'Sign in with Google' : 'Sign up with Google'}</span>
        </button>

        {/* Switch mode footer */}
        <div className="auth-switch-footer">
          {mode === 'login' ? (
            <span>
              Don't have an account?
              <button
                type="button"
                className="auth-switch-btn"
                onClick={() => switchMode('register')}
              >
                Sign up
              </button>
            </span>
          ) : (
            <span>
              Already have an account?
              <button
                type="button"
                className="auth-switch-btn"
                onClick={() => switchMode('login')}
              >
                Log in
              </button>
            </span>
          )}
        </div>
      </div>
    </div>
  )
}
