import React from 'react';
import { Download, LucideIcon } from 'lucide-react';

interface DownloadCardProps {
  icon: LucideIcon;
  title: string;
  subtitle: string;
  buttonText?: string;
  buttonGradient: string;
  onDownload: () => void;
}

export const DownloadCard: React.FC<DownloadCardProps> = ({
  icon: Icon,
  title,
  subtitle,
  buttonText = 'Download',
  buttonGradient,
  onDownload,
}) => {
  return (
    <div
      className="glass-card glass-card-hover"
      style={{
        padding: '24px',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        gap: '20px',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: '18px' }}>
        <div style={{
          width: '44px',
          height: '44px',
          borderRadius: '10px',
          background: 'rgba(30, 41, 59, 0.8)',
          border: '1px solid rgba(51, 65, 85, 0.6)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          color: '#38bdf8',
          flexShrink: 0,
        }}>
          <Icon size={22} />
        </div>
        <div>
          <h3 style={{ fontSize: '15px', fontWeight: '700', color: '#f8fafc', marginBottom: '4px' }}>
            {title}
          </h3>
          <p style={{ fontSize: '12px', color: '#94a3b8' }}>
            {subtitle}
          </p>
        </div>
      </div>

      <button
        onClick={onDownload}
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: '8px',
          padding: '10px 18px',
          borderRadius: '8px',
          background: buttonGradient,
          border: 'none',
          color: '#ffffff',
          fontSize: '13px',
          fontWeight: '700',
          cursor: 'pointer',
          flexShrink: 0,
          boxShadow: '0 4px 14px rgba(0, 0, 0, 0.3)',
          transition: 'all 0.15s ease',
        }}
        onMouseEnter={(e) => {
          e.currentTarget.style.transform = 'translateY(-1px)';
          e.currentTarget.style.filter = 'brightness(1.1)';
        }}
        onMouseLeave={(e) => {
          e.currentTarget.style.transform = 'translateY(0)';
          e.currentTarget.style.filter = 'brightness(1)';
        }}
      >
        <Download size={15} />
        <span>{buttonText}</span>
      </button>
    </div>
  );
};
