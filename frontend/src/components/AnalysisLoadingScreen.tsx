import React, { useState, useEffect } from 'react';
import { Check, AlertTriangle, RefreshCw } from 'lucide-react';

export interface AnalysisLoadingScreenProps {
  fileName?: string;
  isOverlay?: boolean;
  error?: string | null;
  onRetry?: () => void;
  onCancel?: () => void;
  title?: string;
  subtitle?: string;
}

const DEFAULT_STAGES = [
  'Reading workflow structure',
  'Building workflow graph & dependencies',
  'Analysing transformations & lineage',
  'Synthesizing business intelligence',
  'Preparing workflow overview',
];

export const AnalysisLoadingScreen: React.FC<AnalysisLoadingScreenProps> = ({
  fileName,
  isOverlay = false,
  error = null,
  onRetry,
  onCancel,
  title = 'Analysing Workflow',
  subtitle = 'Inspecting workflow structure, lineage, transformations, and business context...',
}) => {
  const [stageIndex, setStageIndex] = useState(0);

  // Smoothly rotate truthful staged progress
  useEffect(() => {
    if (error) return;
    const interval = setInterval(() => {
      setStageIndex((prev) => (prev < DEFAULT_STAGES.length - 1 ? prev + 1 : prev));
    }, 2400);
    return () => clearInterval(interval);
  }, [error]);

  return (
    <div
      role={isOverlay ? 'dialog' : 'status'}
      aria-modal={isOverlay ? true : undefined}
      aria-busy={!error}
      aria-live="polite"
      style={{
        position: 'fixed',
        inset: 0,
        background: isOverlay ? 'rgba(0, 0, 0, 0.72)' : 'var(--color-bg)',
        backdropFilter: isOverlay ? 'blur(5px)' : undefined,
        zIndex: 9999,
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '24px',
        boxSizing: 'border-box',
        overflow: 'hidden',
      }}
    >
      {/* Background subtle radial glow */}
      <div
        style={{
          position: 'absolute',
          width: '500px',
          height: '500px',
          borderRadius: '50%',
          background: 'radial-gradient(circle, rgba(251, 78, 11, 0.08) 0%, rgba(0,0,0,0) 70%)',
          pointerEvents: 'none',
        }}
      />

      {/* Main Loading / Error Card Container */}
      <div
        style={{
          maxWidth: '500px',
          width: '100%',
          background: isOverlay ? 'var(--color-surface)' : 'transparent',
          border: isOverlay ? '1px solid var(--color-border)' : 'none',
          borderRadius: isOverlay ? '12px' : '0px',
          padding: isOverlay ? '36px 32px' : '0px',
          boxShadow: isOverlay ? '0 24px 48px -12px rgba(0, 0, 0, 0.65)' : 'none',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          textAlign: 'center',
          position: 'relative',
          zIndex: 1,
        }}
      >
        <style>{`
          @keyframes pulseLine {
            0% { stroke-dashoffset: 60; }
            100% { stroke-dashoffset: 0; }
          }
          @keyframes nodeGlow {
            0%, 100% { opacity: 0.7; transform: scale(1); }
            50% { opacity: 1; transform: scale(1.08); }
          }
          .pulse-edge-1 {
            stroke-dasharray: 6, 6;
            animation: pulseLine 1.8s linear infinite;
          }
          .pulse-edge-2 {
            stroke-dasharray: 6, 6;
            animation: pulseLine 1.8s linear infinite 0.4s;
          }
          .pulse-node-1 {
            transform-origin: 35px 50px;
            animation: nodeGlow 2.4s ease-in-out infinite;
          }
          .pulse-node-2 {
            transform-origin: 110px 50px;
            animation: nodeGlow 2.4s ease-in-out infinite 0.8s;
          }
          .pulse-node-3 {
            transform-origin: 185px 50px;
            animation: nodeGlow 2.4s ease-in-out infinite 1.6s;
          }
          @media (prefers-reduced-motion: reduce) {
            .pulse-edge-1, .pulse-edge-2, .pulse-node-1, .pulse-node-2, .pulse-node-3 {
              animation: none !important;
            }
          }
        `}</style>

        {error ? (
          /* Error State: Graceful recovery without infinite spinner */
          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', width: '100%' }}>
            <div style={{
              width: '52px',
              height: '52px',
              borderRadius: '50%',
              background: 'rgba(239, 68, 68, 0.12)',
              border: '1px solid rgba(239, 68, 68, 0.3)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: 'var(--color-error)',
              marginBottom: '16px',
            }}>
              <AlertTriangle size={26} />
            </div>

            <div style={{
              fontSize: '11px',
              fontWeight: 800,
              letterSpacing: '1.2px',
              textTransform: 'uppercase',
              color: 'var(--color-error)',
              marginBottom: '6px',
            }}>
              Workflow Analysis Failed
            </div>

            <h3 style={{
              fontSize: '20px',
              fontWeight: 800,
              color: 'var(--color-text)',
              margin: '0 0 10px 0',
              letterSpacing: '-0.2px',
            }}>
              Analysis could not complete
            </h3>

            {fileName && (
              <div style={{
                fontSize: '12px',
                fontFamily: 'var(--font-mono, monospace)',
                color: 'var(--color-text-secondary)',
                background: 'var(--color-surface-secondary)',
                border: '1px solid var(--color-border)',
                padding: '3px 10px',
                borderRadius: 'var(--radius-sm)',
                marginBottom: '14px',
                maxWidth: '90%',
                overflow: 'hidden',
                textOverflow: 'ellipsis',
                whiteSpace: 'nowrap',
              }}>
                {fileName}
              </div>
            )}

            <p style={{
              fontSize: '13px',
              color: 'var(--color-text-secondary)',
              lineHeight: '1.5',
              margin: '0 0 24px 0',
              maxWidth: '380px',
            }}>
              {error || `We couldn't complete the analysis for ${fileName || 'this workflow'}. Please try again.`}
            </p>

            <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
              {onRetry && (
                <button
                  onClick={onRetry}
                  style={{
                    display: 'inline-flex',
                    alignItems: 'center',
                    gap: '7px',
                    padding: '9px 18px',
                    borderRadius: 'var(--radius-sm)',
                    border: '1px solid var(--color-primary)',
                    background: 'var(--color-primary)',
                    color: '#ffffff',
                    fontSize: '13px',
                    fontWeight: '700',
                    cursor: 'pointer',
                    transition: 'all 0.15s ease',
                  }}
                >
                  <RefreshCw size={13} />
                  <span>Try Again</span>
                </button>
              )}

              {onCancel && (
                <button
                  onClick={onCancel}
                  style={{
                    padding: '9px 18px',
                    borderRadius: 'var(--radius-sm)',
                    border: '1px solid var(--color-border)',
                    background: 'var(--color-surface-secondary)',
                    color: 'var(--color-text-secondary)',
                    fontSize: '13px',
                    fontWeight: '600',
                    cursor: 'pointer',
                    transition: 'all 0.15s ease',
                  }}
                >
                  Dismiss
                </button>
              )}
            </div>
          </div>
        ) : (
          /* Normal Loading State: Animated DAG + Staged Intelligence Progress */
          <>
            {/* Animated DAG Graphic */}
            <div style={{ marginBottom: isOverlay ? '24px' : '36px', position: 'relative' }}>
              <svg
                width="220"
                height="90"
                viewBox="0 0 220 90"
                fill="none"
                xmlns="http://www.w3.org/2000/svg"
                style={{ overflow: 'visible' }}
              >
                {/* Connecting Edges */}
                <path d="M 45 45 L 100 45" stroke="var(--color-border)" strokeWidth="2" />
                <path d="M 45 45 L 100 45" stroke="var(--color-primary)" strokeWidth="2" className="pulse-edge-1" />

                <path d="M 120 45 L 175 45" stroke="var(--color-border)" strokeWidth="2" />
                <path d="M 120 45 L 175 45" stroke="var(--color-primary)" strokeWidth="2" className="pulse-edge-2" />

                {/* Node 1: Input (Blue) */}
                <g className="pulse-node-1">
                  <rect x="15" y="25" width="40" height="40" rx="6" fill="var(--color-surface)" stroke="#38bdf8" strokeWidth="1.5" />
                  <rect x="25" y="39" width="20" height="3" rx="1.5" fill="#38bdf8" />
                  <rect x="25" y="47" width="14" height="2.5" rx="1" fill="var(--color-text-muted)" />
                </g>

                {/* Node 2: Transformation / AI (Primary Orange) */}
                <g className="pulse-node-2">
                  <rect x="90" y="23" width="44" height="44" rx="8" fill="var(--color-surface)" stroke="var(--color-primary)" strokeWidth="2" />
                  <circle cx="112" cy="45" r="8" fill="var(--color-primary-subtle)" stroke="var(--color-primary)" strokeWidth="1.5" />
                  <circle cx="112" cy="45" r="3" fill="var(--color-primary)" />
                </g>

                {/* Node 3: Output (Purple) */}
                <g className="pulse-node-3">
                  <rect x="165" y="25" width="40" height="40" rx="6" fill="var(--color-surface)" stroke="#c084fc" strokeWidth="1.5" />
                  <rect x="175" y="39" width="20" height="3" rx="1.5" fill="#c084fc" />
                  <rect x="175" y="47" width="12" height="2.5" rx="1" fill="var(--color-text-muted)" />
                </g>
              </svg>
            </div>

            {/* Application Brand Header */}
            <div
              style={{
                fontSize: '10.5px',
                fontWeight: 800,
                letterSpacing: '1.2px',
                textTransform: 'uppercase',
                color: 'var(--color-primary)',
                marginBottom: '6px',
              }}
            >
              ETL Intelligence & Migration
            </div>

            {/* Main Title */}
            <h2
              style={{
                fontSize: isOverlay ? '20px' : '22px',
                fontWeight: 800,
                color: 'var(--color-text)',
                letterSpacing: '-0.3px',
                margin: '0 0 8px 0',
              }}
            >
              {title}
            </h2>

            {/* Workflow Filename Chip */}
            {fileName && (
              <div
                style={{
                  fontSize: '12.5px',
                  fontFamily: 'var(--font-mono, monospace)',
                  color: 'var(--color-text-secondary)',
                  background: 'var(--color-surface-secondary)',
                  border: '1px solid var(--color-border)',
                  padding: '3px 10px',
                  borderRadius: 'var(--radius-sm)',
                  marginBottom: '14px',
                  maxWidth: '92%',
                  overflow: 'hidden',
                  textOverflow: 'ellipsis',
                  whiteSpace: 'nowrap',
                }}
                title={fileName}
              >
                {fileName}
              </div>
            )}

            {/* Subtitle Reassurance */}
            <p
              style={{
                fontSize: '13px',
                color: 'var(--color-text-muted)',
                margin: '0 0 18px 0',
                lineHeight: '1.5',
                maxWidth: '420px',
              }}
            >
              {subtitle}
            </p>

            {/* Meaningful Staged Progress List */}
            <div
              style={{
                width: '100%',
                display: 'flex',
                flexDirection: 'column',
                gap: '8px',
                padding: '14px 18px',
                borderRadius: '8px',
                background: 'var(--color-surface-secondary)',
                border: '1px solid var(--color-border-subtle)',
                textAlign: 'left',
                marginBottom: '16px',
                boxSizing: 'border-box',
              }}
            >
              {DEFAULT_STAGES.map((stage, idx) => {
                const isCompleted = idx < stageIndex;
                const isActive = idx === stageIndex;

                return (
                  <div
                    key={idx}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: '10px',
                      fontSize: '12px',
                      color: isActive
                        ? 'var(--color-text)'
                        : isCompleted
                        ? 'var(--color-text-muted)'
                        : 'var(--color-text-subtle)',
                      fontWeight: isActive ? 700 : 500,
                      transition: 'all 0.25s ease',
                    }}
                  >
                    <div
                      style={{
                        width: '14px',
                        height: '14px',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        flexShrink: 0,
                      }}
                    >
                      {isCompleted ? (
                        <Check size={13} color="#22c55e" strokeWidth={3} />
                      ) : isActive ? (
                        <span
                          style={{
                            width: '7px',
                            height: '7px',
                            borderRadius: '50%',
                            background: 'var(--color-primary)',
                            boxShadow: '0 0 6px var(--color-primary)',
                          }}
                        />
                      ) : (
                        <span
                          style={{
                            width: '7px',
                            height: '7px',
                            borderRadius: '50%',
                            border: '1.5px solid var(--color-border)',
                          }}
                        />
                      )}
                    </div>
                    <span>{stage}</span>
                  </div>
                );
              })}
            </div>

            {/* Footnote Reassurance */}
            <div
              style={{
                fontSize: '11px',
                color: 'var(--color-text-subtle)',
              }}
            >
              Extracting graph topology, calculating lineage & synthesizing business insights.
            </div>
          </>
        )}
      </div>
    </div>
  );
};
