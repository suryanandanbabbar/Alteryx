import React from 'react';

interface StatCardProps {
  label: string;
  value: number | string;
  subtext?: string;
  colorClass: 'stat-card-blue' | 'stat-card-cyan' | 'stat-card-green' | 'stat-card-yellow';
  accentColor: string;
}

export const StatCard: React.FC<StatCardProps> = ({
  label,
  value,
  subtext,
  colorClass,
  accentColor,
}) => {
  return (
    <div
      className={`glass-card ${colorClass}`}
      style={{
        padding: '20px 24px',
        display: 'flex',
        flexDirection: 'column',
        gap: '6px',
        flex: 1,
        minWidth: '160px',
      }}
    >
      <div style={{
        fontSize: '11px',
        fontWeight: '700',
        letterSpacing: '1px',
        color: '#94a3b8',
        textTransform: 'uppercase',
      }}>
        {label}
      </div>
      <div style={{
        fontSize: '32px',
        fontWeight: '800',
        color: accentColor,
        letterSpacing: '-0.5px',
        lineHeight: '1.1',
      }}>
        {value}
      </div>
      {subtext && (
        <div style={{ fontSize: '11px', color: '#64748b' }}>
          {subtext}
        </div>
      )}
    </div>
  );
};
