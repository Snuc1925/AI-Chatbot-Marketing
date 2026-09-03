import React, { useState, useEffect } from 'react';
import { 
  Code2, 
  Plus, 
  Edit3, 
  Trash2, 
  RefreshCw, 
  CheckCircle2, 
  AlertCircle, 
  Save, 
  X, 
  Search, 
  Copy, 
  Check, 
  Sparkles, 
  Layers, 
  SlidersHorizontal,
  HelpCircle,
  Database
} from 'lucide-react';

const API_BASE = '/api';

export function SqlExamplesManagerView() {
  const [examples, setExamples] = useState([]);
  const [enableRag, setEnableRag] = useState(true);
  const [modeLabel, setModeLabel] = useState('RAG Mode');
  const [vectorCount, setVectorCount] = useState(0);
  const [isLoading, setIsLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [isSyncing, setIsSyncing] = useState(false);
  const [isUpdatingMode, setIsUpdatingMode] = useState(false);
  const [syncStatus, setSyncStatus] = useState(null);
  const [copiedId, setCopiedId] = useState(null);

  // Modal states
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingExample, setEditingExample] = useState(null);
  const [formQuestion, setFormQuestion] = useState('');
  const [formSql, setFormSql] = useState('');
  const [formError, setFormError] = useState('');
  const [isSaving, setIsSaving] = useState(false);

  useEffect(() => {
    fetchSqlExamples();
  }, []);

  const fetchSqlExamples = async () => {
    setIsLoading(true);
    try {
      const res = await fetch(`${API_BASE}/sql-examples`);
      if (res.ok) {
        const data = await res.json();
        setExamples(data.examples || []);
        setEnableRag(data.enable_sql_examples_rag ?? true);
        setModeLabel(data.mode_label || 'RAG Mode');
        setVectorCount(data.vector_store_count ?? 0);
      }
    } catch (e) {
      console.error('Error fetching SQL examples:', e);
    } finally {
      setIsLoading(false);
    }
  };

  const handleToggleMode = async (targetMode) => {
    if (isUpdatingMode || targetMode === enableRag) return;
    setIsUpdatingMode(true);
    try {
      const res = await fetch(`${API_BASE}/sql-examples/mode`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ enable_rag: targetMode }),
      });
      if (res.ok) {
        const data = await res.json();
        setEnableRag(data.enable_sql_examples_rag);
        setModeLabel(data.mode_label);
        setSyncStatus({
          success: true,
          message: `Đã chuyển sang ${data.mode_label} thành công!`,
        });
      }
    } catch (e) {
      console.error('Error toggling SQL examples mode:', e);
      setSyncStatus({
        success: false,
        message: 'Lỗi chuyển đổi chế độ SQL Examples.',
      });
    } finally {
      setIsUpdatingMode(false);
    }
  };

  const handleOpenAddModal = () => {
    setEditingExample(null);
    setFormQuestion('');
    setFormSql('');
    setFormError('');
    setIsModalOpen(true);
  };

  const handleOpenEditModal = (item) => {
    setEditingExample(item);
    setFormQuestion(item.question);
    setFormSql(item.sql);
    setFormError('');
    setIsModalOpen(true);
  };

  const handleSaveExample = async (e) => {
    e.preventDefault();
    if (!formQuestion.trim() || !formSql.trim()) {
      setFormError('Vui lòng nhập đầy đủ Câu hỏi tự nhiên (Question) và Câu lệnh ClickHouse SQL.');
      return;
    }

    setIsSaving(true);
    setFormError('');

    try {
      if (editingExample !== null) {
        // Edit existing
        const res = await fetch(`${API_BASE}/sql-examples/${editingExample.id}`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            question: formQuestion.trim(),
            sql: formSql.trim(),
          }),
        });
        if (!res.ok) throw new Error('Không thể cập nhật SQL example');
      } else {
        // Create new
        const res = await fetch(`${API_BASE}/sql-examples`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            question: formQuestion.trim(),
            sql: formSql.trim(),
          }),
        });
        if (!res.ok) throw new Error('Không thể thêm SQL example mới');
      }

      await fetchSqlExamples();
      setIsModalOpen(false);
      setSyncStatus({
        success: true,
        message: editingExample !== null 
          ? 'Đã cập nhật và tự động đồng bộ lại Qdrant VectorDB!' 
          : 'Đã thêm ví dụ mẫu và đồng bộ vào Qdrant VectorDB!',
      });
    } catch (err) {
      setFormError(err.message || 'Lỗi khi lưu câu lệnh SQL mẫu.');
    } finally {
      setIsSaving(false);
    }
  };

  const handleDeleteExample = async (item) => {
    if (!window.confirm(`Bạn có chắc chắn muốn xóa câu lệnh SQL mẫu #${item.id + 1}: "${item.question}"?`)) {
      return;
    }
    try {
      const res = await fetch(`${API_BASE}/sql-examples/${item.id}`, {
        method: 'DELETE',
      });
      if (res.ok) {
        await fetchSqlExamples();
        setSyncStatus({
          success: true,
          message: `Đã xóa mẫu #${item.id + 1} và đồng bộ lại Qdrant!`,
        });
      } else {
        throw new Error('Xóa thất bại.');
      }
    } catch (e) {
      console.error('Error deleting SQL example:', e);
      setSyncStatus({
        success: false,
        message: 'Lỗi khi xóa câu lệnh SQL mẫu.',
      });
    }
  };

  const handleManualSyncQdrant = async () => {
    setIsSyncing(true);
    setSyncStatus(null);
    try {
      const res = await fetch(`${API_BASE}/sql-examples/sync`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ force_reset: true }),
      });
      const data = await res.json();
      if (res.ok && data.status === 'success') {
        setSyncStatus({
          success: true,
          message: `Đồng bộ thành công! Đã vector hóa ${data.synced_count} câu hỏi mẫu vào collection 'sql_examples' trong Qdrant.`,
        });
        await fetchSqlExamples();
      } else {
        setSyncStatus({
          success: false,
          message: `Đồng bộ thất bại: ${data.error || data.message || 'Lỗi không xác định'}`,
        });
      }
    } catch (e) {
      console.error('Error syncing SQL examples:', e);
      setSyncStatus({
        success: false,
        message: 'Không thể kết nối đến máy chủ để đồng bộ.',
      });
    } finally {
      setIsSyncing(false);
    }
  };

  const handleCopySql = (id, sqlText) => {
    navigator.clipboard.writeText(sqlText);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  const filteredExamples = examples.filter(
    (ex) =>
      ex.question.toLowerCase().includes(searchQuery.toLowerCase()) ||
      ex.sql.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <div className="knowledge-manager-container">
      {/* Top Header */}
      <div className="km-header">
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
            <Code2 size={24} color="var(--primary)" />
            <h2 style={{ margin: 0, fontSize: '20px', fontWeight: 800 }}>
              Mẫu Truy Vấn SQL Đã Kiểm Chứng (Few-Shot Golden SQLs)
            </h2>
          </div>
          <p style={{ margin: 0, fontSize: '13px', color: 'var(--text-muted)' }}>
            Quản lý các cặp <strong>Câu hỏi mẫu</strong> & <strong>ClickHouse SQL chuẩn</strong> trong <code>backend/sql_examples.json</code>. 
            AI sẽ ưu tiên học và suy luận theo các mẫu này để sinh SQL với độ chính xác cao nhất.
          </p>
        </div>

        <div className="km-actions">
          <button className="btn-primary" onClick={handleOpenAddModal}>
            <Plus size={16} />
            <span>Thêm Mẫu SQL Mới</span>
          </button>

          <button 
            className="btn-pill" 
            onClick={handleManualSyncQdrant} 
            disabled={isSyncing}
            style={{ background: '#ffffff', borderColor: 'var(--primary)', color: 'var(--primary)' }}
          >
            <RefreshCw size={15} className={isSyncing ? 'animate-spin' : ''} />
            <span>{isSyncing ? 'Đang đồng bộ Qdrant...' : 'Đồng Bộ Qdrant'}</span>
          </button>
        </div>
      </div>

      {/* Mode Switcher Banner */}
      <div style={{
        background: '#f8fafc',
        border: '1px solid #e2e8f0',
        borderRadius: '12px',
        padding: '14px 18px',
        marginBottom: '16px',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        flexWrap: 'wrap',
        gap: '12px'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <div style={{ 
            background: enableRag ? 'rgba(2, 132, 199, 0.1)' : 'rgba(100, 116, 139, 0.1)',
            padding: '8px',
            borderRadius: '8px',
            color: enableRag ? '#0284c7' : '#64748b'
          }}>
            <SlidersHorizontal size={20} />
          </div>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span style={{ fontSize: '14px', fontWeight: 700, color: '#1e293b' }}>
                Chế độ Nạp Mẫu SQL cho LLM:
              </span>
              <span style={{
                fontSize: '12px',
                fontWeight: 700,
                padding: '2px 8px',
                borderRadius: '12px',
                background: enableRag ? '#dbeafe' : '#f1f5f9',
                color: enableRag ? '#1d4ed8' : '#475569',
                border: `1px solid ${enableRag ? '#bfdbfe' : '#cbd5e1'}`
              }}>
                {enableRag ? '🔍 RAG Mode (Few-Shot Semantic Search)' : '📂 Full Fetch Mode (Toàn bộ mẫu)'}
              </span>
            </div>
            <p style={{ margin: '2px 0 0 0', fontSize: '12px', color: '#64748b' }}>
              {enableRag 
                ? 'Tìm kiếm và đưa top 3 câu hỏi mẫu tương đồng nhất qua VectorDB Qdrant vào prompt.' 
                : 'Đưa toàn bộ tất cả câu lệnh SQL mẫu trong file JSON vào prompt cho LLM tham khảo.'}
            </p>
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <button
            className={`btn-pill ${enableRag ? 'active' : ''}`}
            onClick={() => handleToggleMode(true)}
            disabled={isUpdatingMode}
            style={{
              padding: '6px 14px',
              fontSize: '12px',
              fontWeight: 600,
              background: enableRag ? 'var(--primary)' : '#ffffff',
              color: enableRag ? '#ffffff' : '#475569',
              borderColor: enableRag ? 'var(--primary)' : '#cbd5e1'
            }}
          >
            <Sparkles size={13} />
            <span>Bật RAG Mode</span>
          </button>

          <button
            className={`btn-pill ${!enableRag ? 'active' : ''}`}
            onClick={() => handleToggleMode(false)}
            disabled={isUpdatingMode}
            style={{
              padding: '6px 14px',
              fontSize: '12px',
              fontWeight: 600,
              background: !enableRag ? 'var(--primary)' : '#ffffff',
              color: !enableRag ? '#ffffff' : '#475569',
              borderColor: !enableRag ? 'var(--primary)' : '#cbd5e1'
            }}
          >
            <Layers size={13} />
            <span>Bật Full Fetch Mode</span>
          </button>
        </div>
      </div>

      {syncStatus && (
        <div className={`status-alert ${syncStatus.success ? 'success' : 'error'}`}>
          {syncStatus.success ? <CheckCircle2 size={16} /> : <AlertCircle size={16} />}
          <span>{syncStatus.message}</span>
        </div>
      )}

      {/* Search & Stats */}
      <div className="km-search-row">
        <div className="search-input-wrapper">
          <Search size={16} color="var(--text-muted)" />
          <input
            type="text"
            placeholder="Tìm kiếm mẫu theo câu hỏi hoặc câu lệnh ClickHouse SQL..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="search-input-field"
          />
        </div>
        <div style={{ display: 'flex', gap: '8px' }}>
          <div className="km-stats-pill">
            <Code2 size={14} />
            <span>Tổng số: <strong>{examples.length} mẫu SQL</strong></span>
          </div>
          <div className="km-stats-pill" style={{ background: '#f0fdf4', borderColor: '#bbf7d0', color: '#166534' }}>
            <Database size={14} />
            <span>Qdrant: <strong>{vectorCount} vectors</strong></span>
          </div>
        </div>
      </div>

      {/* Examples List */}
      {isLoading ? (
        <div className="km-loading">
          <RefreshCw size={28} className="animate-spin" color="var(--primary)" />
          <span>Đang tải danh sách câu lệnh SQL mẫu...</span>
        </div>
      ) : filteredExamples.length === 0 ? (
        <div className="km-empty-state">
          <Code2 size={40} color="var(--text-light)" />
          <h3>Chưa tìm thấy câu lệnh SQL mẫu nào</h3>
          <p>Bấm nút "Thêm Mẫu SQL Mới" ở trên để bổ sung mẫu truy vấn đã kiểm chứng.</p>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          {filteredExamples.map((item, idx) => (
            <div key={item.id ?? idx} className="km-rule-card" style={{ padding: '16px' }}>
              <div className="km-card-header" style={{ marginBottom: '10px' }}>
                <div style={{ display: 'flex', alignItems: 'flex-start', gap: '10px', flex: 1 }}>
                  <span className="km-index-tag" style={{ background: '#0284c7' }}>
                    #{item.id + 1}
                  </span>
                  <div style={{ flex: 1 }}>
                    <div style={{ fontSize: '11px', textTransform: 'uppercase', fontWeight: 700, color: 'var(--primary)', letterSpacing: '0.5px' }}>
                      CÂU HỎI NGƯỜI DÙNG
                    </div>
                    <h3 className="km-rule-topic" style={{ fontSize: '15px', color: '#0f172a', marginTop: '2px' }}>
                      {item.question}
                    </h3>
                  </div>
                </div>

                <div className="km-card-btns">
                  <button 
                    className="btn-icon-round" 
                    onClick={() => handleCopySql(item.id, item.sql)}
                    title="Copy câu lệnh SQL"
                  >
                    {copiedId === item.id ? <Check size={15} color="#16a34a" /> : <Copy size={15} color="#64748b" />}
                  </button>
                  <button 
                    className="btn-icon-round" 
                    onClick={() => handleOpenEditModal(item)}
                    title="Chỉnh sửa mẫu SQL này"
                  >
                    <Edit3 size={15} color="var(--primary)" />
                  </button>
                  <button 
                    className="btn-icon-round danger" 
                    onClick={() => handleDeleteExample(item)}
                    title="Xóa mẫu SQL này"
                  >
                    <Trash2 size={15} color="#ef4444" />
                  </button>
                </div>
              </div>

              {/* Code Snippet Box */}
              <div>
                <div style={{ 
                  display: 'flex', 
                  alignItems: 'center', 
                  justifyContent: 'space-between',
                  background: '#0f172a',
                  color: '#94a3b8',
                  padding: '6px 12px',
                  borderTopLeftRadius: '8px',
                  borderTopRightRadius: '8px',
                  fontSize: '11px',
                  fontWeight: 600,
                  fontFamily: 'monospace'
                }}>
                  <span>CLICKHOUSE SQL TEMPLATE</span>
                  <span style={{ color: '#38bdf8' }}>{copiedId === item.id ? '✓ Đã copy SQL' : 'Verified'}</span>
                </div>
                <pre style={{
                  margin: 0,
                  padding: '12px 14px',
                  background: '#1e293b',
                  color: '#f8fafc',
                  borderBottomLeftRadius: '8px',
                  borderBottomRightRadius: '8px',
                  fontSize: '12.5px',
                  fontFamily: 'var(--font-mono, monospace)',
                  lineHeight: '1.5',
                  overflowX: 'auto',
                  whiteSpace: 'pre-wrap',
                  wordBreak: 'break-word',
                  border: '1px solid #334155',
                  borderTop: 'none'
                }}>
                  <code>{item.sql}</code>
                </pre>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Modal Add / Edit */}
      {isModalOpen && (
        <div className="modal-backdrop">
          <div className="modal-card" style={{ maxWidth: '680px' }}>
            <div className="modal-header">
              <h3 className="modal-title">
                {editingExample !== null ? '✏️ Chỉnh Sửa Mẫu SQL' : '➕ Thêm Mẫu SQL Đã Kiểm Chứng Mới'}
              </h3>
              <button className="btn-icon-close" onClick={() => setIsModalOpen(false)}>
                <X size={18} />
              </button>
            </div>

            <form onSubmit={handleSaveExample} className="modal-body">
              {formError && (
                <div className="form-error-alert">
                  <AlertCircle size={15} />
                  <span>{formError}</span>
                </div>
              )}

              <div className="form-group">
                <label className="form-label">
                  Câu hỏi người dùng (Question) <span style={{ color: '#ef4444' }}>*</span>
                </label>
                <input
                  type="text"
                  className="form-input"
                  placeholder="Ví dụ: Tính tỉ lệ nhắn tin thành công qua kênh MyViettel trong tháng này"
                  value={formQuestion}
                  onChange={(e) => setFormQuestion(e.target.value)}
                  autoFocus
                />
                <span className="form-hint">
                  💡 Câu hỏi này sẽ được tự động tạo vector embedding để tìm kiếm tương đồng (RAG) khi người dùng hỏi các câu có ý định tương tự.
                </span>
              </div>

              <div className="form-group">
                <label className="form-label">
                  Câu lệnh ClickHouse SQL Mẫu (SQL) <span style={{ color: '#ef4444' }}>*</span>
                </label>
                <textarea
                  className="form-textarea"
                  rows={8}
                  style={{ fontFamily: 'var(--font-mono, monospace)', fontSize: '13px', lineHeight: '1.45' }}
                  placeholder="SELECT ...&#10;FROM f_adpm_aimkt_campaign_customer_detail&#10;WHERE channel = 'MYVIETTEL'&#10;  AND toYYYYMM(toDate(toString(partition))) = toYYYYMM(now())"
                  value={formSql}
                  onChange={(e) => setFormSql(e.target.value)}
                />
                <span className="form-hint">
                  💡 Viết câu lệnh SELECT ClickHouse chuẩn, format xuống dòng rõ ràng ở SELECT, FROM, JOIN, WHERE, GROUP BY để LLM học cấu trúc tốt nhất.
                </span>
              </div>

              <div className="modal-footer">
                <button
                  type="button"
                  className="btn-pill"
                  onClick={() => setIsModalOpen(false)}
                  disabled={isSaving}
                >
                  Hủy Bỏ
                </button>
                <button type="submit" className="btn-primary" disabled={isSaving}>
                  {isSaving ? (
                    <>
                      <RefreshCw size={15} className="animate-spin" />
                      <span>Đang lưu & Đồng bộ...</span>
                    </>
                  ) : (
                    <>
                      <Save size={15} />
                      <span>Lưu & Tự Động Đồng Bộ Qdrant</span>
                    </>
                  )}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
