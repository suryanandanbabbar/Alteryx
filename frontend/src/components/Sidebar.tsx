import React, { useState, useMemo } from 'react';
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
  Loader2,
  Zap,
  Layers,
  ChevronDown,
  ChevronUp,
  LucideIcon,
} from 'lucide-react';

export interface NavItemConfig {
  id: string;
  label: string;
  caption?: string;
  icon: LucideIcon;
}

export const defaultWorkflowNavItems: NavItemConfig[] = [
  { id: 'overview', label: 'Workflow Overview', caption: 'ETL Intelligence', icon: BarChart2 },
  { id: 'impact', label: 'Impact at a Glance', caption: 'ETL Intelligence', icon: Zap },
  { id: 'diagram', label: 'Workflow Diagram', caption: 'ETL Intelligence', icon: GitFork },
  { id: 'tools', label: 'Tools & Configuration', caption: 'ETL Intelligence', icon: Sliders },
  { id: 'json', label: 'Migrate to JSON', caption: 'ETL Migration', icon: Code },
  { id: 'python', label: 'Migrate to Python', caption: 'ETL Migration', icon: Terminal },
  { id: 'downloads', label: 'Download', caption: ' ', icon: Download },
];

export const defaultPortfolioNavItems: NavItemConfig[] = [
  { id: 'inventory', label: 'ETL Workflow Inventory', caption: 'ETL Discovery', icon: Layers },
  { id: 'rationalisation', label: 'Rationalisation Recommendation', caption: 'ETL Rationalisation', icon: Sparkles },
  { id: 'impact', label: 'Impact at a Glance', caption: 'ETL Intelligence', icon: Zap },
  { id: 'download_xlsx', label: 'Download Portfolio Document', caption: ' ', icon: FileSpreadsheet },
  { id: 'reset', label: 'Upload Different Portfolio', caption: ' ', icon: RefreshCw },
];

interface SidebarProps {
  overview?: AnalysisOverviewDTO | null;
  portfolio?: PortfolioOverviewDTO | null;
  activeSection?: string;
  onNavigate?: (section: string) => void;
  onReset: () => void;
  onOpenRationalisation?: () => void;
  onOpenImpact?: () => void;
  onOpenInventory?: (businessArea?: string | null) => void;
  selectedBusinessArea?: string | null;
  isRationalisationOpen?: boolean;
  isImpactOpen?: boolean;
  onDownloadPortfolioXlsx?: () => void;
  isDownloadingXlsx?: boolean;
  workflowNavItems?: NavItemConfig[];
  portfolioNavItems?: NavItemConfig[];
}

export const Sidebar: React.FC<SidebarProps> = ({
  overview,
  portfolio,
  activeSection,
  onNavigate,
  onReset,
  onOpenRationalisation,
  onOpenImpact,
  onOpenInventory,
  selectedBusinessArea,
  isRationalisationOpen = false,
  isImpactOpen = false,
  onDownloadPortfolioXlsx,
  isDownloadingXlsx = false,
  workflowNavItems = defaultWorkflowNavItems,
  portfolioNavItems = defaultPortfolioNavItems,
}) => {
  const [collapsed, setCollapsed] = useState(false);
  const [inventoryExpanded, setInventoryExpanded] = useState(true);

  const isPortfolioMode = Boolean(portfolio && !overview);
  const isInventoryActive = isPortfolioMode && !isRationalisationOpen && !isImpactOpen;

  // Extract dynamic business areas from portfolio data
  const availableBusinessAreas = useMemo(() => {
    if (!portfolio) return [];
    if (portfolio.business_areas && portfolio.business_areas.length > 0) {
      return portfolio.business_areas
        .filter((ba) => (ba.workflow_count > 0) || (ba.workflows && ba.workflows.length > 0))
        .map((ba) => ({
          name: ba.business_area,
          count: ba.workflow_count || ba.workflows?.length || 0,
        }));
    }
    // Dynamic fallback from portfolio.workflows
    const counts = new Map<string, number>();
    (portfolio.workflows || []).forEach((w) => {
      const tag = w.business_area_tag || w.business_area?.business_area || 'Other / Unclassified';
      counts.set(tag, (counts.get(tag) || 0) + 1);
    });
    return Array.from(counts.entries()).map(([name, count]) => ({ name, count }));
  }, [portfolio]);

  const totalPortfolioWorkflows = portfolio?.metrics?.total_workflows ?? portfolio?.workflows?.length ?? 0;

  // Helper map for configurable portfolio items
  const portfolioItemMap = useMemo(() => {
    const map = new Map<string, NavItemConfig>();
    portfolioNavItems.forEach((item) => map.set(item.id, item));
    return map;
  }, [portfolioNavItems]);

  const inventoryItem = portfolioItemMap.get('inventory') || { id: 'inventory', label: 'ETL Workflow Inventory', caption: 'ETL Workflow Inventory', icon: Layers };
  const rationalisationItem = portfolioItemMap.get('rationalisation') || { id: 'rationalisation', label: 'Rationalisation Recommendation', caption: 'Rationalisation Recommendation', icon: Sparkles };
  const impactItem = portfolioItemMap.get('impact') || { id: 'impact', label: 'Impact at a Glance', caption: 'Impact at a Glance', icon: Zap };
  const downloadItem = portfolioItemMap.get('download_xlsx') || { id: 'download_xlsx', label: 'Download Portfolio Document', caption: 'Download Portfolio Document', icon: FileSpreadsheet };
  const resetItem = portfolioItemMap.get('reset') || { id: 'reset', label: 'Upload Different Portfolio', caption: 'Upload Different Portfolio', icon: RefreshCw };

  return (
    <aside style={{
      width: collapsed ? '64px' : '280px',
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
              ETL Discovery, Intelligence, Rationalisation &amp; Migration
            </div>
            <div style={{
              fontSize: '11.5px',
              color: 'var(--color-text-muted)',
              fontWeight: '500',
              marginTop: '3px',
            }}>
              {isPortfolioMode ? 'Portfolio Estate' : 'Alteryx workflow'}
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
        <nav style={{ display: 'flex', flexDirection: 'column', gap: '4px', flex: 1, overflowY: 'auto' }}>
          {/* Action 1: ETL Workflow Inventory (with Business Area Submenu) */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
            <button
              onClick={() => {
                if (collapsed) {
                  onOpenInventory?.(null);
                  return;
                }
                if (!isInventoryActive) {
                  onOpenInventory?.(selectedBusinessArea || null);
                  setInventoryExpanded(true);
                } else {
                  setInventoryExpanded(!inventoryExpanded);
                }
              }}
              aria-label={inventoryItem.label}
              title={collapsed ? inventoryItem.label : undefined}
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: collapsed ? 'center' : 'space-between',
                padding: collapsed ? '9px 0' : '8px 12px',
                borderRadius: 'var(--radius-sm)',
                border: isInventoryActive ? '1px solid var(--color-primary-border)' : '1px solid transparent',
                background: isInventoryActive ? 'var(--color-primary-subtle)' : 'transparent',
                color: isInventoryActive ? 'var(--color-primary)' : 'var(--color-text-secondary)',
                cursor: 'pointer',
                textAlign: 'left',
                width: '100%',
                transition: 'all 0.12s ease',
              }}
              onMouseEnter={(e) => {
                if (!isInventoryActive) {
                  e.currentTarget.style.backgroundColor = 'var(--color-surface-secondary)';
                  e.currentTarget.style.color = 'var(--color-text)';
                }
              }}
              onMouseLeave={(e) => {
                if (!isInventoryActive) {
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
                <Layers size={16} color={isInventoryActive ? 'var(--color-primary)' : 'var(--color-text-muted)'} />
                {!collapsed && (
                  <div style={{ display: 'flex', flexDirection: 'column' }}>
                    <span style={{ fontSize: '13px', fontWeight: isInventoryActive ? '600' : '500', whiteSpace: 'nowrap' }}>
                      {inventoryItem.label}
                    </span>
                    <span style={{ fontSize: '10px', color: isInventoryActive ? 'var(--color-primary)' : 'var(--color-text-muted)', fontWeight: '500', opacity: 0.85 }}>
                      {inventoryItem.caption || inventoryItem.label}
                    </span>
                  </div>
                )}
              </div>

              {!collapsed && (
                <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                  {inventoryExpanded ? (
                    <ChevronUp size={14} color="var(--color-text-muted)" />
                  ) : (
                    <ChevronDown size={14} color="var(--color-text-muted)" />
                  )}
                </div>
              )}
            </button>

            {/* Business Area Submenu */}
            {!collapsed && inventoryExpanded && (
              <div style={{
                display: 'flex',
                flexDirection: 'column',
                gap: '2px',
                marginLeft: '12px',
                paddingLeft: '12px',
                borderLeft: '1px solid var(--color-border)',
                marginTop: '2px',
                marginBottom: '4px',
              }}>
                {/* All Workflows Option */}
                <button
                  onClick={() => onOpenInventory?.(null)}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    padding: '5px 8px',
                    borderRadius: 'var(--radius-sm, 4px)',
                    border: 'none',
                    background: isInventoryActive && selectedBusinessArea === null ? 'var(--color-primary-subtle, rgba(249, 115, 22, 0.12))' : 'transparent',
                    color: isInventoryActive && selectedBusinessArea === null ? 'var(--color-primary)' : 'var(--color-text-secondary)',
                    cursor: 'pointer',
                    fontSize: '11.5px',
                    fontWeight: isInventoryActive && selectedBusinessArea === null ? '700' : '500',
                    textAlign: 'left',
                    transition: 'all 0.12s ease',
                  }}
                  onMouseEnter={(e) => {
                    if (!(isInventoryActive && selectedBusinessArea === null)) {
                      e.currentTarget.style.color = 'var(--color-text)';
                      e.currentTarget.style.backgroundColor = 'var(--color-surface-secondary)';
                    }
                  }}
                  onMouseLeave={(e) => {
                    if (!(isInventoryActive && selectedBusinessArea === null)) {
                      e.currentTarget.style.color = 'var(--color-text-secondary)';
                      e.currentTarget.style.backgroundColor = 'transparent';
                    }
                  }}
                >
                  <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    All Workflows
                  </span>
                  <span style={{
                    fontSize: '10.5px',
                    padding: '1px 5px',
                    borderRadius: '4px',
                    background: 'var(--color-surface-secondary)',
                    color: 'var(--color-text-muted)',
                  }}>
                    {totalPortfolioWorkflows}
                  </span>
                </button>

                {/* Individual Business Areas */}
                {availableBusinessAreas.map((area) => {
                  const isAreaActive = isInventoryActive && selectedBusinessArea === area.name;
                  return (
                    <button
                      key={area.name}
                      onClick={() => onOpenInventory?.(area.name)}
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'space-between',
                        padding: '5px 8px',
                        borderRadius: 'var(--radius-sm, 4px)',
                        border: 'none',
                        background: isAreaActive ? 'var(--color-primary-subtle, rgba(249, 115, 22, 0.12))' : 'transparent',
                        color: isAreaActive ? 'var(--color-primary)' : 'var(--color-text-secondary)',
                        cursor: 'pointer',
                        fontSize: '11.5px',
                        fontWeight: isAreaActive ? '700' : '500',
                        textAlign: 'left',
                        transition: 'all 0.12s ease',
                      }}
                      onMouseEnter={(e) => {
                        if (!isAreaActive) {
                          e.currentTarget.style.color = 'var(--color-text)';
                          e.currentTarget.style.backgroundColor = 'var(--color-surface-secondary)';
                        }
                      }}
                      onMouseLeave={(e) => {
                        if (!isAreaActive) {
                          e.currentTarget.style.color = 'var(--color-text-secondary)';
                          e.currentTarget.style.backgroundColor = 'transparent';
                        }
                      }}
                    >
                      <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                        {area.name}
                      </span>
                      <span style={{
                        fontSize: '10.5px',
                        padding: '1px 5px',
                        borderRadius: '4px',
                        background: 'var(--color-surface-secondary)',
                        color: isAreaActive ? 'var(--color-primary)' : 'var(--color-text-muted)',
                      }}>
                        {area.count}
                      </span>
                    </button>
                  );
                })}
              </div>
            )}
          </div>

          {/* Action 2: Rationalisation Recommendation */}
          <button
            onClick={onOpenRationalisation}
            aria-label={rationalisationItem.label}
            title={collapsed ? rationalisationItem.label : undefined}
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: collapsed ? 'center' : 'space-between',
              padding: collapsed ? '9px 0' : '8px 12px',
              borderRadius: 'var(--radius-sm)',
              border: isRationalisationOpen ? '1px solid var(--color-primary-border)' : '1px solid transparent',
              background: isRationalisationOpen ? 'var(--color-primary-subtle)' : 'transparent',
              color: isRationalisationOpen ? 'var(--color-primary)' : 'var(--color-text-secondary)',
              cursor: 'pointer',
              textAlign: 'left',
              width: '100%',
              transition: 'all 0.12s ease',
            }}
            onMouseEnter={(e) => {
              if (!isRationalisationOpen) {
                e.currentTarget.style.backgroundColor = 'var(--color-surface-secondary)';
                e.currentTarget.style.color = 'var(--color-text)';
              }
            }}
            onMouseLeave={(e) => {
              if (!isRationalisationOpen) {
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
              <Sparkles size={16} color={isRationalisationOpen ? 'var(--color-primary)' : 'var(--color-text-muted)'} />
              {!collapsed && (
                <div style={{ display: 'flex', flexDirection: 'column' }}>
                  <span style={{ fontSize: '13px', fontWeight: isRationalisationOpen ? '600' : '500', whiteSpace: 'nowrap' }}>
                    {rationalisationItem.label}
                  </span>
                  <span style={{ fontSize: '10px', color: isRationalisationOpen ? 'var(--color-primary)' : 'var(--color-text-muted)', fontWeight: '500', opacity: 0.85 }}>
                    {rationalisationItem.caption || rationalisationItem.label}
                  </span>
                </div>
              )}
            </div>

            {/* Active Dot Indicator */}
            {!collapsed && isRationalisationOpen && (
              <div style={{
                width: '6px',
                height: '6px',
                borderRadius: '50%',
                background: 'var(--color-primary)',
              }} />
            )}
          </button>

          {/* Action 3: Impact at a Glance */}
          <button
            onClick={onOpenImpact}
            aria-label={impactItem.label}
            title={collapsed ? impactItem.label : undefined}
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: collapsed ? 'center' : 'space-between',
              padding: collapsed ? '9px 0' : '8px 12px',
              borderRadius: 'var(--radius-sm)',
              border: isImpactOpen ? '1px solid var(--color-primary-border)' : '1px solid transparent',
              background: isImpactOpen ? 'var(--color-primary-subtle)' : 'transparent',
              color: isImpactOpen ? 'var(--color-primary)' : 'var(--color-text-secondary)',
              cursor: 'pointer',
              textAlign: 'left',
              width: '100%',
              transition: 'all 0.12s ease',
            }}
            onMouseEnter={(e) => {
              if (!isImpactOpen) {
                e.currentTarget.style.backgroundColor = 'var(--color-surface-secondary)';
                e.currentTarget.style.color = 'var(--color-text)';
              }
            }}
            onMouseLeave={(e) => {
              if (!isImpactOpen) {
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
              <Zap size={16} color={isImpactOpen ? 'var(--color-primary)' : 'var(--color-text-muted)'} />
              {!collapsed && (
                <div style={{ display: 'flex', flexDirection: 'column' }}>
                  <span style={{ fontSize: '13px', fontWeight: isImpactOpen ? '600' : '500', whiteSpace: 'nowrap' }}>
                    {impactItem.label}
                  </span>
                  <span style={{ fontSize: '10px', color: isImpactOpen ? 'var(--color-primary)' : 'var(--color-text-muted)', fontWeight: '500', opacity: 0.85 }}>
                    {impactItem.caption || impactItem.label}
                  </span>
                </div>
              )}
            </div>

            {/* Active Dot Indicator */}
            {!collapsed && isImpactOpen && (
              <div style={{
                width: '6px',
                height: '6px',
                borderRadius: '50%',
                background: 'var(--color-primary)',
              }} />
            )}
          </button>

          {/* Action 4: Download Portfolio XLSX */}
          <button
            onClick={onDownloadPortfolioXlsx}
            disabled={isDownloadingXlsx}
            aria-label={downloadItem.label}
            title={collapsed ? downloadItem.label : undefined}
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: collapsed ? 'center' : 'flex-start',
              padding: collapsed ? '9px 0' : '8px 12px',
              borderRadius: 'var(--radius-sm)',
              border: '1px solid transparent',
              background: 'transparent',
              color: 'var(--color-text-secondary)',
              cursor: isDownloadingXlsx ? 'not-allowed' : 'pointer',
              opacity: isDownloadingXlsx ? 0.7 : 1,
              textAlign: 'left',
              width: '100%',
              transition: 'all 0.12s ease',
            }}
            onMouseEnter={(e) => {
              if (isDownloadingXlsx) return;
              e.currentTarget.style.backgroundColor = 'var(--color-surface-secondary)';
              e.currentTarget.style.color = 'var(--color-text)';
            }}
            onMouseLeave={(e) => {
              if (isDownloadingXlsx) return;
              e.currentTarget.style.backgroundColor = 'transparent';
              e.currentTarget.style.color = 'var(--color-text-secondary)';
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
                <Loader2 size={16} color="var(--color-primary)" className="animate-spin" />
              ) : (
                <FileSpreadsheet size={16} color="var(--color-text-muted)" />
              )}
              {!collapsed && (
                <div style={{ display: 'flex', flexDirection: 'column' }}>
                  <span style={{ fontSize: '13px', fontWeight: '500', whiteSpace: 'nowrap' }}>
                    {downloadItem.label}
                  </span>
                  <span style={{ fontSize: '10px', color: 'var(--color-text-muted)', fontWeight: '500', opacity: 0.85 }}>
                    {isDownloadingXlsx ? 'Generating...' : (downloadItem.caption || downloadItem.label)}
                  </span>
                </div>
              )}
            </div>
          </button>

          {/* Action 5: Upload Different Portfolio */}
          <button
            onClick={onReset}
            aria-label={resetItem.label}
            title={collapsed ? resetItem.label : undefined}
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: collapsed ? 'center' : 'flex-start',
              padding: collapsed ? '9px 0' : '8px 12px',
              borderRadius: 'var(--radius-sm)',
              border: '1px solid transparent',
              background: 'transparent',
              color: 'var(--color-text-secondary)',
              cursor: 'pointer',
              textAlign: 'left',
              width: '100%',
              transition: 'all 0.12s ease',
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.backgroundColor = 'var(--color-surface-secondary)';
              e.currentTarget.style.color = 'var(--color-text)';
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.backgroundColor = 'transparent';
              e.currentTarget.style.color = 'var(--color-text-secondary)';
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
                  <span style={{ fontSize: '13px', fontWeight: '500', whiteSpace: 'nowrap' }}>
                    {resetItem.label}
                  </span>
                  <span style={{ fontSize: '10px', color: 'var(--color-text-muted)', fontWeight: '500', opacity: 0.85 }}>
                    {resetItem.caption || resetItem.label}
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
                  padding: collapsed ? '9px 0' : '8px 12px',
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
                    <div style={{ display: 'flex', flexDirection: 'column' }}>
                      <span style={{ fontSize: '13px', fontWeight: isActive ? '600' : '500', whiteSpace: 'nowrap' }}>
                        {item.label}
                      </span>
                      <span style={{ fontSize: '10px', color: isActive ? 'var(--color-primary)' : 'var(--color-text-muted)', fontWeight: '500', opacity: 0.85 }}>
                        {item.caption || item.label}
                      </span>
                    </div>
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
