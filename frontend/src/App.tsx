import { useEffect, useRef, useState } from 'react'
import type { FormEvent } from 'react'
import { askTutor, findSimilarQuestions } from './services/api'
import { isQuestionSearchRequest } from './services/intent'
import type { ChatSession, Message } from './types/api'
import { Mark } from './components/Mark'
import { ChatMessage } from './components/ChatMessage'
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
  const [sessions, setSessions] = useState<ChatSession[]>(getInitialSessions)
  const [activeSessionId, setActiveSessionId] = useState<string>(() => {
    const initial = getInitialSessions()
    return initial[0]?.id || `session_${Date.now()}`
  })
  const [question, setQuestion] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState('')
  const [isSidebarOpen, setIsSidebarOpen] = useState(true)

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

  // Get active session and its messages
  const activeSession = sessions.find((s) => s.id === activeSessionId) || sessions[0]
  const messages = activeSession?.messages ?? []

  // Auto-scroll on new messages or loading state
  useEffect(() => {
    conversationEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages.length, isLoading])

  const startNewChat = () => {
    // If the active session is already blank, just focus the composer
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
    setActiveSessionId(sessionId)
    setError('')
    setQuestion('')
    if (window.innerWidth < 768) {
      setIsSidebarOpen(false)
    }
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

    // Append user message and set title if this is the first message
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

  return (
    <main className={`page ${messages.length > 0 ? 'chat-mode' : ''} ${isSidebarOpen ? 'sidebar-open' : 'sidebar-closed'}`}>
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
        <p className="composer-footnote">Answers are generated from uploaded past papers</p>
      </section>

      {!isSidebarOpen && (
        <nav className="sidebar-rail" aria-label="Quick actions">
          <a className="rail-logo" href="/" aria-label="Paperwise home"><Mark /></a>
          <button type="button" onClick={startNewChat} aria-label="Start a new chat" title="New chat">
            <SidebarGlyph kind="plus" />
          </button>
          <button type="button" onClick={focusComposer} aria-label="Search" title="Search">
            <SidebarGlyph kind="search" />
          </button>
          <button type="button" onClick={() => setIsSidebarOpen(true)} aria-label="Show conversation history" title="History">
            <SidebarGlyph kind="history" />
          </button>
        </nav>
      )}

      {isSidebarOpen && (
        <aside className="conversation-sidebar" id="conversation-sidebar" aria-label="Previous conversations">
          <div className="sidebar-brand">
            <span className="sidebar-brand-mark"><Mark /></span>
            <span>paperwise</span>
            <button className="sidebar-close" type="button" onClick={() => setIsSidebarOpen(false)} aria-label="Close sidebar">
              ×
            </button>
          </div>

          <nav className="sidebar-navigation" aria-label="Sidebar navigation">
            <button type="button" className="new-chat-btn" onClick={startNewChat}>
              <SidebarGlyph kind="plus" />
              <span>New chat</span>
            </button>
            <button type="button" onClick={focusComposer}>
              <SidebarGlyph kind="search" />
              <span>Search</span>
            </button>
          </nav>

          <div className="sidebar-history-heading">History</div>

          <div className="sidebar-history">
            {historySessions.length === 0 || (historySessions.length === 1 && historySessions[0].messages.length === 0) ? (
              <p className="sidebar-empty">Your previous chats will appear here.</p>
            ) : (
              <nav className="conversation-list" aria-label="Conversation history">
                {historySessions.map((s, index) => {
                  const isActive = s.id === activeSessionId
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
        </aside>
      )}

    </main>
  )
}

type SidebarGlyphProps = {
  kind: 'plus' | 'search' | 'history'
}

function SidebarGlyph({ kind }: SidebarGlyphProps) {
  const path =
    kind === 'plus'
      ? 'M12 5v14M5 12h14'
      : kind === 'search'
        ? 'm20 20-4.5-4.5m2-5.5a7.5 7.5 0 1 1-15 0 7.5 7.5 0 0 1 15 0Z'
        : 'M4 6.5h16M4 12h16M4 17.5h16'

  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path d={path} />
    </svg>
  )
}

export default App
