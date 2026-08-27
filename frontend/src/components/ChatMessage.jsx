import React from 'react';
import { User, Bot, Sparkles, CheckCircle2, Database } from 'lucide-react';
import { QuickReplyChips } from './QuickReplyChips';
import { CitationText } from './CitationText';

export const ChatMessage = ({ message, onQuickReply, isLastMessage, isSubmitting }) => {
  const isUser = message.role === 'user';
  const isClarify = message.response_type === 'clarify';
  const isAnswer = message.response_type === 'answer';

  return (
    <div className={`message-row ${isUser ? 'user' : 'bot'}`}>
      <div className={`avatar ${isUser ? 'user' : 'bot'}`}>
        {isUser ? <User size={18} /> : <Bot size={18} />}
      </div>

      <div className="message-content">


        {/* Relevant Knowledge Tags */}
        {!isUser && message.relevant_knowledge && message.relevant_knowledge.length > 0 && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '3px', marginBottom: '6px' }}>
            {message.relevant_knowledge.map((k, idx) => (
              <div
                key={idx}
                style={{
                  fontSize: '11px',
                  color: 'var(--text-muted)',
                  background: 'rgba(241, 245, 249, 0.9)',
                  padding: '3px 8px',
                  borderRadius: '6px',
                  border: '1px solid var(--border-light)',
                  lineHeight: '1.4',
                }}
              >
                💡 <em>{k.length > 120 ? k.slice(0, 120) + '...' : k}</em>
              </div>
            ))}
          </div>
        )}

        {/* Message Bubble */}
        <div className={`bubble ${isUser ? 'user' : 'bot'} ${isClarify ? 'clarify' : ''}`}>
          {isUser ? (
            message.content
          ) : (
            <CitationText text={message.content} citations={message.citations || []} />
          )}
        </div>

        {/* Fallback SQL preview for clarify questions or single SQL if no citations tag */}
        {!isUser && message.generated_sql && (!message.citations || message.citations.length === 0) && (
          <div style={{ marginTop: '8px', background: '#1e293b', color: '#38bdf8', padding: '10px 14px', borderRadius: '8px', fontSize: '12px', fontFamily: 'monospace', overflowX: 'auto' }}>
            <div style={{ color: '#94a3b8', fontSize: '11px', marginBottom: '4px', fontWeight: 600, display: 'flex', alignItems: 'center', gap: '6px' }}>
              <Database size={12} color="#38bdf8" /> SQL Truy vấn (ClickHouse):
            </div>
            <code>{message.generated_sql}</code>
          </div>
        )}

        {/* Slots preview if answered */}
        {!isUser && isAnswer && message.collected_slots && Object.keys(message.collected_slots).length > 0 && (
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '4px', marginTop: '4px' }}>
            {Object.entries(message.collected_slots).map(([k, v]) => (
              <span key={k} className="slot-tag" style={{ fontSize: '11px' }}>
                <CheckCircle2 size={10} color="var(--status-success)" />
                <strong>{k}:</strong> {String(v)}
              </span>
            ))}
          </div>
        )}

        {/* Quick Reply Chips (Only active on latest message if clarify) */}
        {!isUser && isClarify && (
          <QuickReplyChips
            options={message.suggested_options}
            text={message.content}
            onSelectOption={onQuickReply}
            disabled={!isLastMessage || isSubmitting}
          />
        )}
      </div>
    </div>
  );
};

