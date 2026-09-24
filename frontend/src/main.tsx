import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { GoogleOAuthProvider } from '@react-oauth/google'
import { AuthProvider } from './context/AuthContext'
import './index.css'
import App from './App.tsx'

const googleClientId =
  import.meta.env.VITE_GOOGLE_CLIENT_ID ||
  '1033272115548-ln9kptpkqadrc7s9ndio1rlgh9u3ggh6.apps.googleusercontent.com'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <GoogleOAuthProvider clientId={googleClientId}>
      <AuthProvider>
        <App />
      </AuthProvider>
    </GoogleOAuthProvider>
  </StrictMode>,
)
