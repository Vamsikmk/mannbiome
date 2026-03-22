// pages/MyTrials/MyTrials.jsx
import React, { useState, useEffect, useCallback } from 'react';
import { useAppContext } from '../../context';
import apiService from '../../services/api';
import TrialDetailPanel from '../../components/TrialDetailPanel/TrialDetailPanel';
import './MyTrials.css';

const MyTrials = () => {
  const { state, navigateToPage } = useAppContext();
  const [enrolledTrials, setEnrolledTrials] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [selectedTrial, setSelectedTrial] = useState(null);

  const fetchEnrolledTrials = useCallback(async () => {
    if (!state.customerId) return;
    setLoading(true);
    setError('');
    try {
      // Only internal (MannBiome) trials have questionnaires/eligibility
      const trialsResult = await apiService.getInternalClinicalTrials(1000);
      const allTrials = trialsResult?.trials || [];

      // Check eligibility for each trial concurrently
      const eligibilityChecks = await Promise.allSettled(
        allTrials.map((trial) => {
          const trialId = trial.trial_id || trial.id;
          return apiService
            .getCustomerTrialEligibilityResult(state.customerId, trialId)
            .then((res) => ({ trial, eligibility: res }));
        })
      );

      // Keep only trials where customer actively passed eligibility
      // is_eligible=true AND completed_required_questionnaires > 0
      // (without the second check, trials with no questionnaires return is_eligible=true by default)
      const passed = eligibilityChecks
        .filter((r) => {
          if (r.status !== 'fulfilled') return false;
          const eligData = r.value?.eligibility?.data; // request() wraps response in { success, data }
          return (
            eligData?.is_eligible === true &&
            eligData?.completed_required_questionnaires > 0
          );
        })
        .map((r) => r.value.trial);

      setEnrolledTrials(passed);
    } catch (err) {
      setError('Failed to load your trials. Please try again.');
      console.error('MyTrials fetch error:', err);
    } finally {
      setLoading(false);
    }
  }, [state.customerId]);

  useEffect(() => {
    fetchEnrolledTrials();
  }, [fetchEnrolledTrials]);

  const getStatusColor = (status) => {
    const map = {
      active: '#10b981',
      recruiting: '#3b82f6',
      completed: '#6b7280',
      pending: '#f59e0b',
    };
    return map[status?.toLowerCase()] || '#6b7280';
  };

  // Show trial detail with questionnaires inline
  if (selectedTrial) {
    return (
      <div className="my-trials-container">
        <TrialDetailPanel
          trial={selectedTrial}
          customerId={state.customerId}
          onBack={() => setSelectedTrial(null)}
        />
      </div>
    );
  }

  return (
    <div className="my-trials-container">
      {/* Header */}
      <div className="my-trials-header">
        <button className="back-button" onClick={() => navigateToPage('clinical-trials')}>
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <polyline points="15 18 9 12 15 6"></polyline>
          </svg>
          Back to Clinical Trials
        </button>
        <div className="my-trials-title-row">
          <div>
            <h1 className="my-trials-title">My Trials</h1>
            <p className="my-trials-subtitle">
              Trials you are enrolled in — eligibility confirmed
            </p>
          </div>
          <button className="refresh-button" onClick={fetchEnrolledTrials} disabled={loading}>
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <polyline points="23 4 23 10 17 10"></polyline>
              <path d="M20.49 15a9 9 0 11-2.12-9.36L23 10"></path>
            </svg>
            Refresh
          </button>
        </div>
      </div>

      {/* Content */}
      {loading ? (
        <div className="my-trials-loading">
          <div className="spinner"></div>
          <p>Loading your trials…</p>
        </div>
      ) : error ? (
        <div className="my-trials-error">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <circle cx="12" cy="12" r="10"></circle>
            <line x1="12" y1="8" x2="12" y2="12"></line>
            <line x1="12" y1="16" x2="12.01" y2="16"></line>
          </svg>
          {error}
        </div>
      ) : enrolledTrials.length === 0 ? (
        <div className="my-trials-empty">
          <svg viewBox="0 0 64 64" fill="none" stroke="currentColor" strokeWidth="1.5">
            <rect x="8" y="8" width="48" height="56" rx="4"></rect>
            <path d="M20 24h24M20 32h24M20 40h16"></path>
            <circle cx="48" cy="48" r="12" fill="#d1fae5" stroke="#10b981" strokeWidth="2"></circle>
            <path d="M43 48l3 3 6-6" stroke="#10b981" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"></path>
          </svg>
          <p className="empty-title">No enrolled trials yet</p>
          <p className="empty-subtitle">
            Complete an eligibility questionnaire on a trial to get enrolled here.
          </p>
          <button className="browse-button" onClick={() => navigateToPage('clinical-trials')}>
            Browse Clinical Trials
          </button>
        </div>
      ) : (
        <div className="my-trials-list">
          <p className="enrolled-count">
            {enrolledTrials.length} trial{enrolledTrials.length !== 1 ? 's' : ''} enrolled
          </p>
          {enrolledTrials.map((trial) => {
            const trialId = trial.trial_id || trial.id;
            const status = trial.trial_status || trial.status || 'active';
            return (
              <div key={trialId} className="my-trial-card">
                <div className="trial-card-left">
                  <div className="enrolled-badge">
                    <svg viewBox="0 0 20 20" fill="currentColor">
                      <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                    </svg>
                    Enrolled
                  </div>
                  <h3 className="trial-card-name">{trial.trial_name || trial.name || `Trial #${trialId}`}</h3>
                  {trial.trial_description && (
                    <p className="trial-card-desc">{trial.trial_description}</p>
                  )}
                  <div className="trial-card-meta">
                    {trial.sponsor_name && <span className="meta-tag">{trial.sponsor_name}</span>}
                    {trial.product_name && <span className="meta-tag">{trial.product_name}</span>}
                  </div>
                </div>
                <div className="trial-card-right">
                  <span
                    className="trial-status-badge"
                    style={{ background: `${getStatusColor(status)}20`, color: getStatusColor(status) }}
                  >
                    {status.charAt(0).toUpperCase() + status.slice(1)}
                  </span>
                  <button
                    className="open-trial-button"
                    onClick={() => setSelectedTrial(trial)}
                  >
                    Open Trial
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <polyline points="9 18 15 12 9 6"></polyline>
                    </svg>
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};

export default MyTrials;
