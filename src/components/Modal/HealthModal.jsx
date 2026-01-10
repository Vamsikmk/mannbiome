// components/Modal/HealthModal.jsx - Fixed to handle real API data structure
import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { useAppContext } from '../../context';
import apiService from '../../services/api';
import HealthMetrics from './HealthMetrics';
import SpeciesCarousel from './SpeciesCarousel';
import PathwayCarousel from './PathwayCarousel';
import RecommendationsSection from './RecommendationsSection';
import ClinicalTrialsSection from './ClinicalTrialsSection';
import './HealthModal.css';

const HealthModal = () => {
  const { state, closeModal } = useAppContext();
  const [modalData, setModalData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  // Check if this is a detailed health domain modal
  const isDetailedDomainModal = state.modal.isOpen && 
    typeof state.modal.content === 'string' && 
    ['liver', 'aging', 'skin', 'cognitive', 'gut', 'heart'].includes(state.modal.content);

  // Check if modal content is already customer-specific data object
  const isCustomerDataModal = state.modal.isOpen && 
    typeof state.modal.content === 'object' && 
    state.modal.content !== null &&
    (state.modal.content.domain_info || state.modal.content.domain);

  // Domain ID mapping
  const domainIdMap = useMemo(() => ({
    gut: 1,
    liver: 2, 
    heart: 3,
    skin: 4,
    cognitive: 5,
    aging: 6
  }), []);

  // Fetch detailed domain data with customer-specific support
  const fetchDetailedDomainData = useCallback(async (domainName) => {
    setLoading(true);
    setError(null);
    
    try {
      // console.log(`Fetching customer-specific data for ${domainName} domain (Customer ${state.customerId})`);
      
      // Use the enhanced API service that supports customer-specific data
      const response = await apiService.getCustomerDomainBacteria(state.customerId, domainName);
      
      if (response.success) {
        // console.log('Customer-specific modal data received:', response);
        // console.log(`Data source: ${response.source}`);
        
        // Set the customer-specific data
        setModalData(response.data);
        
      } else {
        throw new Error(response.error || 'Failed to load domain data');
      }
    } catch (error) {
      // console.error(`Error loading customer-specific data for ${domainName}:`, error);
      setError(error.message);
    } finally {
      setLoading(false);
    }
  }, [state.customerId, apiService]);

  // Handle modal data changes
  useEffect(() => {
    if (isCustomerDataModal) {
      // Modal content is already a data object, use it directly
      // console.log('Using pre-loaded customer data object');
      setModalData(state.modal.content);
    } else if (isDetailedDomainModal) {
      // Need to fetch data for this domain
      fetchDetailedDomainData(state.modal.content);
    } else {
      // Regular modal, clear modal data
      setModalData(null);
    }
  }, [state.modal.content, isCustomerDataModal, isDetailedDomainModal, fetchDetailedDomainData]);

  // Handle backdrop click
  const handleBackdropClick = useCallback((e) => {
    if (e.target === e.currentTarget) {
      closeModal();
    }
  }, [closeModal]);

  // Don't render if modal is not open
  if (!state.modal.isOpen) {
    return null;
  }

  // Render detailed domain content
  const renderDetailedDomainContent = () => {
    if (loading) {
      return (
        <div className="modal-loading">
          <div className="loading-spinner"></div>
          <p>Loading health data...</p>
        </div>
      );
    }

    if (error) {
      return (
        <div className="modal-error">
          <h3>Error Loading Data</h3>
          <p>{error}</p>
          <button onClick={closeModal} className="btn-primary">Close</button>
        </div>
      );
    }

    if (!modalData) {
      return (
        <div className="modal-loading">
          <p>No data available</p>
        </div>
      );
    }

    // Handle both domain_info and domain structures
    const domainInfo = modalData.domain_info || modalData.domain;
    // Add this debug line right after line 95 (before the domainName assignment)
    // console.log('🔍 Debug modal content:', state.modal.content, typeof state.modal.content);

    const domainName = typeof state.modal.content === 'string' ? 
  `${state.modal.content.charAt(0).toUpperCase() + state.modal.content.slice(1)} Health Details` :
  `${(modalData?.domain?.domain_name || 'health').charAt(0).toUpperCase() + (modalData?.domain?.domain_name || 'health').slice(1)} Health Details`;

    return (
      <div className="detailed-domain-content">
        {/* Back Button */}
        <button className="back-button" onClick={closeModal}>
          ← Back to Overview
        </button>

        {/* Page Title with Customer Info */}
        <h1 className="page-title">
          <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="#00BFA5" strokeWidth="2">
            <path d="M12 2a9 9 0 0 1 9 9c0 3.9-2.5 7.2-6 8.4v1.6a1 1 0 0 1-1 1H10a1 1 0 0 1-1-1v-1.6c-3.5-1.2-6-4.5-6-8.4a9 9 0 0 1 9-9z"/>
          </svg>
          {domainName}
          {domainInfo?.domain_name && (
            <span style={{ fontSize: '18px', color: '#666', fontWeight: 'normal', marginLeft: '12px' }}>
              {domainInfo.domain_name}
            </span>
          )}
        </h1>

        {/* Domain Stats Summary */}
        {domainInfo && (
          <div className="domain-stats-summary">
            <div className="stat-item">
              <span className="stat-label">Score: </span>
              <span className="stat-value">{domainInfo.score || 'N/A'}</span>
            </div>
            <div className="stat-item">
              <span className="stat-label">Diversity: </span>
              <span className="stat-value">{domainInfo.diversity || 'N/A'}</span>
            </div>
            <div className="stat-item">
              <span className="stat-label">Status: </span>
              <span className={`stat-value status-${domainInfo.status}`}>
                {domainInfo.status || 'Unknown'}
              </span>
            </div>
          </div>
        )}

        {/* Domain Comment */}
        {domainInfo?.comment && (
          <div className="domain-comment">
            <p>{domainInfo.comment}</p>
          </div>
        )}

        {/* Health Metrics */}
        {modalData.health_metrics && (
          <HealthMetrics 
            healthMetrics={modalData.health_metrics}
            domainName={domainInfo?.domain_id || state.modal.content}
          />
        )}

        {/* Species Carousel */}
        {modalData.species_carousel && (
          <SpeciesCarousel 
            speciesData={modalData.species_carousel}
            recommendations={modalData.recommendations}
            currentDomain={domainInfo?.domain_id || state.modal.content}
          />
        )}

        {/* Pathway Carousel */}
        {modalData.pathway_carousel && modalData.pathway_carousel.length > 0 && (
          <PathwayCarousel pathwayData={modalData.pathway_carousel} />
        )}

        {/* Recommendations Section */}
        {modalData.recommendations && (
          <RecommendationsSection recommendations={modalData.recommendations} />
        )}

        {/* Clinical Trials Section */}
        <ClinicalTrialsSection domainId={domainInfo?.domain_id || state.modal.content} />

        {/* Doctor's Remarks Section */}
        <div className="modal-section doctor-remarks-section">
          <h3 className="section-title">
            Remarks from your doctor (if any)
          </h3>
          <div className="doctor-remarks-content">
            {/* Empty space for doctor's remarks - can be made editable later */}
          </div>
        </div>

        {/* Clinical Notes */}
        {modalData.clinical_notes && (
          <div className="modal-section">
            <h3 className="section-title" style={{ color: '#2C3E50', marginBottom: '16px' }}>
              Clinical Assessment
            </h3>
            <div className="clinical-notes-content">
              <p>{modalData.clinical_notes}</p>
            </div>
          </div>
        )}

        {/* Disclaimer Section */}
        <div className="modal-section disclaimer-section">
          <h4 className="disclaimer-title">Disclaimer</h4>
          <p className="disclaimer-text">
            These recommendations are based on your current microbiome analysis and should be discussed 
            with your healthcare provider before making any changes to your regimen. Individual results may vary.
          </p>
        </div>
      </div>
    );
  };

  const renderRegularModalContent = () => {
    return (
      <div 
        className="modal-content-wrapper"
        dangerouslySetInnerHTML={{ __html: state.modal.content }}
      />
    );
  };

  return (
    <div className="modal-backdrop" onClick={handleBackdropClick}>
      <div className="modal-container">
        <div className="modal-header">
          <h2 className="modal-title">{state.modal.title}</h2>
          <button className="modal-close" onClick={closeModal}>
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <line x1="18" y1="6" x2="6" y2="18"></line>
              <line x1="6" y1="6" x2="18" y2="18"></line>
            </svg>
          </button>
        </div>
        
        <div className="modal-content">
          {(isDetailedDomainModal || isCustomerDataModal) ? renderDetailedDomainContent() : renderRegularModalContent()}
        </div>
      </div>
    </div>
  );
};

export default HealthModal;