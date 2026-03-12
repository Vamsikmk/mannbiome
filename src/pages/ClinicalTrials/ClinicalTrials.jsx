// pages/ClinicalTrials/ClinicalTrials.jsx - LOCAL FILTERING ARCHITECTURE
import React, { useState, useEffect, useCallback, useMemo, useRef } from 'react';
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

const normalizeQuestionType = (type) => String(type || '').toLowerCase();

const isEligibilityQuestionnaire = (questionnaire) =>
  normalizeQuestionType(questionnaire?.questionnaire_type) === 'eligibility';

const formatUtcDateTime = (value) => {
  if (!value) return '';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return '';
  return `${date.toISOString().replace('T', ' ').slice(0, 16)} UTC`;
};

const ClinicalTrials = () => {
  const { state } = useAppContext();
  const { user } = state;
  
  // CACHED TRIALS - Fetched once per view type and stored locally
  const [cachedTrials, setCachedTrials] = useState({
    all: [],
    internal: [],
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
    source: 'all',            // all, internal, external
    status: 'all',           // all, open, pending, closed
    sponsor: '',             // sponsor name selection
    location: ''             // location selection from dropdown
  });
  const [questionnairesByTrial, setQuestionnairesByTrial] = useState({});
  const [questionnaireLoadingByTrial, setQuestionnaireLoadingByTrial] = useState({});
  const [questionnaireErrorByTrial, setQuestionnaireErrorByTrial] = useState({});
  const [eligibilityByTrial, setEligibilityByTrial] = useState({});
  const [activeQuestionnaire, setActiveQuestionnaire] = useState(null);
  const [activeQuestionnaireDetail, setActiveQuestionnaireDetail] = useState(null);
  const [answers, setAnswers] = useState({});
  const [isSavingDraft, setIsSavingDraft] = useState(false);
  const [isSubmittingQuestionnaire, setIsSubmittingQuestionnaire] = useState(false);
  const [saveMessage, setSaveMessage] = useState('');
  const [saveError, setSaveError] = useState('');
  const autosaveTimerRef = useRef(null);

  // FETCH TRIALS - Load all or domain-specific
  const loadTrialsForView = useCallback(async () => {
    try {
      setLoading(true);
      let externalResponse;
      let internalResponse;

      const mergeTrials = (externalTrials, internalTrials) =>
        deduplicateTrials([...(internalTrials || []), ...(externalTrials || [])]);

      if (filters.domain === 'all') {
        // Load both external and internal trials (fetch once, cache)
        if (cachedTrials.all.length === 0 || cachedTrials.internal.length === 0) {
          [externalResponse, internalResponse] = await Promise.all([
            apiService.getAllClinicalTrials(10000),
            apiService.getInternalClinicalTrials(1000)
          ]);

          const externalTrials = externalResponse?.success ? (externalResponse.trials || []) : [];
          const internalTrials = internalResponse?.success ? (internalResponse.trials || []) : [];
          const uniqueTrials = mergeTrials(externalTrials, internalTrials);

          setCachedTrials(prev => ({
            ...prev,
            all: uniqueTrials,
            internal: internalTrials
          }));
          setCurrentViewTrials(uniqueTrials);
        } else {
          setCurrentViewTrials(cachedTrials.all);
        }
      } else {
        // Load domain-specific external trials and merge with internal trials
        if (!cachedTrials.domain[filters.domain]) {
          [externalResponse, internalResponse] = await Promise.all([
            apiService.getDomainClinicalTrials(filters.domain, 10000),
            cachedTrials.internal.length > 0
              ? Promise.resolve({ success: true, trials: cachedTrials.internal })
              : apiService.getInternalClinicalTrials(1000)
          ]);

          const domainExternal = externalResponse?.success ? (externalResponse.trials || []) : [];
          const internalTrials = internalResponse?.success ? (internalResponse.trials || []) : [];
          const merged = mergeTrials(domainExternal, internalTrials);

          setCachedTrials(prev => ({
            ...prev,
            internal: prev.internal.length > 0 ? prev.internal : internalTrials,
            domain: { ...prev.domain, [filters.domain]: merged }
          }));
          setCurrentViewTrials(merged);
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
  }, [filters.domain, cachedTrials.domain, cachedTrials.all, cachedTrials.internal]);

  // Deduplicate trials by nct_id
  const deduplicateTrials = useCallback((trials) => {
    const trialsMap = new Map();
    trials.forEach(trial => {
      const source = trial?.source || 'external';
      const identifier = trial?.trial_id ?? trial?.id ?? trial?.nct_id ?? trial?.name;
      const uniqueKey = `${source}:${identifier}`;
      if (!trialsMap.has(uniqueKey)) {
        trialsMap.set(uniqueKey, trial);
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

    // 0. SOURCE FILTER (internal vs external)
    if (filters.source !== 'all') {
      results = results.filter(trial => (trial.source || 'external') === filters.source);
    }

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

  const handleToggle = (trial) => {
    const trialId = resolveTrialIdentifier(trial);
    const trialUIKey = resolveTrialUIKey(trial);
    const isInternalTrial = (trial?.source || 'external') === 'internal';
    const nextOpen = !expandedTrials[trialUIKey];
    setExpandedTrials(prev => ({
      ...prev,
      [trialUIKey]: nextOpen
    }));
    if (isInternalTrial && nextOpen && !questionnairesByTrial[trialId] && !questionnaireLoadingByTrial[trialId]) {
      loadTrialQuestionnaires(trial);
    }
  };

  const handleLearnMore = (trial) => {
    if (!trial?.url) return;
    window.open(trial.url, '_blank');
  };

  const resolveTrialIdentifier = (trial) => {
    if (trial?.trial_id !== undefined && trial?.trial_id !== null) return trial.trial_id;
    if (trial?.id !== undefined && trial?.id !== null) return trial.id;
    return trial?.nct_id;
  };

  const resolveTrialUIKey = (trial) => `${trial?.source || 'external'}:${resolveTrialIdentifier(trial)}`;

  const loadTrialQuestionnaires = useCallback(async (trial) => {
    const trialId = resolveTrialIdentifier(trial);
    if (!trialId || !state.customerId) return;

    setQuestionnaireLoadingByTrial(prev => ({ ...prev, [trialId]: true }));
    setQuestionnaireErrorByTrial(prev => ({ ...prev, [trialId]: '' }));
    try {
      const [qResult, eligibilityResult] = await Promise.all([
        apiService.getCustomerTrialQuestionnaires(state.customerId, trialId),
        apiService.getCustomerTrialEligibilityResult(state.customerId, trialId)
      ]);

      if (!qResult.success) {
        throw new Error(qResult.error || 'Failed to load questionnaires');
      }
      setQuestionnairesByTrial(prev => ({ ...prev, [trialId]: qResult.questionnaires || [] }));

      if (eligibilityResult?.success && eligibilityResult?.data) {
        setEligibilityByTrial(prev => ({ ...prev, [trialId]: eligibilityResult.data }));
      }
    } catch (error) {
      setQuestionnaireErrorByTrial(prev => ({ ...prev, [trialId]: error.message || 'Failed to load questionnaires' }));
    } finally {
      setQuestionnaireLoadingByTrial(prev => ({ ...prev, [trialId]: false }));
    }
  }, [state.customerId]);

  const isQuestionnaireLocked = (trialId, questionnaire) => {
    if (questionnaire?.is_locked) return true;
    const list = questionnairesByTrial[trialId] || [];
    const hasEligibility = list.some(isEligibilityQuestionnaire);
    if (!hasEligibility) return false;
    if (isEligibilityQuestionnaire(questionnaire)) return false;
    return eligibilityByTrial?.[trialId]?.is_eligible !== true;
  };

  const openQuestionnaire = async (trial, questionnaire) => {
    const trialId = resolveTrialIdentifier(trial);
    if (!trialId || !state.customerId) return;
    if (isQuestionnaireLocked(trialId, questionnaire)) return;

    setSaveMessage('');
    setSaveError('');
    try {
      const result = await apiService.getCustomerTrialQuestionnaireDetail(
        state.customerId,
        trialId,
        questionnaire.questionnaire_id
      );
      if (!result.success) {
        throw new Error(result.error || 'Failed to load questionnaire detail');
      }

      setActiveQuestionnaire({ trialId, questionnaireId: questionnaire.questionnaire_id });
      setActiveQuestionnaireDetail(result.data);
      setAnswers(result.data?.saved_answers || {});
    } catch (error) {
      setSaveError(error.message || 'Failed to open questionnaire');
    }
  };

  const saveQuestionnaire = async (submit = false) => {
    if (!activeQuestionnaire || !state.customerId) return;
    if (activeQuestionnaireDetail?.response_status === 'submitted') {
      setSaveMessage('This response is already submitted and locked.');
      setSaveError('');
      return;
    }

    setSaveError('');
    setSaveMessage('');
    submit ? setIsSubmittingQuestionnaire(true) : setIsSavingDraft(true);
    try {
      const result = await apiService.saveCustomerTrialQuestionnaireResponse(
        state.customerId,
        activeQuestionnaire.trialId,
        activeQuestionnaire.questionnaireId,
        answers,
        submit
      );
      if (!result.success) {
        throw new Error(result.error || 'Failed to save response');
      }

      setSaveMessage(submit ? 'Questionnaire submitted successfully.' : 'Draft saved.');
      await loadTrialQuestionnaires({ trial_id: activeQuestionnaire.trialId });

      const detail = await apiService.getCustomerTrialQuestionnaireDetail(
        state.customerId,
        activeQuestionnaire.trialId,
        activeQuestionnaire.questionnaireId
      );
      if (detail.success) setActiveQuestionnaireDetail(detail.data);
    } catch (error) {
      setSaveError(error.message || 'Failed to save response');
    } finally {
      setIsSavingDraft(false);
      setIsSubmittingQuestionnaire(false);
    }
  };

  useEffect(() => {
    if (!activeQuestionnaire || !activeQuestionnaireDetail) return undefined;
    if (activeQuestionnaireDetail.response_status === 'submitted') return undefined;

    autosaveTimerRef.current = setInterval(() => {
      saveQuestionnaire(false);
    }, 30000);

    return () => {
      if (autosaveTimerRef.current) {
        clearInterval(autosaveTimerRef.current);
        autosaveTimerRef.current = null;
      }
    };
  }, [activeQuestionnaire, activeQuestionnaireDetail, answers]); // eslint-disable-line react-hooks/exhaustive-deps

  const renderQuestionInput = (question) => {
    const qid = question.id;
    const type = normalizeQuestionType(question.type);
    const value = answers[qid];
    const options = question.options || [];

    const updateAnswer = (nextValue) => {
      setAnswers((prev) => ({ ...prev, [qid]: nextValue }));
    };

    if (type === 'textarea') {
      return <textarea value={value || ''} onChange={(e) => updateAnswer(e.target.value)} rows={3} />;
    }
    if (['number', 'rating', 'scale'].includes(type)) {
      return <input type="number" value={value ?? ''} onChange={(e) => updateAnswer(e.target.value === '' ? null : Number(e.target.value))} />;
    }
    if (['date', 'time', 'datetime'].includes(type)) {
      const inputType = type === 'datetime' ? 'datetime-local' : type;
      return <input type={inputType} value={value || ''} onChange={(e) => updateAnswer(e.target.value)} />;
    }
    if (type === 'yes_no') {
      return (
        <select value={value === undefined || value === null ? '' : String(value)} onChange={(e) => updateAnswer(e.target.value === '' ? null : e.target.value === 'true')}>
          <option value="">Select</option>
          <option value="true">Yes</option>
          <option value="false">No</option>
        </select>
      );
    }
    if (['single_choice', 'dropdown'].includes(type)) {
      return (
        <select value={value || ''} onChange={(e) => updateAnswer(e.target.value)}>
          <option value="">Select an option</option>
          {options.map((opt) => (
            <option key={opt.value} value={opt.value}>{opt.label}</option>
          ))}
        </select>
      );
    }
    if (type === 'multiple_choice') {
      const selected = Array.isArray(value) ? value : [];
      return (
        <div className="question-options">
          {options.map((opt) => (
            <label key={opt.value} className="option-item">
              <input
                type="checkbox"
                checked={selected.includes(opt.value)}
                onChange={(e) => {
                  if (e.target.checked) {
                    updateAnswer([...selected, opt.value]);
                  } else {
                    updateAnswer(selected.filter((v) => v !== opt.value));
                  }
                }}
              />
              {opt.label}
            </label>
          ))}
        </div>
      );
    }
    return <input type="text" value={value || ''} onChange={(e) => updateAnswer(e.target.value)} placeholder={question.placeholder || ''} />;
  };

  const getStatusColor = (status) => {
    switch (status?.toLowerCase()) {
      case 'open':
      case 'recruiting':
      case 'active':
        return '#28a745';
      case 'pending':
      case 'not_yet_recruiting':
      case 'preparing':
      case 'submitted':
      case 'under_review':
        return '#ffc107';
      case 'closed':
      case 'completed':
      case 'withdrawn':
      case 'cancelled':
        return '#6c757d';
      default: return '#17a2b8';
    }
  };

  const getStatusLabel = (status) => {
    switch ((status || '').toLowerCase()) {
      case 'open': return 'Open';
      case 'pending': return 'Pending';
      case 'closed': return 'Closed';
      case 'recruiting': return 'Recruiting';
      case 'not_yet_recruiting': return 'Not Yet Recruiting';
      default: return status || 'Active';
    }
  };

  const resetFilters = () => {
    setSearchTerm('');
    setFilters({
      domain: 'all',
      source: 'all',
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

            {/* Source Filter */}
            <select
              value={filters.source}
              onChange={(e) => handleFilterChange('source', e.target.value)}
              title="Filter by trial source"
            >
              <option value="all">All Sources</option>
              <option value="internal">MannBiome Trials</option>
              <option value="external">Public Trials</option>
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
          <p className="personalization-note">
            {`MannBiome trials: ${filteredTrials.filter((t) => (t.source || 'external') === 'internal').length} | Public trials: ${filteredTrials.filter((t) => (t.source || 'external') === 'external').length}`}
          </p>
          {Object.values(filters).some(f => f !== 'all' && f !== 0 && f !== 999999 && f !== '') && (
            <p className="filters-applied-note">🔍 {Object.entries(filters).filter(([, v]) => v !== 'all' && v !== 0 && v !== 999999 && v !== '').length} filter(s) applied</p>
          )}
        </div>

        {/* Trials List */}
        <div className="trials-grid">
          {paginatedTrials.length > 0 ? paginatedTrials.map((trial) => {
            const trialId = resolveTrialIdentifier(trial);
            const trialUIKey = resolveTrialUIKey(trial);
            const isExpanded = expandedTrials[trialUIKey] || false;
            const isInternalTrial = (trial.source || 'external') === 'internal';
            
            return (
              <div key={trialUIKey} className="trial-card">
                {/* Clickable Header */}
                <div 
                  className="trial-header-clickable"
                  onClick={() => handleToggle(trial)}
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
                        <span className={`trial-source ${isInternalTrial ? 'internal' : 'external'}`}>
                          {isInternalTrial ? 'MannBiome' : 'Public'}
                        </span>
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

                    <div className="questionnaire-section">
                      <div className="questionnaire-header">
                        <h4>Questionnaires</h4>
                        {isInternalTrial && (
                          <button
                            className="questionnaire-load-btn"
                            onClick={(e) => {
                              e.stopPropagation();
                              loadTrialQuestionnaires(trial);
                            }}
                          >
                            Refresh
                          </button>
                        )}
                      </div>

                      {!isInternalTrial && (
                        <p className="questionnaire-info">
                          Questionnaires are available for MannBiome trials only.
                        </p>
                      )}

                      {isInternalTrial && questionnaireLoadingByTrial[trialId] && (
                        <p className="questionnaire-info">Loading linked questionnaires...</p>
                      )}

                      {isInternalTrial && questionnaireErrorByTrial[trialId] && (
                        <p className="questionnaire-error">{questionnaireErrorByTrial[trialId]}</p>
                      )}

                      {isInternalTrial && !questionnaireLoadingByTrial[trialId] && !questionnaireErrorByTrial[trialId] && (
                        <>
                          {Array.isArray(questionnairesByTrial[trialId]) && questionnairesByTrial[trialId].length > 0 ? (
                            <>
                              {eligibilityByTrial[trialId]?.is_eligible === true ? (
                                <p className="questionnaire-success">Eligibility passed. Remaining questionnaires are unlocked.</p>
                              ) : (
                                <p className="questionnaire-lock-note">
                                  Complete and pass eligibility questionnaire first to unlock other questionnaires.
                                </p>
                              )}

                              <div className="questionnaire-list">
                                {(questionnairesByTrial[trialId] || []).map((q) => {
                                  const locked = isQuestionnaireLocked(trialId, q);
                                  const isActive = activeQuestionnaire
                                    && activeQuestionnaire.trialId === trialId
                                    && activeQuestionnaire.questionnaireId === q.questionnaire_id;
                                  return (
                                    <div key={q.questionnaire_id} className={`questionnaire-card ${locked ? 'locked' : ''} ${isActive ? 'active' : ''}`}>
                                      <div className="questionnaire-card-main">
                                        <div>
                                          <div className="questionnaire-title-row">
                                            <strong>{q.questionnaire_name}</strong>
                                            {locked && <span className="lock-badge">Locked</span>}
                                          </div>
                                          <p className="questionnaire-meta">
                                            Type: {q.questionnaire_type} | Questions: {q.question_count} | Progress: {q.progress_percent || 0}% | Visit: {q.current_visit_number || 1}
                                          </p>
                                          {q.next_visit_number && q.unlocks_at_utc && (
                                            <p className="questionnaire-meta">
                                              Next unlock: Visit {q.next_visit_number} at {formatUtcDateTime(q.unlocks_at_utc)}
                                            </p>
                                          )}
                                        </div>
                                        <button
                                          className="questionnaire-open-btn"
                                          disabled={locked}
                                          onClick={(e) => {
                                            e.stopPropagation();
                                            openQuestionnaire(trial, q);
                                          }}
                                        >
                                          {locked ? 'Locked' : `Open Visit ${q.current_visit_number || 1}`}
                                        </button>
                                      </div>
                                    </div>
                                  );
                                })}
                              </div>
                            </>
                          ) : (
                            <p className="questionnaire-info">No linked questionnaires found for this trial.</p>
                          )}
                        </>
                      )}

                      {activeQuestionnaire
                        && activeQuestionnaire.trialId === trialId
                        && activeQuestionnaireDetail && (
                          <div className="questionnaire-form-panel">
                            <div className="questionnaire-form-header">
                              <h4>{activeQuestionnaireDetail.questionnaire?.name}</h4>
                              <span className="autosave-note">
                                Visit {activeQuestionnaireDetail.current_visit_number || 1} (UTC timeline)
                              </span>
                            </div>
                            {activeQuestionnaireDetail?.is_locked && (
                              <p className="questionnaire-lock-note">
                                This questionnaire is locked right now.
                                {activeQuestionnaireDetail?.unlocks_at_utc
                                  ? ` Next unlock: ${formatUtcDateTime(activeQuestionnaireDetail.unlocks_at_utc)}.`
                                  : ''}
                              </p>
                            )}
                            <p className="questionnaire-description">
                              {activeQuestionnaireDetail.questionnaire?.description || 'Please answer all required questions.'}
                            </p>

                            {(activeQuestionnaireDetail.questionnaire?.questions || []).map((question) => (
                              <div key={question.id} className="question-item">
                                <label>
                                  {question.text} {question.isRequired && <span className="required-star">*</span>}
                                </label>
                                {renderQuestionInput(question)}
                              </div>
                            ))}

                            {saveMessage && <p className="questionnaire-success">{saveMessage}</p>}
                            {saveError && <p className="questionnaire-error">{saveError}</p>}

                            <div className="questionnaire-actions">
                              <button
                                className="questionnaire-save-btn"
                                onClick={(e) => {
                                  e.stopPropagation();
                                  saveQuestionnaire(false);
                                }}
                                disabled={
                                  isSavingDraft ||
                                  isSubmittingQuestionnaire ||
                                  activeQuestionnaireDetail?.is_locked ||
                                  activeQuestionnaireDetail?.response_status === 'submitted'
                                }
                              >
                                {activeQuestionnaireDetail?.response_status === 'submitted'
                                  ? 'Locked'
                                  : activeQuestionnaireDetail?.is_locked
                                    ? 'Locked'
                                  : isSavingDraft
                                    ? 'Saving...'
                                    : 'Save Draft'}
                              </button>
                              <button
                                className="questionnaire-submit-btn"
                                onClick={(e) => {
                                  e.stopPropagation();
                                  saveQuestionnaire(true);
                                }}
                                disabled={
                                  isSavingDraft ||
                                  isSubmittingQuestionnaire ||
                                  activeQuestionnaireDetail?.is_locked ||
                                  activeQuestionnaireDetail?.response_status === 'submitted'
                                }
                              >
                                {isSubmittingQuestionnaire
                                  ? 'Submitting...'
                                  : activeQuestionnaireDetail?.response_status === 'submitted'
                                    ? 'Submitted'
                                    : activeQuestionnaireDetail?.is_locked
                                      ? 'Locked'
                                      : `Submit Visit ${activeQuestionnaireDetail.current_visit_number || 1}`}
                              </button>
                            </div>
                          </div>
                        )}
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
                          disabled={!trial.url}
                        >
                          {trial.url ? 'View on ClinicalTrials.gov' : 'Local Trial'}
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