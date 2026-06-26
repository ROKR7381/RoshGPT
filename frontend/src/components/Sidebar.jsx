import './Sidebar.css'

export default function Sidebar({
  conversations,
  activeThreadId,
  onSelectChat,
  onNewChat,
  isOpen,
  onToggle,
}) {
  return (
    <aside className={`sidebar ${isOpen ? 'open' : 'closed'}`}>
      <div className="sidebar-header">
        <div className="brand">RoshGPT</div>
        <button className="new-chat-btn" onClick={onNewChat}>
          <span className="plus-icon">+</span>
          <span>New chat</span>
        </button>
      </div>

      <div className="history-section">
        <div className="history-title">Recent</div>
        <div className="conversation-list">
          {conversations.length === 0 ? (
            <div className="no-chats">No chats yet</div>
          ) : (
            conversations.map((conv) => (
              <div
                key={conv.thread_id}
                className={`conversation-item ${
                  conv.thread_id === activeThreadId ? 'active' : ''
                }`}
                onClick={() => onSelectChat(conv.thread_id)}
              >
                <span className="conv-icon">💬</span>
                <span className="conv-title">{conv.title || 'New Chat'}</span>
              </div>
            ))
          )}
        </div>
      </div>

      <div className="sidebar-footer">
        <div className="footer-item">
          <span className="footer-icon">⚡</span>
          <span>Agentic AI Assistant</span>
        </div>
      </div>
    </aside>
  )
}
