import React, { useEffect, useState } from 'react';

interface SplashScreenProps {
  onComplete?: () => void;
  minDisplayTime?: number; // milliseconds
}

let hasShownInitialSplash = false;

export const SplashScreen: React.FC<SplashScreenProps> = ({
  onComplete,
  minDisplayTime = 1350,
}) => {
  const [stage, setStage] = useState<'entering' | 'ready' | 'fading' | 'gone'>(() => {
    return hasShownInitialSplash ? 'gone' : 'entering';
  });

  useEffect(() => {
    if (hasShownInitialSplash) return;

    const readyTimer = setTimeout(() => {
      setStage('ready');
    }, 150);

    const fadeTimer = setTimeout(() => {
      setStage('fading');
    }, minDisplayTime);

    const endTimer = setTimeout(() => {
      hasShownInitialSplash = true;
      setStage('gone');
      if (onComplete) onComplete();
    }, minDisplayTime + 400);

    return () => {
      clearTimeout(readyTimer);
      clearTimeout(fadeTimer);
      clearTimeout(endTimer);
    };
  }, [minDisplayTime, onComplete]);

  if (stage === 'gone') return null;

  const isFading = stage === 'fading';

  return (
    <div
      role="status"
      aria-live="polite"
      aria-label="Application loading"
      style={{
        position: 'fixed',
        inset: 0,
        zIndex: 99999,
        background: '#0B0F19',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        opacity: isFading ? 0 : 1,
        pointerEvents: isFading ? 'none' : 'auto',
        transition: 'opacity 0.4s cubic-bezier(0.16, 1, 0.3, 1)',
        userSelect: 'none',
      }}
    >
      <style>{`
        @keyframes splashTitleIn {
          0% { opacity: 0; transform: translateY(6px); }
          100% { opacity: 1; transform: translateY(0); }
        }
        @keyframes splashSubtitleIn {
          0% { opacity: 0; transform: translateY(4px); }
          100% { opacity: 0.85; transform: translateY(0); }
        }
        @keyframes splashLineScale {
          0% { transform: scaleX(0); opacity: 0.2; }
          50% { transform: scaleX(0.7); opacity: 1; }
          100% { transform: scaleX(1); opacity: 0.8; }
        }
        @keyframes splashPulse {
          0%, 100% { opacity: 0.4; transform: scaleX(0.92); }
          50% { opacity: 0.95; transform: scaleX(1.04); }
        }
        .splash-title-text {
          animation: splashTitleIn 0.6s cubic-bezier(0.16, 1, 0.3, 1) forwards;
        }
        .splash-subtitle-text {
          opacity: 0;
          animation: splashSubtitleIn 0.6s cubic-bezier(0.16, 1, 0.3, 1) 0.18s forwards;
        }
        .splash-indicator-container {
          opacity: 0;
          animation: splashSubtitleIn 0.5s ease 0.3s forwards;
        }
        .splash-indicator-bar {
          transform-origin: center;
          animation: splashLineScale 1.0s cubic-bezier(0.16, 1, 0.3, 1) forwards, splashPulse 1.8s ease-in-out infinite 1.0s;
        }
        @media (prefers-reduced-motion: reduce) {
          .splash-title-text, .splash-subtitle-text, .splash-indicator-container, .splash-indicator-bar {
            animation: none !important;
            opacity: 1 !important;
            transform: none !important;
          }
        }
      `}</style>

      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', textAlign: 'center', padding: '0 24px' }}>
        {/* Primary Text */}
        <h1
          className="splash-title-text"
          style={{
            color: '#FFFFFF',
            fontSize: '24px',
            fontWeight: 800,
            letterSpacing: '-0.4px',
            fontFamily: 'var(--font-sans)',
            margin: 0,
            lineHeight: 1.25,
          }}
        >
          ETL Intelligence &amp; Migration
        </h1>

        {/* Secondary Text */}
        <div
          className="splash-subtitle-text"
          style={{
            color: '#94A3B8',
            fontSize: '14px',
            fontWeight: 500,
            letterSpacing: '0.1px',
            fontFamily: 'var(--font-sans)',
            marginTop: '6px',
            marginBottom: '28px',
          }}
        >
          Alteryx workflow
        </div>

        {/* Subtle Minimal Loading Indicator */}
        <div
          className="splash-indicator-container"
          style={{
            width: '140px',
            height: '2px',
            borderRadius: '1px',
            background: 'rgba(255, 255, 255, 0.08)',
            overflow: 'hidden',
            position: 'relative',
          }}
        >
          <div
            className="splash-indicator-bar"
            style={{
              position: 'absolute',
              inset: 0,
              background: 'linear-gradient(90deg, transparent 0%, #FB4E0B 50%, transparent 100%)',
              borderRadius: '1px',
            }}
          />
        </div>
      </div>
    </div>
  );
};
