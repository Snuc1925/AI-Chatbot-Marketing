import React from 'react';
import { Bot, RotateCcw, PanelLeft, CheckCircle2, AlertCircle, RefreshCw } from 'lucide-react';

export const Header = ({
  sessionStatus,
  onResetSession,
  isSidebarOpen,
  onToggleSidebar,
  backendConnected,
}) => {
  return (
    <header className="app-header">
      <div className="header-left">
        <button
          className="btn-icon"
          onClick={onToggleSidebar}
          title={isSidebarOpen ? 'Đóng sidebar' : 'Mở sidebar'}
          aria-label="Toggle sidebar"
        >
          <PanelLeft size={18} />
        </button>

        <div className="brand-badge">
          <Bot size={20} />
          <span>AI Marketing Assistant</span>
        </div>

        {backendConnected ? (
          <span className="session-badge idle" style={{ fontSize: '11px', padding: '3px 8px' }}>
            <CheckCircle2 size={12} /> Backend Online
          </span>
        ) : (
          <span className="session-badge waiting" style={{ fontSize: '11px', padding: '3px 8px' }}>
            <AlertCircle size={12} /> Đang kết nối...
          </span>
        )}
      </div>

      <div className="header-actions">
        <button
          className="btn-pill"
          onClick={onResetSession}
          title="Tạo đoạn chat mới"
        >
          <RotateCcw size={14} />
          <span>Đoạn chat mới</span>
        </button>
      </div>
    </header>
  );
};


