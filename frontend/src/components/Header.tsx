import React from 'react';
import { Sun, Moon, CheckCircle2 } from 'lucide-react';
import { useTheme } from '../context/ThemeContext';

interface HeaderProps {
  sectionTitle: string;
  workflowName?: string;
  onBackToPortfolio?: () => void;
  backLabel?: string;
}

export const Header: React.FC<HeaderProps> = ({ sectionTitle, workflowName, onBackToPortfolio, backLabel }) => {
  const { theme, toggleTheme } = useTheme();

  return (
    <header style={{
      height: '56px',
      minHeight: '56px',
      borderBottom: '1px solid var(--color-border)',
      background: 'var(--color-surface)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
      padding: '0 32px',
      boxSizing: 'border-box',
      position: 'sticky',
      top: 0,
      zIndex: 20,
    }}>
      {/* Breadcrumb & Section Title */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
        {onBackToPortfolio ? (
          <button
            onClick={onBackToPortfolio}
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '4px',
              padding: '4px 8px',
              borderRadius: 'var(--radius-sm)',
              border: '1px solid var(--color-border)',
              background: 'var(--color-surface-secondary)',
              color: 'var(--color-primary)',
              fontSize: '12px',
              fontWeight: '700',
              cursor: 'pointer',
              transition: 'all 0.15s ease',
            }}
            title="Return to Portfolio Overview"
          >
            {backLabel || '← All Workflows'}
          </button>
        ) : (
          <span style={{
            fontSize: '12px',
            fontWeight: '600',
            color: 'var(--color-text-muted)',
            letterSpacing: '0.3px',
          }}>
            ETL Intelligence & Migration
          </span>
        )}
        <span style={{ color: 'var(--color-text-subtle)', fontSize: '12px' }}>/</span>
        <h1 style={{
          fontSize: '14px',
          fontWeight: '700',
          color: 'var(--color-text)',
          margin: 0,
        }}>
          {(sectionTitle || '').replace(/^\d+\s+/, '')}
        </h1>
      </div>

      {/* Right Actions: Workflow Status & Theme Toggle */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
        {workflowName && (
          <div style={{
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
            padding: '4px 10px',
            background: 'var(--color-surface-secondary)',
            border: '1px solid var(--color-border)',
            borderRadius: 'var(--radius-sm)',
            fontSize: '12px',
            color: 'var(--color-text-secondary)',
          }}>
            <CheckCircle2 size={13} color="var(--color-success)" />
            <span style={{ fontWeight: '500' }}>{workflowName}</span>
            <span style={{ color: 'var(--color-text-subtle)' }}>·</span>
            <span style={{ color: 'var(--color-success)', fontWeight: '600', fontSize: '11px' }}>
              Analysis complete
            </span>
          </div>
        )}

        {/* Theme Toggle Button */}
        <button
          onClick={toggleTheme}
          aria-label={`Switch to ${theme === 'light' ? 'dark' : 'light'} theme`}
          title={`Switch to ${theme === 'light' ? 'dark' : 'light'} theme`}
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            width: '32px',
            height: '32px',
            borderRadius: 'var(--radius-sm)',
            border: '1px solid var(--color-border)',
            background: 'var(--color-surface)',
            color: 'var(--color-text-secondary)',
            cursor: 'pointer',
            transition: 'all 0.15s ease',
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.backgroundColor = 'var(--color-surface-hover)';
            e.currentTarget.style.color = 'var(--color-text)';
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.backgroundColor = 'var(--color-surface)';
            e.currentTarget.style.color = 'var(--color-text-secondary)';
          }}
        >
          {theme === 'light' ? <Moon size={15} /> : <Sun size={15} />}
        </button>
      </div>
    </header>
  );
};
