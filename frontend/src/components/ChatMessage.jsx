import React, { useState } from 'react';
import { User, Bot, Sparkles, CheckCircle2, Database, ChevronRight, ChevronDown, Brain } from 'lucide-react';
// HIDDEN (not deleted): quick-reply chips are intentionally disabled - the LLM
// no longer generates suggested_options (one consolidated free-text question
// is asked instead), so there's nothing left to render chips from. Re-enable
// by uncommenting this import and the usage below.
// import { QuickReplyChips } from './QuickReplyChips';
import { CitationText } from './CitationText';

export const ChatMessage = ({ message, onQuickReply, isLastMessage, isSubmitting }) => {
  const isUser = message.role === 'user';
  const isClarify = message.response_type === 'clarify';
  const isAnswer = message.response_type === 'answer';

  const [isReasoningOpen, setIsReasoningOpen] = useState(false);
  const hasReasoning =
    !isUser &&
    (message.intent_reasoning || (message.generated_sqls || []).some((s) => s.reasoning));

  return (
    <div className={`message-row ${isUser ? 'user' : 'bot'}`}>
      <div className={`avatar ${isUser ? 'user' : 'bot'}`}>
        {isUser ? <User size={18} /> : <Bot size={18} />}
      </div>

      <div className="message-content">

        {/* Reasoning Dropdown - collapsed by default, shows how the AI reasoned
            about the intent and (if any) each generated SQL, before the answer. */}
        {hasReasoning && (
          <div className="reasoning-toggle-wrapper">
            <button
              type="button"
              className="reasoning-toggle-btn"
              onClick={() => setIsReasoningOpen((prev) => !prev)}
            >
              {isReasoningOpen ? <ChevronDown size={13} /> : <ChevronRight size={13} />}
              <Brain size={13} />
              <span>Xem lý luận của AI (Reasoning)</span>
            </button>

            {isReasoningOpen && (
              <div className="reasoning-panel">
                {message.intent_reasoning && (
                  <div className="reasoning-block">
                    <div className="reasoning-block-label">Ý định & quyết định</div>
                    <p className="reasoning-block-text">{message.intent_reasoning}</p>
                  </div>
                )}
                {(message.generated_sqls || [])
                  .filter((s) => s.reasoning)
                  .map((s, idx) => (
                    <div key={s.id || idx} className="reasoning-block">
                      <div className="reasoning-block-label">
                        SQL [{s.id}]{s.title ? ` - ${s.title}` : ''}
                      </div>
                      <p className="reasoning-block-text">{s.reasoning}</p>
                    </div>
                  ))}
              </div>
            )}
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

        {/* HIDDEN (not deleted): Quick Reply Chips - no suggested_options from
            the backend anymore, user always types their own reply now. */}
        {/* {!isUser && isClarify && (
          <QuickReplyChips
            options={message.suggested_options}
            text={message.content}
            onSelectOption={onQuickReply}
            disabled={!isLastMessage || isSubmitting}
          />
        )} */}
      </div>
    </div>
  );
};
