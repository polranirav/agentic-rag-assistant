import React, { useState, useEffect } from 'react';
import { FileText, MessageSquare, TrendingUp, Zap, BarChart3, Activity } from 'lucide-react';
import { api } from '../utils/api';
import '../styles/simple.css';

interface DocumentStats {
  total: number;
  byType: { [key: string]: number };
  totalSize: number;
}

interface QueryStats {
  total: number;
  byIntent: { [key: string]: number };
  avgResponseTime: number;
}

export const Dashboard: React.FC = () => {
  const [documents, setDocuments] = useState<DocumentStats | null>(null);
  const [queries, setQueries] = useState<QueryStats | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchDashboardData();
  }, []);

  const fetchDashboardData = async () => {
    try {
      // Fetch documents
      const docsResponse = await api.get('/api/upload/documents');
      const docs = docsResponse.data;
      
      const docStats: DocumentStats = {
        total: docs.length,
        byType: {},
        totalSize: 0,
      };

      docs.forEach((doc: any) => {
        docStats.byType[doc.file_type] = (docStats.byType[doc.file_type] || 0) + 1;
        docStats.totalSize += doc.file_size;
      });

      setDocuments(docStats);

      // Fetch query metrics (from backend metrics endpoint)
      try {
        const metricsResponse = await api.get('/metrics');
        const metrics = metricsResponse.data;
        
        const queryStats: QueryStats = {
          total: metrics.total_queries || 0,
          byIntent: metrics.intent_distribution || {},
          avgResponseTime: metrics.avg_latency_ms || 0,
        };
        
        setQueries(queryStats);
      } catch (error) {
        console.error('Error fetching metrics:', error);
        setQueries({
          total: 0,
          byIntent: {},
          avgResponseTime: 0,
        });
      }

      setLoading(false);
    } catch (error) {
      console.error('Error fetching dashboard data:', error);
      setLoading(false);
    }
  };

  const formatFileSize = (bytes: number): string => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  if (loading) {
    return (
      <div className="simple-empty-state">
        <Activity className="simple-spinner" size={32} />
        <p>Loading dashboard...</p>
      </div>
    );
  }

  return (
    <div className="simple-upload-section">
      <div className="simple-upload-header">
        <h2>📊 Analytics Dashboard</h2>
        <p>Overview of your documents and query statistics</p>
      </div>

      {/* Stats Grid */}
      <div className="simple-stats-grid">
        <div className="simple-stat-card">
          <div className="simple-stat-icon">
            <FileText size={24} />
          </div>
          <div className="simple-stat-content">
            <div className="simple-stat-value">{documents?.total || 0}</div>
            <div className="simple-stat-label">Total Documents</div>
          </div>
        </div>

        <div className="simple-stat-card">
          <div className="simple-stat-icon">
            <MessageSquare size={24} />
          </div>
          <div className="simple-stat-content">
            <div className="simple-stat-value">{queries?.total || 0}</div>
            <div className="simple-stat-label">Total Queries</div>
          </div>
        </div>

        <div className="simple-stat-card">
          <div className="simple-stat-icon">
            <TrendingUp size={24} />
          </div>
          <div className="simple-stat-content">
            <div className="simple-stat-value">
              {queries?.avgResponseTime ? `${queries.avgResponseTime.toFixed(0)}ms` : '0ms'}
            </div>
            <div className="simple-stat-label">Avg Response Time</div>
          </div>
        </div>

        <div className="simple-stat-card">
          <div className="simple-stat-icon">
            <Zap size={24} />
          </div>
          <div className="simple-stat-content">
            <div className="simple-stat-value">
              {documents?.totalSize ? formatFileSize(documents.totalSize) : '0 B'}
            </div>
            <div className="simple-stat-label">Total Size</div>
          </div>
        </div>
      </div>

      {/* Document Types */}
      {documents && documents.byType && Object.keys(documents.byType).length > 0 && (
        <div className="simple-dashboard-section">
          <h3>📁 Documents by Type</h3>
          <div className="simple-documents-grid">
            {Object.entries(documents.byType).map(([type, count]) => (
              <div key={type} className="simple-document-card">
                <div className="simple-document-icon">
                  <FileText size={20} />
                </div>
                <div className="simple-document-info">
                  <div className="simple-document-name">{type} Files</div>
                  <div className="simple-document-meta">
                    <span className="simple-document-type">{count} documents</span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Query Intent Distribution */}
      {queries && queries.byIntent && Object.keys(queries.byIntent).length > 0 && (
        <div className="simple-dashboard-section">
          <h3>🎯 Query Intent Distribution</h3>
          <div className="simple-intent-list">
            {Object.entries(queries.byIntent).map(([intent, count]) => (
              <div key={intent} className="simple-intent-item">
                <div className="simple-intent-name">
                  {intent.replace('_', ' ').replace(/\b\w/g, (l) => l.toUpperCase())}
                </div>
                <div className="simple-intent-bar">
                  <div
                    className="simple-intent-fill"
                    style={{
                      width: `${(count as number / queries.total) * 100}%`,
                    }}
                  />
                </div>
                <div className="simple-intent-count">{count}</div>
              </div>
            ))}
          </div>
        </div>
      )}

      {(!documents || documents.total === 0) && (!queries || queries.total === 0) && (
        <div className="simple-empty-state">
          <BarChart3 size={40} />
          <p>No data available yet</p>
          <p className="simple-empty-hint">
            Upload documents and start querying to see analytics
          </p>
        </div>
      )}
    </div>
  );
};
