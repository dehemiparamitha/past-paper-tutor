import { useState } from 'react'
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
