import { useEffect, useState, type FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import { useGoogleLogin } from '@react-oauth/google'
import { useAuth } from '../context/AuthContext'
import './AuthPage.css'

interface AuthPageProps {
  initialTab?: 'login' | 'register'
  onBack?: () => void
  onComplete?: () => void
  onModeChange?: (mode: 'login' | 'register') => void
}

/* --- SVG Icons --- */
function PaperwiseBookIcon() {
  return (
    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z" />
      <path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z" />
    </svg>
  )
}

function GoogleCircleIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <circle cx="12" cy="12" r="10" />
      <path d="M12 8v8" />
      <path d="M8 12h8" />
    </svg>
  )
}

function MailLabelIcon() {
  return (
    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z" />
      <polyline points="22,6 12,13 2,6" />
    </svg>
  )
}

function LockLabelIcon() {
  return (
    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
      <path d="M7 11V7a5 5 0 0 1 10 0v4" />
    </svg>
  )
}

function UserLabelIcon() {
  return (
    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
      <circle cx="12" cy="7" r="4" />
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

function ConstellationBg() {
  return (
    <svg className="pw-exact-constellation" viewBox="0 0 600 600" fill="none" aria-hidden="true">
      {/* Network lines */}
      <line x1="420" y1="140" x2="520" y2="230" stroke="rgba(0, 223, 130, 0.22)" strokeWidth="1" />
      <line x1="520" y1="230" x2="480" y2="380" stroke="rgba(0, 223, 130, 0.18)" strokeWidth="1" />
      <line x1="480" y1="380" x2="560" y2="480" stroke="rgba(0, 223, 130, 0.22)" strokeWidth="1" />
      <line x1="480" y1="380" x2="390" y2="460" stroke="rgba(0, 223, 130, 0.15)" strokeWidth="1" />
      <line x1="390" y1="460" x2="440" y2="540" stroke="rgba(0, 223, 130, 0.12)" strokeWidth="1" />
      <line x1="520" y1="230" x2="350" y2="280" stroke="rgba(0, 223, 130, 0.14)" strokeWidth="1" />
      <line x1="420" y1="140" x2="320" y2="180" stroke="rgba(0, 223, 130, 0.15)" strokeWidth="1" />
      <line x1="320" y1="180" x2="350" y2="280" stroke="rgba(0, 223, 130, 0.12)" strokeWidth="1" />
      <line x1="350" y1="280" x2="390" y2="460" stroke="rgba(0, 223, 130, 0.16)" strokeWidth="1" />

      {/* Node Dots */}
      <circle cx="420" cy="140" r="3.5" fill="#00df82" />
      <circle cx="520" cy="230" r="4.5" fill="#00df82" />
      <circle cx="480" cy="380" r="3.5" fill="#00df82" />
      <circle cx="560" cy="480" r="4.5" fill="#00df82" />
      <circle cx="390" cy="460" r="3.5" fill="#00df82" />
      <circle cx="440" cy="540" r="3" fill="#00df82" />
      <circle cx="350" cy="280" r="3.5" fill="#00df82" />
      <circle cx="320" cy="180" r="3" fill="#00df82" />

      {/* Subtle secondary nodes */}
      <circle cx="280" cy="360" r="2.5" fill="rgba(0, 223, 130, 0.5)" />
      <circle cx="500" cy="100" r="2" fill="rgba(0, 223, 130, 0.4)" />
    </svg>
  )
}

export function AuthPage({ initialTab = 'login', onBack, onComplete, onModeChange }: AuthPageProps) {
  const { loginWithGoogle, loginWithEmail, registerWithEmail } = useAuth()
  const navigate = useNavigate()
  const [mode, setMode] = useState<'login' | 'register'>(initialTab)

  const [fullName, setFullName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')

  const [rememberMe, setRememberMe] = useState(true)
  const [showPassword, setShowPassword] = useState(false)
  const [showConfirmPassword, setShowConfirmPassword] = useState(false)

  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)

  useEffect(() => {
    setMode(initialTab)
    setError(null)
    setNotice(null)
  }, [initialTab])

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
    setNotice(null)

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
          grade: 12,
        })
      }
      if (onComplete) onComplete()
    } catch (err: any) {
      setError(err.message || 'Authentication failed. Please verify credentials.')
    } finally {
      setLoading(false)
    }
  }

  const switchMode = (newMode: 'login' | 'register') => {
    setMode(newMode)
    setError(null)
    setNotice(null)
    setPassword('')
    setConfirmPassword('')
    if (onModeChange) {
      onModeChange(newMode)
    }
  }

  const handleGoHome = () => {
    if (onBack) {
      onBack()
    } else {
      navigate('/')
    }
  }

  return (
    <div className="pw-exact-auth-page">
      {/* Background ambient lighting and network graphic */}
      <div className="pw-exact-glow-green-right" />
      <div className="pw-exact-glow-green-left" />
      <ConstellationBg />

      {/* Main Container */}
      <div className="pw-exact-container">
        
        {/* =========================================================================
            LEFT COLUMN: HERO HEADLINE & VALUE PROP
            ========================================================================= */}
        <div className="pw-exact-hero">
          
          {/* Logo Brand */}
          <button
            type="button"
            className="pw-exact-logo"
            onClick={handleGoHome}
            title="Return to Paperwise home"
          >
            <span className="pw-exact-logo-icon">
              <PaperwiseBookIcon />
            </span>
            <span className="pw-exact-logo-text">Paperwise</span>
          </button>

          {/* Badge */}
          <div className="pw-exact-badge">
            <span>{mode === 'login' ? 'WELCOME BACK' : 'GET STARTED'}</span>
          </div>

          {/* Giant Headline */}
          <h1 className="pw-exact-title">
            {mode === 'login' ? (
              <>
                Resume<br />
                where you<br />
                left off.
              </>
            ) : (
              <>
                Master<br />
                your exams<br />
                with AI.
              </>
            )}
          </h1>

          {/* Subtitle */}
          <p className="pw-exact-subtitle">
            {mode === 'login'
              ? 'Log back in to access your past papers, AI tutor sessions, and study analytics.'
              : 'Create your free student account to access past paper marking schemes and personalized AI tutoring.'}
          </p>

          {/* Value Bullet Points */}
          <ul className="pw-exact-bullets">
            <li>
              <span className="pw-bullet-dot" />
              <span>AI-powered paper summaries</span>
            </li>
            <li>
              <span className="pw-bullet-dot" />
              <span>Smart study analytics dashboard</span>
            </li>
            <li>
              <span className="pw-bullet-dot" />
              <span>Personalized AI tutor sessions</span>
            </li>
          </ul>

        </div>

        {/* =========================================================================
            RIGHT COLUMN: FLOATING AUTHENTICATION CARD
            ========================================================================= */}
        <div className="pw-exact-card-wrap">
          <div className="pw-exact-card">
            
            {/* Card Header */}
            <div className="pw-exact-card-header">
              <h2 className="pw-exact-card-title">
                {mode === 'login' ? 'Sign in to Paperwise' : 'Create your account'}
              </h2>
              <p className="pw-exact-card-sub">
                {mode === 'login'
                  ? 'Welcome back — your papers are waiting.'
                  : 'Start preparing smarter in under 2 minutes.'}
              </p>
            </div>

            {/* Google Continue Button */}
            <button
              type="button"
              className="pw-exact-google-btn"
              onClick={() => googleLogin()}
              disabled={loading}
            >
              <GoogleCircleIcon />
              <span>{mode === 'login' ? 'Continue with Google' : 'Sign up with Google'}</span>
            </button>

            {/* OR Divider */}
            <div className="pw-exact-divider">
              <span className="pw-exact-divider-line" />
              <span className="pw-exact-divider-text">OR</span>
              <span className="pw-exact-divider-line" />
            </div>

            {/* Alert notices */}
            {error && (
              <div className="pw-exact-alert error" role="alert">
                {error}
              </div>
            )}
            {notice && (
              <div className="pw-exact-alert notice" role="status">
                {notice}
              </div>
            )}

            {/* Form */}
            <form className="pw-exact-form" onSubmit={handleSubmit}>
              {mode === 'register' && (
                <div className="pw-exact-field">
                  <label htmlFor="exact-full-name" className="pw-exact-label">
                    <UserLabelIcon />
                    <span>FULL NAME</span>
                  </label>
                  <input
                    id="exact-full-name"
                    type="text"
                    className="pw-exact-input"
                    placeholder="Kasun Perera"
                    value={fullName}
                    onChange={(e) => setFullName(e.target.value)}
                    required
                    autoComplete="name"
                  />
                </div>
              )}

              <div className="pw-exact-field">
                <label htmlFor="exact-email" className="pw-exact-label">
                  <MailLabelIcon />
                  <span>EMAIL ADDRESS</span>
                </label>
                <input
                  id="exact-email"
                  type="email"
                  className="pw-exact-input"
                  placeholder="johndoe@stanford.edu"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                  autoComplete="email"
                />
              </div>

              <div className="pw-exact-field">
                <label htmlFor="exact-password" className="pw-exact-label">
                  <LockLabelIcon />
                  <span>PASSWORD</span>
                </label>
                <div className="pw-exact-input-container">
                  <input
                    id="exact-password"
                    type={showPassword ? 'text' : 'password'}
                    className="pw-exact-input has-toggle"
                    placeholder="••••••••"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    required
                    autoComplete={mode === 'login' ? 'current-password' : 'new-password'}
                    minLength={6}
                  />
                  <button
                    type="button"
                    className="pw-exact-eye-btn"
                    onClick={() => setShowPassword(!showPassword)}
                    aria-label={showPassword ? 'Hide password' : 'Show password'}
                    tabIndex={-1}
                  >
                    {showPassword ? <EyeOffIcon /> : <EyeIcon />}
                  </button>
                </div>
              </div>

              {mode === 'register' && (
                <div className="pw-exact-field">
                  <label htmlFor="exact-confirm-password" className="pw-exact-label">
                    <LockLabelIcon />
                    <span>CONFIRM PASSWORD</span>
                  </label>
                  <div className="pw-exact-input-container">
                    <input
                      id="exact-confirm-password"
                      type={showConfirmPassword ? 'text' : 'password'}
                      className="pw-exact-input has-toggle"
                      placeholder="••••••••"
                      value={confirmPassword}
                      onChange={(e) => setConfirmPassword(e.target.value)}
                      required
                      autoComplete="new-password"
                      minLength={6}
                    />
                    <button
                      type="button"
                      className="pw-exact-eye-btn"
                      onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                      aria-label={showConfirmPassword ? 'Hide password' : 'Show password'}
                      tabIndex={-1}
                    >
                      {showConfirmPassword ? <EyeOffIcon /> : <EyeIcon />}
                    </button>
                  </div>
                </div>
              )}

              {/* Auxiliary Row: Remember me + Forgot password */}
              <div className="pw-exact-aux-row">
                <label className="pw-exact-checkbox-label">
                  <input
                    type="checkbox"
                    checked={rememberMe}
                    onChange={(e) => setRememberMe(e.target.checked)}
                  />
                  <span className="pw-exact-custom-check" />
                  <span className="pw-exact-check-text">Remember me</span>
                </label>

                {mode === 'login' && (
                  <button
                    type="button"
                    className="pw-exact-forgot-link"
                    onClick={() => setNotice('Password reset instructions will be sent to your email.')}
                  >
                    Forgot password?
                  </button>
                )}
              </div>

              {/* Submit Button */}
              <button
                type="submit"
                className="pw-exact-submit-btn"
                disabled={loading}
              >
                {loading ? (
                  <span>Processing...</span>
                ) : (
                  <span>{mode === 'login' ? 'Sign In →' : 'Create Account →'}</span>
                )}
              </button>
            </form>

            {/* Bottom Mode Switch Link */}
            <div className="pw-exact-footer">
              {mode === 'login' ? (
                <span>
                  Don't have an account?{' '}
                  <button
                    type="button"
                    className="pw-exact-switch-btn"
                    onClick={() => switchMode('register')}
                  >
                    Sign up free
                  </button>
                </span>
              ) : (
                <span>
                  Already have an account?{' '}
                  <button
                    type="button"
                    className="pw-exact-switch-btn"
                    onClick={() => switchMode('login')}
                  >
                    Sign in
                  </button>
                </span>
              )}
            </div>

          </div>
        </div>

      </div>
    </div>
  )
}
