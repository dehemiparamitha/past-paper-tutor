import { createContext, useContext, useState, useEffect, type ReactNode } from 'react'
import type { UserProfile } from '../types/api'
import {
  fetchCurrentUserProfile,
  loginWithGoogle as apiLoginWithGoogle,
  loginWithEmail as apiLoginWithEmail,
  registerWithEmail as apiRegisterWithEmail,
  logoutUser as apiLogoutUser,
  getAccessToken,
} from '../services/api'

interface AuthContextType {
  user: UserProfile | null
  isAuthenticated: boolean
  isAdmin: boolean
  isLoading: boolean
  isAuthModalOpen: boolean
  openAuthModal: () => void
  closeAuthModal: () => void
  loginWithGoogle: (idToken: string, grade?: number, targetExam?: string) => Promise<void>
  loginWithEmail: (email: string, pass: string) => Promise<void>
  registerWithEmail: (params: {
    email: string
    password: string
    full_name?: string
    grade?: number
    target_exam?: string
  }) => Promise<void>
  logout: () => Promise<void>
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<UserProfile | null>(null)
  const [isLoading, setIsLoading] = useState<boolean>(true)
  const [isAuthModalOpen, setIsAuthModalOpen] = useState<boolean>(false)

  // Check existing session on boot
  useEffect(() => {
    async function initAuth() {
      const token = getAccessToken()
      if (token) {
        const profile = await fetchCurrentUserProfile()
        if (profile) {
          setUser(profile)
        }
      }
      setIsLoading(false)
    }
    void initAuth()
  }, [])

  const loginWithGoogle = async (idToken: string, grade?: number, targetExam?: string) => {
    setIsLoading(true)
    try {
      const authRes = await apiLoginWithGoogle(idToken, grade, targetExam)
      setUser(authRes.user)
      setIsAuthModalOpen(false)
    } finally {
      setIsLoading(false)
    }
  }

  const loginWithEmail = async (email: string, pass: string) => {
    setIsLoading(true)
    try {
      const authRes = await apiLoginWithEmail(email, pass)
      setUser(authRes.user)
      setIsAuthModalOpen(false)
    } finally {
      setIsLoading(false)
    }
  }

  const registerWithEmail = async (params: {
    email: string
    password: string
    full_name?: string
    grade?: number
    target_exam?: string
  }) => {
    setIsLoading(true)
    try {
      const authRes = await apiRegisterWithEmail(params)
      setUser(authRes.user)
      setIsAuthModalOpen(false)
    } finally {
      setIsLoading(false)
    }
  }

  const logout = async () => {
    await apiLogoutUser()
    setUser(null)
  }

  const openAuthModal = () => setIsAuthModalOpen(true)
  const closeAuthModal = () => setIsAuthModalOpen(false)

  return (
    <AuthContext.Provider
      value={{
        user,
        isAuthenticated: !!user,
        isAdmin: !!user?.is_admin,
        isLoading,
        isAuthModalOpen,
        openAuthModal,
        closeAuthModal,
        loginWithGoogle,
        loginWithEmail,
        registerWithEmail,
        logout,
      }}
    >
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}
