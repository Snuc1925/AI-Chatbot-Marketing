import React, { useState, useEffect } from 'react';
import { 
  BookOpen, 
  Plus, 
  Edit3, 
  Trash2, 
  RefreshCw, 
  CheckCircle2, 
  AlertCircle, 
  Save, 
  X, 
  Search,
  Database,
  FileText
} from 'lucide-react';

const API_BASE = '/api';

export function KnowledgeManagerView() {
  const [rules, setRules] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [isSyncing, setIsSyncing] = useState(false);
  const [syncStatus, setSyncStatus] = useState(null);

  // Modal states
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingRule, setEditingRule] = useState(null);
  const [formTopic, setFormTopic] = useState('');
  const [formDescription, setFormDescription] = useState('');
  const [formError, setFormError] = useState('');
  const [isSaving, setIsSaving] = useState(false);

  useEffect(() => {
    fetchRules();
  }, []);

  const fetchRules = async () => {
    setIsLoading(true);
    try {
      const res = await fetch(`${API_BASE}/knowledge/rules`);
      if (res.ok) {
        const data = await res.json();
        setRules(data);
      }
    } catch (e) {
      console.error('Error fetching knowledge rules:', e);
    } finally {
      setIsLoading(false);
    }
  };

  const handleOpenAddModal = () => {
    setEditingRule(null);
    setFormTopic('');
    setFormDescription('');
    setFormError('');
    setIsModalOpen(true);
  };

  const handleOpenEditModal = (rule) => {
    setEditingRule(rule);
    setFormTopic(rule.topic);
    setFormDescription(rule.description);
    setFormError('');
    setIsModalOpen(true);
  };

  const handleSaveRule = async (e) => {
    e.preventDefault();
    if (!formTopic.trim() || !formDescription.trim()) {
      setFormError('Vui lòng nhập đầy đủ Tiêu đề chủ đề (Topic) và Nội dung quy tắc (Description).');
      return;
    }

    setIsSaving(true);
    setFormError('');

    try {
      if (editingRule !== null) {
        // Edit existing rule
        const res = await fetch(`${API_BASE}/knowledge/rules/${editingRule.id}`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            topic: formTopic.trim(),
            description: formDescription.trim(),
          }),
        });
        if (!res.ok) throw new Error('Không thể cập nhật quy tắc');
      } else {
        // Create new rule
        const res = await fetch(`${API_BASE}/knowledge/rules`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            topic: formTopic.trim(),
            description: formDescription.trim(),
          }),
        });
        if (!res.ok) throw new Error('Không thể thêm quy tắc mới');
      }

      setIsModalOpen(false);
      await fetchRules();
    } catch (err) {
      setFormError(err.message || 'Lỗi khi lưu quy tắc');
    } finally {
      setIsSaving(false);
    }
  };

  const handleDeleteRule = async (rule) => {
    if (!window.confirm(`Bạn có chắc chắn muốn xóa quy tắc: "${rule.topic}"?`)) {
      return;
    }

    try {
      const res = await fetch(`${API_BASE}/knowledge/rules/${rule.id}`, {
        method: 'DELETE',
      });
      if (res.ok) {
        await fetchRules();
      } else {
        alert('Không thể xóa quy tắc.');
      }
    } catch (e) {
      alert(`Lỗi: ${e.message}`);
    }
  };

  const handleManualSyncQdrant = async () => {
    setIsSyncing(true);
    setSyncStatus(null);
    try {
      const res = await fetch(`${API_BASE}/knowledge/sync`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ force_reset: true }),
      });
      if (res.ok) {
        const data = await res.json();
        setSyncStatus({ success: true, message: `Đã đồng bộ thành công ${data.synced_count || 0} quy tắc vào Qdrant Vector Store!` });
        await fetchRules();
      } else {
        setSyncStatus({ success: false, message: 'Đồng bộ thất bại.' });
      }
    } catch (e) {
      setSyncStatus({ success: false, message: `Lỗi đồng bộ: ${e.message}` });
    } finally {
      setIsSyncing(false);
    }
  };

  const filteredRules = rules.filter(
    (r) =>
      r.topic.toLowerCase().includes(searchQuery.toLowerCase()) ||
      r.description.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <div className="knowledge-manager-container">
      {/* Top Action Bar */}
      <div className="km-header">
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
            <BookOpen size={22} color="var(--primary)" />
            <h2 style={{ margin: 0, fontSize: '20px', fontWeight: 800 }}>
              Cấu Hình Tri Thức Nghiệp Vụ (Business Knowledge)
            </h2>
          </div>
          <p style={{ margin: 0, fontSize: '13px', color: 'var(--text-muted)' }}>
            Quản lý các quy tắc nghiệp vụ trong file <code>backend/business_knowledge.json</code>.
            Mỗi bản ghi gồm <strong>topic</strong> và <strong>description</strong> (mô tả bằng ngôn ngữ tự nhiên).
          </p>
        </div>

        <div className="km-actions">
          <button className="btn-primary" onClick={handleOpenAddModal}>
            <Plus size={16} />
            <span>Thêm Quy Tắc Mới</span>
          </button>

          <button 
            className="btn-pill" 
            onClick={handleManualSyncQdrant} 
            disabled={isSyncing}
            style={{ background: '#ffffff', borderColor: 'var(--primary)', color: 'var(--primary)' }}
          >
            <RefreshCw size={15} className={isSyncing ? 'animate-spin' : ''} />
            <span>{isSyncing ? 'Đang đồng bộ Qdrant...' : 'Đồng Bộ Lại Qdrant'}</span>
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
            placeholder="Tìm kiếm quy tắc theo topic hoặc nội dung..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="search-input-field"
          />
        </div>
        <div className="km-stats-pill">
          <FileText size={14} />
          <span>Tổng số: <strong>{rules.length} quy tắc</strong></span>
        </div>
      </div>

      {/* Rules Grid */}
      {isLoading ? (
        <div className="km-loading">
          <RefreshCw size={28} className="animate-spin" color="var(--primary)" />
          <span>Đang tải danh sách quy tắc nghiệp vụ...</span>
        </div>
      ) : filteredRules.length === 0 ? (
        <div className="km-empty-state">
          <BookOpen size={40} color="var(--text-light)" />
          <h3>Chưa tìm thấy quy tắc nghiệp vụ nào</h3>
          <p>Bấm nút "Thêm Quy Tắc Mới" ở trên để bổ sung quy tắc vào hệ thống.</p>
        </div>
      ) : (
        <div className="km-rules-grid">
          {filteredRules.map((rule, idx) => (
            <div key={rule.id ?? idx} className="km-rule-card">
              <div className="km-card-header">
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <span className="km-index-tag">#{rule.id + 1}</span>
                  <h3 className="km-rule-topic">{rule.topic}</h3>
                </div>
                <div className="km-card-btns">
                  <button 
                    className="btn-icon-round" 
                    onClick={() => handleOpenEditModal(rule)}
                    title="Chỉnh sửa quy tắc"
                  >
                    <Edit3 size={15} color="var(--primary)" />
                  </button>
                  <button 
                    className="btn-icon-round danger" 
                    onClick={() => handleDeleteRule(rule)}
                    title="Xóa quy tắc này"
                  >
                    <Trash2 size={15} color="#ef4444" />
                  </button>
                </div>
              </div>
              <div className="km-rule-desc">
                {rule.description}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Modal Add / Edit */}
      {isModalOpen && (
        <div className="modal-backdrop">
          <div className="modal-card">
            <div className="modal-header">
              <h3 className="modal-title">
                {editingRule !== null ? '✏️ Chỉnh Sửa Quy Tắc Nghiệp Vụ' : '➕ Thêm Quy Tắc Nghiệp Vụ Mới'}
              </h3>
              <button className="btn-icon-close" onClick={() => setIsModalOpen(false)}>
                <X size={18} />
              </button>
            </div>

            <form onSubmit={handleSaveRule} className="modal-body">
              {formError && (
                <div className="form-error-alert">
                  <AlertCircle size={15} />
                  <span>{formError}</span>
                </div>
              )}

              <div className="form-group">
                <label className="form-label">
                  Tiêu đề chủ đề (Topic) <span style={{ color: '#ef4444' }}>*</span>
                </label>
                <input
                  type="text"
                  className="form-input"
                  placeholder="Ví dụ: Quy tắc gán kênh mua gói và tính toán doanh thu"
                  value={formTopic}
                  onChange={(e) => setFormTopic(e.target.value)}
                  autoFocus
                />
              </div>

              <div className="form-group">
                <label className="form-label">
                  Mô tả quy tắc tự nhiên (Description) <span style={{ color: '#ef4444' }}>*</span>
                </label>
                <textarea
                  className="form-textarea"
                  rows={6}
                  placeholder="Mô tả bằng tiếng Việt tự nhiên về bảng dữ liệu, điều kiện lọc status, cách JOIN qua isdn/msisdn, quy ước mã tỉnh thành, công thức phần trăm..."
                  value={formDescription}
                  onChange={(e) => setFormDescription(e.target.value)}
                />
                <span className="form-hint">
                  💡 Viết mô tả thuần túy bằng ngôn ngữ tự nhiên. AI sẽ tự hiểu ngữ nghĩa và suy luận ra câu lệnh ClickHouse SQL tương ứng khi nhận câu hỏi từ người dùng.
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
