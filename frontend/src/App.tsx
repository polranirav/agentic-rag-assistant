import React, { useState } from 'react';
import { ChatInterface } from './components/ChatInterface';
import { DocumentUpload } from './components/DocumentUpload';
import { Dashboard } from './components/Dashboard';
import { MessageSquare, Upload, BarChart3 } from 'lucide-react';
import './App.css';
import './styles/simple.css';

function App() {
  const [activeView, setActiveView] = useState<'chat' | 'documents' | 'dashboard'>('chat');

  return (
    <div className="simple-app">
      <div className="simple-header">
        <div className="simple-header-content">
          <div>
            <h1>🚀 Agentic RAG Knowledge Assistant</h1>
            <p>Upload Documents • AI Analysis • Intelligent Answers</p>
          </div>
          <div className="simple-tabs">
            <button
              className={`simple-tab ${activeView === 'chat' ? 'active' : ''}`}
              onClick={() => setActiveView('chat')}
            >
              <MessageSquare size={16} /> Chat
            </button>
            <button
              className={`simple-tab ${activeView === 'documents' ? 'active' : ''}`}
              onClick={() => setActiveView('documents')}
            >
              <Upload size={16} /> Documents
            </button>
            <button
              className={`simple-tab ${activeView === 'dashboard' ? 'active' : ''}`}
              onClick={() => setActiveView('dashboard')}
            >
              <BarChart3 size={16} /> Dashboard
            </button>
          </div>
        </div>
      </div>
      {activeView === 'chat' && <ChatInterface />}
      {activeView === 'documents' && <DocumentUpload />}
      {activeView === 'dashboard' && <Dashboard />}
    </div>
  );
}

export default App;
