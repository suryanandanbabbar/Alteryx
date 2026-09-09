import React, { useState, useEffect } from 'react';
import { Mail, Send, X, AlertCircle, Loader2 } from 'lucide-react';
import { RationalisationCandidateDTO } from '../types/portfolio';

interface EmailCompositionModalProps {
  candidate: RationalisationCandidateDTO;
  portfolioId: string;
  fromAddress?: string | null;
  onClose: () => void;
  onSuccess: (recipient: string) => void;
}

const EMAIL_REGEX = /^[a-zA-Z0-9.!#$%&'*+/=?^_`{|}~-]+@[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(?:\.[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)+$/;

export function buildDefaultEmailSubject(candidate: RationalisationCandidateDTO): string {
  const rec = (candidate.recommendation_type || '').toUpperCase();
  const dse = candidate.data_subsumption_evidence || candidate.consolidation_decision?.data_subsumption_evidence;
  
  if (rec === 'CONSOLIDATE') {
    if (dse && dse.source_workflow_name && dse.target_workflow_name) {
      return `ETL Rationalisation Recommendation – Consolidation: ${dse.source_workflow_name} → ${dse.target_workflow_name}`;
    }
    if (candidate.workflow_names.length >= 2) {
      return `ETL Rationalisation Recommendation – Consolidation: ${candidate.workflow_names[0]} & ${candidate.workflow_names[1]}`;
    }
    return `ETL Rationalisation Recommendation – Consolidation: ${candidate.workflow_names.join(', ')}`;
  }
  
  const primaryWf = candidate.workflow_names[0] || 'Workflow';
  return `ETL Rationalisation Recommendation – Retirement: ${primaryWf}`;
}

export function buildDefaultEmailBody(candidate: RationalisationCandidateDTO, fromAddr: string): string {
  const rec = (candidate.recommendation_type || (candidate as any).recommendation_category || 'CONSOLIDATE').toUpperCase();
  const metrics = candidate.deterministic_metrics || {
    source_overlap: 0,
    target_overlap: 0,
    frequency_overlap: 0,
    transformation_similarity: 0,
    dag_similarity: 0,
  };

  const lines: string[] = [];

  // 1. Salutation
  lines.push('Hello,\n');
  lines.push('I’m sharing the ETL rationalisation recommendation below for your review.\n');

  // 2. Recommendation Section
  lines.push('Recommendation');
  lines.push(rec);
  lines.push('');

  // 3. Workflows in Scope Section
  lines.push('Workflows in Scope');
  if (candidate.workflow_names && candidate.workflow_names.length > 0) {
    candidate.workflow_names.forEach((name) => {
      lines.push(`• ${name}`);
    });
  } else {
    lines.push('• Workflow evaluation candidate');
  }
  lines.push('');

  // 4. Recommendation Rationale Section
  lines.push('Recommendation Rationale');
  if (candidate.reasoning && candidate.reasoning.trim()) {
    lines.push(candidate.reasoning.trim());
  } else {
    lines.push('Deterministic evaluation identified overlapping pipeline architecture and functional redundancy.');
  }
  lines.push('');

  // 5. Supporting Evidence Section
  lines.push('Supporting Evidence');
  const evidenceItems: string[] = [];
  if (metrics.source_overlap !== undefined && metrics.source_overlap !== null) {
    evidenceItems.push(`• Source overlap: ${Math.round(metrics.source_overlap * 100)}%`);
  }
  if (metrics.target_overlap !== undefined && metrics.target_overlap !== null) {
    evidenceItems.push(`• Target overlap: ${Math.round(metrics.target_overlap * 100)}%`);
  }
  if (metrics.frequency_overlap !== undefined && metrics.frequency_overlap !== null) {
    evidenceItems.push(`• Frequency alignment: ${Math.round(metrics.frequency_overlap * 100)}%`);
  }
  if (metrics.transformation_similarity !== undefined && metrics.transformation_similarity !== null) {
    evidenceItems.push(`• Transformation similarity: ${Math.round(metrics.transformation_similarity * 100)}%`);
  }
  if (metrics.dag_similarity !== undefined && metrics.dag_similarity !== null) {
    evidenceItems.push(`• DAG topology similarity: ${Math.round(metrics.dag_similarity * 100)}%`);
  }
  if (evidenceItems.length > 0) {
    lines.push(...evidenceItems);
  } else {
    lines.push('• High structural and schema overlap observed across pipeline stages.');
  }
  lines.push('');

  // 6. Pre-Decommissioning & Execution Validation Section
  if (candidate.validation_requirements && candidate.validation_requirements.length > 0) {
    lines.push('Pre-Decommissioning & Execution Validation');
    candidate.validation_requirements.forEach((req) => {
      const cleanReq = req.replace(/^(\[\s*\]|\[x\]|•|-)\s*/i, '').trim();
      lines.push(`• ${cleanReq}`);
    });
    lines.push('');
  }

  // 7. Review Call-to-action
  lines.push('Please review the recommendation and validation points before any implementation or decommissioning activity is undertaken.\n');

  // 8. Sign-off
  lines.push('Regards,');
  lines.push(fromAddr.trim() || 'ETL Migration Lead');

  return lines.join('\n');
}

export const EmailCompositionModal: React.FC<EmailCompositionModalProps> = ({
  candidate,
  fromAddress,
  onClose,
  onSuccess,
}) => {
  const initialFrom = fromAddress?.trim() || 'team-lead@enterprise.corp';
  const [fromEmail, setFromEmail] = useState(initialFrom);
  const [toEmail, setToEmail] = useState('');
  const [subject, setSubject] = useState(() => buildDefaultEmailSubject(candidate));
  const [body, setBody] = useState(() => buildDefaultEmailBody(candidate, initialFrom));
  const [isBodyEdited, setIsBodyEdited] = useState(false);
  const [isSending, setIsSending] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [validationError, setValidationError] = useState<string | null>(null);

  // Close on Escape key press
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && !isSending) {
        onClose();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [onClose, isSending]);

  // Update body signature if From changes and body has not been manually edited
  const handleFromChange = (newFrom: string) => {
    setFromEmail(newFrom);
    if (validationError) setValidationError(null);
    if (!isBodyEdited) {
      setBody(buildDefaultEmailBody(candidate, newFrom));
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMessage(null);
    setValidationError(null);

    const trimmedFrom = fromEmail.trim();
    if (!trimmedFrom) {
      setValidationError('Please enter a sender "From" email address.');
      return;
    }
    if (!EMAIL_REGEX.test(trimmedFrom)) {
      setValidationError(`Invalid sender email address format: "${trimmedFrom}".`);
      return;
    }

    const trimmedTo = toEmail.trim();
    if (!trimmedTo) {
      setValidationError('Please enter a recipient email address.');
      return;
    }
    if (!EMAIL_REGEX.test(trimmedTo)) {
      setValidationError(`Invalid recipient email address format: "${trimmedTo}".`);
      return;
    }
    if (!subject.trim()) {
      setValidationError('Email subject cannot be empty.');
      return;
    }
    if (!body.trim()) {
      setValidationError('Email body cannot be empty.');
      return;
    }

    // Demo send flow: instantaneous / smooth simulation with zero SMTP dependency
    setIsSending(true);
    setTimeout(() => {
      setIsSending(false);
      onSuccess(trimmedTo);
    }, 350);
  };

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="email-composition-title"
      style={{
        position: 'fixed',
        inset: 0,
        background: 'rgba(0, 0, 0, 0.82)',
        backdropFilter: 'blur(6px)',
        zIndex: 10002,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '24px',
        boxSizing: 'border-box',
      }}
      onClick={() => {
        if (!isSending) onClose();
      }}
    >
      <div
        style={{
          maxWidth: '780px',
          width: '100%',
          maxHeight: '92vh',
          background: '#0e1622',
          border: '1px solid #1e293b',
          borderRadius: '12px',
          boxShadow: '0 25px 65px rgba(0, 0, 0, 0.8), 0 0 20px rgba(59, 130, 246, 0.1)',
          display: 'flex',
          flexDirection: 'column',
          boxSizing: 'border-box',
          overflow: 'hidden',
          animation: 'fadeInScale 0.2s cubic-bezier(0.16, 1, 0.3, 1)',
        }}
        onClick={(e) => e.stopPropagation()}
      >
        <style>
          {`
            @keyframes fadeInScale {
              from {
                opacity: 0;
                transform: scale(0.97);
              }
              to {
                opacity: 1;
                transform: scale(1);
              }
            }
          `}
        </style>

        {/* Modal Header */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            padding: '20px 24px',
            borderBottom: '1px solid #1e293b',
            background: '#090f18',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <div
              style={{
                width: '32px',
                height: '32px',
                borderRadius: '8px',
                background: 'rgba(59, 130, 246, 0.15)',
                border: '1px solid rgba(59, 130, 246, 0.3)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: '#60a5fa',
              }}
            >
              <Mail size={17} />
            </div>
            <div>
              <h3
                id="email-composition-title"
                style={{
                  fontSize: '16px',
                  fontWeight: '700',
                  color: '#f8fafc',
                  margin: 0,
                  letterSpacing: '-0.01em',
                }}
              >
                Compose Rationalisation Email
              </h3>
              <p style={{ fontSize: '11.5px', color: '#94a3b8', margin: '2px 0 0 0' }}>
                Share recommendation details and validation checklist directly with stakeholders
              </p>
            </div>
          </div>

          <button
            onClick={onClose}
            disabled={isSending}
            style={{
              background: '#1e293b',
              border: '1px solid #334155',
              borderRadius: '6px',
              padding: '6px',
              color: '#94a3b8',
              cursor: isSending ? 'not-allowed' : 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              opacity: isSending ? 0.5 : 1,
              transition: 'background 0.15s ease',
            }}
            title="Close"
          >
            <X size={16} />
          </button>
        </div>

        {/* Form Content */}
        <form
          onSubmit={handleSubmit}
          style={{
            display: 'flex',
            flexDirection: 'column',
            gap: '16px',
            padding: '20px 24px',
            overflowY: 'auto',
            flex: 1,
          }}
        >
          {/* Error Banner */}
          {(errorMessage || validationError) && (
            <div
              role="alert"
              style={{
                display: 'flex',
                alignItems: 'flex-start',
                gap: '10px',
                background: 'rgba(239, 68, 68, 0.12)',
                border: '1px solid rgba(239, 68, 68, 0.35)',
                borderRadius: '8px',
                padding: '12px 14px',
                color: '#fca5a5',
                fontSize: '12.5px',
              }}
            >
              <AlertCircle size={17} color="#ef4444" style={{ flexShrink: 0, marginTop: '1px' }} />
              <div style={{ flex: 1 }}>{errorMessage || validationError}</div>
            </div>
          )}

          {/* From Field (Fully Editable) */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
            <label
              htmlFor="email-from-input"
              style={{
                fontSize: '11.5px',
                fontWeight: '700',
                textTransform: 'uppercase',
                letterSpacing: '0.06em',
                color: '#cbd5e1',
              }}
            >
              From Address <span style={{ color: '#ef4444' }}>*</span>
            </label>
            <input
              id="email-from-input"
              type="email"
              required
              value={fromEmail}
              disabled={isSending}
              placeholder="e.g. suryanandan.babbar@exlservice.com"
              onChange={(e) => handleFromChange(e.target.value)}
              style={{
                background: '#070c14',
                border: '1px solid #334155',
                borderRadius: '6px',
                padding: '9px 12px',
                fontSize: '13.5px',
                color: '#f8fafc',
                outline: 'none',
                transition: 'border-color 0.15s ease',
              }}
              onFocus={(e) => (e.target.style.borderColor = '#3b82f6')}
              onBlur={(e) => (e.target.style.borderColor = '#334155')}
            />
          </div>

          {/* To Field (Editable) */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
            <label
              htmlFor="email-to-input"
              style={{
                fontSize: '11.5px',
                fontWeight: '700',
                textTransform: 'uppercase',
                letterSpacing: '0.06em',
                color: '#cbd5e1',
              }}
            >
              To Recipient <span style={{ color: '#ef4444' }}>*</span>
            </label>
            <input
              id="email-to-input"
              type="email"
              required
              placeholder="e.g. neha.luthra@exlservice.com"
              value={toEmail}
              disabled={isSending}
              onChange={(e) => {
                setToEmail(e.target.value);
                if (validationError) setValidationError(null);
              }}
              style={{
                background: '#070c14',
                border: '1px solid #334155',
                borderRadius: '6px',
                padding: '9px 12px',
                fontSize: '13.5px',
                color: '#f8fafc',
                outline: 'none',
                transition: 'border-color 0.15s ease',
              }}
              onFocus={(e) => (e.target.style.borderColor = '#3b82f6')}
              onBlur={(e) => (e.target.style.borderColor = '#334155')}
            />
          </div>

          {/* Subject Field */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
            <label
              htmlFor="email-subject-input"
              style={{
                fontSize: '11.5px',
                fontWeight: '700',
                textTransform: 'uppercase',
                letterSpacing: '0.06em',
                color: '#cbd5e1',
              }}
            >
              Subject <span style={{ color: '#ef4444' }}>*</span>
            </label>
            <input
              id="email-subject-input"
              type="text"
              required
              value={subject}
              disabled={isSending}
              onChange={(e) => {
                setSubject(e.target.value);
                if (validationError) setValidationError(null);
              }}
              style={{
                background: '#070c14',
                border: '1px solid #334155',
                borderRadius: '6px',
                padding: '9px 12px',
                fontSize: '13.5px',
                color: '#f8fafc',
                outline: 'none',
                transition: 'border-color 0.15s ease',
              }}
              onFocus={(e) => (e.target.style.borderColor = '#3b82f6')}
              onBlur={(e) => (e.target.style.borderColor = '#334155')}
            />
          </div>

          {/* Body Field */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', flex: 1 }}>
            <label
              htmlFor="email-body-input"
              style={{
                fontSize: '11.5px',
                fontWeight: '700',
                textTransform: 'uppercase',
                letterSpacing: '0.06em',
                color: '#cbd5e1',
              }}
            >
              Message Body (Editable) <span style={{ color: '#ef4444' }}>*</span>
            </label>
            <textarea
              id="email-body-input"
              required
              rows={12}
              value={body}
              disabled={isSending}
              onChange={(e) => {
                setBody(e.target.value);
                setIsBodyEdited(true);
                if (validationError) setValidationError(null);
              }}
              style={{
                background: '#070c14',
                border: '1px solid #334155',
                borderRadius: '6px',
                padding: '12px 14px',
                fontSize: '13px',
                lineHeight: '1.65',
                color: '#f8fafc',
                fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif',
                resize: 'vertical',
                minHeight: '260px',
                outline: 'none',
                transition: 'border-color 0.15s ease',
              }}
              onFocus={(e) => (e.target.style.borderColor = '#3b82f6')}
              onBlur={(e) => (e.target.style.borderColor = '#334155')}
            />
          </div>

          {/* Modal Footer Actions */}
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'flex-end',
              gap: '12px',
              paddingTop: '12px',
              borderTop: '1px solid #1e293b',
              marginTop: '4px',
            }}
          >
            <button
              type="button"
              onClick={onClose}
              disabled={isSending}
              style={{
                background: 'transparent',
                border: '1px solid #334155',
                borderRadius: '6px',
                padding: '8px 16px',
                fontSize: '13px',
                fontWeight: '600',
                color: '#94a3b8',
                cursor: isSending ? 'not-allowed' : 'pointer',
                opacity: isSending ? 0.5 : 1,
                transition: 'all 0.15s ease',
              }}
              onMouseEnter={(e) => {
                if (!isSending) e.currentTarget.style.borderColor = '#475569';
              }}
              onMouseLeave={(e) => {
                if (!isSending) e.currentTarget.style.borderColor = '#334155';
              }}
            >
              Cancel
            </button>

            <button
              type="submit"
              disabled={isSending}
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '7px',
                background: isSending ? '#1e3a8a' : '#2563eb',
                border: 'none',
                borderRadius: '6px',
                padding: '8px 20px',
                fontSize: '13px',
                fontWeight: '600',
                color: '#ffffff',
                cursor: isSending ? 'not-allowed' : 'pointer',
                boxShadow: '0 2px 8px rgba(37, 99, 235, 0.4)',
                transition: 'background 0.15s ease',
              }}
              onMouseEnter={(e) => {
                if (!isSending) e.currentTarget.style.background = '#1d4ed8';
              }}
              onMouseLeave={(e) => {
                if (!isSending) e.currentTarget.style.background = '#2563eb';
              }}
            >
              {isSending ? (
                <>
                  <Loader2 size={15} className="animate-spin" style={{ animation: 'spin 1s linear infinite' }} />
                  <span>Sending...</span>
                </>
              ) : (
                <>
                  <Send size={14} />
                  <span>Send Email</span>
                </>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
