import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter'
import { oneDark } from 'react-syntax-highlighter/dist/esm/styles/prism'
import './MessageBubble.css'

export default function MessageBubble({ role, content }) {
  const isUser = role === 'user'

  return (
    <div className={`message ${isUser ? 'user' : 'assistant'}`}>
      <div className={`avatar ${isUser ? 'user-avatar' : 'bot-avatar'}`}>
        {isUser ? 'U' : 'AI'}
      </div>
      <div className="message-content">
        {isUser ? (
          <div className="user-text">{content}</div>
        ) : (
          <ReactMarkdown
            remarkPlugins={[remarkGfm]}
            components={{
              code({ node, inline, className, children, ...props }) {
                const match = /language-(\w+)/.exec(className || '')
                return !inline && match ? (
                  <SyntaxHighlighter
                    style={oneDark}
                    language={match[1]}
                    PreTag="div"
                    customStyle={{
                      margin: '12px 0',
                      borderRadius: '8px',
                      fontSize: '14px',
                    }}
                    {...props}
                  >
                    {String(children).replace(/\n$/, '')}
                  </SyntaxHighlighter>
                ) : (
                  <code className={className} {...props}>
                    {children}
                  </code>
                )
              },
              p({ children }) {
                return <p style={{ margin: '8px 0' }}>{children}</p>
              },
              ul({ children }) {
                return <ul style={{ margin: '8px 0', paddingLeft: '24px' }}>{children}</ul>
              },
              ol({ children }) {
                return <ol style={{ margin: '8px 0', paddingLeft: '24px' }}>{children}</ol>
              },
              li({ children }) {
                return <li style={{ margin: '4px 0' }}>{children}</li>
              },
              h1({ children }) {
                return <h1 style={{ margin: '16px 0 8px', fontSize: '24px' }}>{children}</h1>
              },
              h2({ children }) {
                return <h2 style={{ margin: '16px 0 8px', fontSize: '20px' }}>{children}</h2>
              },
              h3({ children }) {
                return <h3 style={{ margin: '12px 0 8px', fontSize: '18px' }}>{children}</h3>
              },
              blockquote({ children }) {
                return (
                  <blockquote
                    style={{
                      borderLeft: '3px solid #444',
                      paddingLeft: '12px',
                      margin: '12px 0',
                      color: '#aaa',
                    }}
                  >
                    {children}
                  </blockquote>
                )
              },
              table({ children }) {
                return (
                  <div style={{ overflowX: 'auto', margin: '12px 0' }}>
                    <table>{children}</table>
                  </div>
                )
              },
              th({ children }) {
                return (
                  <th
                    style={{
                      border: '1px solid #444',
                      padding: '8px 12px',
                      textAlign: 'left',
                      background: '#2a2a2a',
                    }}
                  >
                    {children}
                  </th>
                )
              },
              td({ children }) {
                return (
                  <td
                    style={{
                      border: '1px solid #444',
                      padding: '8px 12px',
                    }}
                  >
                    {children}
                  </td>
                )
              },
              a({ href, children }) {
                return (
                  <a
                    href={href}
                    target="_blank"
                    rel="noopener noreferrer"
                    style={{ color: '#60a5fa', textDecoration: 'underline' }}
                  >
                    {children}
                  </a>
                )
              },
            }}
          >
            {content}
          </ReactMarkdown>
        )}
      </div>
    </div>
  )
}
