import React, { useState, useEffect, useRef, useMemo } from 'react';
import {
  Activity,
  Search,
  RefreshCw,
  CheckCircle2,
  AlertCircle,
  Clock,
  Coins,
  Database,
  Cpu,
  BookOpen,
  Code2,
  Terminal,
  ChevronRight,
  ChevronDown,
  PlayCircle,
  Copy,
  Check,
  Zap,
  Layers,
  MessagesSquare
} from 'lucide-react';

const API_BASE = '/api';

export function RealtimeLogView() {
  const [traces, setTraces] = useState([]);
  const [selectedRequestId, setSelectedRequestId] = useState(null);
  const [selectedTraceDetail, setSelectedTraceDetail] = useState(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [activeTab, setActiveTab] = useState('llm'); // 'timeline' | 'llm' | 'sql' | 'knowledge' | 'raw'
  const [copiedKey, setCopiedKey] = useState(null);
  const [isLiveConnected, setIsLiveConnected] = useState(false);
  const [expandedSessions, setExpandedSessions] = useState(() => new Set());
  const hasAutoExpandedRef = useRef(false);

  const eventSourceRef = useRef(null);

  // 1. Fetch initial trace list
  useEffect(() => {
    fetchTraces();
  }, []);

  // 2. Connect to SSE Live Stream
  useEffect(() => {
    const sse = new EventSource(`${API_BASE}/monitor/live`);
    eventSourceRef.current = sse;

    sse.addEventListener('monitor_connected', () => {
      setIsLiveConnected(true);
    });

    sse.addEventListener('monitor_event', (e) => {
      try {
        const payload = JSON.parse(e.data);
        handleLiveEvent(payload);
      } catch (err) {
        console.error('SSE parse error:', err);
      }
    });

    sse.onerror = () => {
      setIsLiveConnected(false);
    };

    return () => {
      sse.close();
    };
  }, [selectedRequestId]);

  // 3. Load detail when selectedRequestId changes
  useEffect(() => {
    if (selectedRequestId) {
      fetchTraceDetail(selectedRequestId);
    }
  }, [selectedRequestId]);

  const handleLiveEvent = (eventData) => {
    // Refresh traces list on trace start or finish
    if (eventData.event === 'trace_started' || eventData.event === 'trace_finished') {
      fetchTraces();
    }
    // If currently viewing the active request, refresh its detail
    if (selectedRequestId && eventData.request_id === selectedRequestId) {
      fetchTraceDetail(selectedRequestId);
    }
  };

  const fetchTraces = async () => {
    try {
      const res = await fetch(`${API_BASE}/monitor/traces`);
      if (res.ok) {
        const data = await res.json();
        setTraces(data);
        // Select first if none selected
        if (!selectedRequestId && data.length > 0) {
          setSelectedRequestId(data[0].request_id);
        }
      }
    } catch (e) {
      console.error('Failed to fetch traces:', e);
    }
  };

  const fetchTraceDetail = async (reqId) => {
    try {
      const res = await fetch(`${API_BASE}/monitor/traces/${reqId}`);
      if (res.ok) {
        const data = await res.json();
        setSelectedTraceDetail(data);
      }
    } catch (e) {
      console.error('Failed to fetch trace detail:', e);
    }
  };

  const copyToClipboard = (text, key) => {
    navigator.clipboard.writeText(typeof text === 'string' ? text : JSON.stringify(text, null, 2));
    setCopiedKey(key);
    setTimeout(() => setCopiedKey(null), 2000);
  };

  const filteredTraces = traces.filter((t) =>
    t.query?.toLowerCase().includes(searchQuery.toLowerCase()) ||
    t.request_id?.toLowerCase().includes(searchQuery.toLowerCase()) ||
    t.session_id?.toLowerCase().includes(searchQuery.toLowerCase()) ||
    t.client_ip?.toLowerCase().includes(searchQuery.toLowerCase())
  );

  // Group traces by session_id - each session is a collapsible group, newest
  // session first (traces already arrive newest-first from the API, so the
  // first trace seen for a session is also that session's most recent activity).
  const sessionGroups = useMemo(() => {
    const groups = new Map();
    for (const t of filteredTraces) {
      const sid = t.session_id || 'unknown';
      if (!groups.has(sid)) {
        groups.set(sid, { session_id: sid, latestTimestamp: t.timestamp || 0, clientIp: t.client_ip, traces: [] });
      }
      const g = groups.get(sid);
      g.traces.push(t);
      if ((t.timestamp || 0) > g.latestTimestamp) g.latestTimestamp = t.timestamp;
    }
    return Array.from(groups.values()).sort((a, b) => b.latestTimestamp - a.latestTimestamp);
  }, [filteredTraces]);

  // Auto-expand the most recent session on first load, and whichever session
  // owns the currently selected trace (e.g. after clicking one from an SSE update).
  useEffect(() => {
    if (sessionGroups.length === 0) return;
    setExpandedSessions((prev) => {
      const next = new Set(prev);
      if (!hasAutoExpandedRef.current) {
        next.add(sessionGroups[0].session_id);
        hasAutoExpandedRef.current = true;
      }
      const owner = sessionGroups.find((g) => g.traces.some((t) => t.request_id === selectedRequestId));
      if (owner) next.add(owner.session_id);
      return next;
    });
  }, [sessionGroups, selectedRequestId]);

  const toggleSession = (sid) => {
    setExpandedSessions((prev) => {
      const next = new Set(prev);
      if (next.has(sid)) next.delete(sid);
      else next.add(sid);
      return next;
    });
  };

  return (
    <div className="monitor-split-container">
      {/* LEFT COLUMN: QUERY / REQUEST LIST */}
      <div className="monitor-left-panel">
        <div className="panel-header">
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Terminal size={18} color="var(--primary)" />
              <h3 style={{ margin: 0, fontSize: '15px', fontWeight: 700 }}>Request Traces</h3>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              <span className={`live-indicator ${isLiveConnected ? 'active' : ''}`} title={isLiveConnected ? 'SSE Live Stream Connected' : 'Connecting...'}>
                <span className="live-dot"></span>
                <span>{isLiveConnected ? 'LIVE' : 'OFFLINE'}</span>
              </span>
              <button className="btn-icon-tiny" onClick={fetchTraces} title="Tải lại danh sách">
                <RefreshCw size={14} />
              </button>
            </div>
          </div>

          {/* Search Box */}
          <div className="search-bar-small" style={{ marginTop: '10px' }}>
            <Search size={14} color="var(--text-muted)" />
            <input
              type="text"
              placeholder="Tìm theo query, session ID..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="search-input-small"
            />
          </div>
        </div>

        {/* Sessions List (each session is a collapsible group of its request traces) */}
        <div className="traces-list-scroll">
          {sessionGroups.length === 0 ? (
            <div className="empty-traces">
              <Activity size={32} color="var(--text-light)" />
              <p>Chưa có lượt truy vấn nào được ghi nhận.</p>
            </div>
          ) : (
            sessionGroups.map((group) => {
              const isExpanded = expandedSessions.has(group.session_id);
              const latestFormatted = group.latestTimestamp
                ? new Date(group.latestTimestamp * 1000).toLocaleTimeString('vi-VN')
                : 'N/A';
              const hasRunning = group.traces.some((t) => t.status === 'running');
              const hasError = group.traces.some((t) => t.status === 'error');

              return (
                <div key={group.session_id} className="session-group">
                  <div className="session-group-header" onClick={() => toggleSession(group.session_id)}>
                    {isExpanded ? <ChevronDown size={15} /> : <ChevronRight size={15} />}
                    <MessagesSquare size={14} color="var(--primary)" />
                    <span className="session-id-tag" title={group.session_id}>
                      {group.session_id.slice(0, 8)}
                    </span>
                    <span className="session-count-badge">{group.traces.length} request{group.traces.length > 1 ? 's' : ''}</span>
                    {hasRunning && <span className="status-badge running animate-pulse"><RefreshCw size={10} className="animate-spin" /></span>}
                    {hasError && !hasRunning && <span className="status-badge error"><AlertCircle size={10} /></span>}
                    <span className="session-latest-time">{latestFormatted}</span>
                  </div>

                  {isExpanded && (
                    <div className="session-traces-sublist">
                      {group.traces.map((trace) => {
                        const isSelected = trace.request_id === selectedRequestId;
                        const isRunning = trace.status === 'running';
                        const isError = trace.status === 'error';
                        const timeFormatted = trace.timestamp
                          ? new Date(trace.timestamp * 1000).toLocaleTimeString('vi-VN')
                          : 'N/A';

                        return (
                          <div
                            key={trace.request_id}
                            className={`trace-item-card ${isSelected ? 'selected' : ''}`}
                            onClick={() => setSelectedRequestId(trace.request_id)}
                          >
                            <div className="trace-card-top">
                              <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                                {isRunning ? (
                                  <span className="status-badge running animate-pulse">
                                    <RefreshCw size={11} className="animate-spin" /> RUNNING
                                  </span>
                                ) : isError ? (
                                  <span className="status-badge error">
                                    <AlertCircle size={11} /> ERROR
                                  </span>
                                ) : (
                                  <span className="status-badge done">
                                    <CheckCircle2 size={11} /> DONE
                                  </span>
                                )}
                                <span className="trace-time">{timeFormatted}</span>
                              </div>

                              <div className="trace-metrics-compact">
                                <span title="Total Tokens">
                                  <Coins size={11} /> {trace.total_tokens?.toLocaleString() || 0}
                                </span>
                                <span title="Latency">
                                  <Clock size={11} /> {trace.total_latency_ms ? `${trace.total_latency_ms}ms` : '...'}
                                </span>
                              </div>
                            </div>

                            <div className="trace-query-snippet">
                              {trace.query || '(Empty query)'}
                            </div>

                            <div className="trace-meta-footer">
                              <span>ID: <code>{trace.request_id.slice(-8)}</code></span>
                              <span>IP: <code>{trace.client_ip || 'unknown'}</code></span>
                              {trace.sql_count > 0 && (
                                <span className="sql-count-tag">
                                  <Database size={10} /> {trace.sql_count} SQL
                                </span>
                              )}
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  )}
                </div>
              );
            })
          )}
        </div>
      </div>

      {/* RIGHT COLUMN: REALTIME EXECUTION TRACE & LLM INSPECTOR */}
      <div className="monitor-right-panel">
        {selectedTraceDetail ? (
          <div className="trace-detail-container">
            {/* Header with Query & Global Metrics */}
            <div className="trace-detail-header">
              <div className="trace-title-row">
                <div style={{ flex: 1 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '6px' }}>
                    <span className={`status-badge ${selectedTraceDetail.status === 'completed' ? 'done' : selectedTraceDetail.status === 'running' ? 'running animate-pulse' : 'error'}`}>
                      {selectedTraceDetail.status.toUpperCase()}
                    </span>
                    <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
                      Request ID: <code>{selectedTraceDetail.request_id}</code> | Session ID: <code>{selectedTraceDetail.session_id}</code> | Client IP: <code>{selectedTraceDetail.client_ip || 'unknown'}</code>
                    </span>
                  </div>
                  <h2 className="trace-query-full">"{selectedTraceDetail.query}"</h2>
                </div>
              </div>

              {/* Metrics Summary Cards */}
              <div className="metrics-summary-grid">
                <div className="metric-box">
                  <div className="metric-label">
                    <Clock size={13} color="var(--primary)" />
                    <span>Total Latency</span>
                  </div>
                  <div className="metric-value">{selectedTraceDetail.total_latency_ms ? `${selectedTraceDetail.total_latency_ms} ms` : 'Đang đo...'}</div>
                </div>

                <div className="metric-box">
                  <div className="metric-label">
                    <Coins size={13} color="#f59e0b" />
                    <span>Total Tokens</span>
                  </div>
                  <div className="metric-value highlight">{selectedTraceDetail.total_tokens?.toLocaleString() || 0}</div>
                  <div className="metric-sub">
                    Prompt: <strong>{selectedTraceDetail.prompt_tokens?.toLocaleString() || 0}</strong> | Output: <strong>{selectedTraceDetail.completion_tokens?.toLocaleString() || 0}</strong>
                  </div>
                </div>

                <div className="metric-box">
                  <div className="metric-label">
                    <Database size={13} color="#10b981" />
                    <span>ClickHouse Queries</span>
                  </div>
                  <div className="metric-value">{selectedTraceDetail.sql_queries?.length || 0}</div>
                </div>

                <div className="metric-box">
                  <div className="metric-label">
                    <Cpu size={13} color="#8b5cf6" />
                    <span>LLM Calls</span>
                  </div>
                  <div className="metric-value">{selectedTraceDetail.llm_traces?.length || 0}</div>
                </div>
              </div>

              {/* Sub-tabs Navigation */}
              <div className="sub-tabs-bar">
                <button
                  className={`sub-tab-btn ${activeTab === 'llm' ? 'active' : ''}`}
                  onClick={() => setActiveTab('llm')}
                >
                  <Cpu size={15} />
                  <span>LLM Inspector ({selectedTraceDetail.llm_traces?.length || 0})</span>
                </button>

                <button
                  className={`sub-tab-btn ${activeTab === 'sql' ? 'active' : ''}`}
                  onClick={() => setActiveTab('sql')}
                >
                  <Database size={15} />
                  <span>ClickHouse SQL ({selectedTraceDetail.sql_queries?.length || 0})</span>
                </button>

                <button
                  className={`sub-tab-btn ${activeTab === 'timeline' ? 'active' : ''}`}
                  onClick={() => setActiveTab('timeline')}
                >
                  <Layers size={15} />
                  <span>Pipeline Steps ({selectedTraceDetail.steps?.length || 0})</span>
                </button>

                <button
                  className={`sub-tab-btn ${activeTab === 'raw' ? 'active' : ''}`}
                  onClick={() => setActiveTab('raw')}
                >
                  <Code2 size={15} />
                  <span>Raw JSON Trace</span>
                </button>
              </div>
            </div>

            {/* Sub-tab Contents */}
            <div className="trace-detail-body">
              {/* TAB: LLM INSPECTOR */}
              {activeTab === 'llm' && (
                <div className="llm-inspector-tab">
                  {selectedTraceDetail.llm_traces && selectedTraceDetail.llm_traces.length > 0 ? (
                    selectedTraceDetail.llm_traces.map((call, idx) => (
                      <div key={idx} className="llm-call-card">
                        <div className="llm-card-header">
                          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                            <span className="call-index-badge">LLM Call #{idx + 1}</span>
                            <span className="call-type-name">{call.call_type}</span>
                            <span className="model-tag">{call.model}</span>
                          </div>
                          <div className="token-pills-row">
                            <span className="token-pill prompt">Prompt: <strong>{call.prompt_tokens}</strong></span>
                            <span className="token-pill output">Output: <strong>{call.completion_tokens}</strong></span>
                            <span className="token-pill total">Total: <strong>{call.total_tokens}</strong></span>
                            <span className="token-pill latency"><Clock size={11} /> {call.latency_ms}ms</span>
                          </div>
                        </div>

                        {/* Input Messages Section */}
                        <div className="code-section">
                          <div className="code-header">
                            <span style={{ fontWeight: 600, color: 'var(--primary-dark)' }}>
                              📥 Input Messages Payload (System Prompt + Contexts + User Query)
                            </span>
                            <button
                              className="btn-copy"
                              onClick={() => copyToClipboard(call.input_messages, `input_${idx}`)}
                            >
                              {copiedKey === `input_${idx}` ? <Check size={13} color="#10b981" /> : <Copy size={13} />}
                              <span>{copiedKey === `input_${idx}` ? 'Đã copy' : 'Copy'}</span>
                            </button>
                          </div>
                          <div className="messages-stream-box">
                            {call.input_messages?.map((msg, mIdx) => (
                              <div key={mIdx} className={`message-bubble-trace ${msg.role}`}>
                                <div className="msg-role-tag">{msg.role.toUpperCase()}</div>
                                <pre className="msg-pre-content">{msg.content}</pre>
                              </div>
                            ))}
                          </div>
                        </div>

                        {/* Raw Output Section */}
                        <div className="code-section" style={{ marginTop: '14px' }}>
                          <div className="code-header">
                            <span style={{ fontWeight: 600, color: '#16a34a' }}>
                              📤 Raw Output Trả Về Từ LLM
                            </span>
                            <button
                              className="btn-copy"
                              onClick={() => copyToClipboard(call.raw_output, `output_${idx}`)}
                            >
                              {copiedKey === `output_${idx}` ? <Check size={13} color="#10b981" /> : <Copy size={13} />}
                              <span>{copiedKey === `output_${idx}` ? 'Đã copy' : 'Copy'}</span>
                            </button>
                          </div>
                          <pre className="raw-output-pre">{call.raw_output}</pre>
                        </div>
                      </div>
                    ))
                  ) : (
                    <div className="empty-section">
                      <Cpu size={32} color="var(--text-light)" />
                      <p>Chưa có lượt gọi LLM nào được ghi nhận cho request này.</p>
                    </div>
                  )}
                </div>
              )}

              {/* TAB: CLICKHOUSE SQL */}
              {activeTab === 'sql' && (
                <div className="sql-inspector-tab">
                  {selectedTraceDetail.sql_queries && selectedTraceDetail.sql_queries.length > 0 ? (
                    selectedTraceDetail.sql_queries.map((item, idx) => (
                      <div key={idx} className="sql-card">
                        <div className="sql-card-header">
                          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                            <span className="sql-id-tag">[{item.id}]</span>
                            <h4 className="sql-title">{item.title || 'Truy vấn ClickHouse'}</h4>
                          </div>
                          {item.execution_time_ms && (
                            <span className="sql-timing-tag">
                              <Zap size={12} color="#f59e0b" /> {item.execution_time_ms} ms
                            </span>
                          )}
                        </div>

                        <div className="sql-code-box">
                          <pre>{item.sql}</pre>
                          <button
                            className="btn-copy"
                            onClick={() => copyToClipboard(item.sql, `sql_${idx}`)}
                            style={{ position: 'absolute', top: '10px', right: '10px' }}
                          >
                            {copiedKey === `sql_${idx}` ? <Check size={13} color="#10b981" /> : <Copy size={13} />}
                          </button>
                        </div>

                        {/* Raw Result Table / JSON */}
                        <div style={{ marginTop: '10px' }}>
                          <div style={{ fontSize: '12px', fontWeight: 700, color: 'var(--text-muted)', marginBottom: '6px' }}>
                            Kết quả dữ liệu trả về từ ClickHouse (Rows: {Array.isArray(item.result) ? item.result.length : 0}):
                          </div>
                          <pre className="result-data-box">
                            {JSON.stringify(item.result, null, 2)}
                          </pre>
                        </div>
                      </div>
                    ))
                  ) : (
                    <div className="empty-section">
                      <Database size={32} color="var(--text-light)" />
                      <p>Không có câu truy vấn SQL nào được thực thi trong lượt này.</p>
                    </div>
                  )}
                </div>
              )}

              {/* TAB: PIPELINE TIMELINE STEPS */}
              {activeTab === 'timeline' && (
                <div className="timeline-inspector-tab">
                  <div className="timeline-track">
                    {selectedTraceDetail.steps?.map((step, idx) => (
                      <div key={idx} className="timeline-node">
                        <div className="node-icon-col">
                          <div className={`node-circle ${step.status}`}>
                            {step.status === 'completed' ? <CheckCircle2 size={16} /> : step.status === 'running' ? <RefreshCw size={16} className="animate-spin" /> : <AlertCircle size={16} />}
                          </div>
                          {idx < selectedTraceDetail.steps.length - 1 && <div className="node-line"></div>}
                        </div>

                        <div className="node-content-card">
                          <div className="node-card-header">
                            <div>
                              <span className="step-name-badge">{step.step}</span>
                              <h4 className="step-title">{step.title}</h4>
                            </div>
                            {step.latency_ms && (
                              <span className="step-time-badge">
                                <Clock size={11} /> {step.latency_ms} ms
                              </span>
                            )}
                          </div>

                          {step.data && Object.keys(step.data).length > 0 && (
                            <pre className="step-data-preview">
                              {JSON.stringify(step.data, null, 2)}
                            </pre>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* TAB: RAW JSON */}
              {activeTab === 'raw' && (
                <div className="raw-inspector-tab">
                  <div style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: '8px' }}>
                    <button
                      className="btn-pill"
                      onClick={() => copyToClipboard(selectedTraceDetail, 'full_json')}
                    >
                      {copiedKey === 'full_json' ? <Check size={14} color="#10b981" /> : <Copy size={14} />}
                      <span>Copy Full JSON Trace</span>
                    </button>
                  </div>
                  <pre className="raw-json-box">
                    {JSON.stringify(selectedTraceDetail, null, 2)}
                  </pre>
                </div>
              )}
            </div>
          </div>
        ) : (
          <div className="empty-panel-placeholder">
            <Terminal size={48} color="var(--text-light)" />
            <h3>Chọn một lượt query bên trái để xem chi tiết log & metrics</h3>
            <p>Hoặc gửi câu hỏi mới từ Chatbot (Port 3000) để theo dõi luồng xử lý realtime.</p>
          </div>
        )}
      </div>
    </div>
  );
}
