// pages/Download/Download.jsx
import React, { useState, useEffect } from 'react';
import { useAppContext } from '../../context';
import { useDownload } from '../../hooks/useDownload';
import './Download.css';

const Download = () => {
  const { state } = useAppContext();
  const { user, loading } = state;
  const [reportType, setReportType] = useState('full');
  const [selectedDomains, setSelectedDomains] = useState({
    cognitive: false,
    aging: false,
    skin: false,
    gut: false,
    heart: false
  });
  const [statusMessage, setStatusMessage] = useState('');
  const [isSuccess, setIsSuccess] = useState(false);

  const { isLoading, error, downloadReport } = useDownload();

  // Debug logging to understand user object structure
  useEffect(() => {
    // console.log('Debug - Full state:', state);
    // console.log('Debug - User object:', user);
    // console.log('Debug - Available user properties:', Object.keys(user || {}));
    // console.log('Debug - Potential customer IDs:', {
    //   'user.user_id': user?.user_id,
    //   'user.customer_id': user?.customer_id,
    //   'user.userId': user?.userId,
    //   'state.customerId': state?.customerId,
    //   'state.userId': state?.userId
    // });
  }, [state, user]);

  useEffect(() => {
    if (error) {
      setStatusMessage(error);
      setIsSuccess(false);
    }
  }, [error]);

  // Return blank while loading to keep it clean
  if (loading) {
    return <div className="content-section"></div>;
  }

  const handleReportTypeChange = (type) => {
    setReportType(type);
  };

  const handleDomainChange = (domain, checked) => {
    setSelectedDomains(prev => ({
      ...prev,
      [domain]: checked
    }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    try {
      // Try multiple possible sources for customer ID with better fallback
      const customerId = user?.user_id || 
                        user?.customer_id || 
                        user?.userId || 
                        state?.customerId || 
                        state?.userId ||
                        1; // Fallback to customer ID 1 for testing
      
      // console.log('Looking for customer ID in:', {
      //   'user.user_id': user?.user_id,
      //   'user.customer_id': user?.customer_id,
      //   'user.userId': user?.userId,
      //   'state.customerId': state?.customerId,
      //   'state.userId': state?.userId,
      //   'using': customerId
      // });
      
      if (!customerId) {
        // console.error('No customer ID found in user context');
        setStatusMessage('User session error. Please refresh the page and try again.');
        setIsSuccess(false);
        return;
      }

      // console.log(`Attempting download with customer ID: ${customerId}`);

      if (reportType === 'full') {
        await downloadReport('full', null, customerId);
        setStatusMessage('Full report generated successfully!');
        setIsSuccess(true);
      } else {
        const domains = Object.keys(selectedDomains).filter(
          domain => selectedDomains[domain]
        );
        
        if (domains.length === 0) {
          setStatusMessage('Please select at least one domain');
          setIsSuccess(false);
          return;
        }

        await downloadReport('domain', domains, customerId);
        setStatusMessage('Domain-specific reports generated successfully!');
        setIsSuccess(true);
      }
    } catch (error) {
      // console.error('Download error:', error);
      setStatusMessage(error.message || 'Error generating report. Please try again.');
      setIsSuccess(false);
    }

    // Clear status message after 5 seconds instead of 3
    setTimeout(() => {
      setStatusMessage('');
      setIsSuccess(false);
    }, 5000);
  };

  const domains = [
    { id: 'cognitive', label: 'Cognitive Health' },
    { id: 'aging', label: 'Aging Health' },
    { id: 'skin', label: 'Skin Health' },
    { id: 'gut', label: 'Gut Health' },
    { id: 'heart', label: 'Heart Health' }
  ];

  return (
    <div id="download" className="content-section">
      <div className="page-title-container">
        <h1 className="page-title">Download Reports</h1>
        <div className="last-updated">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <circle cx="12" cy="12" r="10"></circle>
            <polyline points="12 6 12 12 16 14"></polyline>
          </svg>
          Last updated: {user?.lastUpdated || user?.last_updated || 'N/A'}
        </div>
      </div>
      
      <div className="download-section">
        <h2 className="section-title">Download Analysis Report</h2>
        
       
        
        <form onSubmit={handleSubmit}>
          <div className="radio-group">
            <label className="radio-option">
              <input 
                type="radio" 
                name="reportType" 
                value="full" 
                checked={reportType === 'full'}
                onChange={(e) => handleReportTypeChange(e.target.value)}
              />
              <span>Full Analysis Report</span>
            </label>
            
            <label className="radio-option">
              <input 
                type="radio" 
                name="reportType" 
                value="domain"
                checked={reportType === 'domain'}
                onChange={(e) => handleReportTypeChange(e.target.value)}
              />
              <span>Domain Specific Report</span>
            </label>

            {reportType === 'domain' && (
              <div className="checkbox-group">
                {domains.map((domain) => (
                  <label key={domain.id} className="checkbox-option">
                    <input 
                      type="checkbox" 
                      name="domains" 
                      value={domain.id}
                      checked={selectedDomains[domain.id]}
                      onChange={(e) => handleDomainChange(domain.id, e.target.checked)}
                    />
                    <span>{domain.label}</span>
                  </label>
                ))}
              </div>
            )}
          </div>

          <button type="submit" className="download-btn" disabled={isLoading}>
            {isLoading ? 'Generating Report...' : 'Download Report'}
            {isLoading && <span className="loading"></span>}
          </button>
          
          {statusMessage && (
            <div className={`status-message ${isSuccess ? 'success' : 'error'}`}>
              {statusMessage}
            </div>
          )}
        </form>
      </div>
    </div>
  );
};

export default Download;