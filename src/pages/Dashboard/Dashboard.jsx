// pages/Dashboard/Dashboard.jsx - Updated to work with new backend structure
import React, { useState } from 'react';
import { useAppContext } from '../../context';
import Gauge from '../../components/Charts/Gauge';
import UploadReport from '../../components/UploadReport/UploadReport';
import './Dashboard.css';

const Dashboard = () => {
  const { state, openModal } = useAppContext();
  const { user, healthData, loading } = state;
  const [isExpanded, setIsExpanded] = useState(false);

  // Show loading indicator while fetching customer data
  if (loading) {
    return (
      <div className="dashboard-loading">
        <div className="loading-spinner"></div>
        <p className="loading-text">Loading your microbiome data...</p>
      </div>
    );
  }

  // Helper function to format numbers to 1 decimal place
  const formatScore = (score) => {
    if (score === null || score === undefined || isNaN(score)) {
      return 0;
    }
    return Number(Number(score).toFixed(1)); // Ensure it's a number for the Gauge
  };

  // Format date as "Dec 26, 2025 12:30 PM"
  const formatLastUpdated = (dateString) => {
    if (!dateString) return 'N/A';
    
    try {
      const date = new Date(dateString);
      const options = { 
        year: 'numeric', 
        month: 'short', 
        day: 'numeric',
        hour: 'numeric',
        minute: '2-digit',
        hour12: true
      };
      return date.toLocaleString('en-US', options);
    } catch (error) {
      console.error('Error formatting date:', error);
      return dateString;
    }
  };

  // Get diversity score - check both overall domain and top-level
  const getDiversityScore = () => {
    // First try to get from overall domain (new structure)
    if (healthData.domains?.overall?.diversity !== undefined) {
      return formatScore(healthData.domains.overall.diversity);
    }
    // Fallback to top-level diversity score (old structure)
    return formatScore(healthData.diversityScore);
  };

  // Sort domains by status and score to get actual good/bad domains
  const sortDomainsByPerformance = () => {
    if (!healthData.domains) return { good: [], bad: [] };

    const domainEntries = Object.entries(healthData.domains)
      .filter(([key]) => key !== 'overall') // Exclude overall from domain lists
      .map(([id, data]) => ({
        id,
        label: formatDomainLabel(id),
        score: data.score,
        status: data.status,
        icon: getDomainIcon(id)
      }));

    // Sort by score (highest first for good, lowest first for bad)
    const goodDomains = domainEntries
      .filter(domain => domain.status === 'good')
      .sort((a, b) => b.score - a.score)
      .slice(0, 3);

    const badDomains = domainEntries
      .filter(domain => domain.status === 'poor' || domain.status === 'warning')
      .sort((a, b) => a.score - b.score) // Lowest scores first
      .slice(0, 3);

    return { good: goodDomains, bad: badDomains };
  };

  const formatDomainLabel = (domainId) => {
    const labels = {
      heart: 'Heart Health',
      gut: 'Gut Health', 
      cognitive: 'Cognitive Health',
      liver: 'Liver Health',
      skin: 'Skin Health',
      aging: 'Aging'
    };
    return labels[domainId] || domainId.charAt(0).toUpperCase() + domainId.slice(1) + ' Health';
  };

  const getDomainIcon = (domainId) => {
    const icons = {
      heart: (
        <path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z"/>
      ),
      gut: (
        <>
          <path d="M18 8h1a4 4 0 0 1 0 8h-1"/>
          <path d="M2 8h16v9a4 4 0 0 1-4 4H6a4 4 0 0 1-4-4V8z"/>
          <line x1="6" y1="1" x2="6" y2="4"/>
          <line x1="10" y1="1" x2="10" y2="4"/>
          <line x1="14" y1="1" x2="14" y2="4"/>
        </>
      ),
      cognitive: (
        <>
          <circle cx="12" cy="12" r="10"/>
          <path d="M12 16a4 4 0 1 0 0-8 4 4 0 0 0 0 8z"/>
        </>
      ),
      liver: (
        <path d="M20.5 7.27683C20.5 11.4164 12 19 12 19C12 19 3.5 11.4164 3.5 7.27683C3.5 3.13727 7.35786 0 12 0C16.6421 0 20.5 3.13727 20.5 7.27683Z"/>
      ),
      skin: (
        <>
          <circle cx="12" cy="12" r="10"/>
          <path d="M8 15h8"/>
          <path d="M8 9h8"/>
        </>
      ),
      aging: (
        <>
          <circle cx="12" cy="12" r="10"/>
          <path d="M12 16v-4"/>
          <path d="M12 8h.01"/>
        </>
      )
    };
    return icons[domainId] || icons.heart; // Default fallback
  };

  const toggleReadMore = () => {
    setIsExpanded(!isExpanded);
  };

  const handleDomainClick = (domainId, domainLabel) => {
    // Pass the domain ID for API lookup
    openModal(domainId, `${domainLabel} Details`);
  };

  // Get sorted domains
  const { good: goodDomains, bad: badDomains } = sortDomainsByPerformance();
  
  // Format the diversity score for display and Gauge component
  const formattedDiversityScore = getDiversityScore();

  return (
    <div id="current-report" className="content-section">
      <div className="page-title-container">
        <h1 className="page-title">Microbiome Health Dashboard</h1>
        <div className="last-updated">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <circle cx="12" cy="12" r="10"></circle>
            <polyline points="12 6 12 12 16 14"></polyline>
          </svg>
          Last updated: {formatLastUpdated(healthData.last_updated)}
        </div>
      </div>

      {/* Upload Report Section */}
      <UploadReport />
      
      <div className="analysis-layout">
        <div className="analysis-card">
          <h2 className="meter-title">Microbiome Diversity</h2>
          <div className="gauge-container">
            <Gauge 
              value={formattedDiversityScore} // ✅ Properly formatted number
              label="DIVERSITY SCORE" 
              color="#00BFA5" 
            />
          </div>

          <div className="diversity-explanation">
            <p className="explanation-text">
              Microbiome diversity refers to the variety and abundance of different microbial species in your gut. Higher diversity is generally associated with better health outcomes and a more resilient gut ecosystem.
              <span className={`hidden-text ${isExpanded ? 'show' : ''}`}>
                {' '}It helps improve digestion, strengthen immunity, and reduce inflammation. Your score of {formattedDiversityScore.toFixed(1)} indicates moderate diversity, with room for improvement through dietary changes and lifestyle adjustments.
              </span>
            </p>
            <button className="read-more-btn" onClick={toggleReadMore}>
              {isExpanded ? 'Read Less' : 'Read More'}
            </button>
          </div>
        </div>

        <div className="analysis-card health-areas">
          <div className="domains-container">
            <div className="health-section bad-domains">
              <h2 className="domains-title">Areas Needing Attention</h2>
              
              <div className="health-items-wrapper">
                {badDomains.length > 0 ? badDomains.map((domain) => (
                  <div 
                    key={domain.id}
                    className="health-item bad-area" 
                    onClick={() => handleDomainClick(domain.id, domain.label)}
                  >
                    <div className="health-icon">
                      <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                        {domain.icon}
                      </svg>
                    </div>
                    <span className="health-text">{domain.label}</span>
                  </div>
                )) : (
                  <div className="no-domains-message">
                    <p>All your health domains are performing well! 🎉</p>
                  </div>
                )}
              </div>
            </div>
            
            <div className="health-section good-domains">
              <h2 className="domains-title">Strong Performing Areas</h2>
              
              <div className="health-items-wrapper">
                {goodDomains.length > 0 ? goodDomains.map((domain) => (
                  <div 
                    key={domain.id}
                    className="health-item good-area" 
                    onClick={() => handleDomainClick(domain.id, domain.label)}
                  >
                    <div className="health-icon">
                      <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                        {domain.icon}
                      </svg>
                    </div>
                    <span className="health-text">{domain.label}</span>
                  </div>
                )) : (
                  <div className="no-domains-message">
                    <p>Focus on improving your health domains to see them here.</p>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Dashboard;