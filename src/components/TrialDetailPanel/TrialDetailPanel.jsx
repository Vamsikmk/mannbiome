// components/TrialDetailPanel/TrialDetailPanel.jsx
// Shared questionnaire experience — used by MyTrials (and can be reused elsewhere)
import React, { useState, useEffect, useCallback, useRef } from 'react';
import apiService from '../../services/api';
import './TrialDetailPanel.css';

const normalizeQuestionType = (type) => String(type || '').toLowerCase();

const isEligibilityQuestionnaire = (q) =>
  normalizeQuestionType(q?.questionnaire_type) === 'eligibility';

const formatUtcDateTime = (value) => {
  if (!value) return '';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return '';
  return `${date.toISOString().replace('T', ' ').slice(0, 16)} UTC`;
};

const TrialDetailPanel = ({ trial, customerId, onBack }) => {
  const trialId = trial?.trial_id || trial?.id;

  // Questionnaire state
  const [questionnaires, setQuestionnaires] = useState([]);
  const [eligibility, setEligibility] = useState(null);
  const [qLoading, setQLoading] = useState(false);
  const [qError, setQError] = useState('');

  // Active questionnaire state
  const [activeQuestionnaire, setActiveQuestionnaire] = useState(null);
  const [activeQuestionnaireDetail, setActiveQuestionnaireDetail] = useState(null);
  const [answers, setAnswers] = useState({});
  const [saveMessage, setSaveMessage] = useState('');
  const [saveError, setSaveError] = useState('');
  const [isSavingDraft, setIsSavingDraft] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const autosaveRef = useRef(null);

  // Consent gate state
  const [consentStatus, setConsentStatus] = useState(null);
  const [consentAgreed, setConsentAgreed] = useState(false);
  const [isSigning, setIsSigning] = useState(false);
  const [consentError, setConsentError] = useState('');

  // Load questionnaires on mount
  const loadQuestionnaires = useCallback(async () => {
    if (!trialId || !customerId) return;
    setQLoading(true);
    setQError('');
    try {
      const [qResult, eligResult, consentResult] = await Promise.all([
        apiService.getCustomerTrialQuestionnaires(customerId, trialId),
        apiService.getCustomerTrialEligibilityResult(customerId, trialId),
        apiService.getConsentStatus(customerId, trialId),
      ]);
      if (!qResult.success) throw new Error(qResult.error || 'Failed to load questionnaires');
      setQuestionnaires(qResult.questionnaires || []);
      if (eligResult?.success && eligResult?.data) setEligibility(eligResult.data);
      if (consentResult?.success && consentResult?.data) setConsentStatus(consentResult.data);
    } catch (err) {
      setQError(err.message || 'Failed to load questionnaires');
    } finally {
      setQLoading(false);
    }
  }, [trialId, customerId]);

  useEffect(() => { loadQuestionnaires(); }, [loadQuestionnaires]);

  // Autosave every 30s while a questionnaire is open
  useEffect(() => {
    if (!activeQuestionnaire || !activeQuestionnaireDetail) return;
    if (activeQuestionnaireDetail.response_status === 'submitted') return;
    autosaveRef.current = setInterval(() => saveQuestionnaire(false), 30000);
    return () => { clearInterval(autosaveRef.current); autosaveRef.current = null; };
  }, [activeQuestionnaire, activeQuestionnaireDetail, answers]); // eslint-disable-line react-hooks/exhaustive-deps

  const consentRequired = consentStatus?.has_consent_form === true && consentStatus?.has_signed !== true;

  const isLocked = (q) => {
    if (q?.is_locked) return true;
    const hasEligQ = questionnaires.some(isEligibilityQuestionnaire);
    if (isEligibilityQuestionnaire(q)) return false;
    if (hasEligQ && eligibility?.is_eligible !== true) return true;
    if (consentRequired) return true;
    return false;
  };

  const handleSignConsent = async () => {
    setConsentError('');
    setIsSigning(true);
    try {
      const result = await apiService.signConsent(customerId, trialId);
      if (!result.success) throw new Error(result.error || 'Failed to sign consent');
      setConsentStatus((prev) => ({ ...prev, has_signed: true, signature: result.data?.signature }));
    } catch (err) {
      setConsentError(err.message || 'Failed to sign consent. Please try again.');
    } finally {
      setIsSigning(false);
    }
  };

  const openQuestionnaire = async (q) => {
    if (isLocked(q)) return;
    setSaveMessage(''); setSaveError('');
    try {
      const result = await apiService.getCustomerTrialQuestionnaireDetail(customerId, trialId, q.questionnaire_id);
      if (!result.success) throw new Error(result.error || 'Failed to load questionnaire');
      setActiveQuestionnaire({ trialId, questionnaireId: q.questionnaire_id });
      setActiveQuestionnaireDetail(result.data);
      setAnswers(result.data?.saved_answers || {});
    } catch (err) {
      setSaveError(err.message || 'Failed to open questionnaire');
    }
  };

  const saveQuestionnaire = async (submit = false) => {
    if (!activeQuestionnaire || !customerId) return;
    if (activeQuestionnaireDetail?.response_status === 'submitted') {
      setSaveMessage('This response is already submitted and locked.');
      return;
    }
    setSaveError(''); setSaveMessage('');
    submit ? setIsSubmitting(true) : setIsSavingDraft(true);
    try {
      const result = await apiService.saveCustomerTrialQuestionnaireResponse(
        customerId, activeQuestionnaire.trialId, activeQuestionnaire.questionnaireId, answers, submit
      );
      if (!result.success) throw new Error(result.error || 'Failed to save');
      setSaveMessage(submit ? 'Questionnaire submitted successfully.' : 'Draft saved.');
      await loadQuestionnaires();
      const detail = await apiService.getCustomerTrialQuestionnaireDetail(
        customerId, activeQuestionnaire.trialId, activeQuestionnaire.questionnaireId
      );
      if (detail.success) setActiveQuestionnaireDetail(detail.data);
    } catch (err) {
      setSaveError(err.message || 'Failed to save');
    } finally {
      setIsSavingDraft(false); setIsSubmitting(false);
    }
  };

  const renderQuestionInput = (question) => {
    const qid = question.id;
    const type = normalizeQuestionType(question.type);
    const value = answers[qid];
    const options = question.options || [];
    const update = (v) => setAnswers((prev) => ({ ...prev, [qid]: v }));

    if (type === 'textarea')
      return <textarea value={value || ''} onChange={(e) => update(e.target.value)} rows={3} />;
    if (['number', 'rating', 'scale'].includes(type))
      return <input type="number" value={value ?? ''} onChange={(e) => update(e.target.value === '' ? null : Number(e.target.value))} />;
    if (['date', 'time', 'datetime'].includes(type))
      return <input type={type === 'datetime' ? 'datetime-local' : type} value={value || ''} onChange={(e) => update(e.target.value)} />;
    if (type === 'yes_no')
      return (
        <select value={value === undefined || value === null ? '' : String(value)} onChange={(e) => update(e.target.value === '' ? null : e.target.value === 'true')}>
          <option value="">Select</option>
          <option value="true">Yes</option>
          <option value="false">No</option>
        </select>
      );
    if (['single_choice', 'dropdown'].includes(type))
      return (
        <select value={value || ''} onChange={(e) => update(e.target.value)}>
          <option value="">Select an option</option>
          {options.map((opt) => <option key={opt.value} value={opt.value}>{opt.label}</option>)}
        </select>
      );
    if (type === 'multiple_choice') {
      const selected = Array.isArray(value) ? value : [];
      return (
        <div className="tdp-question-options">
          {options.map((opt) => (
            <label key={opt.value} className="tdp-option-item">
              <input type="checkbox" checked={selected.includes(opt.value)}
                onChange={(e) => update(e.target.checked ? [...selected, opt.value] : selected.filter((v) => v !== opt.value))} />
              {opt.label}
            </label>
          ))}
        </div>
      );
    }
    return <input type="text" value={value || ''} onChange={(e) => update(e.target.value)} placeholder={question.placeholder || ''} />;
  };

  return (
    <div className="tdp-container">
      {/* Trial header */}
      <div className="tdp-header">
        <button className="tdp-back-btn" onClick={onBack}>
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <polyline points="15 18 9 12 15 6"></polyline>
          </svg>
          Back to My Trials
        </button>
        <div className="tdp-trial-info">
          <h2 className="tdp-trial-name">{trial?.name || trial?.trial_name || `Trial #${trialId}`}</h2>
          {trial?.trial_description && <p className="tdp-trial-desc">{trial.trial_description}</p>}
          <div className="tdp-trial-meta">
            {trial?.sponsor_name && <span className="tdp-meta-tag">{trial.sponsor_name}</span>}
            {trial?.product_name && <span className="tdp-meta-tag">{trial.product_name}</span>}
            <span className="tdp-enrolled-badge">
              <svg viewBox="0 0 20 20" fill="currentColor">
                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
              </svg>
              Enrolled
            </span>
          </div>
        </div>
      </div>

      {/* Questionnaires section */}
      <div className="tdp-section">
        <div className="tdp-section-header">
          <h3>Questionnaires</h3>
          <button className="tdp-refresh-btn" onClick={loadQuestionnaires} disabled={qLoading}>
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <polyline points="23 4 23 10 17 10"></polyline>
              <path d="M20.49 15a9 9 0 11-2.12-9.36L23 10"></path>
            </svg>
            Refresh
          </button>
        </div>

        {qLoading && <p className="tdp-info">Loading questionnaires…</p>}
        {qError && <p className="tdp-error">{qError}</p>}

        {!qLoading && !qError && (
          <>
            {questionnaires.length === 0 ? (
              <p className="tdp-info">No questionnaires linked to this trial.</p>
            ) : (
              <>
                {eligibility?.is_eligible === true ? (
                  <p className="tdp-success">Eligibility passed.</p>
                ) : (
                  <p className="tdp-lock-note">Complete and pass the eligibility questionnaire first to unlock others.</p>
                )}

                {/* Consent gate — shown after eligibility passes, if consent form exists and not yet signed */}
                {eligibility?.is_eligible === true && consentStatus?.has_consent_form === true && (
                  <div className={`tdp-consent-gate ${consentStatus.has_signed ? 'signed' : 'pending'}`}>
                    {consentStatus.has_signed ? (
                      <div className="tdp-consent-signed">
                        <svg viewBox="0 0 20 20" fill="currentColor" className="tdp-consent-check">
                          <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                        </svg>
                        <span>Consent form signed. All questionnaires are unlocked.</span>
                      </div>
                    ) : (
                      <>
                        <div className="tdp-consent-header">
                          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="tdp-consent-icon">
                            <path d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                          </svg>
                          <strong>Consent Form Required</strong>
                        </div>
                        <p className="tdp-consent-desc">
                          Before accessing the remaining questionnaires, you must review and sign the consent form for this trial.
                        </p>
                        {consentStatus.consent_document?.s3_url && (
                          <a
                            href={consentStatus.consent_document.s3_url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="tdp-consent-doc-link"
                          >
                            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                              <path d="M15 3H6a2 2 0 00-2 2v14a2 2 0 002 2h12a2 2 0 002-2V8z" />
                              <polyline points="13 3 13 8 18 8" />
                            </svg>
                            View Consent Form: {consentStatus.consent_document.document_name}
                          </a>
                        )}
                        <label className="tdp-consent-checkbox">
                          <input
                            type="checkbox"
                            checked={consentAgreed}
                            onChange={(e) => setConsentAgreed(e.target.checked)}
                          />
                          I have read and agree to the terms and conditions of this consent form.
                        </label>
                        {consentError && <p className="tdp-error">{consentError}</p>}
                        <button
                          className="tdp-consent-sign-btn"
                          disabled={!consentAgreed || isSigning}
                          onClick={handleSignConsent}
                        >
                          {isSigning ? 'Signing…' : 'Sign & Continue'}
                        </button>
                      </>
                    )}
                  </div>
                )}

                <div className="tdp-questionnaire-list">
                  {questionnaires.map((q) => {
                    const locked = isLocked(q);
                    const isActive = activeQuestionnaire?.questionnaireId === q.questionnaire_id;
                    return (
                      <div key={q.questionnaire_id} className={`tdp-q-card ${locked ? 'locked' : ''} ${isActive ? 'active' : ''}`}>
                        {/* Questionnaire card header */}
                        <div className="tdp-q-card-main">
                          <div className="tdp-q-info">
                            <div className="tdp-q-title-row">
                              <strong>{q.questionnaire_name}</strong>
                              {locked && <span className="tdp-lock-badge">Locked</span>}
                            </div>
                            <p className="tdp-q-meta">
                              Type: {q.questionnaire_type} | Questions: {q.question_count} | Progress: {q.progress_percent || 0}% | Visit: {q.current_visit_number || 1}
                            </p>
                            {q.next_visit_number && q.unlocks_at_utc && (
                              <p className="tdp-q-meta">
                                Next unlock: Visit {q.next_visit_number} at {formatUtcDateTime(q.unlocks_at_utc)}
                              </p>
                            )}
                          </div>
                          <button
                            className="tdp-open-btn"
                            disabled={locked}
                            onClick={() => openQuestionnaire(q)}
                          >
                            {locked ? 'Locked' : `Open Visit ${q.current_visit_number || 1}`}
                          </button>
                        </div>

                        {/* Inline questionnaire form */}
                        {isActive && activeQuestionnaireDetail && (
                          <div className="tdp-form-panel">
                            <div className="tdp-form-header">
                              <h4>{activeQuestionnaireDetail.questionnaire?.name}</h4>
                              <span className="tdp-autosave-note">
                                Visit {activeQuestionnaireDetail.current_visit_number || 1} · autosaves every 30s
                              </span>
                            </div>

                            {activeQuestionnaireDetail?.is_locked && (
                              <p className="tdp-lock-note">
                                This questionnaire is locked.
                                {activeQuestionnaireDetail?.unlocks_at_utc
                                  ? ` Next unlock: ${formatUtcDateTime(activeQuestionnaireDetail.unlocks_at_utc)}.`
                                  : ''}
                              </p>
                            )}

                            <p className="tdp-form-desc">
                              {activeQuestionnaireDetail.questionnaire?.description || 'Please answer all required questions.'}
                            </p>

                            {(activeQuestionnaireDetail.questionnaire?.questions || []).map((question) => (
                              <div key={question.id} className="tdp-question-item">
                                <label>
                                  {question.text}
                                  {question.isRequired && <span className="tdp-required">*</span>}
                                </label>
                                {renderQuestionInput(question)}
                              </div>
                            ))}

                            {saveMessage && <p className="tdp-success">{saveMessage}</p>}
                            {saveError && <p className="tdp-error">{saveError}</p>}

                            <div className="tdp-form-actions">
                              <button
                                className="tdp-save-btn"
                                onClick={() => saveQuestionnaire(false)}
                                disabled={isSavingDraft || isSubmitting || activeQuestionnaireDetail?.is_locked || activeQuestionnaireDetail?.response_status === 'submitted'}
                              >
                                {activeQuestionnaireDetail?.response_status === 'submitted' ? 'Locked'
                                  : activeQuestionnaireDetail?.is_locked ? 'Locked'
                                  : isSavingDraft ? 'Saving…'
                                  : 'Save Draft'}
                              </button>
                              <button
                                className="tdp-submit-btn"
                                onClick={() => saveQuestionnaire(true)}
                                disabled={isSavingDraft || isSubmitting || activeQuestionnaireDetail?.is_locked || activeQuestionnaireDetail?.response_status === 'submitted'}
                              >
                                {isSubmitting ? 'Submitting…'
                                  : activeQuestionnaireDetail?.response_status === 'submitted' ? 'Submitted ✓'
                                  : activeQuestionnaireDetail?.is_locked ? 'Locked'
                                  : `Submit Visit ${activeQuestionnaireDetail.current_visit_number || 1}`}
                              </button>
                              <button className="tdp-close-btn" onClick={() => { setActiveQuestionnaire(null); setActiveQuestionnaireDetail(null); }}>
                                Close
                              </button>
                            </div>
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              </>
            )}
          </>
        )}
      </div>
    </div>
  );
};

export default TrialDetailPanel;
