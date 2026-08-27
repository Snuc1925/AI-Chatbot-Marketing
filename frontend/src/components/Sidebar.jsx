import React from 'react';
import { 
  Plus, 
  MessageSquare, 
  Trash2, 
  Clock, 
  Database,
  Sparkles,
  Bot
} from 'lucide-react';

export const Sidebar = ({
  isOpen,
  sessions = [],
  activeSessionId,
  onSelectSession,
  onNewChat,
  onDeleteSession,
  backendConnected,
}) => {
  return (
    <aside className={`sidebar ${isOpen ? '' : 'collapsed'}`}>
      {/* Sidebar Header & New Chat Button */}
      <div className="sidebar-header">
        <button className="btn-new-chat" onClick={onNewChat} title="Tạo đoạn chat mới">
          <Plus size={16} />
          <span>Đoạn chat mới</span>
        </button>
      </div>

      <div className="sidebar-content">
        <div className="sidebar-section-title">
          <MessageSquare size={14} />
          <span>LỊCH SỬ ĐOẠN CHAT</span>
        </div>

        <div className="sessions-list-scroll">
          {sessions.length === 0 ? (
            <div className="empty-sessions">
              <MessageSquare size={28} color="var(--text-light)" />
              <p>Chưa có đoạn chat nào.</p>
              <span>Hãy đặt câu hỏi để bắt đầu cuộc trò chuyện mới!</span>
            </div>
          ) : (
            sessions.map((sess) => {
              const isActive = sess.id === activeSessionId;
              const formattedTime = sess.timestamp
                ? new Date(sess.timestamp).toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit' })
                : '';

              return (
                <div
                  key={sess.id}
                  className={`session-history-item ${isActive ? 'active' : ''}`}
                  onClick={() => onSelectSession(sess.id)}
                  title={sess.title || 'Đoạn chat mới'}
                >
                  <MessageSquare size={14} className="session-item-icon" />
                  
                  <div className="session-item-body">
                    <div className="session-item-title">
                      {sess.title || 'Đoạn chat chưa có tiêu đề'}
                    </div>
                    <div className="session-item-time">
                      <Clock size={10} /> {formattedTime} · {sess.messages?.length || 0} tin nhắn
                    </div>
                  </div>

                  <button
                    className="btn-delete-session"
                    onClick={(e) => {
                      e.stopPropagation();
                      onDeleteSession(sess.id);
                    }}
                    title="Xóa đoạn chat này"
                  >
                    <Trash2 size={13} />
                  </button>
                </div>
              );
            })
          )}
        </div>
      </div>

      {/* Sidebar Footer System Info */}
      <div className="sidebar-footer-card">
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '11px', fontWeight: 700, color: 'var(--primary-dark)', marginBottom: '4px' }}>
          <Database size={13} color="var(--primary)" />
          <span>ClickHouse & Tri Thức RAG</span>
        </div>
        <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
          Hệ thống phân tích Marketing Viettel
        </div>
      </div>
    </aside>
  );
};
