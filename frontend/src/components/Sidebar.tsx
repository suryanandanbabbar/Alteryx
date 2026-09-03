import React, { useState } from 'react';
import { AnalysisOverviewDTO } from '../types/workflow';
import { PortfolioOverviewDTO } from '../types/portfolio';
import { 
  BarChart2, 
  GitFork, 
  Code, 
  Terminal, 
  Download, 
  ArrowLeft, 
  FileText, 
  Menu, 
  Sliders,
  Sparkles,
  RefreshCw,
  FolderKanban,
  FileSpreadsheet,
  Loader2
} from 'lucide-react';

interface SidebarProps {
  overview?: AnalysisOverviewDTO | null;
  portfolio?: PortfolioOverviewDTO | null;
  activeSection?: string;
  onNavigate?: (section: string) => void;
  onReset: () => void;
  onOpenRationalisation?: () => void;
  onDownloadPortfolioXlsx?: () => void;
  isDownloadingXlsx?: boolean;
}

export const Sidebar: React.FC<SidebarProps> = ({
  overview,
  portfolio,
  activeSection,
  onNavigate,
  onReset,
  onOpenRationalisation,
  onDownloadPortfolioXlsx,
  isDownloadingXlsx = false,
}) => {
  const [collapsed, setCollapsed] = useState(false);

  const isPortfolioMode = Boolean(portfolio && !overview);

  const workflowNavItems = [
    { id: 'overview', label: 'Overview', icon: BarChart2 },
    { id: 'diagram', label: 'Workflow Diagram', icon: GitFork },
    { id: 'tools', label: 'Tools & Configuration', icon: Sliders },
    { id: 'json', label: 'JSON', icon: Code },
    { id: 'python', label: 'Python', icon: Terminal },
    { id: 'downloads', label: 'Download', icon: Download },
  ];

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
              {isPortfolioMode ? 'Portfolio estate' : 'Alteryx workflow'}
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
          {isPortfolioMode ? 'Portfolio Actions' : 'Workflow Steps'}
        </div>
      )}

      {/* Portfolio Mode Actions or Workflow Navigation List */}
      {isPortfolioMode ? (
        <nav style={{ display: 'flex', flexDirection: 'column', gap: '8px', flex: 1 }}>
          {/* Action 1: Rationalisation Recommendation */}
          <button
            onClick={onOpenRationalisation}
            aria-label="Rationalisation Recommendation"
            title={collapsed ? 'Rationalisation Recommendation' : undefined}
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: collapsed ? 'center' : 'space-between',
              padding: collapsed ? '10px 0' : '10px 12px',
              borderRadius: 'var(--radius-sm)',
              border: '1px solid rgba(16, 185, 129, 0.4)',
              background: 'linear-gradient(135deg, rgba(6, 78, 59, 0.35) 0%, rgba(15, 23, 42, 0.8) 100%)',
              color: '#ecfdf5',
              cursor: 'pointer',
              textAlign: 'left',
              width: '100%',
              transition: 'all 0.15s ease',
              boxShadow: '0 2px 6px rgba(16, 185, 129, 0.12)',
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.borderColor = 'rgba(52, 211, 153, 0.8)';
              e.currentTarget.style.background = 'linear-gradient(135deg, rgba(6, 78, 59, 0.55) 0%, rgba(15, 23, 42, 0.95) 100%)';
              e.currentTarget.style.transform = 'translateY(-1px)';
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.borderColor = 'rgba(16, 185, 129, 0.4)';
              e.currentTarget.style.background = 'linear-gradient(135deg, rgba(6, 78, 59, 0.35) 0%, rgba(15, 23, 42, 0.8) 100%)';
              e.currentTarget.style.transform = 'none';
            }}
          >
            <div style={{
              display: 'flex',
              alignItems: 'center',
              gap: collapsed ? '0' : '10px',
              justifyContent: 'center',
              overflow: 'hidden',
            }}>
              <Sparkles size={16} color="#34d399" />
              {!collapsed && (
                <div style={{ display: 'flex', flexDirection: 'column' }}>
                  <span style={{ fontSize: '12.5px', fontWeight: '700', whiteSpace: 'nowrap', color: '#ecfdf5' }}>
                    Rationalisation
                  </span>
                  <span style={{ fontSize: '10.5px', color: '#6ee7b7', fontWeight: '500' }}>
                    Recommendation View
                  </span>
                </div>
              )}
            </div>

            {!collapsed && (
              <span style={{ color: '#34d399', fontWeight: '700', fontSize: '11.5px', flexShrink: 0 }}>
                View →
              </span>
            )}
          </button>

          {/* Action 2: Download Portfolio XLSX */}
          <button
            onClick={onDownloadPortfolioXlsx}
            disabled={isDownloadingXlsx}
            aria-label="Download Portfolio XLSX"
            title={collapsed ? 'Download Portfolio XLSX' : undefined}
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: collapsed ? 'center' : 'flex-start',
              padding: collapsed ? '10px 0' : '10px 12px',
              borderRadius: 'var(--radius-sm)',
              border: '1px solid rgba(56, 189, 248, 0.35)',
              background: 'linear-gradient(135deg, rgba(3, 105, 161, 0.3) 0%, rgba(15, 23, 42, 0.75) 100%)',
              color: '#f0f9ff',
              cursor: isDownloadingXlsx ? 'not-allowed' : 'pointer',
              opacity: isDownloadingXlsx ? 0.7 : 1,
              textAlign: 'left',
              width: '100%',
              transition: 'all 0.15s ease',
            }}
            onMouseEnter={(e) => {
              if (isDownloadingXlsx) return;
              e.currentTarget.style.borderColor = 'rgba(56, 189, 248, 0.8)';
              e.currentTarget.style.background = 'linear-gradient(135deg, rgba(3, 105, 161, 0.5) 0%, rgba(15, 23, 42, 0.9) 100%)';
              e.currentTarget.style.transform = 'translateY(-1px)';
            }}
            onMouseLeave={(e) => {
              if (isDownloadingXlsx) return;
              e.currentTarget.style.borderColor = 'rgba(56, 189, 248, 0.35)';
              e.currentTarget.style.background = 'linear-gradient(135deg, rgba(3, 105, 161, 0.3) 0%, rgba(15, 23, 42, 0.75) 100%)';
              e.currentTarget.style.transform = 'none';
            }}
          >
            <div style={{
              display: 'flex',
              alignItems: 'center',
              gap: collapsed ? '0' : '10px',
              justifyContent: 'center',
              overflow: 'hidden',
            }}>
              {isDownloadingXlsx ? (
                <Loader2 size={16} color="#38bdf8" className="animate-spin" />
              ) : (
                <FileSpreadsheet size={16} color="#38bdf8" />
              )}
              {!collapsed && (
                <div style={{ display: 'flex', flexDirection: 'column' }}>
                  <span style={{ fontSize: '12.5px', fontWeight: '600', whiteSpace: 'nowrap', color: '#f0f9ff' }}>
                    Portfolio XLSX
                  </span>
                  <span style={{ fontSize: '10.5px', color: '#7dd3fc', fontWeight: '500' }}>
                    {isDownloadingXlsx ? 'Generating...' : 'Download Report'}
                  </span>
                </div>
              )}
            </div>
          </button>

          {/* Action 3: Upload Different Portfolio */}
          <button
            onClick={onReset}
            aria-label="Upload Different Portfolio"
            title={collapsed ? 'Upload Different Portfolio' : undefined}
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: collapsed ? 'center' : 'flex-start',
              padding: collapsed ? '10px 0' : '10px 12px',
              borderRadius: 'var(--radius-sm)',
              border: '1px solid var(--color-border)',
              background: 'var(--color-surface)',
              color: 'var(--color-text-secondary)',
              cursor: 'pointer',
              textAlign: 'left',
              width: '100%',
              transition: 'all 0.15s ease',
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.color = 'var(--color-text)';
              e.currentTarget.style.borderColor = 'var(--color-text-muted)';
              e.currentTarget.style.background = 'var(--color-surface-hover)';
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.color = 'var(--color-text-secondary)';
              e.currentTarget.style.borderColor = 'var(--color-border)';
              e.currentTarget.style.background = 'var(--color-surface)';
            }}
          >
            <div style={{
              display: 'flex',
              alignItems: 'center',
              gap: collapsed ? '0' : '10px',
              justifyContent: 'center',
              overflow: 'hidden',
            }}>
              <RefreshCw size={16} color="var(--color-text-muted)" />
              {!collapsed && (
                <div style={{ display: 'flex', flexDirection: 'column' }}>
                  <span style={{ fontSize: '12.5px', fontWeight: '600', whiteSpace: 'nowrap', color: 'var(--color-text)' }}>
                    Upload Portfolio
                  </span>
                  <span style={{ fontSize: '10.5px', color: 'var(--color-text-muted)', fontWeight: '500' }}>
                    Analyze Different Estate
                  </span>
                </div>
              )}
            </div>
          </button>
        </nav>
      ) : (
        <nav style={{ display: 'flex', flexDirection: 'column', gap: '4px', flex: 1 }}>
          {workflowNavItems.map((item) => {
            const isActive = activeSection === item.id;
            const Icon = item.icon;

            return (
              <button
                key={item.id}
                onClick={() => onNavigate && onNavigate(item.id)}
                aria-label={item.label}
                title={collapsed ? item.label : undefined}
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
                  <Icon size={16} color={isActive ? 'var(--color-primary)' : 'var(--color-text-muted)'} />
                  {!collapsed && (
                    <span style={{ fontSize: '13px', fontWeight: isActive ? '600' : '500', whiteSpace: 'nowrap' }}>
                      {item.label}
                    </span>
                  )}
                </div>

                {/* Active Dot Indicator */}
                {!collapsed && isActive && (
                  <div style={{
                    width: '6px',
                    height: '6px',
                    borderRadius: '50%',
                    background: 'var(--color-primary)',
                  }} />
                )}
              </button>
            );
          })}
        </nav>
      )}

      {/* Active Estate Card or Active Workflow Card (Expanded only) */}
      {!collapsed && isPortfolioMode && portfolio && (
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
            Portfolio Estate
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
            <FolderKanban size={13} color="var(--color-primary)" style={{ flexShrink: 0 }} />
            <span>{portfolio.portfolio_name || 'Workflow Portfolio'}</span>
          </div>
          <div style={{ fontSize: '11px', color: 'var(--color-text-muted)', display: 'flex', gap: '6px', alignItems: 'center' }}>
            <span>{portfolio.metrics?.successful_workflows ?? portfolio.workflows?.length ?? 0} workflows analysed</span>
          </div>
        </div>
      )}

      {!collapsed && !isPortfolioMode && overview && (
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

      {/* Convert Another File Button (Workflow mode only) */}
      {!isPortfolioMode && (
        <button
          onClick={onReset}
          className="btn-secondary"
          aria-label="Analyze another file"
          title={collapsed ? `Analyze another file (${overview?.source.original_filename})` : undefined}
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
      )}
    </aside>
  );
};
