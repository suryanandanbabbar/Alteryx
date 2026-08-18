import React from 'react';
import { AnalysisOverviewDTO } from '../types/workflow';
import { 
  BarChart2, 
  GitFork, 
  Code, 
  Terminal, 
  Download, 
  ArrowLeft, 
  FileText,
  Check
} from 'lucide-react';

interface SidebarProps {
  overview: AnalysisOverviewDTO;
  activeSection: string;
  onNavigate: (section: string) => void;
  onReset: () => void;
}

export const Sidebar: React.FC<SidebarProps> = ({
  overview,
  activeSection,
  onNavigate,
  onReset,
}) => {
  const navItems = [
    { id: 'overview', number: '01', label: 'Overview', icon: BarChart2 },
    { id: 'diagram', number: '02', label: 'Workflow Diagram', icon: GitFork },
    { id: 'json', number: '03', label: 'JSON', icon: Code },
    { id: 'python', number: '04', label: 'Python', icon: Terminal },
    { id: 'downloads', number: '05', label: 'Download', icon: Download },
  ];

  // Track visited/completed sections
  const sectionOrder = ['overview', 'diagram', 'json', 'python', 'downloads'];
  const activeIndex = sectionOrder.indexOf(activeSection);

  return (
    <aside style={{
      width: '260px',
      minWidth: '260px',
      height: '100vh',
      position: 'sticky',
      top: 0,
      background: 'var(--color-surface)',
      borderRight: '1px solid var(--color-border)',
      display: 'flex',
      flexDirection: 'column',
      padding: '20px 16px',
      boxSizing: 'border-box',
      zIndex: 30,
    }}>
      {/* Brand Header */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '24px', paddingLeft: '6px' }}>
        <div style={{
          width: '28px',
          height: '28px',
          borderRadius: 'var(--radius-sm)',
          background: 'var(--color-primary)',
          color: '#ffffff',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          fontWeight: '800',
          fontSize: '13px',
          letterSpacing: '-0.5px',
        }}>
          A
        </div>
        <div>
          <div style={{ fontSize: '14px', fontWeight: '800', color: 'var(--color-text)', letterSpacing: '-0.3px', lineHeight: 1.2 }}>
            AWA
          </div>
          <div style={{ fontSize: '11px', color: 'var(--color-text-muted)', fontWeight: '500' }}>
            Alteryx Workflow Analyzer
          </div>
        </div>
      </div>

      {/* Navigation Label */}
      <div style={{
        fontSize: '10px',
        fontWeight: '700',
        letterSpacing: '1px',
        color: 'var(--color-text-muted)',
        marginBottom: '10px',
        paddingLeft: '8px',
        textTransform: 'uppercase',
      }}>
        Workflow Steps
      </div>

      {/* Navigation List */}
      <nav style={{ display: 'flex', flexDirection: 'column', gap: '4px', flex: 1 }}>
        {navItems.map((item, index) => {
          const isActive = activeSection === item.id;
          const isCompleted = activeIndex > index;
          const Icon = item.icon;

          return (
            <button
              key={item.id}
              onClick={() => onNavigate(item.id)}
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                padding: '9px 12px',
                borderRadius: 'var(--radius-sm)',
                border: isActive ? '1px solid var(--color-primary-border)' : '1px solid transparent',
                background: isActive ? 'var(--color-primary-subtle)' : 'transparent',
                color: isActive ? 'var(--color-primary)' : 'var(--color-text-secondary)',
                cursor: 'pointer',
                textAlign: 'left',
                width: '100%',
                transition: 'all 0.12s ease',
              }}
              onMouseEnter={(e) => {
                if (!isActive) {
                  e.currentTarget.style.backgroundColor = 'var(--color-surface-secondary)';
                  e.currentTarget.style.color = 'var(--color-text)';
                }
              }}
              onMouseLeave={(e) => {
                if (!isActive) {
                  e.currentTarget.style.backgroundColor = 'transparent';
                  e.currentTarget.style.color = 'var(--color-text-secondary)';
                }
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                <span style={{
                  fontFamily: 'var(--font-mono)',
                  fontSize: '11px',
                  fontWeight: '600',
                  color: isActive ? 'var(--color-primary)' : 'var(--color-text-subtle)',
                }}>
                  {item.number}
                </span>
                <Icon size={15} color={isActive ? 'var(--color-primary)' : 'var(--color-text-muted)'} />
                <span style={{ fontSize: '13px', fontWeight: isActive ? '600' : '500' }}>
                  {item.label}
                </span>
              </div>

              {/* Status Indicator */}
              <div>
                {isCompleted ? (
                  <Check size={13} color="var(--color-success)" strokeWidth={2.5} />
                ) : isActive ? (
                  <div style={{
                    width: '6px',
                    height: '6px',
                    borderRadius: '50%',
                    background: 'var(--color-primary)',
                  }} />
                ) : null}
              </div>
            </button>
          );
        })}
      </nav>

      {/* Active File Card */}
      <div style={{
        background: 'var(--color-surface-secondary)',
        border: '1px solid var(--color-border)',
        borderRadius: 'var(--radius-sm)',
        padding: '12px',
        marginBottom: '12px',
      }}>
        <div style={{
          fontSize: '10px',
          fontWeight: '700',
          letterSpacing: '0.8px',
          color: 'var(--color-text-muted)',
          marginBottom: '6px',
          textTransform: 'uppercase',
        }}>
          Current Workflow
        </div>
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: '6px',
          color: 'var(--color-text)',
          fontWeight: '600',
          fontSize: '12px',
          marginBottom: '4px',
          wordBreak: 'break-all',
        }}>
          <FileText size={13} color="var(--color-primary)" style={{ flexShrink: 0 }} />
          <span>{overview.source.original_filename}</span>
        </div>
        <div style={{ fontSize: '11px', color: 'var(--color-text-muted)', display: 'flex', gap: '6px', alignItems: 'center' }}>
          <span>{overview.metrics.total_nodes} tools</span>
          <span>·</span>
          <span>{overview.metrics.total_connections} edges</span>
        </div>
      </div>

      {/* Convert Another File Button */}
      <button
        onClick={onReset}
        className="btn-secondary"
        style={{
          width: '100%',
          padding: '8px 12px',
          fontSize: '12px',
        }}
      >
        <ArrowLeft size={13} />
        <span>Analyze another file</span>
      </button>
    </aside>
  );
};
