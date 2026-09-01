import React, { useState, useMemo } from 'react';
import {
  ArrowRight,
  AlertTriangle,
  RefreshCw,
  Search,
  ArrowLeft,
  ShieldCheck,
  Scale,
  FileCheck2,
  TrendingUp,
  HelpCircle,
} from 'lucide-react';
import { PortfolioOverviewDTO, PortfolioWorkflowSummaryDTO } from '../types/portfolio';

interface PortfolioPageProps {
  portfolio: PortfolioOverviewDTO;
  selectedBusinessArea?: string | null;
  onSelectBusinessArea?: (area: string | null) => void;
  onSelectWorkflow: (workflowId: string, businessArea?: string) => void;
  onReset: () => void;
}

const CONFIGURED_BUSINESS_AREAS = [
  { name: 'Claims & Risk', icon: ShieldCheck, color: '#0284c7' },
  { name: 'Legal', icon: Scale, color: '#8b5cf6' },
  { name: 'Underwriting', icon: FileCheck2, color: '#10b981' },
  { name: 'Sales & Distribution', icon: TrendingUp, color: '#f59e0b' },
];

const UNCLASSIFIED_AREA = { name: 'Other / Unclassified', icon: HelpCircle, color: '#6b7280' };

export const PortfolioPage: React.FC<PortfolioPageProps> = ({
  portfolio,
  selectedBusinessArea,
  onSelectBusinessArea,
  onSelectWorkflow,
  onReset,
}) => {
  // Local fallback if selectedBusinessArea is not externally controlled
  const [localArea, setLocalArea] = useState<string | null>(null);
  const currentArea = selectedBusinessArea !== undefined ? selectedBusinessArea : localArea;

  const setCurrentArea = (area: string | null) => {
    if (onSelectBusinessArea) {
      onSelectBusinessArea(area);
    }
    setLocalArea(area);
  };

  const [searchQuery, setSearchQuery] = useState('');

  const { metrics } = portfolio;

  // Derive business area counts reactively from workflows
  const areaCounts: Record<string, number> = useMemo(() => {
    const counts: Record<string, number> = {
      'Claims & Risk': 0,
      'Legal': 0,
      'Underwriting': 0,
      'Sales & Distribution': 0,
    };
    let unclassified = 0;

    for (const w of portfolio.workflows) {
      if (w.status === 'SUCCESS') {
        const area = w.business_area?.business_area;
        if (area && counts[area] !== undefined) {
          counts[area]++;
        } else {
          unclassified++;
        }
      }
    }

    return { ...counts, 'Other / Unclassified': unclassified };
  }, [portfolio.workflows]);

  // Determine visible business area cards per Requirement 5
  // Prefer displaying only business areas represented in the uploaded portfolio.
  const visibleAreas = useMemo(() => {
    const areasWithWorkflows = CONFIGURED_BUSINESS_AREAS.filter((a) => (areaCounts[a.name] || 0) > 0);
    const result = areasWithWorkflows.length > 0 ? areasWithWorkflows : CONFIGURED_BUSINESS_AREAS;
    if ((areaCounts['Other / Unclassified'] || 0) > 0) {
      return [...result, UNCLASSIFIED_AREA];
    }
    return result;
  }, [areaCounts]);

  // Get all workflows for the currently selected business area (Level 2)
  const currentAreaWorkflows = useMemo(() => {
    if (!currentArea) return [];
    return portfolio.workflows.filter((w) => {
      if (currentArea === 'Other / Unclassified') {
        const area = w.business_area?.business_area;
        return !area || area === 'UNCLASSIFIED' || area === 'Other / Unclassified';
      }
      return w.business_area?.business_area === currentArea;
    });
  }, [portfolio.workflows, currentArea]);

  // Filtered workflows for Level 2 Dashboard Summary search
  const filteredAreaWorkflows = useMemo(() => {
    if (!searchQuery) return currentAreaWorkflows;
    const q = searchQuery.toLowerCase();
    return currentAreaWorkflows.filter((w) => (
      w.filename.toLowerCase().includes(q) ||
      w.relative_path.toLowerCase().includes(q) ||
      w.sources.some((s) => s.toLowerCase().includes(q)) ||
      w.targets.some((t) => t.toLowerCase().includes(q)) ||
      (w.business_purpose && w.business_purpose.toLowerCase().includes(q))
    ));
  }, [currentAreaWorkflows, searchQuery]);

  // Compact list renderer for sources and targets (Requirement 14 & 15)
  const renderCompactList = (items: string[], emptyLabel: string = 'None') => {
    if (!items || items.length === 0) {
      return <span style={{ color: 'var(--color-text-muted)', fontStyle: 'italic', fontSize: '12px' }}>{emptyLabel}</span>;
    }
    const displayItems = items.slice(0, 2);
    const remaining = items.length - 2;
    return (
      <div style={{ display: 'flex', flexDirection: 'column', gap: '3px' }}>
        {displayItems.map((item, idx) => (
          <span
            key={idx}
            style={{
              fontSize: '12px',
              color: 'var(--color-text)',
              fontFamily: 'var(--font-mono, monospace)',
              overflow: 'hidden',
              textOverflow: 'ellipsis',
              whiteSpace: 'nowrap',
              maxWidth: '220px',
              display: 'block',
            }}
            title={item}
          >
            {item}
          </span>
        ))}
        {remaining > 0 && (
          <span
            style={{
              fontSize: '11px',
              color: 'var(--color-primary)',
              fontWeight: '600',
              cursor: 'help',
            }}
            title={items.slice(2).join('\n')}
          >
            +{remaining} more
          </span>
        )}
      </div>
    );
  };

  // -------------------------------------------------------------------------
  // LEVEL 2: Dashboard Summary (When a business area is selected)
  // -------------------------------------------------------------------------
  if (currentArea) {
    const areaMeta = CONFIGURED_BUSINESS_AREAS.find((a) => a.name === currentArea) || UNCLASSIFIED_AREA;
    const AreaIcon = areaMeta.icon;

    return (
      <div style={{ maxWidth: '1400px', margin: '0 auto', display: 'flex', flexDirection: 'column', gap: '24px' }}>
        {/* Top Navigation Action Bar */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '16px' }}>
          <button
            onClick={() => {
              setCurrentArea(null);
              setSearchQuery('');
            }}
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '8px',
              padding: '6px 12px',
              borderRadius: 'var(--radius-sm)',
              border: '1px solid var(--color-border)',
              background: 'var(--color-surface)',
              color: 'var(--color-primary)',
              fontSize: '13px',
              fontWeight: '700',
              cursor: 'pointer',
              transition: 'all 0.15s ease',
            }}
            title="Return to Business Area Portfolio"
          >
            <ArrowLeft size={15} /> All Business Areas
          </button>

          <button
            onClick={onReset}
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '8px',
              padding: '6px 14px',
              fontSize: '13px',
              fontWeight: '600',
              borderRadius: 'var(--radius-sm)',
              border: '1px solid var(--color-border)',
              background: 'var(--color-surface)',
              color: 'var(--color-text)',
              cursor: 'pointer',
            }}
          >
            <RefreshCw size={13} /> Upload Different Portfolio
          </button>
        </div>

        {/* Dashboard Summary Header per Requirement 8 */}
        <div style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'flex-start',
          paddingBottom: '16px',
          borderBottom: '1px solid var(--color-border)',
          flexWrap: 'wrap',
          gap: '16px',
        }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '6px' }}>
              <span
                style={{
                  fontSize: '11px',
                  fontWeight: '700',
                  textTransform: 'uppercase',
                  letterSpacing: '0.08em',
                  padding: '3px 8px',
                  borderRadius: '4px',
                  background: 'var(--color-primary-subtle)',
                  color: 'var(--color-primary)',
                }}
              >
                ETL Portfolio
              </span>
              <span style={{ fontSize: '13px', color: 'var(--color-text-muted)' }}>
                Portfolio ID: <code style={{ fontSize: '12px' }}>{portfolio.portfolio_id}</code>
              </span>
            </div>

            <h1 style={{ fontSize: '28px', fontWeight: '800', color: 'var(--color-text)', letterSpacing: '-0.5px', margin: '0 0 6px 0' }}>
              Dashboard Summary
            </h1>

            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <div style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '6px',
                padding: '4px 10px',
                borderRadius: '6px',
                background: 'var(--color-surface-secondary)',
                border: '1px solid var(--color-border)',
                fontWeight: '700',
                fontSize: '14px',
                color: 'var(--color-text)',
              }}>
                <AreaIcon size={16} color={areaMeta.color} />
                <span>{currentArea}</span>
              </div>
              <span style={{ fontSize: '14px', fontWeight: '600', color: 'var(--color-text-secondary)' }}>
                {currentAreaWorkflows.length} {currentAreaWorkflows.length === 1 ? 'Workflow' : 'Workflows'}
              </span>
            </div>
          </div>

          {/* Lightweight search within selected business area per Requirement 31 */}
          <div style={{ minWidth: '280px', position: 'relative', display: 'flex', alignItems: 'center' }}>
            <Search size={15} color="var(--color-text-muted)" style={{ position: 'absolute', left: '12px' }} />
            <input
              type="text"
              placeholder={`Search in ${currentArea}...`}
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              style={{
                width: '100%',
                padding: '8px 12px 8px 34px',
                borderRadius: 'var(--radius-sm)',
                border: '1px solid var(--color-border)',
                background: 'var(--color-surface)',
                color: 'var(--color-text)',
                fontSize: '13px',
              }}
            />
          </div>
        </div>

        {/* Dashboard Summary Workflow Table per Requirement 9-16 */}
        <div className="app-card" style={{ overflow: 'hidden', padding: 0 }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '13px' }}>
            <thead>
              <tr style={{ background: 'var(--color-surface-secondary)', borderBottom: '1px solid var(--color-border)' }}>
                <th style={{ padding: '14px 20px', fontWeight: '700', color: 'var(--color-text-secondary)', minWidth: '220px' }}>Workflow</th>
                <th style={{ padding: '14px 16px', fontWeight: '700', color: 'var(--color-text-secondary)' }}>Business Summary</th>
                <th style={{ padding: '14px 16px', fontWeight: '700', color: 'var(--color-text-secondary)', textAlign: 'center', width: '70px' }}>Tools</th>
                <th style={{ padding: '14px 16px', fontWeight: '700', color: 'var(--color-text-secondary)', textAlign: 'center', width: '100px' }}>Connections</th>
                <th style={{ padding: '14px 16px', fontWeight: '700', color: 'var(--color-text-secondary)', minWidth: '180px' }}>Sources</th>
                <th style={{ padding: '14px 16px', fontWeight: '700', color: 'var(--color-text-secondary)', minWidth: '180px' }}>Targets</th>
                <th style={{ padding: '14px 20px', fontWeight: '700', color: 'var(--color-text-secondary)', textAlign: 'right', width: '110px' }}>Action</th>
              </tr>
            </thead>
            <tbody>
              {filteredAreaWorkflows.length === 0 ? (
                <tr>
                  <td colSpan={7} style={{ padding: '36px', textAlign: 'center', color: 'var(--color-text-muted)' }}>
                    No workflows found matching "{searchQuery}" in {currentArea}.
                  </td>
                </tr>
              ) : (
                filteredAreaWorkflows.map((wf: PortfolioWorkflowSummaryDTO) => {
                  const isSuccess = wf.status === 'SUCCESS';
                  return (
                    <tr
                      key={wf.workflow_id}
                      onClick={() => isSuccess && onSelectWorkflow(wf.workflow_id, currentArea)}
                      style={{
                        borderBottom: '1px solid var(--color-border)',
                        cursor: isSuccess ? 'pointer' : 'default',
                        transition: 'background 0.15s ease',
                      }}
                      onMouseEnter={(e) => {
                        if (isSuccess) e.currentTarget.style.background = 'var(--color-surface-hover)';
                      }}
                      onMouseLeave={(e) => {
                        e.currentTarget.style.background = 'transparent';
                      }}
                    >
                      {/* 1. Workflow Column per Requirement 10 */}
                      <td style={{ padding: '14px 20px', verticalAlign: 'top' }}>
                        <div style={{ fontWeight: '700', color: 'var(--color-text)', wordBreak: 'break-word' }}>
                          {wf.filename}
                        </div>
                        {wf.relative_path && wf.relative_path !== wf.filename && (
                          <div style={{ fontSize: '11px', color: 'var(--color-text-muted)', marginTop: '2px' }}>
                            {wf.relative_path}
                          </div>
                        )}
                        {!isSuccess && (
                          <div style={{
                            display: 'inline-flex',
                            alignItems: 'center',
                            gap: '4px',
                            color: '#b91c1c',
                            fontSize: '11px',
                            fontWeight: '700',
                            marginTop: '4px',
                          }}>
                            <AlertTriangle size={12} /> Failed: {wf.error_message || 'Analysis error'}
                          </div>
                        )}
                      </td>

                      {/* 2. Business Summary Column per Requirement 11 */}
                      <td style={{ padding: '14px 16px', color: 'var(--color-text-secondary)', verticalAlign: 'top' }}>
                        <div style={{
                          fontSize: '13px',
                          lineHeight: '1.45',
                          maxHeight: '4.4em',
                          overflow: 'hidden',
                          textOverflow: 'ellipsis',
                          display: '-webkit-box',
                          WebkitLineClamp: 3,
                          WebkitBoxOrient: 'vertical',
                        }}>
                          {wf.business_purpose || 'Analytical data processing workflow.'}
                        </div>
                      </td>

                      {/* 3. Tools Column per Requirement 12 */}
                      <td style={{ padding: '14px 16px', textAlign: 'center', fontWeight: '700', color: 'var(--color-text)', verticalAlign: 'top' }}>
                        {wf.node_count}
                      </td>

                      {/* 4. Connections Column per Requirement 13 */}
                      <td style={{ padding: '14px 16px', textAlign: 'center', fontWeight: '700', color: 'var(--color-text)', verticalAlign: 'top' }}>
                        {wf.connection_count}
                      </td>

                      {/* 5. Sources Column per Requirement 14 */}
                      <td style={{ padding: '14px 16px', verticalAlign: 'top' }}>
                        {renderCompactList(wf.sources, 'None')}
                      </td>

                      {/* 6. Targets Column per Requirement 15 */}
                      <td style={{ padding: '14px 16px', verticalAlign: 'top' }}>
                        {renderCompactList(wf.targets, 'None')}
                      </td>

                      {/* 7. Action Column per Requirement 16 */}
                      <td style={{ padding: '14px 20px', textAlign: 'right', verticalAlign: 'top' }}>
                        {isSuccess && (
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              onSelectWorkflow(wf.workflow_id, currentArea);
                            }}
                            style={{
                              display: 'inline-flex',
                              alignItems: 'center',
                              gap: '4px',
                              padding: '6px 12px',
                              fontSize: '12px',
                              fontWeight: '700',
                              borderRadius: 'var(--radius-sm)',
                              border: '1px solid var(--color-border)',
                              background: 'var(--color-primary-subtle)',
                              color: 'var(--color-primary)',
                              cursor: 'pointer',
                              transition: 'all 0.15s ease',
                            }}
                          >
                            Inspect <ArrowRight size={13} />
                          </button>
                        )}
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>
    );
  }

  // -------------------------------------------------------------------------
  // LEVEL 1: Business Area Portfolio (Initial Landing View)
  // -------------------------------------------------------------------------
  return (
    <div style={{ maxWidth: '1400px', margin: '0 auto', display: 'flex', flexDirection: 'column', gap: '32px' }}>
      {/* Portfolio Title & Action Bar per Requirement 3 */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '16px' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '8px' }}>
            <span
              style={{
                fontSize: '11px',
                fontWeight: '700',
                textTransform: 'uppercase',
                letterSpacing: '0.08em',
                padding: '3px 8px',
                borderRadius: '4px',
                background: 'var(--color-primary-subtle)',
                color: 'var(--color-primary)',
              }}
            >
              ETL Portfolio
            </span>
            <span style={{ fontSize: '13px', color: 'var(--color-text-muted)' }}>
              Portfolio ID: <code style={{ fontSize: '12px' }}>{portfolio.portfolio_id}</code>
            </span>
          </div>

          <h1 style={{ fontSize: '28px', fontWeight: '800', color: 'var(--color-text)', letterSpacing: '-0.5px', margin: 0 }}>
            {portfolio.portfolio_name}
          </h1>

          <p style={{ fontSize: '14px', color: 'var(--color-text-secondary)', margin: '6px 0 0 0' }}>
            Select a business area to inspect workflows, operations, and cross-functional deliverables.
          </p>

          {/* Prominent Dynamic Workflow Count per Requirement 3 */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '14px', marginTop: '16px', flexWrap: 'wrap' }}>
            <div style={{
              display: 'inline-flex',
              alignItems: 'baseline',
              gap: '8px',
              padding: '8px 16px',
              borderRadius: 'var(--radius-sm)',
              background: 'var(--color-surface)',
              border: '1px solid var(--color-border)',
              boxShadow: '0 1px 3px rgba(0,0,0,0.05)',
            }}>
              <span style={{ fontSize: '22px', fontWeight: '800', color: 'var(--color-primary)' }}>
                {metrics.successful_workflows}
              </span>
              <span style={{ fontSize: '12px', fontWeight: '700', letterSpacing: '0.08em', color: 'var(--color-text-secondary)', textTransform: 'uppercase' }}>
                WORKFLOWS ANALYSED
              </span>
            </div>

            {metrics.failed_workflows > 0 && (
              <div style={{
                display: 'inline-flex',
                alignItems: 'baseline',
                gap: '8px',
                padding: '8px 16px',
                borderRadius: 'var(--radius-sm)',
                background: 'var(--color-error-subtle)',
                border: '1px solid rgba(220, 38, 38, 0.3)',
              }}>
                <span style={{ fontSize: '20px', fontWeight: '800', color: 'var(--color-error)' }}>
                  {metrics.failed_workflows}
                </span>
                <span style={{ fontSize: '12px', fontWeight: '700', letterSpacing: '0.08em', color: 'var(--color-error)', textTransform: 'uppercase' }}>
                  {metrics.failed_workflows === 1 ? 'WORKFLOW FAILED' : 'WORKFLOWS FAILED'}
                </span>
              </div>
            )}
          </div>
        </div>

        <button
          onClick={onReset}
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: '8px',
            padding: '8px 16px',
            fontSize: '13px',
            fontWeight: '600',
            borderRadius: 'var(--radius-sm)',
            border: '1px solid var(--color-border)',
            background: 'var(--color-surface)',
            color: 'var(--color-text)',
            cursor: 'pointer',
          }}
        >
          <RefreshCw size={14} /> Upload Different Portfolio
        </button>
      </div>

      {/* Business Area Cards Grid per Requirement 2, 4, 5, 7 */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))',
        gap: '20px',
      }}>
        {visibleAreas.map((area) => {
          const Icon = area.icon;
          const count = areaCounts[area.name] || 0;

          return (
            <div
              key={area.name}
              onClick={() => setCurrentArea(area.name)}
              className="app-card"
              style={{
                padding: '24px',
                cursor: 'pointer',
                borderRadius: 'var(--radius-md, 8px)',
                border: '1px solid var(--color-border)',
                background: 'var(--color-surface)',
                transition: 'all 0.2s ease',
                display: 'flex',
                flexDirection: 'column',
                justifyContent: 'space-between',
                minHeight: '160px',
                boxShadow: '0 1px 3px rgba(0,0,0,0.04)',
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.borderColor = 'var(--color-primary)';
                e.currentTarget.style.boxShadow = '0 4px 12px rgba(2, 132, 199, 0.12)';
                e.currentTarget.style.transform = 'translateY(-2px)';
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.borderColor = 'var(--color-border)';
                e.currentTarget.style.boxShadow = '0 1px 3px rgba(0,0,0,0.04)';
                e.currentTarget.style.transform = 'translateY(0)';
              }}
            >
              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
                  <span style={{ fontSize: '16px', fontWeight: '800', color: 'var(--color-text)' }}>
                    {area.name}
                  </span>
                  <div style={{
                    width: '38px',
                    height: '38px',
                    borderRadius: '8px',
                    background: 'var(--color-surface-secondary)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                  }}>
                    <Icon size={20} color={area.color} />
                  </div>
                </div>

                <div style={{ display: 'flex', alignItems: 'baseline', gap: '6px' }}>
                  <span style={{ fontSize: '32px', fontWeight: '800', color: 'var(--color-text)' }}>
                    {count}
                  </span>
                  <span style={{ fontSize: '14px', fontWeight: '600', color: 'var(--color-text-muted)' }}>
                    {count === 1 ? 'Workflow' : 'Workflows'}
                  </span>
                </div>
              </div>

              {/* View Portfolio Button per Requirement 4 & 7 */}
              <div style={{ marginTop: '24px' }}>
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    setCurrentArea(area.name);
                  }}
                  style={{
                    display: 'inline-flex',
                    alignItems: 'center',
                    gap: '6px',
                    padding: '8px 14px',
                    borderRadius: 'var(--radius-sm)',
                    border: '1px solid var(--color-primary)',
                    background: 'var(--color-primary-subtle)',
                    color: 'var(--color-primary)',
                    fontSize: '13px',
                    fontWeight: '700',
                    cursor: 'pointer',
                    transition: 'all 0.15s ease',
                  }}
                >
                  View Portfolio <ArrowRight size={14} />
                </button>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
