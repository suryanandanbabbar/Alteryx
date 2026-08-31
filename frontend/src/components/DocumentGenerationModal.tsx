import React from 'react';
import { FileText, Table, Sparkles } from 'lucide-react';

export type ReportType = 'business' | 'tool-specifications' | 'technical' | 'sttm';

interface DocumentGenerationModalProps {
  type: ReportType;
}

export const DocumentGenerationModal: React.FC<DocumentGenerationModalProps> = ({ type }) => {
  const isBusiness = type === 'business';
  const isSttm = type === 'sttm';
  const title = isBusiness
    ? 'Preparing Business Report'
    : isSttm
    ? 'Preparing Source-to-Target Mapping'
    : 'Preparing Tool Specifications';
  const subtitle = isBusiness
    ? 'Generating your Business Report... AI-generated analysis is being prepared.'
    : isSttm
    ? 'Generating your Source-to-Target Mapping... AI-powered lineage analysis is being prepared.'
    : 'Generating your Tool Specifications... AI-generated tool analysis is being prepared.';

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-live="polite"
      style={{
        position: 'fixed',
        inset: 0,
        background: 'rgba(0, 0, 0, 0.65)',
        backdropFilter: 'blur(4px)',
        zIndex: 9999,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '20px',
        boxSizing: 'border-box',
      }}
    >
      <div
        style={{
          maxWidth: '440px',
          width: '100%',
          background: 'var(--color-surface)',
          border: '1px solid var(--color-border)',
          borderRadius: 'var(--radius-lg, 8px)',
          padding: '36px 28px',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          textAlign: 'center',
          boxShadow: '0 20px 40px rgba(0, 0, 0, 0.35)',
          position: 'relative',
        }}
      >
        <style>{`
          @keyframes docFloat {
            0%, 100% { transform: translateY(0px); }
            50% { transform: translateY(-6px); }
          }
          @keyframes pulseGlow {
            0%, 100% { opacity: 0.4; transform: scale(1); }
            50% { opacity: 0.8; transform: scale(1.1); }
          }
          @keyframes sparkRotate {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
          }
          .doc-icon-container {
            animation: docFloat 2.8s ease-in-out infinite;
          }
          .glow-ring {
            animation: pulseGlow 2.4s ease-in-out infinite;
          }
          .spark-icon {
            animation: sparkRotate 8s linear infinite;
          }
          @media (prefers-reduced-motion: reduce) {
            .doc-icon-container, .glow-ring, .spark-icon {
              animation: none !important;
            }
          }
        `}</style>

        {/* Animated Document Icon with Subtle Glow */}
        <div style={{ position: 'relative', marginBottom: '24px' }} className="doc-icon-container">
          <div
            className="glow-ring"
            style={{
              position: 'absolute',
              inset: '-10px',
              borderRadius: '50%',
              background: 'radial-gradient(circle, rgba(251, 78, 11, 0.25) 0%, rgba(251, 78, 11, 0) 70%)',
            }}
          />

          <div
            style={{
              width: '64px',
              height: '64px',
              borderRadius: '16px',
              background: 'var(--color-surface-secondary)',
              border: '1.5px solid var(--color-primary-border)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: 'var(--color-primary)',
              position: 'relative',
              boxShadow: '0 4px 14px rgba(0, 0, 0, 0.15)',
            }}
          >
            {isBusiness ? <FileText size={30} /> : <Table size={30} />}

            {/* Sparkle Badge */}
            <div
              style={{
                position: 'absolute',
                top: '-4px',
                right: '-4px',
                width: '20px',
                height: '20px',
                borderRadius: '50%',
                background: 'var(--color-primary)',
                color: '#ffffff',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                boxShadow: '0 2px 6px rgba(0,0,0,0.2)',
              }}
            >
              <Sparkles size={11} className="spark-icon" />
            </div>
          </div>
        </div>

        {/* Brand Pre-title */}
        <div
          style={{
            fontSize: '10.5px',
            fontWeight: 800,
            letterSpacing: '1px',
            textTransform: 'uppercase',
            color: 'var(--color-primary)',
            marginBottom: '6px',
          }}
        >
          Document Generation
        </div>

        {/* Modal Title */}
        <h3
          style={{
            fontSize: '18px',
            fontWeight: 800,
            color: 'var(--color-text)',
            margin: '0 0 10px 0',
            letterSpacing: '-0.2px',
          }}
        >
          {title}
        </h3>

        {/* Modal Description */}
        <p
          style={{
            fontSize: '13px',
            color: 'var(--color-text-secondary)',
            lineHeight: '1.5',
            margin: '0 0 24px 0',
          }}
        >
          {subtitle}
        </p>

        {/* Indeterminate Animated Progress Bar */}
        <div
          style={{
            width: '100%',
            height: '4px',
            borderRadius: '2px',
            background: 'var(--color-surface-secondary)',
            overflow: 'hidden',
            position: 'relative',
            marginBottom: '14px',
          }}
        >
          <style>{`
            @keyframes indeterminateSlide {
              0% { left: -40%; width: 40%; }
              50% { left: 30%; width: 50%; }
              100% { left: 100%; width: 40%; }
            }
            .indeterminate-bar {
              animation: indeterminateSlide 1.6s ease-in-out infinite;
            }
            @media (prefers-reduced-motion: reduce) {
              .indeterminate-bar {
                animation: none !important;
                left: 0 !important;
                width: 100% !important;
              }
            }
          `}</style>
          <div
            className="indeterminate-bar"
            style={{
              position: 'absolute',
              top: 0,
              bottom: 0,
              background: 'var(--color-primary)',
              borderRadius: '2px',
            }}
          />
        </div>

        <span style={{ fontSize: '11.5px', color: 'var(--color-text-muted)', fontWeight: 500 }}>
          Your download will trigger automatically when complete.
        </span>
      </div>
    </div>
  );
};
