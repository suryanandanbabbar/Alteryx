import React from 'react';
import { LucideIcon, Download } from 'lucide-react';

interface DownloadCardProps {
  icon: LucideIcon;
  title: string;
  subtitle: string;
  formatBadge?: string;
  isPrimary?: boolean;
  onDownload: () => void;
}

export const DownloadCard: React.FC<DownloadCardProps> = ({
  icon: Icon,
  title,
  subtitle,
  formatBadge,
  isPrimary = false,
  onDownload,
}) => {
  return (
    <div
      className="app-card app-card-hover"
      style={{
        padding: '16px 20px',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        borderLeft: isPrimary ? '4px solid var(--color-primary)' : undefined,
        background: isPrimary ? 'var(--color-primary-subtle)' : 'var(--color-surface)',
        gap: '16px',
        flexWrap: 'wrap',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
        <div style={{
          width: '36px',
          height: '36px',
          borderRadius: 'var(--radius-sm)',
          background: isPrimary ? 'var(--color-primary)' : 'var(--color-surface-secondary)',
          color: isPrimary ? '#ffffff' : 'var(--color-text)',
          border: '1px solid var(--color-border)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          flexShrink: 0,
        }}>
          <Icon size={18} />
        </div>

        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span style={{ fontSize: '14px', fontWeight: '700', color: 'var(--color-text)' }}>
              {title}
            </span>
            {formatBadge && (
              <span style={{
                fontFamily: 'var(--font-mono)',
                fontSize: '11px',
                fontWeight: '600',
                color: 'var(--color-text-muted)',
                background: 'var(--color-surface-secondary)',
                border: '1px solid var(--color-border)',
                padding: '1px 6px',
                borderRadius: 'var(--radius-sm)',
              }}>
                {formatBadge}
              </span>
            )}
          </div>
          <div style={{ fontSize: '12px', color: 'var(--color-text-muted)', marginTop: '2px' }}>
            {subtitle}
          </div>
        </div>
      </div>

      <button
        onClick={onDownload}
        className={isPrimary ? 'btn-primary' : 'btn-secondary'}
        style={{ padding: '8px 16px', fontSize: '12px', flexShrink: 0 }}
      >
        <Download size={13} />
        <span>{isPrimary ? 'Download all' : 'Download'}</span>
      </button>
    </div>
  );
};
