import React, { useState, useEffect } from 'react';

interface AnalysisLoadingScreenProps {
  fileName?: string;
}

const ANALYSIS_STAGES = [
  'Reading workflow structure...',
  'Building workflow graph & dependencies...',
  'Analyzing tools and data flow...',
  'Generating AI-powered workflow insights...',
  'Preparing workflow documentation...',
];

export const AnalysisLoadingScreen: React.FC<AnalysisLoadingScreenProps> = ({ fileName }) => {
  const [stageIndex, setStageIndex] = useState(0);

  // Smoothly rotate truthful status messages
  useEffect(() => {
    const interval = setInterval(() => {
      setStageIndex((prev) => (prev < ANALYSIS_STAGES.length - 1 ? prev + 1 : prev));
    }, 2800);
    return () => clearInterval(interval);
  }, []);

  return (
    <div
      role="status"
      aria-live="polite"
      style={{
        position: 'fixed',
        inset: 0,
        background: 'var(--color-bg)',
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

      {/* Main Loading Card Container */}
      <div
        style={{
          maxWidth: '480px',
          width: '100%',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          textAlign: 'center',
          position: 'relative',
          zIndex: 1,
        }}
      >
        {/* Animated DAG Nodes Graphic */}
        <div style={{ marginBottom: '36px', position: 'relative' }}>
          <svg
            width="220"
            height="100"
            viewBox="0 0 220 100"
            fill="none"
            xmlns="http://www.w3.org/2000/svg"
            style={{ overflow: 'visible' }}
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
              @keyframes flowParticle {
                0% { offset-distance: 0%; opacity: 0; }
                20% { opacity: 1; }
                80% { opacity: 1; }
                100% { offset-distance: 100%; opacity: 0; }
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

            {/* Connecting Edges */}
            <path
              d="M 45 50 L 100 50"
              stroke="var(--color-border)"
              strokeWidth="2"
            />
            <path
              d="M 45 50 L 100 50"
              stroke="var(--color-primary)"
              strokeWidth="2"
              className="pulse-edge-1"
            />

            <path
              d="M 120 50 L 175 50"
              stroke="var(--color-border)"
              strokeWidth="2"
            />
            <path
              d="M 120 50 L 175 50"
              stroke="var(--color-primary)"
              strokeWidth="2"
              className="pulse-edge-2"
            />

            {/* Node 1: Input (Blue) */}
            <g className="pulse-node-1">
              <rect
                x="15"
                y="30"
                width="40"
                height="40"
                rx="6"
                fill="var(--color-surface)"
                stroke="#38bdf8"
                strokeWidth="1.5"
              />
              <rect x="25" y="44" width="20" height="3" rx="1.5" fill="#38bdf8" />
              <rect x="25" y="52" width="14" height="2.5" rx="1" fill="var(--color-text-muted)" />
            </g>

            {/* Node 2: Transformation / AI (Primary Orange) */}
            <g className="pulse-node-2">
              <rect
                x="90"
                y="28"
                width="44"
                height="44"
                rx="8"
                fill="var(--color-surface)"
                stroke="var(--color-primary)"
                strokeWidth="2"
              />
              <circle cx="112" cy="50" r="8" fill="var(--color-primary-subtle)" stroke="var(--color-primary)" strokeWidth="1.5" />
              <circle cx="112" cy="50" r="3" fill="var(--color-primary)" />
            </g>

            {/* Node 3: Output (Purple) */}
            <g className="pulse-node-3">
              <rect
                x="165"
                y="30"
                width="40"
                height="40"
                rx="6"
                fill="var(--color-surface)"
                stroke="#c084fc"
                strokeWidth="1.5"
              />
              <rect x="175" y="44" width="20" height="3" rx="1.5" fill="#c084fc" />
              <rect x="175" y="52" width="12" height="2.5" rx="1" fill="var(--color-text-muted)" />
            </g>
          </svg>
        </div>

        {/* Application Brand Header */}
        <div
          style={{
            fontSize: '11px',
            fontWeight: 800,
            letterSpacing: '1.2px',
            textTransform: 'uppercase',
            color: 'var(--color-primary)',
            marginBottom: '8px',
          }}
        >
          ETL Intelligence & Migration
        </div>

        {/* Main Title */}
        <h2
          style={{
            fontSize: '22px',
            fontWeight: 800,
            color: 'var(--color-text)',
            letterSpacing: '-0.3px',
            margin: '0 0 10px 0',
          }}
        >
          Analyzing workflow
        </h2>

        {/* Subtitle / Filename */}
        {fileName ? (
          <div
            style={{
              fontSize: '13px',
              fontFamily: 'var(--font-mono)',
              color: 'var(--color-text-secondary)',
              background: 'var(--color-surface)',
              border: '1px solid var(--color-border)',
              padding: '3px 10px',
              borderRadius: 'var(--radius-sm)',
              marginBottom: '20px',
              maxWidth: '90%',
              overflow: 'hidden',
              textOverflow: 'ellipsis',
              whiteSpace: 'nowrap',
            }}
          >
            {fileName}
          </div>
        ) : (
          <p
            style={{
              fontSize: '13.5px',
              color: 'var(--color-text-muted)',
              margin: '0 0 20px 0',
            }}
          >
            Analyzing your Alteryx workflow... This may take a moment.
          </p>
        )}

        {/* Rotating Stage Status Box */}
        <div
          style={{
            minHeight: '42px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            padding: '8px 18px',
            borderRadius: 'var(--radius-md)',
            background: 'var(--color-surface)',
            border: '1px solid var(--color-border)',
            boxShadow: '0 2px 8px rgba(0, 0, 0, 0.08)',
          }}
        >
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '10px',
            }}
          >
            <div
              style={{
                width: '8px',
                height: '8px',
                borderRadius: '50%',
                background: 'var(--color-primary)',
                boxShadow: '0 0 8px var(--color-primary)',
              }}
            />
            <span
              style={{
                fontSize: '13px',
                fontWeight: 600,
                color: 'var(--color-text)',
                transition: 'all 0.3s ease',
              }}
            >
              {ANALYSIS_STAGES[stageIndex]}
            </span>
          </div>
        </div>

        {/* Footnote reassurance */}
        <div
          style={{
            fontSize: '11.5px',
            color: 'var(--color-text-muted)',
            marginTop: '28px',
          }}
        >
          Extracting graph topology, calculating lineage & synthesizing business insights.
        </div>
      </div>
    </div>
  );
};
