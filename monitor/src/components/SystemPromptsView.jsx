import React, { useState, useEffect } from 'react';
import { Wand2, RefreshCw, Save, RotateCcw, CheckCircle2, AlertCircle, FileCode } from 'lucide-react';

const API_BASE = '/api';

export function SystemPromptsView() {
  const [prompts, setPrompts] = useState([]);
  const [drafts, setDrafts] = useState({});
  const [isLoading, setIsLoading] = useState(true);
  const [savingKey, setSavingKey] = useState(null);
  const [status, setStatus] = useState(null);

  useEffect(() => {
    fetchPrompts();
  }, []);

  const fetchPrompts = async () => {
    setIsLoading(true);
    try {
      const res = await fetch(`${API_BASE}/prompts`);
      if (res.ok) {
        const data = await res.json();
        setPrompts(data || []);
        const nextDrafts = {};
        for (const p of data || []) nextDrafts[p.key] = p.content;
        setDrafts(nextDrafts);
      }
    } catch (e) {
      console.error('Error fetching system prompts:', e);
    } finally {
      setIsLoading(false);
    }
  };

  const handleSave = async (key) => {
    setSavingKey(key);
    setStatus(null);
    try {
      const res = await fetch(`${API_BASE}/prompts/${encodeURIComponent(key)}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ content: drafts[key] || '' }),
      });
      if (!res.ok) throw new Error('Không thể lưu system prompt.');
      const updated = await res.json();
      setPrompts((prev) => prev.map((p) => (p.key === key ? updated : p)));
      setStatus({ success: true, message: `Đã lưu prompt "${updated.label}". Áp dụng ngay cho lần chat tiếp theo, không cần khởi động lại backend.` });
    } catch (e) {
      setStatus({ success: false, message: e.message || 'Lỗi khi lưu system prompt.' });
    } finally {
      setSavingKey(null);
    }
  };

  const handleReset = async (key) => {
    if (!window.confirm('Khôi phục prompt này về nội dung mặc định ban đầu?')) return;
    setSavingKey(key);
    setStatus(null);
    try {
      const res = await fetch(`${API_BASE}/prompts/${encodeURIComponent(key)}/reset`, { method: 'POST' });
      if (!res.ok) throw new Error('Không thể khôi phục prompt mặc định.');
      const updated = await res.json();
      setPrompts((prev) => prev.map((p) => (p.key === key ? updated : p)));
      setDrafts((prev) => ({ ...prev, [key]: updated.content }));
      setStatus({ success: true, message: `Đã khôi phục prompt "${updated.label}" về mặc định.` });
    } catch (e) {
      setStatus({ success: false, message: e.message || 'Lỗi khi khôi phục system prompt.' });
    } finally {
      setSavingKey(null);
    }
  };

  return (
    <div className="knowledge-manager-container">
      {/* Top Header */}
      <div className="km-header">
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
            <Wand2 size={24} color="var(--primary)" />
            <h2 style={{ margin: 0, fontSize: '20px', fontWeight: 800 }}>
              System Prompts (system_prompts.json)
            </h2>
          </div>
          <p style={{ margin: 0, fontSize: '13px', color: 'var(--text-muted)' }}>
            Chỉnh sửa trực tiếp system prompt điều khiển hành vi LLM. Bấm "Lưu" sẽ áp dụng ngay cho request kế tiếp,
            <strong> không cần khởi động lại backend</strong>.
          </p>
        </div>
        <div className="km-actions">
          <button className="btn-pill" onClick={fetchPrompts} disabled={isLoading}>
            <RefreshCw size={15} className={isLoading ? 'animate-spin' : ''} />
            <span>Tải lại</span>
          </button>
        </div>
      </div>

      {status && (
        <div className={`status-alert ${status.success ? 'success' : 'error'}`}>
          {status.success ? <CheckCircle2 size={16} /> : <AlertCircle size={16} />}
          <span>{status.message}</span>
        </div>
      )}

      {isLoading ? (
        <div className="km-loading">
          <RefreshCw size={28} className="animate-spin" color="var(--primary)" />
          <span>Đang tải system prompts...</span>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          {prompts.map((p) => {
            const isDirty = drafts[p.key] !== p.content;
            return (
              <div key={p.key} className="km-rule-card" style={{ padding: '16px' }}>
                <div className="km-card-header" style={{ marginBottom: '10px' }}>
                  <div style={{ display: 'flex', alignItems: 'flex-start', gap: '10px', flex: 1 }}>
                    <span className="km-index-tag" style={{ background: '#0284c7' }}>
                      <FileCode size={13} />
                    </span>
                    <div style={{ flex: 1 }}>
                      <div style={{ fontSize: '11px', textTransform: 'uppercase', fontWeight: 700, color: 'var(--primary)', letterSpacing: '0.5px' }}>
                        {p.key}
                      </div>
                      <h3 className="km-rule-topic" style={{ fontSize: '15px', color: '#0f172a', marginTop: '2px' }}>
                        {p.label}
                      </h3>
                    </div>
                  </div>
                  {!p.is_default && (
                    <span
                      style={{
                        fontSize: '11px',
                        fontWeight: 700,
                        padding: '2px 8px',
                        borderRadius: '12px',
                        background: '#fef3c7',
                        color: '#92400e',
                        border: '1px solid #fde68a',
                        whiteSpace: 'nowrap',
                      }}
                    >
                      Đã tùy chỉnh
                    </span>
                  )}
                </div>

                <textarea
                  className="form-textarea"
                  rows={14}
                  style={{ fontFamily: 'var(--font-mono, monospace)', fontSize: '12.5px', lineHeight: '1.5', width: '100%' }}
                  value={drafts[p.key] ?? ''}
                  onChange={(e) => setDrafts((prev) => ({ ...prev, [p.key]: e.target.value }))}
                />

                <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '8px', marginTop: '10px' }}>
                  <button
                    className="btn-pill"
                    onClick={() => handleReset(p.key)}
                    disabled={savingKey === p.key}
                  >
                    <RotateCcw size={14} />
                    <span>Khôi phục mặc định</span>
                  </button>
                  <button
                    className="btn-primary"
                    onClick={() => handleSave(p.key)}
                    disabled={savingKey === p.key || !isDirty}
                  >
                    {savingKey === p.key ? (
                      <>
                        <RefreshCw size={15} className="animate-spin" />
                        <span>Đang lưu...</span>
                      </>
                    ) : (
                      <>
                        <Save size={15} />
                        <span>Lưu Thay Đổi</span>
                      </>
                    )}
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
