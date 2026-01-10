// pages/ClinicalTrials/ClinicalTrials.jsx - LOCAL FILTERING ARCHITECTURE
import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { useAppContext } from '../../context';
import apiService from '../../services/api';
import './ClinicalTrials.css';

// Helper function to safely join array values
const safeJoin = (value, separator = ', ') => {
  if (Array.isArray(value)) {
    return value.join(separator) || 'N/A';
  }
  if (typeof value === 'string') {
    return value || 'N/A';
  }
  return 'N/A';
};

const ClinicalTrials = () => {
  const { state } = useAppContext();
  const { user } = state;
  
  // CACHED TRIALS - Fetched once per view type and stored locally
  const [cachedTrials, setCachedTrials] = useState({
    all: [],
    domain: {},
    personalized: [],
    search: []
  });
  const [currentViewTrials, setCurrentViewTrials] = useState([]); // Trials for current view
  
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [expandedTrials, setExpandedTrials] = useState({});
  const [currentPage, setCurrentPage] = useState(1); // Pagination - current page number
    // ALL FILTERS (applied locally on cached data)
  const [filters, setFilters] = useState({
    domain: 'all',
    status: 'all',           // all, open, pending, closed
    sponsor: '',             // sponsor name selection
    location: ''             // location selection from dropdown
  });

  // FETCH TRIALS - Load all or domain-specific
  const loadTrialsForView = useCallback(async () => {
    try {
      setLoading(true);
      let response;

      if (filters.domain === 'all') {
        // Load all trials (fetch once, cache)
        if (cachedTrials.all.length === 0) {
          response = await apiService.getAllClinicalTrials(10000);
          
          if (response.success) {
            const uniqueTrials = deduplicateTrials(response.trials || []);
            setCachedTrials(prev => ({
              ...prev,
              all: uniqueTrials
            }));
            setCurrentViewTrials(uniqueTrials);
          }
        } else {
          setCurrentViewTrials(cachedTrials.all);
        }
      } else {
        // Load domain-specific trials (fetch once, cache by domain)
        if (!cachedTrials.domain[filters.domain]) {
          response = await apiService.getDomainClinicalTrials(
            filters.domain,
            10000
          );
          
          if (response.success) {
            const uniqueTrials = deduplicateTrials(response.trials || []);
            setCachedTrials(prev => ({
              ...prev,
              domain: { ...prev.domain, [filters.domain]: uniqueTrials }
            }));
            setCurrentViewTrials(uniqueTrials);
          }
        } else {
          setCurrentViewTrials(cachedTrials.domain[filters.domain]);
        }
      }
    } catch (error) {
      console.error('Error loading trials:', error);
      setCurrentViewTrials([]);
    } finally {
      setLoading(false);
    }
  }, [filters.domain, cachedTrials.domain, cachedTrials.all]);

  // Deduplicate trials by nct_id
  const deduplicateTrials = useCallback((trials) => {
    const trialsMap = new Map();
    trials.forEach(trial => {
      if (!trialsMap.has(trial.nct_id)) {
        trialsMap.set(trial.nct_id, trial);
      }
    });
    return Array.from(trialsMap.values());
  }, []);

  // Load trials on mount and when domain changes
  useEffect(() => {
    loadTrialsForView();
  }, [filters.domain, loadTrialsForView]);

  // Extract available filter options from loaded trials
  const availableFilters = useMemo(() => {
    const filterOptions = {
      statuses: new Set(),
      conditions: new Set(),
      sponsors: new Set(),
      interventions: new Set()
    };

    currentViewTrials.forEach(trial => {
      // Collect statuses
      if (trial.status_raw) {
        filterOptions.statuses.add(trial.status_raw);
      }

      // Collect conditions
      if (trial.conditions) {
        const conds = Array.isArray(trial.conditions) ? trial.conditions : [trial.conditions];
        conds.forEach(c => {
          if (c && c !== 'N/A' && typeof c === 'string') {
            filterOptions.conditions.add(c);
          }
        });
      }

      // Collect sponsors
      if (trial.sponsor && trial.sponsor !== 'Unknown Sponsor') {
        filterOptions.sponsors.add(trial.sponsor);
      }

      // Collect interventions
      if (trial.interventions) {
        const interventions = Array.isArray(trial.interventions) ? trial.interventions : [trial.interventions];
        interventions.forEach(i => {
          if (i && i !== 'N/A' && typeof i === 'string') {
            filterOptions.interventions.add(i);
          }
        });
      }
    });

    // Convert to sorted arrays
    const result = {
      statuses: Array.from(filterOptions.statuses).sort(),
      conditions: Array.from(filterOptions.conditions).sort(),
      sponsors: Array.from(filterOptions.sponsors).sort(),
      interventions: Array.from(filterOptions.interventions).sort()
    };

    return result;
  }, [currentViewTrials]);

  // APPLY ALL FILTERS LOCALLY (no API calls)
  const filteredTrials = useMemo(() => {
    let results = currentViewTrials;

    // 1. STATUS FILTER (using mapped status: open, pending, closed)
    if (filters.status !== 'all') {
      results = results.filter(trial => {
        const trialStatus = trial.status || '';
        return trialStatus === filters.status;
      });
    }

    // 2. SPONSOR FILTER
    if (filters.sponsor.trim()) {
      results = results.filter(trial => {
        return trial.sponsor === filters.sponsor;
      });
    }

    // 3. LOCATION FILTER
    if (filters.location.trim()) {
      results = results.filter(trial => {
        let countries = trial.countries || [];
        
        // Handle JSON string format
        if (typeof countries === 'string') {
          try {
            countries = JSON.parse(countries);
          } catch (e) {
            countries = [];
          }
        }
        
        // Handle array format
        if (Array.isArray(countries)) {
          return countries.includes(filters.location);
        }
        
        return false;
      });
    }

    // 4. SEARCH TERM FILTER
    if (searchTerm.trim()) {
      const searchLower = searchTerm.toLowerCase();
      results = results.filter(trial =>
        trial.name.toLowerCase().includes(searchLower) ||
        trial.description.toLowerCase().includes(searchLower) ||
        trial.sponsor.toLowerCase().includes(searchLower) ||
        (trial.nct_id && trial.nct_id.toLowerCase().includes(searchLower))
      );
    }

    return results;
  }, [currentViewTrials, filters, searchTerm]);

  // Reset pagination when filters or search changes
  useEffect(() => {
    setCurrentPage(1);
  }, [filters, searchTerm]);

  // Pagination logic - show 10 trials per page
  const TRIALS_PER_PAGE = 10;
  const paginatedTrials = useMemo(() => {
    const startIndex = (currentPage - 1) * TRIALS_PER_PAGE;
    const endIndex = startIndex + TRIALS_PER_PAGE;
    return filteredTrials.slice(startIndex, endIndex);
  }, [filteredTrials, currentPage]);

  const totalPages = Math.ceil(filteredTrials.length / TRIALS_PER_PAGE);

  const handleSearch = (e) => {
    setSearchTerm(e.target.value);
  };

  // Handle ANY filter change - applies locally, no API call
  const handleFilterChange = (filterType, value) => {
    setFilters(prev => ({
      ...prev,
      [filterType]: value
    }));
  };

  const handleToggle = (trialId) => {
    setExpandedTrials(prev => ({
      ...prev,
      [trialId]: !prev[trialId]
    }));
  };

  const handleLearnMore = (trial) => {
    window.open(trial.url, '_blank');
  };

  const getStatusColor = (status) => {
    switch (status?.toLowerCase()) {
      case 'recruiting': return '#28a745';
      case 'completed': return '#6c757d';
      case 'not_yet_recruiting': return '#ffc107';
      default: return '#17a2b8';
    }
  };

  const getStatusLabel = (status) => {
    switch (status) {
      case 'RECRUITING': return 'Recruiting';
      case 'NOT_YET_RECRUITING': return 'Not Yet Recruiting';
      default: return status || 'Active';
    }
  };

  const resetFilters = () => {
    setSearchTerm('');
    setFilters({
      domain: 'all',
      status: 'all',
      sponsor: '',
      location: ''
    });
  };

  // Get unique locations from all trials in current view
  const availableLocations = useMemo(() => {
    const locations = new Set();
    console.log(`📍 Extracting locations from ${currentViewTrials.length} trials`);
    
    currentViewTrials.forEach(trial => {
      let countries = trial.countries || [];
      
      // Handle JSON string format
      if (typeof countries === 'string') {
        try {
          countries = JSON.parse(countries);
          console.log(`  Parsed countries from string: ${JSON.stringify(countries)}`);
        } catch (e) {
          console.log(`  Failed to parse countries string: ${countries}`);
          countries = [];
        }
      }
      
      // Handle array format
      if (Array.isArray(countries)) {
        countries.forEach(country => {
          if (country && country !== 'N/A' && country !== 'Unknown') {
            locations.add(country);
          }
        });
      }
    });
    
    const result = Array.from(locations).sort();
    console.log(`✅ Available locations: ${result.length} unique countries:`, result);
    return result;
  }, [currentViewTrials]);

  if (loading) {
    return (
      <div id="clinical-trials" className="content-section">
        <div className="clinical-trials-container">
          <div className="loading-state">
            <div className="loading-spinner"></div>
            <p>Loading clinical trials...</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div id="clinical-trials" className="content-section">
      <div className="clinical-trials-container">
        {/* Header Section */}
        <div className="clinical-trials-header">
          <div className="page-title-container">
            <h1 className="clinical-trials-title">Clinical Trials</h1>
            <div className="last-updated">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <circle cx="12" cy="12" r="10"></circle>
                <polyline points="12 6 12 12 16 14"></polyline>
              </svg>
              Last updated: {new Date().toLocaleDateString()}
            </div>
          </div>
          <p className="clinical-trials-subtitle">
            Discover clinical trials and research studies in microbiome health and wellness. 
            Join cutting-edge research to advance scientific understanding while potentially improving your health.
          </p>
        </div>

        {/* Search and Filters */}
        <div className="search-filter-container">
          <div className="search-bar">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <circle cx="11" cy="11" r="8"></circle>
              <path d="M21 21l-4.35-4.35"></path>
            </svg>
            <input
              type="text"
              placeholder="Search trials by name, keyword, or sponsor..."
              value={searchTerm}
              onChange={handleSearch}
            />
            {searchTerm && (
              <button className="clear-search" onClick={() => setSearchTerm('')}>
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <line x1="18" y1="6" x2="6" y2="18"></line>
                  <line x1="6" y1="6" x2="18" y2="18"></line>
                </svg>
              </button>
            )}
          </div>

          {/* FILTER CONTROLS */}
          <div className="filter-controls">
            {/* Domain Filter */}
            <select 
              value={filters.domain} 
              onChange={(e) => handleFilterChange('domain', e.target.value)}
              title="Filter by health domain"
            >
              <option value="all">All Domains</option>
              <option value="gut">Gut Health</option>
              <option value="liver">Liver Health</option>
              <option value="heart">Heart Health</option>
              <option value="cognitive">Cognitive Health</option>
              <option value="aging">Aging & Longevity</option>
              <option value="skin">Skin Health</option>
            </select>

            {/* Status Filter */}
            <select 
              value={filters.status} 
              onChange={(e) => handleFilterChange('status', e.target.value)}
              title="Filter by recruitment status"
            >
              <option value="all">All Status</option>
              <option value="open">Open (Recruiting)</option>
              <option value="pending">Pending (Not Yet Recruiting)</option>
              <option value="closed">Closed</option>
            </select>

            {/* Sponsor Filter */}
            <select
              value={filters.sponsor}
              onChange={(e) => handleFilterChange('sponsor', e.target.value)}
              title="Filter by trial sponsor"
            >
              <option value="">All Sponsors</option>
              {availableFilters.sponsors.map(sponsor => (
                <option key={sponsor} value={sponsor}>
                  {sponsor}
                </option>
              ))}
            </select>

            {/* Location Filter - Dropdown */}
            <select
              value={filters.location}
              onChange={(e) => handleFilterChange('location', e.target.value)}
              title="Filter by trial location/country"
            >
              <option value="">All Locations</option>
              {availableLocations.map(location => (
                <option key={location} value={location}>
                  {location}
                </option>
              ))}
            </select>

            {/* Reset Button */}
            <button 
              className="reset-filters-btn"
              onClick={resetFilters}
              title="Reset all filters to default"
            >
              Reset Filters
            </button>
          </div>
        </div>

        {/* Results Summary */}
        <div className="results-summary">
          <p>Showing <strong>{filteredTrials.length}</strong> clinical trials (of {currentViewTrials.length} total in {filters.domain === 'all' ? 'all domains' : filters.domain + ' view'})</p>
          {Object.values(filters).some(f => f !== 'all' && f !== 0 && f !== 999999 && f !== '') && (
            <p className="filters-applied-note">🔍 {Object.entries(filters).filter(([, v]) => v !== 'all' && v !== 0 && v !== 999999 && v !== '').length} filter(s) applied</p>
          )}
        </div>

        {/* Trials List */}
        <div className="trials-grid">
          {paginatedTrials.length > 0 ? paginatedTrials.map((trial) => {
            const isExpanded = expandedTrials[trial.nct_id] || false;
            
            return (
              <div key={trial.nct_id} className="trial-card">
                {/* Clickable Header */}
                <div 
                  className="trial-header-clickable"
                  onClick={() => handleToggle(trial.nct_id)}
                >
                  <div className="trial-header-content">
                    <div className="trial-title-info">
                      <h3 className="trial-title">{trial.name}</h3>
                      <div className="trial-meta">
                        <span 
                          className="trial-status"
                          style={{ backgroundColor: getStatusColor(trial.status) }}
                        >
                          {getStatusLabel(trial.status)}
                        </span>
                        <span className="trial-duration">{trial.duration || 'N/A'}</span>
                        <span className="trial-nct">{trial.nct_id}</span>
                      </div>
                    </div>
                    
                    <div className="trial-participation">
                      <div className="participation-info">
                        <span className="participants-count">
                          {trial.enrollment !== undefined && trial.enrollment !== null && trial.enrollment > 0
                            ? `${trial.enrollment.toLocaleString()} participants`
                            : 'Enrollment N/A'}
                        </span>
                        <span className="participants-label">Target Enrollment</span>
                      </div>
                    </div>
                    
                    <div className={`trial-arrow ${isExpanded ? 'expanded' : ''}`}>
                      ▼
                    </div>
                  </div>
                </div>

                {/* Expandable Content */}
                {isExpanded && (
                  <div className="trial-expanded-content">
                    <p className="trial-description">{trial.description}</p>
                    
                    <div className="trial-details">
                      <div className="detail-group">
                        <strong>Conditions:</strong>
                        <p>{safeJoin(trial.conditions)}</p>
                      </div>
                      <div className="detail-group">
                        <strong>Interventions:</strong>
                        <p>{safeJoin(trial.interventions)}</p>
                      </div>
                      <div className="detail-group">
                        <strong>Locations:</strong>
                        <p>{safeJoin(trial.countries)}</p>
                      </div>
                    </div>
                    
                    <div className="trial-footer">
                      <div className="trial-info">
                        <div className="vendor-info">
                          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                            <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/>
                            <circle cx="12" cy="7" r="4"/>
                          </svg>
                          {trial.sponsor || 'N/A'}
                        </div>
                      </div>
                      <div className="trial-actions">
                        <button 
                          className="learn-more-btn"
                          onClick={(e) => {
                            e.stopPropagation();
                            handleLearnMore(trial);
                          }}
                        >
                          View on ClinicalTrials.gov
                        </button>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            );
          }) : (
            <div className="no-results">
              <p>No clinical trials found matching your criteria.</p>
              <button onClick={resetFilters}>
                Reset Filters
              </button>
            </div>
          )}
        </div>

        {/* Pagination Controls */}
        {filteredTrials.length > 0 && (
          <div className="pagination-container">
            <div className="pagination-info">
              Showing {(currentPage - 1) * TRIALS_PER_PAGE + 1} - {Math.min(currentPage * TRIALS_PER_PAGE, filteredTrials.length)} of {filteredTrials.length} trials
            </div>
            <div className="pagination-controls">
              <button 
                className="pagination-btn"
                onClick={() => setCurrentPage(currentPage - 1)}
                disabled={currentPage === 1}
              >
                ← Previous
              </button>
              
              <div className="pagination-numbers">
                {/* Smart pagination: show first 3, ellipsis if needed, then last page */}
                {Array.from({ length: totalPages }, (_, i) => i + 1).map((page, idx, arr) => {
                  // Always show first 3 pages
                  if (page <= 3) {
                    return (
                      <button
                        key={page}
                        className={`page-number ${currentPage === page ? 'active' : ''}`}
                        onClick={() => setCurrentPage(page)}
                      >
                        {page}
                      </button>
                    );
                  }
                  // Show ellipsis before last pages if there's a gap
                  if (page === 4 && totalPages > 6) {
                    return <span key="ellipsis" className="pagination-ellipsis">...</span>;
                  }
                  // Skip middle pages if totalPages > 6
                  if (page > 3 && page < totalPages - 2 && totalPages > 6) {
                    return null;
                  }
                  // Always show last 3 pages
                  if (page > totalPages - 3) {
                    return (
                      <button
                        key={page}
                        className={`page-number ${currentPage === page ? 'active' : ''}`}
                        onClick={() => setCurrentPage(page)}
                      >
                        {page}
                      </button>
                    );
                  }
                  return null;
                })}
              </div>

              <button 
                className="pagination-btn"
                onClick={() => setCurrentPage(currentPage + 1)}
                disabled={currentPage === totalPages}
              >
                Next →
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default ClinicalTrials;