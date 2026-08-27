import React, { useState, useRef, useEffect } from 'react';
import { Send, CornerDownLeft, Sparkles } from 'lucide-react';

export const ChatInput = ({ onSendMessage, isSubmitting, sessionStatus }) => {
  const [input, setInput] = useState('');
  const textareaRef = useRef(null);

  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 140)}px`;
    }
  }, [input]);

  const handleSubmit = (e) => {
    e?.preventDefault();
    if (!input.trim() || isSubmitting) return;
    onSendMessage(input.trim());
    setInput('');
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  return (
    <div className="input-container">
      <form className="input-box" onSubmit={handleSubmit}>
        <textarea
          ref={textareaRef}
          className="chat-textarea"
          placeholder={
            sessionStatus === 'WAITING_CLARIFY'
              ? 'Nhập câu trả lời bổ sung (hoặc click vào các gợi ý ở trên)...'
              : 'Hỏi về tỷ lệ gửi tin, khung giờ phản hồi, độ tuổi, gói cước...'
          }
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          rows={1}
          disabled={isSubmitting}
        />

        <button
          type="submit"
          className="btn-send"
          disabled={!input.trim() || isSubmitting}
          title="Gửi tin nhắn (Enter)"
        >
          <Send size={16} />
        </button>
      </form>

      <div className="input-footer">
        <span>
          {sessionStatus === 'WAITING_CLARIFY' ? (
            <strong style={{ color: 'var(--status-waiting)' }}>⚡ Đang trong luồng làm rõ thông tin (Follow-up)</strong>
          ) : (
            'Nhấn Enter để gửi, Shift + Enter để xuống dòng'
          )}
        </span>
        <span>AI Marketing RAG Engine</span>
      </div>
    </div>
  );
};
