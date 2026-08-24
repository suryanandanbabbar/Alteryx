import React, { useState } from 'react';
import { AnalysisOverviewDTO } from '../types/workflow';
import { 
  BarChart2, 
  GitFork, 
  Code, 
  Terminal, 
  Download, 
  ArrowLeft, 
  FileText,
  Check,
  Menu
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
  const [collapsed, setCollapsed] = useState(false);

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
      width: collapsed ? '64px' : '260px',
      minWidth: collapsed ? '64px' : '260px',
      height: '100vh',
      position: 'sticky',
      top: 0,
      background: 'var(--color-surface)',
      borderRight: '1px solid var(--color-border)',
      display: 'flex',
      flexDirection: 'column',
      padding: collapsed ? '20px 10px' : '20px 16px',
      boxSizing: 'border-box',
      zIndex: 30,
      transition: 'width 0.2s cubic-bezier(0.4, 0, 0.2, 1), min-width 0.2s cubic-bezier(0.4, 0, 0.2, 1), padding 0.2s ease',
      overflowX: 'hidden',
    }}>
      {/* Brand Header & Collapse Toggle */}
      <div style={{
        display: 'flex',
        alignItems: collapsed ? 'center' : 'flex-start',
        justifyContent: collapsed ? 'center' : 'space-between',
        gap: '8px',
        marginBottom: '24px',
        paddingLeft: collapsed ? '0' : '4px',
      }}>
        {!collapsed && (
          <div style={{ flex: 1, overflow: 'hidden' }}>
            <div style={{
              fontSize: '13.5px',
              fontWeight: '800',
              color: 'var(--color-text)',
              letterSpacing: '-0.3px',
              lineHeight: 1.25,
            }}>
              ETL Intelligence & Migration
            </div>
            <div style={{
              fontSize: '11.5px',
              color: 'var(--color-text-muted)',
              fontWeight: '500',
              marginTop: '3px',
            }}>
              Alteryx workflow
            </div>
          </div>
        )}

        <button
          onClick={() => setCollapsed(!collapsed)}
          aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
          title={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
          style={{
            background: 'transparent',
            border: '1px solid transparent',
            borderRadius: 'var(--radius-sm)',
            padding: collapsed ? '8px' : '6px',
            cursor: 'pointer',
            color: 'var(--color-text-muted)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            flexShrink: 0,
            transition: 'all 0.15s ease',
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.backgroundColor = 'var(--color-surface-secondary)';
            e.currentTarget.style.color = 'var(--color-text)';
            e.currentTarget.style.borderColor = 'var(--color-border)';
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.backgroundColor = 'transparent';
            e.currentTarget.style.color = 'var(--color-text-muted)';
            e.currentTarget.style.borderColor = 'transparent';
          }}
        >
          <Menu size={collapsed ? 18 : 16} />
        </button>
      </div>

      {/* Navigation Label */}
      {!collapsed && (
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
      )}

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
              aria-label={`${item.number} ${item.label}`}
              title={collapsed ? `${item.number} ${item.label}` : undefined}
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: collapsed ? 'center' : 'space-between',
                padding: collapsed ? '9px 0' : '9px 12px',
                borderRadius: 'var(--radius-sm)',
                border: isActive ? '1px solid var(--color-primary-border)' : '1px solid transparent',
                background: isActive ? 'var(--color-primary-subtle)' : 'transparent',
                color: isActive ? 'var(--color-primary)' : 'var(--color-text-secondary)',
                cursor: 'pointer',
                textAlign: 'left',
                width: '100%',
                transition: 'all 0.12s ease',
                position: 'relative',
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
              <div style={{
                display: 'flex',
                alignItems: 'center',
                gap: collapsed ? '0' : '10px',
                justifyContent: 'center',
                overflow: 'hidden',
              }}>
                {!collapsed && (
                  <span style={{
                    fontFamily: 'var(--font-mono)',
                    fontSize: '11px',
                    fontWeight: '600',
                    color: isActive ? 'var(--color-primary)' : 'var(--color-text-subtle)',
                  }}>
                    {item.number}
                  </span>
                )}
                <Icon size={16} color={isActive ? 'var(--color-primary)' : 'var(--color-text-muted)'} />
                {!collapsed && (
                  <span style={{ fontSize: '13px', fontWeight: isActive ? '600' : '500', whiteSpace: 'nowrap' }}>
                    {item.label}
                  </span>
                )}
              </div>

              {/* Status Indicator */}
              {!collapsed ? (
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
              ) : isCompleted ? (
                <div style={{
                  position: 'absolute',
                  top: '5px',
                  right: '6px',
                  width: '5px',
                  height: '5px',
                  borderRadius: '50%',
                  background: 'var(--color-success)',
                }} />
              ) : null}
            </button>
          );
        })}
      </nav>

      {/* Active File Card (Expanded only) */}
      {!collapsed && (
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
      )}

      {/* Convert Another File Button */}
      <button
        onClick={onReset}
        className="btn-secondary"
        aria-label="Analyze another file"
        title={collapsed ? `Analyze another file (${overview.source.original_filename})` : undefined}
        style={{
          width: '100%',
          padding: collapsed ? '8px 0' : '8px 12px',
          fontSize: '12px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          gap: '6px',
        }}
      >
        <ArrowLeft size={14} />
        {!collapsed && <span>Analyze another file</span>}
      </button>
    </aside>
  );
};
