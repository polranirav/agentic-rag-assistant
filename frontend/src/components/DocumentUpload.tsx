import React, { useState, useRef, useEffect } from 'react';
import { Upload, FileText, X, CheckCircle, Loader, AlertCircle } from 'lucide-react';
import { api } from '../utils/api';
import '../styles/simple.css';

interface Document {
  filename: string;
  file_type: string;
  file_size: number;
  uploaded_at: string;
}

export const DocumentUpload: React.FC = () => {
  const [documents, setDocuments] = useState<Document[]>([]);
  const [uploading, setUploading] = useState(false);
  const [ingesting, setIngesting] = useState(false);
  const [uploadStatus, setUploadStatus] = useState<{ type: 'success' | 'error'; message: string } | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Load documents on mount
  useEffect(() => {
    loadDocuments();
  }, []);

  const loadDocuments = async () => {
    try {
      const response = await api.get<Document[]>('/api/upload/documents');
      setDocuments(response.data);
    } catch (error) {
      console.error('Error loading documents:', error);
    }
  };

  const handleFileSelect = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const files = event.target.files;
    if (!files || files.length === 0) return;

    setUploading(true);
    setUploadStatus(null);

    const totalFiles = files.length;
    let successCount = 0;
    let failCount = 0;

    // Upload files in parallel
    const uploadPromises = Array.from(files).map(async (file) => {
      const formData = new FormData();
      formData.append('file', file);

      try {
        await api.post('/api/upload/', formData, {
          headers: {
            'Content-Type': 'multipart/form-data',
          },
        });
        successCount++;
        return { success: true, name: file.name };
      } catch (error: any) {
        failCount++;
        return { success: false, name: file.name, error: error.response?.data?.detail || 'Upload failed' };
      }
    });

    await Promise.all(uploadPromises);
    await loadDocuments(); // Refresh list

    // Show result
    if (failCount === 0) {
      setUploadStatus({
        type: 'success',
        message: `Successfully uploaded ${successCount} file${successCount > 1 ? 's' : ''}!`
      });
    } else if (successCount === 0) {
      setUploadStatus({
        type: 'error',
        message: `Failed to upload ${failCount} file${failCount > 1 ? 's' : ''}`
      });
    } else {
      setUploadStatus({
        type: 'success',
        message: `Uploaded ${successCount} file${successCount > 1 ? 's' : ''}, ${failCount} failed`
      });
    }

    // Clear file input
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
    setUploading(false);
  };

  const handleIngest = async () => {
    setIngesting(true);
    setUploadStatus(null);

    try {
      const response = await api.post('/api/upload/ingest');
      setUploadStatus({ type: 'success', message: 'Documents ingested successfully! You can now query them.' });
    } catch (error: any) {
      setUploadStatus({
        type: 'error',
        message: error.response?.data?.detail || 'Ingestion failed. Please check server logs.',
      });
    } finally {
      setIngesting(false);
    }
  };

  const handleDelete = async (filename: string) => {
    // Optimistic UI update - remove from list immediately
    const previousDocs = documents;
    setDocuments(docs => docs.filter(d => d.filename !== filename));
    setUploadStatus({ type: 'success', message: `Deleting ${filename}...` });

    try {
      // Encode filename to handle special characters in URL
      const encodedFilename = encodeURIComponent(filename);
      await api.delete(`/api/upload/documents/${encodedFilename}`);
      setUploadStatus({ type: 'success', message: `Deleted ${filename}` });
    } catch (error: any) {
      // Revert on error
      console.error('Delete error:', error);
      setDocuments(previousDocs);
      setUploadStatus({
        type: 'error',
        message: error.response?.data?.detail || 'Delete failed. Please try again.',
      });
    }
  };

  const formatFileSize = (bytes: number): string => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  return (
    <div className="simple-upload-section">
      <div className="simple-upload-header">
        <h2>📁 Document Management</h2>
        <p>Upload documents (PDF, TXT, MD, DOCX, CSV, JSON) to build your knowledge base</p>
      </div>

      {/* Upload Area */}
      <div className="simple-upload-area">
        <input
          ref={fileInputRef}
          type="file"
          accept=".pdf,.txt,.md,.docx,.csv,.json"
          onChange={handleFileSelect}
          multiple
          style={{ display: 'none' }}
        />
        <button
          className="simple-upload-btn"
          onClick={() => fileInputRef.current?.click()}
          disabled={uploading}
        >
          {uploading ? (
            <>
              <Loader className="simple-spinner" size={18} />
              Uploading...
            </>
          ) : (
            <>
              <Upload size={18} />
              Choose Files to Upload
            </>
          )}
        </button>
        <p className="simple-upload-hint">
          Drag & drop or click to select multiple files (PDF, TXT, MD, DOCX, CSV, JSON)
        </p>
      </div>

      {/* Status Message */}
      {uploadStatus && (
        <div className={`simple-status ${uploadStatus.type}`}>
          {uploadStatus.type === 'success' ? (
            <CheckCircle size={16} />
          ) : (
            <AlertCircle size={16} />
          )}
          <span>{uploadStatus.message}</span>
        </div>
      )}

      {/* Documents List */}
      {documents.length > 0 && (
        <div>
          <div className="simple-documents-header">
            <h3>📚 Uploaded Documents ({documents.length})</h3>
            <button
              className="simple-send-btn"
              onClick={handleIngest}
              disabled={ingesting}
            >
              {ingesting ? (
                <>
                  <Loader className="simple-spinner" size={14} />
                  Processing...
                </>
              ) : (
                <>
                  <FileText size={14} />
                  Ingest All Documents
                </>
              )}
            </button>
          </div>

          <div className="simple-documents-grid">
            {documents.map((doc, index) => (
              <div key={index} className="simple-document-card">
                <div className="simple-document-icon">
                  <FileText size={20} />
                </div>
                <div className="simple-document-info">
                  <div className="simple-document-name">{doc.filename}</div>
                  <div className="simple-document-meta">
                    <span className="simple-document-type">{doc.file_type}</span>
                    <span className="simple-document-size">{formatFileSize(doc.file_size)}</span>
                  </div>
                </div>
                <button
                  className="simple-delete-btn"
                  onClick={() => handleDelete(doc.filename)}
                  title="Delete document"
                >
                  <X size={14} />
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      {documents.length === 0 && (
        <div className="simple-empty-state">
          <FileText size={40} />
          <p>No documents uploaded yet</p>
          <p className="simple-empty-hint">
            Upload your first document to start building your knowledge base
          </p>
        </div>
      )}
    </div>
  );
};
