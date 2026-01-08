// pages/Analysis/Analysis.jsx - Updated to work with new backend structure
import React from 'react';
import { useAppContext } from '../../context';
import './Analysis.css';

const Analysis = () => {
  const { state, openModal } = useAppContext();
  const { user, healthData, loading } = state;

  // Return blank while loading to keep it clean
  if (loading) {
    return <div className="content-section"></div>;
  }

  // Helper function to format numbers to 1 decimal place
  const formatScore = (score) => {
    if (score === null || score === undefined || isNaN(score)) {
      return '0.0';
    }
    return Number(score).toFixed(1);
  };

  // Generate domains array from healthData.domains
  const generateDomainsArray = () => {
    if (!healthData.domains) {
      return [];
    }

    const domainConfigs = {
      overall: {
        title: 'Overall Health',
        comment: 'Your overall health indicators show positive trends with room for improvement in specific areas.',
        modalFile: 'Overall_Analysis_Report.html'
      },
      liver: {
        title: 'Liver Health',
        comment: 'Liver health markers show room for improvement. Focus on beneficial dietary changes.',
        modalFile: 'Liver Health.html'
      },
      aging: {
        title: 'Aging',
        comment: 'Aging markers indicate need for lifestyle modifications and targeted interventions.',
        modalFile: 'Aging_Health.html'
      },
      skin: {
        title: 'Skin Health',
        comment: 'Moderate skin health markers. Consider dietary adjustments to improve skin microbiome.',
        modalFile: 'Skin Health.html'
      },
      cognitive: {
        title: 'Cognitive Health',
        comment: 'Strong cognitive health markers present. Continue maintaining current dietary habits.',
        modalFile: 'Cognitive_Health_Card.html'
      },
      gut: {
        title: 'Gut Health',
        comment: 'Good gut health indicators with opportunity for enhancing microbial diversity.',
        modalFile: 'Gut Health.html'
      },
      heart: {
        title: 'Heart Health',
        comment: 'Good cardiovascular health indicators with opportunities for optimization.',
        modalFile: 'Heart_Health.html'
      }
    };

    // Create domains array from healthData.domains
    return Object.entries(healthData.domains).map(([domainId, domainData]) => {
      const config = domainConfigs[domainId] || {
        title: domainId.charAt(0).toUpperCase() + domainId.slice(1) + ' Health',
        comment: `Health markers for ${domainId} domain.`,
        modalFile: `${domainId}_health.html`
      };

      return {
        id: domainId,
        title: config.title,
        score: formatScore(domainData.score),
        diversity: formatScore(domainData.diversity),
        status: domainData.status || 'unknown',
        comment: config.comment,
        modalFile: config.modalFile
      };
    });
  };

  // Generate domains array
  const domains = generateDomainsArray();

  const getStatusLabel = (status) => {
    switch (status) {
      case 'good':
        return 'Good Health Status';
      case 'warning':
        return 'Needs Attention';
      case 'poor':
        return 'Requires Improvement';
      case 'critical':
        return 'Needs Immediate Action';
      default:
        return 'Health Status';
    }
  };

  const handleExploreClick = (domain) => {
    // Pass the domain ID for API lookup
    openModal(domain.id, `${domain.title} Details`);
  };

  // Show loading or error state if no domains
  if (!healthData.domains || Object.keys(healthData.domains).length === 0) {
    return (
      <div id="analysis" className="content-section">
        <div className="page-title-container">
          <h1 className="page-title">Analysis by Health Domain</h1>
          <div className="last-updated">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <circle cx="12" cy="12" r="10"></circle>
              <polyline points="12 6 12 12 16 14"></polyline>
            </svg>
            Last updated: {user.lastUpdated}
          </div>
        </div>
        
        <div className="loading-message">
          <p>Loading health domain analysis...</p>
        </div>
      </div>
    );
  }

  return (
    <div id="analysis" className="content-section">
      <div className="page-title-container">
        <h1 className="page-title">Analysis by Health Domain</h1>
        <div className="last-updated">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <circle cx="12" cy="12" r="10"></circle>
            <polyline points="12 6 12 12 16 14"></polyline>
          </svg>
          Last updated: {user.lastUpdated}
        </div>
      </div>
      
      <div className="domains-grid">
        {domains.map((domain) => (
          <div key={domain.id} className={`domain-card status-${domain.status}`}>
            <div className="status-bar"></div>
            <span className="status-label">{getStatusLabel(domain.status)}</span>
            <h2 className="domain-title">{domain.title}</h2>
            <div className="metric-row">
              <span className="metric-label">Score:</span>
              <span className="metric-value">{domain.score}</span>
            </div>
            <div className="metric-row">
              <span className="metric-label">Diversity:</span>
              <span className="metric-value">{domain.diversity}</span>
            </div>
            <p className="domain-comment">{domain.comment}</p>
            <button 
              className="explore-button"
              onClick={() => handleExploreClick(domain)}
            >
              Explore Details →
            </button>
          </div>
        ))}
      </div>
      
      {/* Summary section */}
      {/* <div className="analysis-summary">
        <h3>Analysis Summary</h3>
        <p>
          You have {domains.length} health domains analyzed. 
          {domains.filter(d => d.status === 'good').length > 0 && 
            ` ${domains.filter(d => d.status === 'good').length} performing well,`}
          {domains.filter(d => d.status === 'warning').length > 0 && 
            ` ${domains.filter(d => d.status === 'warning').length} need attention,`}
          {domains.filter(d => d.status === 'poor').length > 0 && 
            ` ${domains.filter(d => d.status === 'poor').length} require improvement.`}
        </p>
      </div> */}
    </div>
  );
};

export default Analysis;