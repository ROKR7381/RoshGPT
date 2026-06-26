import { useState, useEffect, useCallback } from 'react'
import Sidebar from './components/Sidebar'
import ChatArea from './components/ChatArea'
import InputArea from './components/InputArea'
import './App.css'

const MODELS = [
  'gpt-4o',
  'gpt-4o-mini',
  'gpt-4-turbo',
  'gpt-4',
  'gpt-3.5-turbo',
  'o1-mini',
  'o1-preview',
]

export default function App() {
  const [threadId, setThreadId] = useState(() => {
    const saved = localStorage.getItem('thread_id')
    if (saved) return saved
    const id = crypto.randomUUID()
    localStorage.setItem('thread_id', id)
    return id
  })

  const [conversations, setConversations] = useState([])
  const [messages, setMessages] = useState([])
  const [isLoading, setIsLoading] = useState(false)
  const [status, setStatus] = useState('Ready')
  const [selectedModel, setSelectedModel] = useState(() => {
    return localStorage.getItem('selected_model') || 'gpt-4o-mini'
  })
  const [sidebarOpen, setSidebarOpen] = useState(true)

  const loadConversations = useCallback(async () => {
    try {
      const res = await fetch('/api/conversations')
      const data = await res.json()
      setConversations(data.conversations || [])
    } catch (e) {
      console.error('Failed to load conversations:', e)
    }
  }, [])

  const loadConversation = useCallback(async (tid) => {
    try {
      const res = await fetch(`/api/history/${tid}`)
      const data = await res.json()
      setMessages(data.messages || [])
    } catch (e) {
      console.error('Failed to load conversation:', e)
    }
  }, [])

  useEffect(() => {
    loadConversations()
    loadConversation(threadId)
  }, [threadId, loadConversations, loadConversation])

  useEffect(() => {
    localStorage.setItem('selected_model', selectedModel)
  }, [selectedModel])

  const handleNewChat = () => {
    const id = crypto.randomUUID()
    setThreadId(id)
    localStorage.setItem('thread_id', id)
    setMessages([])
    loadConversations()
  }

  const handleSelectChat = (tid) => {
    setThreadId(tid)
    localStorage.setItem('thread_id', tid)
    loadConversation(tid)
    loadConversations()
  }

  const handleSendMessage = async (text) => {
    if (!text.trim() || isLoading) return

    const userMsg = { role: 'user', content: text }
    setMessages((prev) => [...prev, userMsg])
    setIsLoading(true)
    setStatus(`Thinking with ${selectedModel}...`)

    const likelyTool = detectLikelyTool(text)

    try {
      const response = await fetch('/api/chat/stream', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: text,
          thread_id: threadId,
          model: selectedModel,
        }),
      })

      if (!response.ok) {
        const errData = await response.json().catch(() => ({}))
        throw new Error(errData.detail || 'Request failed')
      }

      const reader = response.body.getReader()
      const decoder = new TextDecoder('utf-8')
      let buffer = ''
      let botContent = ''
      let firstToken = false

      setMessages((prev) => [...prev, { role: 'assistant', content: '' }])

      while (true) {
        const { value, done } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const parts = buffer.split(/\r?\n\r?\n/)
        buffer = parts.pop() || ''

        for (const part of parts) {
          const lines = part.split(/\r?\n/).filter((l) => l.startsWith('data:'))
          if (!lines.length) continue

          const jsonText = lines
            .map((l) => l.replace(/^data:\s*/, ''))
            .join('\n')
            .trim()

          if (!jsonText || jsonText === '[DONE]') continue

          try {
            const data = JSON.parse(jsonText)

            if (data.token) {
              if (!firstToken) {
                firstToken = true
                setStatus(`Generating with ${selectedModel}...`)
              }
              botContent += data.token
              setMessages((prev) => {
                const updated = [...prev]
                updated[updated.length - 1] = {
                  role: 'assistant',
                  content: botContent,
                }
                return updated
              })
            }

            if (data.error) {
              botContent += `\n\nError: ${data.error}`
              setMessages((prev) => {
                const updated = [...prev]
                updated[updated.length - 1] = {
                  role: 'assistant',
                  content: botContent,
                }
                return updated
              })
            }
          } catch {}
        }
      }

      // Handle remaining buffer
      if (buffer.trim()) {
        const lines = buffer.split(/\r?\n/).filter((l) => l.startsWith('data:'))
        const jsonText = lines
          .map((l) => l.replace(/^data:\s*/, ''))
          .join('\n')
          .trim()
        if (jsonText && jsonText !== '[DONE]') {
          try {
            const data = JSON.parse(jsonText)
            if (data.token) botContent += data.token
            setMessages((prev) => {
              const updated = [...prev]
              updated[updated.length - 1] = {
                role: 'assistant',
                content: botContent,
              }
              return updated
            })
          } catch {}
        }
      }
    } catch (e) {
      setMessages((prev) => [
        ...prev.slice(0, -1),
        { role: 'assistant', content: `Error: ${e.message}` },
      ])
    } finally {
      setIsLoading(false)
      setStatus('Ready')
      loadConversations()
    }
  }

  const handleUpload = async (file) => {
    const userMsg = { role: 'user', content: `📎 Uploaded document: ${file.name}` }
    setMessages((prev) => [...prev, userMsg])
    setStatus('Uploading document...')

    const formData = new FormData()
    formData.append('file', file)
    formData.append('thread_id', threadId)

    try {
      const res = await fetch('/api/upload', { method: 'POST', body: formData })
      const data = await res.json()

      if (data.success) {
        setMessages((prev) => [
          ...prev,
          {
            role: 'assistant',
            content: `${data.message}\n\nYou can now ask questions about this document.`,
          },
        ])
      } else {
        setMessages((prev) => [
          ...prev,
          { role: 'assistant', content: `Upload failed: ${data.message}` },
        ])
      }
      loadConversations()
    } catch (e) {
      setMessages((prev) => [
        ...prev,
        { role: 'assistant', content: `Upload failed: ${e.message}` },
      ])
    } finally {
      setStatus('Ready')
    }
  }

  return (
    <div className="app">
      <Sidebar
        conversations={conversations}
        activeThreadId={threadId}
        onSelectChat={handleSelectChat}
        onNewChat={handleNewChat}
        isOpen={sidebarOpen}
        onToggle={() => setSidebarOpen(!sidebarOpen)}
      />
      <main className="main">
        <div className="topbar">
          <div className="topbar-left">
            <button
              className="sidebar-toggle"
              onClick={() => setSidebarOpen(!sidebarOpen)}
            >
              ☰
            </button>
            <span>RoshGPT</span>
          </div>
          <div className="status">{status}</div>
        </div>
        <ChatArea messages={messages} />
        <InputArea
          onSend={handleSendMessage}
          onUpload={handleUpload}
          models={MODELS}
          selectedModel={selectedModel}
          onModelChange={setSelectedModel}
          isLoading={isLoading}
        />
      </main>
    </div>
  )
}

function detectLikelyTool(message) {
  const text = message.toLowerCase()
  if (/remember that|save this|store this/.test(text)) return 'Memory Save'
  if (/what do you remember|recall/.test(text)) return 'Memory Recall'
  if (/document|pdf|file|uploaded|summarize/.test(text)) return 'Document Search'
  if (/latest|current|today|news|search web/.test(text)) return 'Web Search'
  if (/\d+\s*[\+\-\*\/]\s*\d+|calculate/.test(text)) return 'Calculator'
  return null
}
