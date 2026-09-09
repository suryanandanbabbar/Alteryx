import React, { useEffect } from 'react';
import { Check, X } from 'lucide-react';

interface EmailSuccessToastProps {
  recipient: string;
  onClose: () => void;
  autoCloseMs?: number;
}

export const EmailSuccessToast: React.FC<EmailSuccessToastProps> = ({
  recipient,
  onClose,
  autoCloseMs = 4000,
}) => {
  useEffect(() => {
    const timer = setTimeout(() => {
      onClose();
    }, autoCloseMs);
    return () => clearTimeout(timer);
  }, [onClose, autoCloseMs]);

  return (
    <div
      role="status"
      aria-live="polite"
      style={{
        position: 'fixed',
        bottom: '28px',
        right: '28px',
        zIndex: 10005,
        display: 'flex',
        alignItems: 'center',
        gap: '14px',
        background: '#0d1520',
        border: '1px solid rgba(16, 185, 129, 0.4)',
        borderRadius: '10px',
        padding: '14px 18px',
        boxShadow: '0 12px 32px rgba(0, 0, 0, 0.5), 0 0 16px rgba(16, 185, 129, 0.15)',
        maxWidth: '420px',
        animation: 'slideUpFade 0.3s cubic-bezier(0.16, 1, 0.3, 1)',
      }}
    >
      <style>
        {`
          @keyframes slideUpFade {
            from {
              opacity: 0;
              transform: translateY(12px) scale(0.96);
            }
            to {
              opacity: 1;
              transform: translateY(0) scale(1);
            }
          }
          @keyframes popCheck {
            0% {
              transform: scale(0.6);
              opacity: 0;
            }
            60% {
              transform: scale(1.15);
              opacity: 1;
            }
            100% {
              transform: scale(1);
              opacity: 1;
            }
          }
        `}
      </style>

      {/* Animated Green Check Badge */}
      <div
        style={{
          width: '36px',
          height: '36px',
          borderRadius: '50%',
          background: 'rgba(16, 185, 129, 0.18)',
          border: '1.5px solid #10b981',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          flexShrink: 0,
          animation: 'popCheck 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275) forwards',
        }}
      >
        <Check size={20} color="#10b981" strokeWidth={3} />
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: '2px', flex: 1, minWidth: 0 }}>
        <div style={{ fontSize: '13.5px', fontWeight: '700', color: '#f8fafc', letterSpacing: '-0.01em' }}>
          Email Sent Successfully
        </div>
        <div
          style={{
            fontSize: '12px',
            color: '#94a3b8',
            overflow: 'hidden',
            textOverflow: 'ellipsis',
            whiteSpace: 'nowrap',
          }}
          title={recipient}
        >
          Recommendation dispatched to <span style={{ color: '#cbd5e1', fontWeight: '600' }}>{recipient}</span>
        </div>
      </div>

      <button
        onClick={onClose}
        style={{
          background: 'transparent',
          border: 'none',
          color: '#64748b',
          cursor: 'pointer',
          padding: '4px',
          borderRadius: '4px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          transition: 'color 0.15s ease',
        }}
        onMouseEnter={(e) => (e.currentTarget.style.color = '#f8fafc')}
        onMouseLeave={(e) => (e.currentTarget.style.color = '#64748b')}
        title="Dismiss notification"
      >
        <X size={15} />
      </button>
    </div>
  );
};
