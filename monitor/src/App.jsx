import React, { useState } from 'react';
import { RealtimeLogView } from './components/RealtimeLogView';
import { KnowledgeManagerView } from './components/KnowledgeManagerView';
import { SchemaViewerView } from './components/SchemaViewerView';
import { SystemPromptsView } from './components/SystemPromptsView';
// HIDDEN (not deleted): SQL Examples tab is intentionally disabled - its content
// now overlaps with Business Knowledge. Re-enable by uncommenting this import and
// the tab button/route below.
// import { SqlExamplesManagerView } from './components/SqlExamplesManagerView';
import { Activity, BookOpen, Database, Wand2, Layers, ExternalLink } from 'lucide-react';

export default function App() {
  const [activeMainTab, setActiveMainTab] = useState('monitor'); // 'monitor' | 'knowledge' | 'schema' | 'prompts'

  return (
    <div className="admin-app">
      {/* Top Navbar */}
      <header className="admin-navbar">
        <div className="admin-nav-left">
          <div className="admin-logo-badge">
            <Layers size={20} color="#ffffff" />
            <span>AI Marketing Admin & Monitor</span>
          </div>

          <div className="main-nav-tabs">
            <button
              className={`main-nav-tab ${activeMainTab === 'monitor' ? 'active' : ''}`}
              onClick={() => setActiveMainTab('monitor')}
            >
              <Activity size={16} />
              <span>Realtime Execution Log</span>
            </button>

            <button
              className={`main-nav-tab ${activeMainTab === 'knowledge' ? 'active' : ''}`}
              onClick={() => setActiveMainTab('knowledge')}
            >
              <BookOpen size={16} />
              <span>Tri Thức Nghiệp Vụ (business_knowledge.json)</span>
            </button>

            <button
              className={`main-nav-tab ${activeMainTab === 'schema' ? 'active' : ''}`}
              onClick={() => setActiveMainTab('schema')}
            >
              <Database size={16} />
              <span>Schema ClickHouse (view-only)</span>
            </button>

            <button
              className={`main-nav-tab ${activeMainTab === 'prompts' ? 'active' : ''}`}
              onClick={() => setActiveMainTab('prompts')}
            >
              <Wand2 size={16} />
              <span>System Prompts</span>
            </button>

            {/* HIDDEN (not deleted): Mẫu Truy Vấn SQL (sql_examples.json) tab -
                content now overlaps with Business Knowledge, so it's disabled for
                now. Uncomment this button + the route below to bring it back. */}
            {/* <button
              className={`main-nav-tab ${activeMainTab === 'sql_examples' ? 'active' : ''}`}
              onClick={() => setActiveMainTab('sql_examples')}
            >
              <Code2 size={16} />
              <span>Mẫu Truy Vấn SQL (sql_examples.json)</span>
            </button> */}
          </div>
        </div>

        <div className="admin-nav-right">
          <a
            href="http://localhost:3000"
            target="_blank"
            rel="noreferrer"
            className="btn-pill-light"
            title="Mở giao diện Chatbot Người Dùng (Port 3000)"
          >
            <span>Mở User Chatbot (Port 3000)</span>
            <ExternalLink size={13} />
          </a>
        </div>
      </header>

      {/* Main Content Area */}
      <main className="admin-content-area">
        {activeMainTab === 'monitor' && <RealtimeLogView />}
        {activeMainTab === 'knowledge' && <KnowledgeManagerView />}
        {activeMainTab === 'schema' && <SchemaViewerView />}
        {activeMainTab === 'prompts' && <SystemPromptsView />}
        {/* {activeMainTab === 'sql_examples' && <SqlExamplesManagerView />} */}
      </main>
    </div>
  );
}
