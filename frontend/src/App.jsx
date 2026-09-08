import React, { useState, useEffect, useRef } from 'react';
import { Header } from './components/Header';
import { Sidebar } from './components/Sidebar';
import { ChatMessage } from './components/ChatMessage';
import { ChatInput } from './components/ChatInput';
import { Sparkles, Bot } from 'lucide-react';

const API_BASE = '/api';

export function App() {
  // Load sessions from localStorage
  const [sessions, setSessions] = useState(() => {
    try {
      const saved = localStorage.getItem('ai_mkt_chat_sessions');
      return saved ? JSON.parse(saved) : [];
    } catch {
      return [];
    }
  });

  const [activeSessionId, setActiveSessionId] = useState(() => {
    const savedId = localStorage.getItem('ai_mkt_active_session_id');
    return savedId || `sess-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`;
  });

  const [messages, setMessages] = useState([]);
  const [sessionStatus, setSessionStatus] = useState('IDLE');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);
  const [backendConnected, setBackendConnected] = useState(true);

  const chatEndRef = useRef(null);

  // Sync activeSessionId to localStorage
  useEffect(() => {
    localStorage.setItem('ai_mkt_active_session_id', activeSessionId);
  }, [activeSessionId]);

  // Sync sessions to localStorage
  useEffect(() => {
    try {
      localStorage.setItem('ai_mkt_chat_sessions', JSON.stringify(sessions));
    } catch (e) {
      console.warn('Failed to save sessions to localStorage:', e);
    }
  }, [sessions]);

  // When activeSessionId changes, load its messages
  useEffect(() => {
    const current = sessions.find((s) => s.id === activeSessionId);
    if (current) {
      setMessages(current.messages || []);
    } else {
      setMessages([]);
    }
    checkHealth();
  }, [activeSessionId]);

  // Auto scroll to bottom
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isSubmitting]);

  const checkHealth = async () => {
    try {
      const res = await fetch(`${API_BASE}/health`);
      setBackendConnected(res.ok);
    } catch {
      setBackendConnected(false);
    }
  };

  const updateSessionMessages = (sessId, newMessages, firstQueryText = '') => {
    setSessions((prev) => {
      const index = prev.findIndex((s) => s.id === sessId);
      if (index >= 0) {
        const updated = [...prev];
        updated[index] = {
          ...updated[index],
          messages: newMessages,
          title: updated[index].title || firstQueryText.slice(0, 40) || 'Đoạn chat mới',
          timestamp: Date.now(),
        };
        return updated;
      } else {
        // Create new session entry
        return [
          {
            id: sessId,
            title: firstQueryText.slice(0, 40) || 'Đoạn chat mới',
            timestamp: Date.now(),
            messages: newMessages,
          },
          ...prev,
        ];
      }
    });
  };

  const handleNewChat = () => {
    const newId = `sess-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`;
    setActiveSessionId(newId);
    setMessages([]);
    setSessionStatus('IDLE');
  };

  const handleSelectSession = (sessId) => {
    setActiveSessionId(sessId);
  };

  const handleDeleteSession = async (sessId) => {
    try {
      await fetch(`${API_BASE}/chat/session/${sessId}`, { method: 'DELETE' });
    } catch (e) {
      console.warn('Error deleting session on backend:', e);
    }

    setSessions((prev) => {
      const filtered = prev.filter((s) => s.id !== sessId);
      if (sessId === activeSessionId) {
        if (filtered.length > 0) {
          setActiveSessionId(filtered[0].id);
        } else {
          const newId = `sess-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`;
          setActiveSessionId(newId);
          setMessages([]);
        }
      }
      return filtered;
    });
  };

  const [elapsedSeconds, setElapsedSeconds] = useState(0);

  // Timer counter when processing query
  useEffect(() => {
    let interval;
    if (isSubmitting) {
      setElapsedSeconds(0);
      interval = setInterval(() => {
        setElapsedSeconds((prev) => prev + 1);
      }, 1000);
    }
    return () => {
      if (interval) clearInterval(interval);
    };
  }, [isSubmitting]);

  const handleSendMessage = async (text) => {
    if (!text.trim() || isSubmitting) return;

    const queryText = text.trim();
    const userMsg = {
      id: `user-${Date.now()}`,
      role: 'user',
      content: queryText,
    };

    const newMessages = [...messages, userMsg];
    setMessages(newMessages);
    updateSessionMessages(activeSessionId, newMessages, queryText);
    setIsSubmitting(true);

    const history = messages.slice(-6).map((m) => ({
      role: m.role,
      content: m.content,
    }));

    try {
      const response = await fetch(`${API_BASE}/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          query: queryText,
          session_id: activeSessionId,
          chat_history: history,
        }),
      });

      if (!response.ok) {
        throw new Error(`HTTP Error: ${response.status}`);
      }

      const data = await response.json();
      setSessionStatus(data.session_status || 'IDLE');

      const botMsg = {
        id: `bot-${Date.now()}`,
        role: 'bot',
        content: data.message,
        response_type: data.response_type,
        citations: data.citations || [],
        collected_slots: data.collected_slots || {},
        missing_slots: data.missing_slots || [],
        intent_reasoning: data.intent_reasoning || '',
        generated_sqls: data.generated_sqls || [],
        generated_sql: data.generated_sql || null,
      };

      const updatedMessages = [...newMessages, botMsg];
      setMessages(updatedMessages);
      updateSessionMessages(activeSessionId, updatedMessages, queryText);
    } catch (error) {
      console.error('Chat error:', error);
      const errorMsg = {
        id: `bot-${Date.now()}`,
        role: 'bot',
        content: `⚠️ Lỗi kết nối backend: ${error.message}. Vui lòng thử lại.`,
        response_type: 'error',
      };
      const updatedMessages = [...newMessages, errorMsg];
      setMessages(updatedMessages);
      updateSessionMessages(activeSessionId, updatedMessages, queryText);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleResetSession = () => {
    handleNewChat();
  };

  const defaultStarterSuggestions = [
    'Tỷ lệ gửi SMS thành công của chiến dịch KhuyenMai_4G tháng này',
    'Doanh thu và số thuê bao mua gói qua chiến dịch MyViettel',
    'Phân tích nhóm tuổi và giới tính có tỷ lệ phản hồi cao nhất',
    'Khung giờ có tỷ lệ phản hồi chiến dịch cao nhất trong ngày',
  ];

  return (
    <div className="app-container">
      {/* Sessions Sidebar */}
      <Sidebar
        isOpen={isSidebarOpen}
        sessions={sessions}
        activeSessionId={activeSessionId}
        onSelectSession={handleSelectSession}
        onNewChat={handleNewChat}
        onDeleteSession={handleDeleteSession}
        backendConnected={backendConnected}
      />

      {/* Main Chat Area */}
      <div className="main-chat">
        <Header
          sessionStatus={sessionStatus}
          onResetSession={handleResetSession}
          isSidebarOpen={isSidebarOpen}
          onToggleSidebar={() => setIsSidebarOpen((prev) => !prev)}
          backendConnected={backendConnected}
        />

        {/* Chat Feed */}
        <div className="chat-feed">
          {messages.length === 0 ? (
            <div className="welcome-card">
              <div className="welcome-icon">
                <Bot size={30} />
              </div>
              <h2 className="welcome-title">Chào mừng đến với AI Marketing Assistant</h2>
              <p className="welcome-desc">
                Trợ lý AI phân tích dữ liệu Marketing Viettel tích hợp Business Knowledge RAG,
                tự động sinh ClickHouse SQL và trích dẫn số liệu chính xác.
              </p>

              <div className="starter-grid">
                {defaultStarterSuggestions.map((prompt, idx) => (
                  <button
                    key={idx}
                    className="starter-btn"
                    onClick={() => handleSendMessage(prompt)}
                  >
                    <Sparkles size={14} color="var(--primary)" />
                    <span>{prompt}</span>
                  </button>
                ))}
              </div>
            </div>
          ) : (
            messages.map((msg, index) => (
              <ChatMessage
                key={msg.id}
                message={msg}
                onQuickReply={handleSendMessage}
                isLastMessage={index === messages.length - 1}
                isSubmitting={isSubmitting}
              />
            ))
          )}

          {isSubmitting && (
            <div className="message-row bot">
              <div className="avatar bot">
                <Bot size={18} />
              </div>
              <div className="typing-indicator-box">
                <div className="typing-indicator">
                  <div className="typing-dot" />
                  <div className="typing-dot" />
                  <div className="typing-dot" />
                </div>
                <span className="typing-timer">
                  Đang xử lý... <strong>{elapsedSeconds}s</strong>
                </span>
              </div>
            </div>
          )}

          <div ref={chatEndRef} />
        </div>

        {/* Chat Input */}
        <ChatInput
          onSendMessage={handleSendMessage}
          isSubmitting={isSubmitting}
          sessionStatus={sessionStatus}
        />
      </div>
    </div>
  );
}
