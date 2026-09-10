import { useState } from 'react'
import type { FormEvent } from 'react'
import './App.css'

type Message = {
  id: number
  role: 'user' | 'assistant'
  content: string
}

function getAnswer(payload: unknown): string {
  if (typeof payload === 'string') return payload
  if (Array.isArray(payload)) {
    return payload
      .map((item) => getAnswer(item))
      .filter(Boolean)
      .join('\n\n')
  }
  if (!payload || typeof payload !== 'object') return ''

  const data = payload as Record<string, unknown>
  const answer = data.answer ?? data.content ?? data.response ?? data.result ?? data.output ?? data.text
  if (typeof answer === 'object') return getAnswer(answer)
  return typeof answer === 'string' ? answer : ''
}

const exampleQuestions = [
  'Explain a concept from the past papers',
  'What topics appear most often?',
  'Give me an exam-style explanation',
]

function Mark() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path d="M12 2.8 14 10l7.2 2-7.2 2-2 7.2-2-7.2-7.2-2 7.2-2L12 2.8Z" />
    </svg>
  )
}

function App() {
  const [messages, setMessages] = useState<Message[]>([])
  const [question, setQuestion] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState('')

  const askQuestion = async (event?: FormEvent) => {
    event?.preventDefault()
    const value = question.trim()
    if (!value || isLoading) return

    setMessages((current) => [...current, { id: Date.now(), role: 'user', content: value }])
    setQuestion('')
    setError('')
    setIsLoading(true)

    try {
      const response = await fetch(`${import.meta.env.VITE_API_URL ?? 'http://localhost:8000'}/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question: value }),
      })
      if (!response.ok) throw new Error('Request failed')
      const result: unknown = await response.json()
      const answer = getAnswer(result)
      if (!answer) throw new Error('The API returned no answer text.')
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
    <main className={`page ${messages.length > 0 ? 'chat-mode' : ''}`}>
      <header className="header">
        <a className="wordmark" href="/" aria-label="Paperwise home">
          <span className="logo"><Mark /></span>
          <span>paperwise</span>
        </a>
        <span className="header-note">Past paper tutor</span>
      </header>

      <section className="hero">
        <h1>What can I help you understand?</h1>
        <p className="intro">Ask questions about your past papers and get clear, exam-focused answers.</p>
      </section>

      <section className="workspace" aria-label="Past paper tutor">
        <div className="conversation" aria-live="polite">
          {messages.map((message) => (
            <div className={`message ${message.role}`} key={message.id}>
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

      <footer className="footer">Built for revision, one question at a time.</footer>
    </main>
  )
}

export default App
