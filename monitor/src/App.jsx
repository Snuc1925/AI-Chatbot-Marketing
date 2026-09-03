import React, { useState } from 'react';
import { RealtimeLogView } from './components/RealtimeLogView';
import { KnowledgeManagerView } from './components/KnowledgeManagerView';
import { SqlExamplesManagerView } from './components/SqlExamplesManagerView';
import { Activity, BookOpen, Code2, Layers, Terminal, ExternalLink } from 'lucide-react';

export default function App() {
  const [activeMainTab, setActiveMainTab] = useState('monitor'); // 'monitor' | 'knowledge' | 'sql_examples'

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
              className={`main-nav-tab ${activeMainTab === 'sql_examples' ? 'active' : ''}`}
              onClick={() => setActiveMainTab('sql_examples')}
            >
              <Code2 size={16} />
              <span>Mẫu Truy Vấn SQL (sql_examples.json)</span>
            </button>
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
        {activeMainTab === 'sql_examples' && <SqlExamplesManagerView />}
      </main>
    </div>
  );
}
