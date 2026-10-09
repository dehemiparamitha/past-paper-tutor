import { useEffect, useRef, useState } from 'react'
import type { FormEvent } from 'react'
import {
  Routes,
  Route,
  Navigate,
  useNavigate,
  useLocation,
} from 'react-router-dom'
import { askTutor, findSimilarQuestions } from './services/api'
import { isQuestionSearchRequest } from './services/intent'
import type { ChatSession, Message } from './types/api'
import { Mark } from './components/Mark'
import { ChatMessage } from './components/ChatMessage'
import { TopicAnalytics } from './components/TopicAnalytics'
import { PracticeGenerator } from './components/PracticeGenerator'
import { LandingPage } from './components/LandingPage'
import { AuthPage } from './components/AuthPage'
import { ProfileSetup } from './components/ProfileSetup'
import { useAuth } from './context/AuthContext'
import './App.css'

const STORAGE_KEY = 'paperwise_chat_sessions_v1'

function getInitialSessions(): ChatSession[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (raw) {
      const parsed = JSON.parse(raw) as ChatSession[]
      if (Array.isArray(parsed) && parsed.length > 0) {
        return parsed
      }
    }
  } catch {
    // Fallback on error
  }
  const defaultId = `session_${Date.now()}`
  return [
    {
      id: defaultId,
      title: 'New chat',
      messages: [],
      createdAt: Date.now(),
      updatedAt: Date.now(),
    },
  ]
}

function App() {
  const { user, isAuthenticated, isLoading: authIsLoading, needsOnboarding, logout } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()

  const [practiceTopic, setPracticeTopic] = useState<string>('')
  const [practiceGrade, setPracticeGrade] = useState<number | undefined>(undefined)
  const [sessions, setSessions] = useState<ChatSession[]>(getInitialSessions)
  const [activeSessionId, setActiveSessionId] = useState<string>(() => {
    const initial = getInitialSessions()
    return initial[0]?.id || `session_${Date.now()}`
  })
  const [question, setQuestion] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState('')
  const [isSidebarOpen, setIsSidebarOpen] = useState(true)
  const [isProfileMenuOpen, setIsProfileMenuOpen] = useState(false)
  const profileMenuRef = useRef<HTMLDivElement | null>(null)

  const messageRefs = useRef<Record<number, HTMLDivElement | null>>({})
  const composerRef = useRef<HTMLTextAreaElement | null>(null)
  const conversationEndRef = useRef<HTMLDivElement | null>(null)

  // Persist sessions to localStorage
  useEffect(() => {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(sessions))
    } catch {
      // Storage quota or privacy mode
    }
  }, [sessions])

  // Close profile menu when clicking outside
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (profileMenuRef.current && !profileMenuRef.current.contains(e.target as Node)) {
        setIsProfileMenuOpen(false)
      }
    }
    if (isProfileMenuOpen) {
      document.addEventListener('mousedown', handleClickOutside)
    }
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [isProfileMenuOpen])

  // Get active session and its messages
  const activeSession = sessions.find((s) => s.id === activeSessionId) || sessions[0]
  const messages = activeSession?.messages ?? []

  // Auto-scroll on new messages or loading state
  const isChatTab = location.pathname === '/chat' || (location.pathname === '/' && isAuthenticated && !needsOnboarding)
  useEffect(() => {
    if (isChatTab) {
      conversationEndRef.current?.scrollIntoView({ behavior: 'smooth' })
    }
  }, [messages.length, isLoading, isChatTab])

  const startNewChat = () => {
    navigate('/chat')
    if (activeSession && activeSession.messages.length === 0) {
      composerRef.current?.focus()
      return
    }

    const newId = `session_${Date.now()}_${Math.random().toString(36).slice(2, 6)}`
    const newSession: ChatSession = {
      id: newId,
      title: 'New chat',
      messages: [],
      createdAt: Date.now(),
      updatedAt: Date.now(),
    }

    setSessions((prev) => [newSession, ...prev])
    setActiveSessionId(newId)
    setError('')
    setQuestion('')
    composerRef.current?.focus()
  }

  const selectSession = (sessionId: string) => {
    navigate('/chat')
    setActiveSessionId(sessionId)
    setError('')
    setQuestion('')
    if (window.innerWidth < 768) {
      setIsSidebarOpen(false)
    }
  }

  const handlePracticeTopic = (topicName: string, grade?: number) => {
    setPracticeTopic(topicName)
    setPracticeGrade(grade)
    navigate('/practice')
  }

  const deleteSession = (sessionId: string, e: React.MouseEvent) => {
    e.stopPropagation()
    setSessions((prev) => {
      const filtered = prev.filter((s) => s.id !== sessionId)
      if (filtered.length === 0) {
        const fallback: ChatSession = {
          id: `session_${Date.now()}`,
          title: 'New chat',
          messages: [],
          createdAt: Date.now(),
          updatedAt: Date.now(),
        }
        setActiveSessionId(fallback.id)
        return [fallback]
      }
      if (activeSessionId === sessionId) {
        setActiveSessionId(filtered[0].id)
      }
      return filtered
    })
  }

  const focusComposer = () => {
    composerRef.current?.focus()
  }

  const askQuestion = async (event?: FormEvent) => {
    event?.preventDefault()
    const value = question.trim()
    if (!value || isLoading) return

    const userMsgId = Date.now()
    const userMessage: Message = {
      id: userMsgId,
      role: 'user',
      content: value,
      createdAt: Date.now(),
    }

    setQuestion('')
    setError('')
    setIsLoading(true)

    setSessions((prev) =>
      prev.map((s) => {
        if (s.id !== activeSessionId) return s
        const isFirst = s.messages.length === 0
        const newTitle = isFirst ? (value.length > 28 ? value.slice(0, 28) + '...' : value) : s.title
        return {
          ...s,
          title: newTitle,
          messages: [...s.messages, userMessage],
          updatedAt: Date.now(),
        }
      }),
    )

    if (isQuestionSearchRequest(value)) {
      try {
        const results = await findSimilarQuestions(value)
        const assistantMsg: Message = {
          id: Date.now() + 1,
          role: 'assistant',
          content:
            results.length > 0
              ? `I found **${results.length}** past paper question${results.length > 1 ? 's' : ''} related to this topic:`
              : 'I searched the past paper database, but could not find any questions specifically related to that topic. Try searching for topics like "polymers", "photosynthesis", "nitrogen cycle", "urinary system", or "forces".',
          similarQuestions: results,
          createdAt: Date.now(),
        }

        setSessions((prev) =>
          prev.map((s) =>
            s.id === activeSessionId
              ? { ...s, messages: [...s.messages, assistantMsg], updatedAt: Date.now() }
              : s,
          ),
        )
      } catch {
        setError('The tutor could not find similar questions. Check that the backend is running and try again.')
      } finally {
        setIsLoading(false)
      }
      return
    }

    try {
      const answer = await askTutor(value)
      const assistantMsg: Message = {
        id: Date.now() + 1,
        role: 'assistant',
        content: answer,
        createdAt: Date.now(),
      }

      setSessions((prev) =>
        prev.map((s) =>
          s.id === activeSessionId
            ? { ...s, messages: [...s.messages, assistantMsg], updatedAt: Date.now() }
            : s,
        ),
      )
    } catch {
      setError('The tutor could not answer. Check that the backend is running and VITE_API_URL points to the correct port.')
    } finally {
      setIsLoading(false)
    }
  }

  // Filter only sessions that have at least one message or the current empty session
  const historySessions = sessions.filter((s) => s.messages.length > 0 || s.id === activeSessionId)

  // Loading spinner while auth is initializing
  if (authIsLoading) {
    return (
      <div className="auth-card-layout" style={{ display: 'grid', placeItems: 'center', minHeight: '100vh' }}>
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 16 }}>
          <div className="auth-logo-mark" style={{ width: 36, height: 36, borderRadius: 8 }}><Mark /></div>
          <div className="auth-spinner" style={{ width: 22, height: 22 }} />
        </div>
      </div>
    )
  }

  // Helper render for the authenticated main workspace (Chat, Analytics, Practice)
  const renderAuthenticatedWorkspace = (tab: 'chat' | 'analytics' | 'practice') => (
    <main
      className={`page ${messages.length > 0 && tab === 'chat' ? 'chat-mode' : ''} ${tab === 'analytics' ? 'analytics-mode' : ''
        } ${tab === 'practice' ? 'practice-mode' : ''} ${isSidebarOpen ? 'sidebar-open' : 'sidebar-closed'}`}
    >
      {tab === 'chat' && (
        <>
          <section className="hero">
            <h1>What can I help you understand?</h1>
            <p className="intro">Ask questions about your past papers and get clear, exam-focused answers.</p>
          </section>

          <section className="workspace" aria-label="Past paper tutor">
            <div className="conversation" aria-live="polite">
              {messages.map((message) => (
                <ChatMessage
                  key={message.id}
                  message={message}
                  ref={(element) => {
                    messageRefs.current[message.id] = element
                  }}
                />
              ))}

              {isLoading && (
                <div className="message assistant">
                  <div className="avatar"><Mark /></div>
                  <div className="message-body">
                    <span className="message-name">Paperwise</span>
                    <p className="typing"><i /><i /><i /></p>
                  </div>
                </div>
              )}

              <div ref={conversationEndRef} style={{ height: 1 }} />
            </div>

            {error && <p className="error">{error}</p>}

            <form className="composer" onSubmit={askQuestion}>
              <textarea
                ref={composerRef}
                value={question}
                onChange={(event) => setQuestion(event.target.value)}
                onKeyDown={(event) => {
                  if (event.key === 'Enter' && !event.shiftKey) {
                    event.preventDefault()
                    void askQuestion()
                  }
                }}
                placeholder="Ask about a past paper..."
                aria-label="Ask about a past paper"
                rows={1}
              />
              <button type="submit" disabled={!question.trim() || isLoading} aria-label="Send question">
                ↑
              </button>
            </form>
            <p className="composer-footnote">Answers are generated from verified past papers in the syllabus database</p>
          </section>
        </>
      )}

      {tab === 'analytics' && (
        <TopicAnalytics onPracticeTopic={handlePracticeTopic} />
      )}

      {tab === 'practice' && (
        <PracticeGenerator
          initialTopic={practiceTopic}
          initialGrade={practiceGrade}
          onBackToAnalytics={() => navigate('/analytics')}
        />
      )}

      {!isSidebarOpen && (
        <nav className="sidebar-rail" aria-label="Quick actions">
          <button
            type="button"
            className="rail-logo"
            onClick={() => setIsSidebarOpen(true)}
            aria-label="Open sidebar"
            title="Open sidebar"
          >
            <Mark size={22} />
          </button>
          <button type="button" onClick={startNewChat} aria-label="Start a new chat" title="New chat">
            <SidebarGlyph kind="plus" />
          </button>
          <button
            type="button"
            onClick={() => {
              navigate('/chat')
              focusComposer()
            }}
            aria-label="Search"
            title="Search"
          >
            <SidebarGlyph kind="search" />
          </button>
          <button
            type="button"
            className={tab === 'analytics' ? 'active-rail-btn' : ''}
            onClick={() => navigate('/analytics')}
            aria-label="Topic Analytics"
            title="Topic Analytics"
          >
            <SidebarGlyph kind="analytics" />
          </button>
          <button
            type="button"
            className={tab === 'practice' ? 'active-rail-btn' : ''}
            onClick={() => navigate('/practice')}
            aria-label="Practice Questions"
            title="Practice & Quizzes"
          >
            <SidebarGlyph kind="practice" />
          </button>
          <button type="button" onClick={() => setIsSidebarOpen(true)} aria-label="Show conversation history" title="History">
            <SidebarGlyph kind="history" />
          </button>

          {/* Rail profile button with dropdown */}
          <div style={{ marginTop: 'auto', position: 'relative' }} ref={profileMenuRef}>
            {isProfileMenuOpen && (
              <div className="user-profile-dropdown rail-dropdown" role="menu">
                <button
                  type="button"
                  className="profile-dropdown-btn"
                  role="menuitem"
                  onClick={() => {
                    setIsProfileMenuOpen(false)
                    navigate('/settings')
                  }}
                >
                  <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                    <circle cx="12" cy="12" r="3" />
                    <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z" />
                  </svg>
                  <span>Settings</span>
                </button>
                <div className="profile-dropdown-divider" />
                <button
                  type="button"
                  className="profile-dropdown-btn danger"
                  role="menuitem"
                  onClick={async () => {
                    setIsProfileMenuOpen(false)
                    await logout()
                    navigate('/')
                  }}
                >
                  <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                    <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" />
                    <polyline points="16 17 21 12 16 7" />
                    <line x1="21" y1="12" x2="9" y2="12" />
                  </svg>
                  <span>Log out</span>
                </button>
              </div>
            )}
            <button
              type="button"
              className="user-avatar-circle rail-user-avatar"
              onClick={() => setIsProfileMenuOpen((o) => !o)}
              aria-haspopup="true"
              aria-expanded={isProfileMenuOpen}
              title={`${user?.full_name || user?.email || 'User Profile'} \u00b7 Click to open menu`}
            >
              {(user?.full_name || user?.email || 'U').charAt(0).toUpperCase()}
            </button>
          </div>
        </nav>
      )}

      {isSidebarOpen && (
        <aside className="conversation-sidebar" id="conversation-sidebar" aria-label="Previous conversations">
          <div className="sidebar-brand">
            <span className="sidebar-brand-mark"><Mark /></span>
            <span style={{ cursor: 'pointer' }} onClick={() => navigate('/chat')}>paperwise</span>
            <button className="sidebar-close" type="button" onClick={() => setIsSidebarOpen(false)} aria-label="Close sidebar">
              ×
            </button>
          </div>

          <nav className="sidebar-navigation" aria-label="Sidebar navigation">
            <button type="button" className="new-chat-btn" onClick={startNewChat}>
              <SidebarGlyph kind="plus" />
              <span>New chat</span>
            </button>
            <button
              type="button"
              onClick={() => {
                navigate('/chat')
                focusComposer()
              }}
            >
              <SidebarGlyph kind="search" />
              <span>Search</span>
            </button>
            <button
              type="button"
              className={`nav-analytics-btn ${tab === 'analytics' ? 'active' : ''}`}
              onClick={() => navigate('/analytics')}
            >
              <SidebarGlyph kind="analytics" />
              <span>Analytics</span>
              <span className="nav-pill-badge">Trends</span>
            </button>
            <button
              type="button"
              className={`nav-practice-btn ${tab === 'practice' ? 'active' : ''}`}
              onClick={() => navigate('/practice')}
            >
              <SidebarGlyph kind="practice" />
              <span>Practice</span>
              <span className="nav-pill-badge practice-badge">Quizzes</span>
            </button>
          </nav>

          <div className="sidebar-history-heading">History</div>

          <div className="sidebar-history">
            {historySessions.length === 0 || (historySessions.length === 1 && historySessions[0].messages.length === 0) ? (
              <p className="sidebar-empty">Your previous chats will appear here.</p>
            ) : (
              <nav className="conversation-list" aria-label="Conversation history">
                {historySessions.map((s) => {
                  const isActive = tab === 'chat' && s.id === activeSessionId
                  return (
                    <div
                      key={s.id}
                      className={`conversation-item-wrap ${isActive ? 'active' : ''}`}
                    >
                      <button
                        className="conversation-item"
                        type="button"
                        onClick={() => selectSession(s.id)}
                      >
                        <span className="conversation-title">{s.title || 'Untitled chat'}</span>
                      </button>
                      {historySessions.length > 1 && (
                        <button
                          className="conversation-delete"
                          type="button"
                          title="Delete chat"
                          aria-label="Delete chat"
                          onClick={(e) => deleteSession(s.id, e)}
                        >
                          ×
                        </button>
                      )}
                    </div>
                  )
                })}
              </nav>
            )}
          </div>

          {/* User Profile / Settings Footer */}
          <div className="user-profile-footer" ref={profileMenuRef}>
            {isProfileMenuOpen && (
              <div className="user-profile-dropdown" role="menu">
                <button
                  type="button"
                  className="profile-dropdown-btn"
                  role="menuitem"
                  onClick={() => {
                    setIsProfileMenuOpen(false)
                    navigate('/settings')
                  }}
                >
                  <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                    <circle cx="12" cy="12" r="3" />
                    <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z" />
                  </svg>
                  <span>Settings</span>
                </button>
                <div className="profile-dropdown-divider" />
                <button
                  type="button"
                  className="profile-dropdown-btn danger"
                  role="menuitem"
                  onClick={async () => {
                    setIsProfileMenuOpen(false)
                    await logout()
                    navigate('/')
                  }}
                >
                  <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                    <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" />
                    <polyline points="16 17 21 12 16 7" />
                    <line x1="21" y1="12" x2="9" y2="12" />
                  </svg>
                  <span>Log out</span>
                </button>
              </div>
            )}

            <button
              type="button"
              className="user-profile-badge"
              onClick={() => setIsProfileMenuOpen((o) => !o)}
              aria-haspopup="true"
              aria-expanded={isProfileMenuOpen}
              title={`${user?.full_name || user?.email || 'User'} — Click to open menu`}
            >
              <div className="user-avatar-circle">
                {(user?.full_name || user?.email || 'U').charAt(0).toUpperCase()}
              </div>
              <div className="user-badge-info">
                <span className="user-badge-name">{user?.full_name || user?.email}</span>
                <span className="user-badge-role">
                  {user?.is_admin ? '⚡ Administrator' : `Grade ${user?.grade || 11} Student`}
                </span>
              </div>
              <span className={`user-badge-chevron ${isProfileMenuOpen ? 'open' : ''}`}>▲</span>
            </button>
          </div>
        </aside>
      )}
    </main>
  )

  return (
    <Routes>
      {/* 1. Landing / Root Route */}
      <Route
        path="/"
        element={
          !isAuthenticated ? (
            <LandingPage
              onGetStarted={() => navigate('/register')}
              onLogin={() => navigate('/login')}
            />
          ) : needsOnboarding ? (
            <Navigate to="/onboarding" replace />
          ) : (
            renderAuthenticatedWorkspace('chat')
          )
        }
      />

      {/* 2. Login Route */}
      <Route
        path="/login"
        element={
          isAuthenticated ? (
            <Navigate to={needsOnboarding ? '/onboarding' : '/chat'} replace />
          ) : (
            <AuthPage
              initialTab="login"
              onModeChange={(mode) => navigate(mode === 'register' ? '/register' : '/login')}
              onComplete={() => navigate(needsOnboarding ? '/onboarding' : '/chat')}
            />
          )
        }
      />

      {/* 3. Register / Signup Routes */}
      <Route
        path="/register"
        element={
          isAuthenticated ? (
            <Navigate to={needsOnboarding ? '/onboarding' : '/chat'} replace />
          ) : (
            <AuthPage
              initialTab="register"
              onModeChange={(mode) => navigate(mode === 'register' ? '/register' : '/login')}
              onComplete={() => navigate(needsOnboarding ? '/onboarding' : '/chat')}
            />
          )
        }
      />
      <Route path="/signup" element={<Navigate to="/register" replace />} />

      {/* 4. Onboarding / Profile Setup Route */}
      <Route
        path="/onboarding"
        element={
          !isAuthenticated ? (
            <Navigate to="/login" replace />
          ) : (
            <ProfileSetup onComplete={() => navigate('/chat')} />
          )
        }
      />
      {/* 4b. Settings (same as onboarding, but navigates back to /chat on complete) */}
      <Route
        path="/settings"
        element={
          !isAuthenticated ? (
            <Navigate to="/login" replace />
          ) : (
            <ProfileSetup onComplete={() => navigate('/chat')} isEditMode />
          )
        }
      />
      <Route path="/profile-setup" element={<Navigate to="/onboarding" replace />} />
      <Route path="/setup-profile" element={<Navigate to="/onboarding" replace />} />

      {/* 5. Chat Tutor Workspace Route */}
      <Route
        path="/chat"
        element={
          !isAuthenticated ? (
            <Navigate to="/login" replace />
          ) : needsOnboarding ? (
            <Navigate to="/onboarding" replace />
          ) : (
            renderAuthenticatedWorkspace('chat')
          )
        }
      />

      {/* 6. Topic Analytics & Trends Route */}
      <Route
        path="/analytics"
        element={
          !isAuthenticated ? (
            <Navigate to="/login" replace />
          ) : needsOnboarding ? (
            <Navigate to="/onboarding" replace />
          ) : (
            renderAuthenticatedWorkspace('analytics')
          )
        }
      />

      {/* 7. Practice Questions & Quiz Generator Route */}
      <Route
        path="/practice"
        element={
          !isAuthenticated ? (
            <Navigate to="/login" replace />
          ) : needsOnboarding ? (
            <Navigate to="/onboarding" replace />
          ) : (
            renderAuthenticatedWorkspace('practice')
          )
        }
      />

      {/* 8. Fallback / Catch-All */}
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}

type SidebarGlyphProps = {
  kind: 'plus' | 'search' | 'history' | 'chat' | 'analytics' | 'practice' | 'login'
}

function SidebarGlyph({ kind }: SidebarGlyphProps) {
  if (kind === 'chat') {
    return (
      <svg width="22" height="22" viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M7.9 20A9 9 0 1 0 4 16.1L2 22Z" />
      </svg>
    )
  }

  if (kind === 'analytics') {
    return (
      <svg width="22" height="22" viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M18 20V10M12 20V4M6 20v-6" />
      </svg>
    )
  }

  if (kind === 'practice') {
    return (
      <svg width="22" height="22" viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5" />
      </svg>
    )
  }

  if (kind === 'login') {
    return (
      <svg width="22" height="22" viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M15 3h4a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2h-4" />
        <polyline points="10 17 15 12 10 7" />
        <line x1="15" y1="12" x2="3" y2="12" />
      </svg>
    )
  }

  const path =
    kind === 'plus'
      ? 'M12 5v14M5 12h14'
      : kind === 'search'
        ? 'm20 20-4.5-4.5m2-5.5a7.5 7.5 0 1 1-15 0 7.5 7.5 0 0 1 15 0Z'
        : 'M4 6.5h16M4 12h16M4 17.5h16'

  return (
    <svg width="22" height="22" viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d={path} />
    </svg>
  )
}

export default App
