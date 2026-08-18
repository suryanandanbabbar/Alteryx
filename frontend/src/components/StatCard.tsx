import React from 'react';

interface StatCardProps {
  label: string;
  value: number | string;
  subtext?: string;
  accentColor?: string;
}

export const StatCard: React.FC<StatCardProps> = ({
  label,
  value,
  subtext,
  accentColor,
}) => {
  return (
    <div
      className="app-card app-card-hover"
      style={{
        padding: '16px 20px',
        borderTop: accentColor ? `3px solid ${accentColor}` : undefined,
        display: 'flex',
        flexDirection: 'column',
        gap: '4px',
      }}
    >
      <div style={{
        fontSize: '11px',
        fontWeight: '600',
        letterSpacing: '0.5px',
        color: 'var(--color-text-muted)',
        textTransform: 'uppercase',
      }}>
        {label}
      </div>
      <div style={{
        fontSize: '24px',
        fontWeight: '700',
        color: 'var(--color-text)',
        letterSpacing: '-0.5px',
      }}>
        {value}
      </div>
      {subtext && (
        <div style={{ fontSize: '12px', color: 'var(--color-text-muted)' }}>
          {subtext}
        </div>
      )}
    </div>
  );
};
