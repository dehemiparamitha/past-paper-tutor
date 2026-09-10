import { useRef, useState } from 'react'
import type { FormEvent } from 'react'
import { askTutor, findSimilarQuestions } from './services/api'
import { isQuestionSearchRequest } from './services/intent'
import type { Message, SimilarQuestion } from './types/api'
import { Mark } from './components/Mark'
import { SimilarQuestions } from './components/SimilarQuestions'
import './App.css'

const exampleQuestions = [
  'Explain a concept from the past papers',
  'What topics appear most often?',
  'Give me an exam-style explanation',
]

function App() {
  const [messages, setMessages] = useState<Message[]>([])
  const [question, setQuestion] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [similarQuestions, setSimilarQuestions] = useState<SimilarQuestion[]>([])
  const [error, setError] = useState('')
  const [isSidebarOpen, setIsSidebarOpen] = useState(true)
  const messageRefs = useRef<Record<number, HTMLDivElement | null>>({})
  const composerRef = useRef<HTMLTextAreaElement | null>(null)

  const conversationMessages = messages.filter((message) => message.role === 'user')

  const openConversation = (messageId: number) => {
    setIsSidebarOpen(true)
    messageRefs.current[messageId]?.scrollIntoView({ behavior: 'smooth', block: 'start' })
  }

  const startNewChat = () => {
    setMessages([])
    setSimilarQuestions([])
    setError('')
    setQuestion('')
    composerRef.current?.focus()
  }

  const focusComposer = () => {
    composerRef.current?.focus()
  }

  const askQuestion = async (event?: FormEvent) => {
    event?.preventDefault()
    const value = question.trim()
    if (!value || isLoading) return

    setMessages((current) => [...current, { id: Date.now(), role: 'user', content: value }])
    setQuestion('')
    setError('')
    setSimilarQuestions([])
    setIsLoading(true)

    if (isQuestionSearchRequest(value)) {
      try {
        setSimilarQuestions(await findSimilarQuestions(value))
      } catch {
        setError('The tutor could not find similar questions. Check that the backend is running and try again.')
      } finally {
        setIsLoading(false)
      }
      return
    }

    try {
      const answer = await askTutor(value)
      setMessages((current) => [
        ...current,
        {
          id: Date.now() + 1,
          role: 'assistant',
          content: answer,
        },
      ])
    } catch {
      setError('The tutor could not answer. Check that the backend is running and VITE_API_URL points to the correct port.')
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <main className={`page ${messages.length > 0 ? 'chat-mode' : ''} ${isSidebarOpen ? 'sidebar-open' : 'sidebar-closed'}`}>


      <section className="hero">
        <h1>What can I help you understand?</h1>
        <p className="intro">Ask questions about your past papers and get clear, exam-focused answers.</p>
      </section>

      <section className="workspace" aria-label="Past paper tutor">
        <div className="conversation" aria-live="polite">
          {messages.map((message) => (
            <div
              className={`message ${message.role}`}
              key={message.id}
              ref={(element) => {
                messageRefs.current[message.id] = element
              }}
            >
              {message.role === 'assistant' && <div className="avatar"><Mark /></div>}
              <div className="message-body">
                <span className="message-name">{message.role === 'assistant' ? 'Paperwise' : 'You'}</span>
                <p>{message.content}</p>
              </div>
            </div>
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
          <SimilarQuestions questions={similarQuestions} />
        </div>

        {messages.length === 0 && (
          <div className="examples">
            <div className="example-list">
              {exampleQuestions.map((example) => (
                <button key={example} onClick={() => setQuestion(example)}>{example}<span>↗</span></button>
              ))}
            </div>
          </div>
        )}

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
          <button type="submit" disabled={!question.trim() || isLoading} aria-label="Send question">↑</button>
        </form>
        <p className="composer-footnote">Answers are generated from uploaded past papers </p>
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
            <button type="button" onClick={startNewChat}>
              <SidebarGlyph kind="plus" />
              <span>New chat</span>
            </button>
            <button type="button" onClick={focusComposer}>
              <SidebarGlyph kind="search" />
              <span>Search</span>
            </button>
            <button className="sidebar-history-link" type="button">
              <SidebarGlyph kind="history" />
              <span>History</span>
            </button>
          </nav>
          <div className="sidebar-history">
            {conversationMessages.length === 0 ? (
              <p className="sidebar-empty">Your questions will appear here.</p>
            ) : (
              <nav className="conversation-list" aria-label="Conversation history">
                {conversationMessages.map((message, index) => (
                  <button
                    className="conversation-item"
                    type="button"
                    key={message.id}
                    onClick={() => openConversation(message.id)}
                  >
                    <span className="conversation-number">0{index + 1}</span>
                    <span>{message.content}</span>
                  </button>
                ))}
              </nav>
            )}
          </div>
        </aside>
      )}

      <footer className="footer">Built for revision, one question at a time.</footer>
    </main>
  )
}

type SidebarGlyphProps = {
  kind: 'plus' | 'search' | 'history'
}

function SidebarGlyph({ kind }: SidebarGlyphProps) {
  const path = kind === 'plus'
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
