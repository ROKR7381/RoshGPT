import { useEffect, useRef } from 'react'
import MessageBubble from './MessageBubble'
import './ChatArea.css'

export default function ChatArea({ messages }) {
  const bottomRef = useRef(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  if (messages.length === 0) {
    return (
      <div className="chat-area">
        <div className="welcome-screen">
          <div className="welcome-icon">✨</div>
          <h1>How can I help you today?</h1>
          <p>
            Ask questions, upload documents, use tools, search the web, and
            chat with memory.
          </p>
          <div className="suggestion-cards">
            <div className="suggestion-card">
              <div className="card-icon">🔍</div>
              <div className="card-text">Search latest web info</div>
            </div>
            <div className="suggestion-card">
              <div className="card-icon">📄</div>
              <div className="card-text">Summarize uploaded document</div>
            </div>
            <div className="suggestion-card">
              <div className="card-icon">🧠</div>
              <div className="card-text">Save something to memory</div>
            </div>
            <div className="suggestion-card">
              <div className="card-icon">🧮</div>
              <div className="card-text">Use calculator tool</div>
            </div>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="chat-area">
      <div className="messages-container">
        {messages.map((msg, i) => (
          <MessageBubble key={i} role={msg.role} content={msg.content} />
        ))}
        <div ref={bottomRef} />
      </div>
    </div>
  )
}
