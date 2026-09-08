import React, { useState, useEffect } from 'react';
import { Database, RefreshCw, Search, Table2, KeyRound } from 'lucide-react';

const API_BASE = '/api';

export function SchemaViewerView() {
  const [tables, setTables] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [expandedTable, setExpandedTable] = useState(null);

  useEffect(() => {
    fetchTables();
  }, []);

  const fetchTables = async () => {
    setIsLoading(true);
    try {
      const res = await fetch(`${API_BASE}/schema/tables`);
      if (res.ok) {
        const data = await res.json();
        setTables(data || []);
        if (data && data.length > 0) setExpandedTable(data[0].table_name);
      }
    } catch (e) {
      console.error('Error fetching schema tables:', e);
    } finally {
      setIsLoading(false);
    }
  };

  const filteredTables = tables.filter(
    (t) =>
      t.table_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      (t.description || '').toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <div className="knowledge-manager-container">
      {/* Top Header */}
      <div className="km-header">
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
            <Database size={24} color="var(--primary)" />
            <h2 style={{ margin: 0, fontSize: '20px', fontWeight: 800 }}>
              Cấu Trúc Bảng ClickHouse (schemas.json)
            </h2>
          </div>
          <p style={{ margin: 0, fontSize: '13px', color: 'var(--text-muted)' }}>
            Chỉ xem (view-only). <code>schemas.json</code> gắn trực tiếp với <code>backend/sql/init.sql</code>,
            nên việc thêm/sửa/xóa bảng cần thực hiện thủ công ở phía backend để tránh lệch giữa metadata và DDL thật.
          </p>
        </div>

        <div className="km-actions">
          <button className="btn-pill" onClick={fetchTables} disabled={isLoading}>
            <RefreshCw size={15} className={isLoading ? 'animate-spin' : ''} />
            <span>Tải lại</span>
          </button>
        </div>
      </div>

      {/* Search & Stats */}
      <div className="km-search-row">
        <div className="search-input-wrapper">
          <Search size={16} color="var(--text-muted)" />
          <input
            type="text"
            placeholder="Tìm kiếm theo tên bảng hoặc mô tả nghiệp vụ..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="search-input-field"
          />
        </div>
        <div className="km-stats-pill">
          <Table2 size={14} />
          <span>Tổng số: <strong>{tables.length} bảng</strong></span>
        </div>
      </div>

      {/* Tables List */}
      {isLoading ? (
        <div className="km-loading">
          <RefreshCw size={28} className="animate-spin" color="var(--primary)" />
          <span>Đang tải metadata schema...</span>
        </div>
      ) : filteredTables.length === 0 ? (
        <div className="km-empty-state">
          <Database size={40} color="var(--text-light)" />
          <h3>Chưa có bảng nào được cấu hình</h3>
          <p>Thêm metadata bảng vào <code>backend/schemas.json</code>.</p>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          {filteredTables.map((t) => {
            const isOpen = expandedTable === t.table_name;
            return (
              <div key={t.table_name} className="km-rule-card" style={{ padding: '16px' }}>
                <div
                  className="km-card-header"
                  style={{ marginBottom: isOpen ? '10px' : 0, cursor: 'pointer' }}
                  onClick={() => setExpandedTable(isOpen ? null : t.table_name)}
                >
                  <div style={{ display: 'flex', alignItems: 'flex-start', gap: '10px', flex: 1 }}>
                    <span className="km-index-tag" style={{ background: '#0284c7' }}>
                      <Table2 size={13} />
                    </span>
                    <div style={{ flex: 1 }}>
                      <h3 className="km-rule-topic" style={{ fontSize: '15px', color: '#0f172a', fontFamily: 'var(--font-mono, monospace)' }}>
                        {t.table_name}
                      </h3>
                      {t.description && (
                        <p style={{ margin: '4px 0 0 0', fontSize: '13px', color: 'var(--text-muted)' }}>{t.description}</p>
                      )}
                    </div>
                  </div>
                  <div className="km-stats-pill" style={{ background: '#f0fdf4', borderColor: '#bbf7d0', color: '#166534' }}>
                    <KeyRound size={13} />
                    <span>{t.column_count ?? (t.columns || []).length} cột</span>
                  </div>
                </div>

                {isOpen && (
                  <div style={{ overflowX: 'auto' }}>
                    <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '13px' }}>
                      <thead>
                        <tr style={{ textAlign: 'left', borderBottom: '1px solid #e2e8f0', color: 'var(--text-muted)' }}>
                          <th style={{ padding: '6px 8px', fontWeight: 700 }}>Tên cột</th>
                          <th style={{ padding: '6px 8px', fontWeight: 700 }}>Kiểu dữ liệu</th>
                          <th style={{ padding: '6px 8px', fontWeight: 700 }}>Mô tả</th>
                        </tr>
                      </thead>
                      <tbody>
                        {(t.columns || []).map((col) => (
                          <tr key={col.name} style={{ borderBottom: '1px solid #f1f5f9' }}>
                            <td style={{ padding: '6px 8px', fontFamily: 'var(--font-mono, monospace)', color: '#0f172a' }}>{col.name}</td>
                            <td style={{ padding: '6px 8px', color: '#0284c7', fontFamily: 'var(--font-mono, monospace)' }}>{col.type}</td>
                            <td style={{ padding: '6px 8px', color: 'var(--text-muted)' }}>{col.description || '—'}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
