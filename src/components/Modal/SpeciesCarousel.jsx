import React, { useState } from 'react';
import './SpeciesCarousel.css';


// Add this component at the top of your file
const ConfidenceTooltip = ({ level, className = "" }) => {
  const [isVisible, setIsVisible] = useState(false);

  const getConfidenceInfo = (confidenceLevel) => {
    switch (confidenceLevel?.toUpperCase()) {
      case 'A':
        return {
          title: 'High Confidence (A)',
          description: 'Strong scientific evidence with multiple peer-reviewed studies supporting this bacterial identification and health associations.',
          color: '#059669'
        };
      case 'B':
        return {
          title: 'Medium Confidence (B)', 
          description: 'Moderate scientific evidence with some peer-reviewed studies supporting this bacterial identification and health associations.',
          color: '#d97706'
        };
      case 'C':
        return {
          title: 'Lower Confidence (C)',
          description: 'Limited scientific evidence. This bacterial identification and health associations are based on preliminary research or computational predictions.',
          color: '#ea580c'
        };
      default:
        return {
          title: 'Unknown Confidence',
          description: 'Confidence level not specified.',
          color: '#4b5563'
        };
    }
  };

  const confidenceInfo = getConfidenceInfo(level);

  return (
    <div className="confidence-tooltip-wrapper" style={{ position: 'relative', display: 'inline-block' }}>
      <div
        className="confidence-trigger"
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: '4px',
          cursor: 'help'
        }}
        onMouseEnter={() => setIsVisible(true)}
        onMouseLeave={() => setIsVisible(false)}
      >
        <span style={{ fontWeight: '500' }}>{level?.toUpperCase()}</span>
        <span style={{ fontSize: '12px', opacity: 0.7 }}>ℹ️</span>
      </div>

      {isVisible && (
        <div style={{
          position: 'absolute',
          zIndex: 1000,
          bottom: '100%',
          left: '50%',
          transform: 'translateX(-50%)',
          marginBottom: '8px',
          width: '280px',
          padding: '12px',
          backgroundColor: 'white',
          borderRadius: '8px',
          boxShadow: '0 4px 12px rgba(0, 0, 0, 0.15)',
          border: '1px solid #e2e8f0'
        }}>
          <div style={{
            padding: '8px',
            borderRadius: '6px',
            backgroundColor: '#f8fafc',
            border: '1px solid #e2e8f0'
          }}>
            <h4 style={{
              fontWeight: '600',
              fontSize: '14px',
              color: confidenceInfo.color,
              marginBottom: '4px'
            }}>
              {confidenceInfo.title}
            </h4>
            <p style={{
              fontSize: '12px',
              color: '#374151',
              lineHeight: '1.4',
              margin: 0
            }}>
              {confidenceInfo.description}
            </p>
          </div>
        </div>
      )}
    </div>
  );
};

// Abundance Level Tooltip Component
const AbundanceLevelTooltip = ({ status, percentage }) => {
  const [isVisible, setIsVisible] = useState(false);

  const getAbundanceInfo = (status) => {
    switch (status?.toLowerCase()) {
      case 'good':
        return {
          title: 'Optimal Level',
          description: 'This bacteria is present at a healthy level that supports your wellbeing. The green indicator shows your current abundance is within the beneficial range.',
          color: '#4CAF50'
        };
      case 'normal':
        return {
          title: 'Normal Level',
          description: 'This bacteria is present at a typical level. The orange indicator shows your abundance is within the normal range, neither particularly high nor low.',
          color: '#FF9800'
        };
      case 'low':
        return {
          title: 'Below Optimal',
          description: 'This bacteria is detected at lower than optimal levels. The red indicator suggests you may benefit from interventions to increase this bacterial population.',
          color: '#FF5722'
        };
      case 'high':
        return {
          title: 'Above Normal',
          description: 'This bacteria is present at elevated levels. The red indicator shows higher than typical abundance, which may require attention depending on the bacteria type.',
          color: '#FF5722'
        };
      default:
        return {
          title: 'Abundance Level',
          description: 'This visual indicator shows where your bacteria level falls on the Low to High spectrum.',
          color: '#666'
        };
    }
  };

  const abundanceInfo = getAbundanceInfo(status);

  return (
    <div 
      style={{ position: 'relative', width: '100%', cursor: 'help' }}
      onMouseEnter={() => setIsVisible(true)}
      onMouseLeave={() => setIsVisible(false)}
    >
      <div style={{
        display: 'flex',
        alignItems: 'center',
        gap: '8px',
        marginBottom: '4px'
      }}>
        <span style={{ fontSize: '12px', color: '#666', fontWeight: '500' }}>Abundance Level</span>
        <span style={{ fontSize: '12px', opacity: 0.7 }}>ℹ️</span>
      </div>

      {isVisible && (
        <div style={{
          position: 'absolute',
          zIndex: 1000,
          top: '100%',
          left: '0',
          marginTop: '8px',
          width: '320px',
          padding: '12px',
          backgroundColor: 'white',
          borderRadius: '8px',
          boxShadow: '0 4px 12px rgba(0, 0, 0, 0.15)',
          border: '1px solid #e2e8f0'
        }}>
          <div style={{
            padding: '8px',
            borderRadius: '6px',
            backgroundColor: '#f8fafc',
            border: '1px solid #e2e8f0'
          }}>
            <h4 style={{
              fontWeight: '600',
              fontSize: '14px',
              color: abundanceInfo.color,
              marginBottom: '4px'
            }}>
              {abundanceInfo.title}
            </h4>
            <p style={{
              fontSize: '12px',
              color: '#374151',
              lineHeight: '1.4',
              marginBottom: '8px'
            }}>
              {abundanceInfo.description}
            </p>
            <div style={{
              fontSize: '11px',
              color: '#6b7280',
              paddingTop: '8px',
              borderTop: '1px solid #e5e7eb'
            }}>
              <strong>How to read:</strong> The colored bar shows relative abundance. The vertical line marks your current level on the Low → High spectrum.
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
// ✅ SpeciesItem component inline
const SpeciesItem = ({ species, category }) => {
  const formatPercentage = (percentage) => {
    if (percentage < 0.001) {
      return `${percentage.toFixed(6)}`;     // 0.000251
    } else if (percentage < 0.01) {
      return `${percentage.toFixed(4)}`;     // 0.0251  
    } else {
      return `${percentage.toFixed(3)}`;     // 0.918
    }
  };

  const getStatusColor = (status) => {
    const colorMap = {
      'good': '#4CAF50',
      'normal': '#FF9800', 
      'low': '#FF5722',
      'high': '#FF5722'
    };
    return colorMap[status?.toLowerCase()] || '#666';
  };

  const formatAbundance = (abundance) => {
    if (abundance < 0.000001) {
      return abundance.toExponential(2);
    } else if (abundance < 0.001) {
      return abundance.toFixed(6);
    } else {
      return abundance.toFixed(4);
    }
  };

  const handleMicrobeWikiClick = (e) => {
    if (species.microbewiki_url) {
      e.preventDefault();
      window.open(species.microbewiki_url, '_blank', 'noopener,noreferrer');
    }
  };

  return (
    <div className="species-item">
      <div className="species-header">
        <h4 className="species-name" style={{ fontSize: '18px', fontWeight: '600', color: '#1a202c' }}>
          <i>{species.name}</i>
          {species.microbewiki_url && (
            <button 
              className="species-name-link"
              onClick={handleMicrobeWikiClick}
              title="Learn more about this bacteria"
              aria-label={`Learn more about ${species.name}`}
            >
              🔗
            </button>
          )}
        </h4>
        <div 
          className="species-status"
          style={{ color: getStatusColor(species.status) }}
        >
          {species.status?.toUpperCase()}
        </div>
      </div>
      
      <div className="species-metrics">
        <div className="metric-row">
          <span className="metric-label" style={{ fontSize: '14px', color: '#718096' }}>Current Level:</span>
          <span className="metric-value" style={{ fontSize: '14px', fontWeight: '600', color: '#1a202c' }}>{formatAbundance(species.current_level)}</span>
        </div>
       {species.evidence_strength && (
  <div className="metric-row">
    <span className="metric-label" style={{ fontSize: '14px', color: '#718096' }}>Confidence Level:</span>
    <ConfidenceTooltip level={species.evidence_strength} />
  </div>
)}
      </div>

      <div className="species-progress">
        <AbundanceLevelTooltip status={species.status} percentage={species.percentage} />
        <div className="progress-bar">
          <div 
            className="progress-fill"
            style={{ 
              width: `${Math.min(species.range_fill_width || 50, 100)}%`,
              backgroundColor: getStatusColor(species.status)
            }}
          />
          <div 
            className="progress-marker"
            style={{ 
              left: `${Math.min(species.marker_position || 55, 100)}%`
            }}
          />
        </div>
        <div className="progress-labels">
          <span>Low</span>
          <span>High</span>
        </div>
      </div>

      {/* MicrobeWiki Link icon is now next to the species name in the header */}
    </div>
  );
};

// ✅ UPDATED: RecommendationItem component for card format like Image 1
const RecommendationItem = ({ item }) => {
  return (
    <div className="recommendation-item-card">
      <div className="recommendation-header">
        <h4 className="recommendation-title">{item.title || item.name}</h4>
        <span className="recommendation-checkmark">✓</span>
      </div>
      
      <p className="recommendation-description">{item.description}</p>
      
      <div className="recommendation-details">
        <div className="detail-row">
          <span className="detail-label">Dosage:</span>
          <span className="detail-value">{item.dosage}</span>
        </div>
        <div className="detail-row">
          <span className="detail-label">Why:</span>
          <span className="detail-value">{item.reason}</span>
        </div>
      </div>

      {/* Show key strains for probiotics */}
      {item.key_strains && (
        <div className="key-strains">
          <strong>Key Strains:</strong>
          <ul>
            {item.key_strains.map((strain, index) => (
              <li key={index}>{strain}</li>
            ))}
          </ul>
        </div>
      )}

      {/* Show benefits if available */}
      {item.benefits && (
        <div className="benefits">
          <strong>Benefits:</strong>
          <ul>
            {item.benefits.map((benefit, index) => (
              <li key={index}>{benefit}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
};

// ✅ NEW: RecommendationsSection component
// ✅ UPDATED: RecommendationsSection component with domain-specific support
const RecommendationsSection = ({ recommendations, currentDomain }) => {
  // console.log('🔍 RecommendationsSection received:', recommendations);
  // console.log('🔍 Full RecommendationsSection received:', recommendations);
  // console.log('🔍 Probiotics data:', recommendations?.probiotics);
  // console.log('🔍 First probiotic item:', recommendations?.probiotics?.[0]);
  // console.log('🔍 Supplements data:', recommendations?.supplements);
  // console.log('🔍 First supplement item:', recommendations?.supplements?.[0]);
  
  if (!recommendations) return null;

  // ✅ NEW: Helper function to get current domain from URL or context
  const getCurrentDomain = () => {
  // console.log('🎯 Checking domain:', currentDomain);
  // console.log('🎯 Available domains:', recommendations.domain_specific ? Object.keys(recommendations.domain_specific) : 'none');
  
  // Use the passed currentDomain prop
  if (currentDomain && recommendations.domain_specific && recommendations.domain_specific[currentDomain]) {
    return currentDomain;
  }
  
  // Fallback: try to find any available domain
  if (recommendations.domain_specific) {
    const domains = Object.keys(recommendations.domain_specific);
    return domains[0];
  }
  
  return null;
};

const activeDomain = getCurrentDomain(); // ← Changed variable name to activeDomain
  // ✅ NEW: Render domain-specific recommendations
  const renderDomainSpecificRecommendations = () => {
    if (!recommendations.domain_specific || !currentDomain) return null;

    const domainRecs = recommendations.domain_specific[currentDomain];
    if (!domainRecs) return null;

    return (
      <div className="recommendation-category domain-specific-category">
        <div className="category-header">
          <h3 className="category-title" style={{ 
            background: 'linear-gradient(135deg, #00BFA5, #4CAF50)',
            color: 'white',
            border: 'none'
          }}>
            🎯 {currentDomain.charAt(0).toUpperCase() + currentDomain.slice(1)}-Specific Recommendations
          </h3>
        </div>
        
        <div className="domain-specific-grid" style={{ 
          display: 'grid', 
          gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', 
          gap: '20px' 
        }}>
          {/* Domain-specific supplements */}
          {domainRecs.supplements && domainRecs.supplements.length > 0 && (
            <div className="domain-specific-section">
              <h4 style={{ color: '#00BFA5', marginBottom: '12px' }}>💊 Specialized Supplements</h4>
              <ul style={{ listStyle: 'none', padding: 0 }}>
                {domainRecs.supplements.map((supplement, index) => (
                  <li key={index} style={{ 
                    background: '#f8f9fa', 
                    padding: '12px', 
                    marginBottom: '8px', 
                    borderRadius: '8px',
                    borderLeft: '4px solid #00BFA5'
                  }}>
                    <strong style={{ color: '#2C3E50' }}>{supplement}</strong>
                    <div style={{ fontSize: '12px', color: '#666', marginTop: '4px' }}>
                      Specifically targeted for {currentDomain} health optimization
                    </div>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Domain-specific lifestyle */}
          {domainRecs.lifestyle && domainRecs.lifestyle.length > 0 && (
            <div className="domain-specific-section">
              <h4 style={{ color: '#4CAF50', marginBottom: '12px' }}>🏃 Specialized Lifestyle</h4>
              <ul style={{ listStyle: 'none', padding: 0 }}>
                {domainRecs.lifestyle.map((lifestyle, index) => (
                  <li key={index} style={{ 
                    background: '#f8f9fa', 
                    padding: '12px', 
                    marginBottom: '8px', 
                    borderRadius: '8px',
                    borderLeft: '4px solid #4CAF50'
                  }}>
                    <strong style={{ color: '#2C3E50' }}>{lifestyle}</strong>
                    <div style={{ fontSize: '12px', color: '#666', marginTop: '4px' }}>
                      Tailored for {currentDomain} health improvement
                    </div>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Domain-specific diet */}
          {domainRecs.diet && domainRecs.diet.length > 0 && (
            <div className="domain-specific-section">
              <h4 style={{ color: '#FF9800', marginBottom: '12px' }}>🥗 Specialized Diet</h4>
              <ul style={{ listStyle: 'none', padding: 0 }}>
                {domainRecs.diet.map((diet, index) => (
                  <li key={index} style={{ 
                    background: '#f8f9fa', 
                    padding: '12px', 
                    marginBottom: '8px', 
                    borderRadius: '8px',
                    borderLeft: '4px solid #FF9800'
                  }}>
                    <strong style={{ color: '#2C3E50' }}>{diet}</strong>
                    <div style={{ fontSize: '12px', color: '#666', marginTop: '4px' }}>
                      Focused on {currentDomain} health support
                    </div>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      </div>
    );
  };

  return (
    <div className="recommendations-section">
      <h2 className="recommendations-title">Recommendations</h2>
      
      {/* ✅ NEW: Domain-Specific Recommendations Section (at the top for prominence) */}
      {renderDomainSpecificRecommendations()}
      
      {/* ✅ NEW: Dietary Recommendations */}
      {recommendations.dietary_recommendations && recommendations.dietary_recommendations.length > 0 && (
        <div className="recommendation-category">
          <div className="category-header">
            <h3 className="category-title">🥗 Dietary Recommendations</h3>
          </div>
          <div className="recommendation-grid">
            {recommendations.dietary_recommendations.map((item, index) => (
              <div key={index} className="recommendation-item-card">
                <div className="recommendation-header">
                  <h4 className="recommendation-title">{item.item}</h4>
                  <span className={`priority-badge ${item.priority}`}>{item.priority}</span>
                </div>
                <p className="recommendation-description">{item.rationale}</p>
                <div className="recommendation-details">
                  <div className="detail-row">
                    <span className="detail-label">Frequency:</span>
                    <span className="detail-value">{item.frequency}</span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ✅ NEW: Lifestyle Recommendations */}
      {recommendations.lifestyle_recommendations && recommendations.lifestyle_recommendations.length > 0 && (
        <div className="recommendation-category">
          <div className="category-header">
            <h3 className="category-title">🏃 Lifestyle Recommendations</h3>
          </div>
          <div className="recommendation-grid">
            {recommendations.lifestyle_recommendations.map((item, index) => (
              <div key={index} className="recommendation-item-card">
                <div className="recommendation-header">
                  <h4 className="recommendation-title">{item.activity}</h4>
                  <span className={`priority-badge ${item.priority}`}>{item.priority}</span>
                </div>
                <p className="recommendation-description">{item.rationale}</p>
                <div className="recommendation-details">
                  <div className="detail-row">
                    <span className="detail-label">Implementation:</span>
                    <span className="detail-value">{item.implementation}</span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ✅ UPDATED: Probiotic Recommendations */}
      {recommendations.probiotic_recommendations && recommendations.probiotic_recommendations.length > 0 && (
        <div className="recommendation-category">
          <div className="category-header">
            <h3 className="category-title">🦠 Probiotic Recommendations</h3>
          </div>
          <div className="recommendation-grid">
            {recommendations.probiotic_recommendations.map((item, index) => (
              <div key={index} className="recommendation-item-card">
                <div className="recommendation-header">
                  <h4 className="recommendation-title">{item.strain}</h4>
                  <span className="recommendation-checkmark">✓</span>
                </div>
                <p className="recommendation-description">{item.rationale}</p>
                <div className="recommendation-details">
                  <div className="detail-row">
                    <span className="detail-label">Dosage:</span>
                    <span className="detail-value">{item.dosage}</span>
                  </div>
                  <div className="detail-row">
                    <span className="detail-label">Duration:</span>
                    <span className="detail-value">{item.duration}</span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ✅ NEW: Prebiotic Recommendations */}
      {recommendations.prebiotic_recommendations && recommendations.prebiotic_recommendations.length > 0 && (
        <div className="recommendation-category">
          <div className="category-header">
            <h3 className="category-title">🌾 Prebiotic Recommendations</h3>
          </div>
          <div className="recommendation-grid">
            {recommendations.prebiotic_recommendations.map((item, index) => (
              <div key={index} className="recommendation-item-card">
                <div className="recommendation-header">
                  <h4 className="recommendation-title">{item.source}</h4>
                  <span className="recommendation-checkmark">✓</span>
                </div>
                <p className="recommendation-description">{item.rationale}</p>
                <div className="recommendation-details">
                  <div className="detail-row">
                    <span className="detail-label">Amount:</span>
                    <span className="detail-value">{item.amount}</span>
                  </div>
                  {item.food_sources && (
                    <div className="detail-row">
                      <span className="detail-label">Food Sources:</span>
                      <span className="detail-value">{item.food_sources.join(', ')}</span>
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ✅ LEGACY: Keep old structure for backwards compatibility */}
      {recommendations.probiotics && recommendations.probiotics.length > 0 && (
        <div className="recommendation-category">
          <div className="category-header">
            <h3 className="category-title">Probiotics (Legacy)</h3>
          </div>
          <div className="recommendation-grid">
            {recommendations.probiotics.map((item, index) => (
              <RecommendationItem key={item.id || index} item={item} />
            ))}
          </div>
        </div>
      )}

      {/* ✅ LEGACY: Keep old structure for backwards compatibility */}
      {recommendations.supplements && recommendations.supplements.length > 0 && (
        <div className="recommendation-category">
          <div className="category-header">
            <h3 className="category-title">Supplements (Legacy)</h3>
          </div>
          <div className="recommendation-grid">
            {recommendations.supplements.map((item, index) => (
              <RecommendationItem key={item.id || index} item={item} />
            ))}
          </div>
        </div>
      )}

      {/* ✅ EXISTING: Metabolic Pathways */}
      {recommendations.metabolic_pathways && recommendations.metabolic_pathways.length > 0 && (
        <div className="recommendation-category">
          <div className="category-header">
            <h3 className="category-title">Metabolic Pathways</h3>
          </div>
          <div className="pathway-grid">
            {recommendations.metabolic_pathways.map((pathway, index) => (
              <div key={pathway.id || index} className="pathway-item">
                <h4 className="pathway-name">{pathway.name}</h4>
                <div className="pathway-status">
                  <span>Status: {pathway.status}</span>
                  <span>Current: {pathway.current_score} → Target: {pathway.target_score}</span>
                </div>
                <p className="pathway-description">{pathway.description}</p>
                <div className="pathway-timeline">
                  <strong>Timeline:</strong> {pathway.improvement_timeline}
                </div>
                {pathway.key_factors && (
                  <div className="pathway-factors">
                    <strong>Key Factors:</strong>
                    <ul>
                      {pathway.key_factors.map((factor, idx) => (
                        <li key={idx}>{factor}</li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ✅ NEW: Summary Section */}
      {recommendations.summary && (
        <div className="recommendation-category">
          <div className="category-header">
            <h3 className="category-title">📋 Summary</h3>
          </div>
          <div className="summary-content" style={{
            background: '#f8f9fa',
            padding: '20px',
            borderRadius: '8px',
            border: '1px solid #e9ecef',
            fontSize: '14px',
            lineHeight: '1.6',
            color: '#495057'
          }}>
            {recommendations.summary}
          </div>
        </div>
      )}
    </div>
  );
};

// ✅ UPDATED: Main SpeciesCarousel component
const SpeciesCarousel = ({ speciesData, recommendations, currentDomain }) => {// ← Add recommendations prop
  // Track current page for each category separately
  const [categoryPages, setCategoryPages] = useState({});

  // console.log('📊 SpeciesCarousel received data:', speciesData);
  // console.log('💊 SpeciesCarousel received recommendations:', recommendations); // ← Debug log

  // ✅ FIXED: Handle the correct data structure - reordered to show keystone at the end
  const categoryOrder = ['bacteria', 'probiotics', 'virus', 'fungi', 'pathogens', 'protozoa', 'keystone'];
  
  // ✅ FIXED: Check for species array inside each category object
  const slides = categoryOrder.filter(category => {
    const categoryData = speciesData?.[category];
    return categoryData && categoryData.species && categoryData.species.length > 0;
  });

  // console.log('🔍 Available slides:', slides);
  // console.log('🔍 Slides data:', slides.map(cat => ({
  //   category: cat,
  //   speciesCount: speciesData?.[cat]?.species?.length || 0
  // })));

  const moveToSlide = (slideIndex) => {
    setCategoryPages(prev => ({ ...prev, [slideIndex]: slideIndex }));
  };

  const moveToPage = (category, direction) => {
    const currentPage = categoryPages[category] || 0;
    const newPage = direction === 'next' ? currentPage + 1 : Math.max(0, currentPage - 1);
    setCategoryPages(prev => ({ ...prev, [category]: newPage }));
  };

  const formatCategoryTitle = (category) => {
    const categoryData = speciesData?.[category];
    if (categoryData && categoryData.title) {
      return categoryData.title;
    }
    
    const titleMap = {
      'bacteria': 'Top Bacterial Species',
      'probiotics': 'Probiotic Organisms',
      'virus': 'Viral Species',
      'fungi': 'Fungal Species',
      'pathogens': 'Pathogenic Species',
      'protozoa': 'Protozoa Species',
      'keystone': '⭐ Keystone Species'
    };
    return titleMap[category] || category.charAt(0).toUpperCase() + category.slice(1);
  };

  const formatCategoryStatus = (category) => {
    const categoryData = speciesData?.[category];
    if (categoryData && categoryData.status) {
      return categoryData.status;
    }
    
    const statusMap = {
      'excellent': 'Excellent',
      'good': 'Good',
      'normal': 'Normal',
      'warning': 'Low (Good)'
    };
    return statusMap[category] || 'Normal';
  };

  // ✅ IMPROVED: Better validation
  if (!speciesData) {
    return (
      <div className="species-carousel">
        <div className="loading">Loading bacteria data...</div>
      </div>
    );
  }

  if (!slides.length) {
    return (
      <div className="species-carousel">
        <div className="no-data">
          <p>No species data available</p>
        </div>
      </div>
    );
  }

  return (
    <div className="species-carousel-container">
      {/* ✅ UPDATED: Vertical Species List with Per-Category Pagination */}
      <div className="species-carousel">
        {slides.map((category) => {
          const categoryData = speciesData[category];
          const allSpecies = categoryData.species;
          const status = formatCategoryStatus(category);
          const itemsPerPage = 6;
          const currentPage = categoryPages[category] || 0;
          const totalPages = Math.ceil(allSpecies.length / itemsPerPage);
          const startIdx = currentPage * itemsPerPage;
          const endIdx = startIdx + itemsPerPage;
          const pageSpecies = allSpecies.slice(startIdx, endIdx);

          return (
            <div key={category} className="species-category-section">
              {/* Category Title and Status */}
              <div className="species-category-header">
                <h3 className="species-category-title" style={category === 'keystone' ? { color: '#f57c00' } : { color: '#00BFA5' }}>
                  {formatCategoryTitle(category)}
                </h3>
                <span 
                  className="species-category-status"
                  style={{ 
                    background: category === 'keystone' ? '#f57c00' : (status === 'Good' ? '#4CAF50' : status === 'Monitor' ? '#FF5722' : '#FF9800'),
                    color: 'white'
                  }}
                >
                  {category === 'keystone' ? `COUNT: ${allSpecies.length}` : `Status: ${status}`}
                </span>
              </div>

              {/* Vertical Species Cards or List */}
              <div className={category === 'keystone' ? 'keystone-simple-list' : 'species-vertical-list'}>
                {category === 'keystone' ? (
                  // Simple list for keystone species - just names
                  <ul className="keystone-names-list">
                    {pageSpecies.map((speciesItem, index) => (
                      <li key={`${category}-${startIdx + index}`} className="keystone-name-item">
                        {speciesItem.name}
                      </li>
                    ))}
                  </ul>
                ) : (
                  // Full cards for other categories
                  pageSpecies.map((speciesItem, index) => (
                    <SpeciesItem
                      key={`${category}-${startIdx + index}`}
                      species={speciesItem}
                      category={category}
                    />
                  ))
                )}
              </div>

              {/* Pagination Controls */}
              {totalPages > 1 && (
                <div className="species-pagination">
                  <button 
                    className="pagination-btn"
                    onClick={() => moveToPage(category, 'prev')}
                    disabled={currentPage === 0}
                  >
                    ← Previous
                  </button>
                  <span className="pagination-info">
                    Page {currentPage + 1} of {totalPages}
                  </span>
                  <button 
                    className="pagination-btn"
                    onClick={() => moveToPage(category, 'next')}
                    disabled={currentPage >= totalPages - 1}
                  >
                    Next →
                  </button>
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* ✅ NEW: Recommendations Section */}
      <RecommendationsSection recommendations={recommendations} currentDomain={currentDomain} />
    </div>
  );
};

export default SpeciesCarousel;