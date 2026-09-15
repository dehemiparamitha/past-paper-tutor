import { forwardRef } from 'react'
import Markdown from 'react-markdown'
import type { Message } from '../types/api'
import { Mark } from './Mark'
import { SimilarQuestions } from './SimilarQuestions'

type ChatMessageProps = {
  message: Message
}

export const ChatMessage = forwardRef<HTMLDivElement, ChatMessageProps>(
  function ChatMessage({ message }, ref) {
    const isAssistant = message.role === 'assistant'

    return (
      <div className={`message ${message.role}`} ref={ref}>
        {isAssistant && (
          <div className="avatar">
            <Mark />
          </div>
        )}
        <div className="message-body">
          <span className="message-name">{isAssistant ? 'Paperwise' : 'You'}</span>
          {isAssistant ? (
            <div className="message-content">
              {message.content && <Markdown>{message.content}</Markdown>}
              {message.similarQuestions && message.similarQuestions.length > 0 && (
                <SimilarQuestions questions={message.similarQuestions} />
              )}
            </div>
          ) : (
            <p>{message.content}</p>
          )}
        </div>
      </div>
    )
  },
)
