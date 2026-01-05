// components/UploadReport/UploadReport.jsx
import React, { useState, useRef } from 'react';
import { useAppContext } from '../../context';
import './UploadReport.css';

const UploadReport = () => {
  const { state, loadDashboardData } = useAppContext();
  const [selectedFile, setSelectedFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [uploadStatus, setUploadStatus] = useState(null);
  const [uploadResult, setUploadResult] = useState(null);
  const fileInputRef = useRef(null);

  const handleFileSelect = (event) => {
    const file = event.target.files[0];
    if (file) {
      // Validate file type
      if (file.type !== 'application/pdf') {
        setUploadStatus({
          type: 'error',
          message: 'Please select a PDF file'
        });
        return;
      }
      
      // Validate file size (max 10MB)
      if (file.size > 10 * 1024 * 1024) {
        setUploadStatus({
          type: 'error',
          message: 'File size must be less than 10MB'
        });
        return;
      }

      setSelectedFile(file);
      setUploadStatus(null);
      setUploadResult(null);
    }
  };

  const handleUpload = async () => {
    if (!selectedFile) {
      setUploadStatus({
        type: 'error',
        message: 'Please select a file first'
      });
      return;
    }

    if (!state.customerId) {
      setUploadStatus({
        type: 'error',
        message: 'No customer ID found'
      });
      return;
    }

    setUploading(true);
    setUploadStatus({
      type: 'info',
      message: 'Uploading and processing report...'
    });

    try {
      const formData = new FormData();
      formData.append('file', selectedFile);

      const apiBaseUrl = process.env.REACT_APP_API_BASE_URL;
      const response = await fetch(
        `${apiBaseUrl}/api/customer/${state.customerId}/upload-report`,
        {
          method: 'POST',
          body: formData,
        }
      );

      if (!response.ok) {
        const errorText = await response.text();
        let errorMessage = 'Upload failed';
        try {
          const errorData = JSON.parse(errorText);
          errorMessage = errorData.error || errorData.message || 'Upload failed';
        } catch (e) {
          errorMessage = errorText || `Server error: ${response.status}`;
        }
        throw new Error(errorMessage);
      }

      const data = await response.json();

      if (data.success) {
        setUploadStatus({
          type: 'success',
          message: 'Report processed successfully!'
        });
        setUploadResult(data.data);

        // Reload dashboard data after successful upload
        setTimeout(() => {
          loadDashboardData();
        }, 2000);
      } else {
        throw new Error(data.error || 'Upload failed');
      }
    } catch (error) {
      console.error('Upload error:', error);
      setUploadStatus({
        type: 'error',
        message: error.message || 'Failed to upload report'
      });
      setUploadResult(null);
    } finally {
      setUploading(false);
    }
  };

  const handleReset = () => {
    setSelectedFile(null);
    setUploadStatus(null);
    setUploadResult(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const formatFileName = (name) => {
    if (name.length > 30) {
      return name.substring(0, 27) + '...';
    }
    return name;
  };

  return (
    <div className="upload-report-container">
      <div className="upload-card">
        <div className="upload-header">
          <svg className="upload-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
            <polyline points="17 8 12 3 7 8"></polyline>
            <line x1="12" y1="3" x2="12" y2="15"></line>
          </svg>
          <h3 className="upload-title">Upload New Report</h3>
        </div>

        <div className="upload-body">
          {!selectedFile ? (
            <div className="upload-zone" onClick={() => fileInputRef.current?.click()}>
              <svg className="upload-placeholder-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
                <polyline points="14 2 14 8 20 8"></polyline>
                <line x1="12" y1="18" x2="12" y2="12"></line>
                <line x1="9" y1="15" x2="15" y2="15"></line>
              </svg>
              <p className="upload-instructions">
                Click to select a PDF report
              </p>
              <p className="upload-hint">
                Maximum file size: 10MB
              </p>
            </div>
          ) : (
            <div className="file-selected">
              <div className="file-info">
                <svg className="file-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
                  <polyline points="14 2 14 8 20 8"></polyline>
                </svg>
                <div className="file-details">
                  <p className="file-name" title={selectedFile.name}>
                    {formatFileName(selectedFile.name)}
                  </p>
                  <p className="file-size">
                    {(selectedFile.size / 1024).toFixed(1)} KB
                  </p>
                </div>
              </div>
              <button 
                className="remove-file-btn" 
                onClick={handleReset}
                disabled={uploading}
                title="Remove file"
              >
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <line x1="18" y1="6" x2="6" y2="18"></line>
                  <line x1="6" y1="6" x2="18" y2="18"></line>
                </svg>
              </button>
            </div>
          )}

          <input
            ref={fileInputRef}
            type="file"
            accept=".pdf"
            onChange={handleFileSelect}
            style={{ display: 'none' }}
          />

          {uploadStatus && (
            <div className={`upload-status ${uploadStatus.type}`}>
              {uploadStatus.type === 'success' && (
                <svg className="status-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <polyline points="20 6 9 17 4 12"></polyline>
                </svg>
              )}
              {uploadStatus.type === 'error' && (
                <svg className="status-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <circle cx="12" cy="12" r="10"></circle>
                  <line x1="15" y1="9" x2="9" y2="15"></line>
                  <line x1="9" y1="9" x2="15" y2="15"></line>
                </svg>
              )}
              {uploadStatus.type === 'info' && (
                <div className="spinner"></div>
              )}
              <span>{uploadStatus.message}</span>
            </div>
          )}

          {uploadResult && (
            <div className="upload-results">
              <h4 className="results-title">Processing Results</h4>
              <div className="results-grid">
                <div className="result-item">
                  <span className="result-label">Bacteria Extracted:</span>
                  <span className="result-value">{uploadResult.bacteria_extracted}</span>
                </div>
                <div className="result-item">
                  <span className="result-label">Bacteria Scored:</span>
                  <span className="result-value">{uploadResult.bacteria_scored}</span>
                </div>
                <div className="result-item">
                  <span className="result-label">Domains Analyzed:</span>
                  <span className="result-value">{uploadResult.domains_scored}</span>
                </div>
              </div>
            </div>
          )}

          <div className="upload-actions">
            <button
              className="upload-btn primary"
              onClick={handleUpload}
              disabled={!selectedFile || uploading}
            >
              {uploading ? (
                <>
                  <div className="btn-spinner"></div>
                  Processing...
                </>
              ) : (
                <>
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
                    <polyline points="17 8 12 3 7 8"></polyline>
                    <line x1="12" y1="3" x2="12" y2="15"></line>
                  </svg>
                  Upload & Process
                </>
              )}
            </button>
            
            {selectedFile && !uploading && (
              <button
                className="upload-btn secondary"
                onClick={handleReset}
              >
                Clear
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default UploadReport;
