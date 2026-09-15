import { forwardRef } from 'react'
import Markdown from 'react-markdown'
import type { Message } from '../types/api'
import { Mark } from './Mark'

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
              <Markdown>{message.content}</Markdown>
            </div>
          ) : (
            <p>{message.content}</p>
          )}
        </div>
      </div>
    )
  },
)
