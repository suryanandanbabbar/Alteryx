import React, { useState, useMemo } from 'react';
import {
  ArrowRight,
  ArrowLeft,
  ArrowUpRight,
  AlertTriangle,
  RefreshCw,
  Search,
  ShieldCheck,
  Scale,
  FileCheck2,
  TrendingUp,
  HelpCircle,
  Database,
  Target,
  LucideIcon,
  X,
} from 'lucide-react';
import { PortfolioOverviewDTO, PortfolioWorkflowSummaryDTO } from '../types/portfolio';

interface PortfolioPageProps {
  portfolio: PortfolioOverviewDTO;
  selectedBusinessArea?: string | null;
  onSelectBusinessArea?: (area: string | null) => void;
  onSelectWorkflow: (workflowId: string, businessArea?: string) => void;
  onReset: () => void;
}

interface DomainConfig {
  name: string;
  icon: LucideIcon;
  color: string;
  subtleBg: string;
  borderColor: string;
  description: string;
}

const CONFIGURED_BUSINESS_AREAS: DomainConfig[] = [
  {
    name: 'Claims & Risk',
    icon: ShieldCheck,
    color: '#38bdf8',
    subtleBg: 'rgba(56, 189, 248, 0.08)',
    borderColor: 'rgba(56, 189, 248, 0.25)',
    description: 'Loss exposure, claim volume, fraud detection & reserves',
  },
  {
    name: 'Legal',
    icon: Scale,
    color: '#c084fc',
    subtleBg: 'rgba(192, 132, 252, 0.08)',
    borderColor: 'rgba(192, 132, 252, 0.25)',
    description: 'Contract analysis, compliance, matters & regulatory reporting',
  },
  {
    name: 'Underwriting',
    icon: FileCheck2,
    color: '#34d399',
    subtleBg: 'rgba(52, 211, 153, 0.08)',
    borderColor: 'rgba(52, 211, 153, 0.25)',
    description: 'Policy lifecycle, eligibility scoring & premium calculation',
  },
  {
    name: 'Sales & Distribution',
    icon: TrendingUp,
    color: '#fbbf24',
    subtleBg: 'rgba(251, 191, 36, 0.08)',
    borderColor: 'rgba(251, 191, 36, 0.25)',
    description: 'Producer commissions, sales volume & territory aggregation',
  },
];

const UNCLASSIFIED_DOMAIN: DomainConfig = {
  name: 'Other / Unclassified',
  icon: HelpCircle,
  color: '#94a3b8',
  subtleBg: 'rgba(148, 163, 184, 0.06)',
  borderColor: 'rgba(148, 163, 184, 0.2)',
  description: 'Workflows pending explicit business-domain attribution',
};

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
  const [hoveredDomainCard, setHoveredDomainCard] = useState<string | null>(null);
  const [hoveredWorkflowId, setHoveredWorkflowId] = useState<string | null>(null);

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

  // Determine visible business area cards per Requirement 5:
  // Prefer displaying only business areas represented in the uploaded portfolio.
  const visibleAreas = useMemo(() => {
    const areasWithWorkflows = CONFIGURED_BUSINESS_AREAS.filter((a) => (areaCounts[a.name] || 0) > 0);
    const result = areasWithWorkflows.length > 0 ? areasWithWorkflows : CONFIGURED_BUSINESS_AREAS;
    if ((areaCounts['Other / Unclassified'] || 0) > 0) {
      return [...result, UNCLASSIFIED_DOMAIN];
    }
    return result;
  }, [areaCounts]);

  // Workflows for currently selected domain (Level 2)
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

  // Contextual summary strip metrics for Level 2
  const areaMetrics = useMemo(() => {
    let tools = 0;
    let connections = 0;
    const uniqueSources = new Set<string>();
    const uniqueTargets = new Set<string>();

    for (const w of currentAreaWorkflows) {
      tools += w.node_count || 0;
      connections += w.connection_count || 0;
      (w.sources || []).forEach((s) => uniqueSources.add(s));
      (w.targets || []).forEach((t) => uniqueTargets.add(t));
    }

    return {
      workflows: currentAreaWorkflows.length,
      tools,
      connections,
      sources: uniqueSources.size,
      targets: uniqueTargets.size,
    };
  }, [currentAreaWorkflows]);

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

  // Render ALL dataset chips directly without truncation (+1 more is completely removed)
  const renderAllDatasetChips = (items: string[], emptyLabel: string = 'None', isTarget: boolean = false) => {
    if (!items || items.length === 0) {
      return (
        <span style={{ color: 'var(--color-text-subtle)', fontStyle: 'italic', fontSize: '12px' }}>
          {emptyLabel}
        </span>
      );
    }

    return (
      <div style={{
        display: 'flex',
        flexWrap: 'wrap',
        gap: '8px',
        alignItems: 'flex-start',
      }}>
        {items.map((item, idx) => (
          <div
            key={idx}
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '6px',
              padding: '4px 10px',
              borderRadius: '5px',
              background: isTarget ? 'rgba(34, 197, 94, 0.08)' : 'var(--color-surface)',
              border: isTarget ? '1px solid rgba(34, 197, 94, 0.28)' : '1px solid var(--color-border)',
              maxWidth: '100%',
            }}
          >
            {isTarget ? (
              <Target size={12} color="#22c55e" style={{ flexShrink: 0 }} />
            ) : (
              <Database size={12} color="var(--color-text-muted)" style={{ flexShrink: 0 }} />
            )}
            <span
              style={{
                fontSize: '12px',
                color: isTarget ? 'var(--color-text)' : 'var(--color-text)',
                fontFamily: 'var(--font-mono, monospace)',
                wordBreak: 'break-word',
                lineHeight: '1.35',
              }}
            >
              {item}
            </span>
          </div>
        ))}
      </div>
    );
  };

  // -------------------------------------------------------------------------
  // LEVEL 2: Dashboard Summary — Wide Horizontal Workflow Intelligence Cards
  // -------------------------------------------------------------------------
  if (currentArea) {
    const areaMeta = CONFIGURED_BUSINESS_AREAS.find((a) => a.name === currentArea) || UNCLASSIFIED_DOMAIN;
    const AreaIcon = areaMeta.icon;

    return (
      <div style={{ maxWidth: '1440px', margin: '0 auto', display: 'flex', flexDirection: 'column', gap: '32px' }}>
        {/* Top Navigation Strip */}
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
              padding: '7px 14px',
              borderRadius: 'var(--radius-sm)',
              border: '1px solid var(--color-border)',
              background: 'var(--color-surface)',
              color: 'var(--color-text-secondary)',
              fontSize: '12.5px',
              fontWeight: '600',
              cursor: 'pointer',
              transition: 'all 0.18s ease',
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
            title="Return to Business Area Portfolio"
          >
            <ArrowLeft size={15} /> All Business Areas
          </button>

          <button
            onClick={onReset}
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '6px',
              padding: '6px 12px',
              fontSize: '12px',
              fontWeight: '500',
              borderRadius: 'var(--radius-sm)',
              border: '1px solid var(--color-border)',
              background: 'transparent',
              color: 'var(--color-text-muted)',
              cursor: 'pointer',
              transition: 'all 0.15s ease',
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.color = 'var(--color-text)';
              e.currentTarget.style.borderColor = 'var(--color-text-muted)';
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.color = 'var(--color-text-muted)';
              e.currentTarget.style.borderColor = 'var(--color-border)';
            }}
          >
            <RefreshCw size={12} /> Upload Different Portfolio
          </button>
        </div>

        {/* Dashboard Summary Header */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
          <div style={{
            fontSize: '11px',
            fontWeight: '700',
            textTransform: 'uppercase',
            letterSpacing: '0.14em',
            color: 'var(--color-primary)',
          }}>
            ETL PORTFOLIO
          </div>

          <h1 style={{ fontSize: '32px', fontWeight: '800', color: 'var(--color-text)', letterSpacing: '-0.02em', margin: 0 }}>
            Dashboard Summary
          </h1>

          <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginTop: '4px' }}>
            <div style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '7px',
              padding: '4px 12px',
              borderRadius: '6px',
              background: areaMeta.subtleBg,
              border: `1px solid ${areaMeta.borderColor}`,
              fontSize: '14px',
              fontWeight: '700',
              color: areaMeta.color,
            }}>
              <AreaIcon size={15} color={areaMeta.color} />
              <span>{currentArea}</span>
            </div>

            <span style={{ fontSize: '14px', fontWeight: '600', color: 'var(--color-text-muted)' }}>
              {currentAreaWorkflows.length} {currentAreaWorkflows.length === 1 ? 'Workflow' : 'Workflows'}
            </span>
          </div>
        </div>

        {/* Restrained Contextual Executive Metric Strip */}
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: '24px',
          padding: '14px 22px',
          borderRadius: 'var(--radius-md)',
          background: 'var(--color-surface)',
          border: '1px solid var(--color-border)',
          boxShadow: '0 1px 3px rgba(0,0,0,0.08)',
          flexWrap: 'wrap',
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span style={{ fontSize: '18px', fontWeight: '800', color: 'var(--color-text)' }}>
              {String(areaMetrics.workflows).padStart(2, '0')}
            </span>
            <span style={{ fontSize: '11px', fontWeight: '600', color: 'var(--color-text-muted)', textTransform: 'uppercase', letterSpacing: '0.08em' }}>
              Workflows
            </span>
          </div>

          <div style={{ width: '1px', height: '18px', background: 'var(--color-border)' }} />

          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span style={{ fontSize: '18px', fontWeight: '800', color: 'var(--color-text)' }}>
              {String(areaMetrics.tools).padStart(2, '0')}
            </span>
            <span style={{ fontSize: '11px', fontWeight: '600', color: 'var(--color-text-muted)', textTransform: 'uppercase', letterSpacing: '0.08em' }}>
              Tools
            </span>
          </div>

          <div style={{ width: '1px', height: '18px', background: 'var(--color-border)' }} />

          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span style={{ fontSize: '18px', fontWeight: '800', color: 'var(--color-text)' }}>
              {String(areaMetrics.connections).padStart(2, '0')}
            </span>
            <span style={{ fontSize: '11px', fontWeight: '600', color: 'var(--color-text-muted)', textTransform: 'uppercase', letterSpacing: '0.08em' }}>
              Connections
            </span>
          </div>

          <div style={{ width: '1px', height: '18px', background: 'var(--color-border)' }} />

          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span style={{ fontSize: '18px', fontWeight: '800', color: '#22c55e' }}>
              {String(areaMetrics.targets).padStart(2, '0')}
            </span>
            <span style={{ fontSize: '11px', fontWeight: '600', color: 'var(--color-text-muted)', textTransform: 'uppercase', letterSpacing: '0.08em' }}>
              Production Targets
            </span>
          </div>

          <div style={{ width: '1px', height: '18px', background: 'var(--color-border)' }} />

          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span style={{ fontSize: '18px', fontWeight: '800', color: 'var(--color-text)' }}>
              {String(areaMetrics.sources).padStart(2, '0')}
            </span>
            <span style={{ fontSize: '11px', fontWeight: '600', color: 'var(--color-text-muted)', textTransform: 'uppercase', letterSpacing: '0.08em' }}>
              Sources
            </span>
          </div>
        </div>

        {/* Lightweight Search Toolbar within Selected Business Area */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '12px' }}>
          <div style={{ minWidth: '320px', position: 'relative', display: 'flex', alignItems: 'center' }}>
            <Search size={14} color="var(--color-text-muted)" style={{ position: 'absolute', left: '12px' }} />
            <input
              type="text"
              placeholder={`Filter workflows in ${currentArea}...`}
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              style={{
                width: '100%',
                padding: '9px 12px 9px 34px',
                borderRadius: 'var(--radius-sm)',
                border: '1px solid var(--color-border)',
                background: 'var(--color-surface)',
                color: 'var(--color-text)',
                fontSize: '12.5px',
                outline: 'none',
                transition: 'border-color 0.15s ease',
              }}
              onFocus={(e) => { e.currentTarget.style.borderColor = 'var(--color-primary)'; }}
              onBlur={(e) => { e.currentTarget.style.borderColor = 'var(--color-border)'; }}
            />
            {searchQuery && (
              <button
                onClick={() => setSearchQuery('')}
                style={{
                  position: 'absolute',
                  right: '10px',
                  background: 'none',
                  border: 'none',
                  color: 'var(--color-text-muted)',
                  cursor: 'pointer',
                  padding: '2px',
                  display: 'flex',
                  alignItems: 'center',
                }}
                title="Clear filter"
              >
                <X size={13} />
              </button>
            )}
          </div>

          <span style={{ fontSize: '12px', color: 'var(--color-text-muted)' }}>
            Showing {filteredAreaWorkflows.length} of {currentAreaWorkflows.length} workflows
          </span>
        </div>

        {/* Horizontal Workflow Intelligence Cards (One wide card per row) */}
        {filteredAreaWorkflows.length === 0 ? (
          <div style={{
            padding: '60px 24px',
            textAlign: 'center',
            background: 'var(--color-surface)',
            border: '1px solid var(--color-border)',
            borderRadius: '10px',
          }}>
            <Search size={32} color="var(--color-text-muted)" style={{ margin: '0 auto 16px' }} />
            <h3 style={{ fontSize: '18px', fontWeight: '700', color: 'var(--color-text)', margin: '0 0 8px 0' }}>
              No workflows found
            </h3>
            <p style={{ fontSize: '13px', color: 'var(--color-text-secondary)', margin: '0 0 20px 0' }}>
              No workflows match "{searchQuery}" in {currentArea}. Try a different workflow name, dataset, or keyword.
            </p>
            <button
              onClick={() => setSearchQuery('')}
              style={{
                padding: '8px 16px',
                borderRadius: 'var(--radius-sm)',
                border: '1px solid var(--color-border)',
                background: 'var(--color-surface-secondary)',
                color: 'var(--color-text)',
                fontSize: '12.5px',
                fontWeight: '600',
                cursor: 'pointer',
              }}
            >
              Clear Search Filter
            </button>
          </div>
        ) : (
          <div style={{
            display: 'flex',
            flexDirection: 'column',
            gap: '24px',
          }}>
            {filteredAreaWorkflows.map((wf: PortfolioWorkflowSummaryDTO) => {
              const isSuccess = wf.status === 'SUCCESS';
              const isHovered = hoveredWorkflowId === wf.workflow_id;

              return (
                <div
                  key={wf.workflow_id}
                  onClick={() => isSuccess && onSelectWorkflow(wf.workflow_id, currentArea)}
                  onMouseEnter={() => setHoveredWorkflowId(wf.workflow_id)}
                  onMouseLeave={() => setHoveredWorkflowId(null)}
                  style={{
                    width: '100%',
                    position: 'relative',
                    padding: '28px 32px',
                    borderRadius: '10px',
                    background: isHovered ? 'var(--color-surface-hover)' : 'var(--color-surface)',
                    border: isHovered
                      ? '1px solid var(--color-primary-border)'
                      : '1px solid var(--color-border)',
                    boxShadow: isHovered
                      ? '0 12px 28px -10px rgba(0, 0, 0, 0.45)'
                      : '0 2px 6px rgba(0, 0, 0, 0.08)',
                    transform: isHovered ? 'translateY(-2px)' : 'none',
                    transition: 'all 0.2s cubic-bezier(0.16, 1, 0.3, 1)',
                    cursor: isSuccess ? 'pointer' : 'default',
                    display: 'flex',
                    flexDirection: 'column',
                    gap: '20px',
                  }}
                >
                  {/* Top Row: Identity, Business Summary & Inspect Action */}
                  <div style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'flex-start',
                    flexWrap: 'wrap',
                    gap: '20px',
                  }}>
                    <div style={{ flex: 1, minWidth: '300px' }}>
                      {/* Status & Overline */}
                      <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '8px' }}>
                        {isSuccess ? (
                          <div style={{
                            display: 'inline-flex',
                            alignItems: 'center',
                            gap: '6px',
                            fontSize: '11px',
                            fontWeight: '700',
                            letterSpacing: '0.08em',
                            color: '#22c55e',
                            textTransform: 'uppercase',
                          }}>
                            <span style={{ width: '6px', height: '6px', borderRadius: '50%', background: '#22c55e' }} />
                            Analysed
                          </div>
                        ) : (
                          <div style={{
                            display: 'inline-flex',
                            alignItems: 'center',
                            gap: '5px',
                            fontSize: '11px',
                            fontWeight: '700',
                            letterSpacing: '0.08em',
                            color: 'var(--color-error)',
                            textTransform: 'uppercase',
                          }}>
                            <AlertTriangle size={12} />
                            Analysis Failed
                          </div>
                        )}

                        <span style={{
                          fontSize: '10px',
                          fontWeight: '700',
                          textTransform: 'uppercase',
                          letterSpacing: '0.12em',
                          color: 'var(--color-text-subtle)',
                        }}>
                          WORKFLOW
                        </span>
                      </div>

                      {/* Filename & Path */}
                      <h2 style={{
                        fontSize: '19px',
                        fontWeight: '800',
                        color: isHovered ? 'var(--color-primary)' : 'var(--color-text)',
                        margin: '0 0 4px 0',
                        lineHeight: '1.35',
                        wordBreak: 'break-word',
                        transition: 'color 0.15s ease',
                        letterSpacing: '-0.01em',
                      }}>
                        {wf.filename}
                      </h2>

                      {wf.relative_path && wf.relative_path !== wf.filename && (
                        <div style={{
                          fontSize: '11.5px',
                          color: 'var(--color-text-subtle)',
                          fontFamily: 'var(--font-mono, monospace)',
                          wordBreak: 'break-all',
                          marginBottom: '8px',
                        }}>
                          {wf.relative_path}
                        </div>
                      )}

                      {!isSuccess && wf.error_message && (
                        <div style={{ fontSize: '11.5px', color: 'var(--color-error)', margin: '4px 0 8px 0' }}>
                          {wf.error_message}
                        </div>
                      )}

                      {/* Business Purpose Narrative (Comfortably wraps across wide card) */}
                      <p style={{
                        fontSize: '13.5px',
                        lineHeight: '1.6',
                        color: 'var(--color-text-secondary)',
                        margin: '8px 0 0 0',
                        maxWidth: '1050px',
                      }}>
                        {wf.business_purpose || 'Analytical data processing workflow.'}
                      </p>
                    </div>

                    {/* Inspect Workflow Action CTA */}
                    {isSuccess && (
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          onSelectWorkflow(wf.workflow_id, currentArea);
                        }}
                        style={{
                          display: 'inline-flex',
                          alignItems: 'center',
                          gap: '7px',
                          padding: '9px 18px',
                          borderRadius: 'var(--radius-sm)',
                          border: isHovered
                            ? '1px solid var(--color-primary)'
                            : '1px solid var(--color-border)',
                          background: isHovered
                            ? 'var(--color-primary)'
                            : 'var(--color-primary-subtle)',
                          color: isHovered
                            ? '#ffffff'
                            : 'var(--color-primary)',
                          fontSize: '13px',
                          fontWeight: '700',
                          cursor: 'pointer',
                          transition: 'all 0.18s ease',
                          whiteSpace: 'nowrap',
                          alignSelf: 'flex-start',
                        }}
                      >
                        <span>Inspect Workflow</span>
                        <ArrowRight
                          size={14}
                          style={{
                            transform: isHovered ? 'translateX(3px)' : 'none',
                            transition: 'transform 0.18s ease',
                          }}
                        />
                      </button>
                    )}
                  </div>

                  {/* Hairline Divider */}
                  <div style={{ height: '1px', background: 'var(--color-border-subtle)' }} />

                  {/* Metrics Row: Tools & Connections */}
                  <div style={{ display: 'flex', alignItems: 'center', gap: '16px', flexWrap: 'wrap' }}>
                    <div style={{
                      display: 'inline-flex',
                      alignItems: 'baseline',
                      gap: '8px',
                      padding: '6px 14px',
                      borderRadius: '6px',
                      background: 'var(--color-surface-secondary)',
                      border: '1px solid var(--color-border)',
                    }}>
                      <span style={{ fontSize: '18px', fontWeight: '800', color: 'var(--color-text)', lineHeight: '1' }}>
                        {wf.node_count}
                      </span>
                      <span style={{ fontSize: '11px', fontWeight: '700', textTransform: 'uppercase', letterSpacing: '0.08em', color: 'var(--color-text-muted)' }}>
                        Tools
                      </span>
                    </div>

                    <div style={{
                      display: 'inline-flex',
                      alignItems: 'baseline',
                      gap: '8px',
                      padding: '6px 14px',
                      borderRadius: '6px',
                      background: 'var(--color-surface-secondary)',
                      border: '1px solid var(--color-border)',
                    }}>
                      <span style={{ fontSize: '18px', fontWeight: '800', color: 'var(--color-text)', lineHeight: '1' }}>
                        {wf.connection_count}
                      </span>
                      <span style={{ fontSize: '11px', fontWeight: '700', textTransform: 'uppercase', letterSpacing: '0.08em', color: 'var(--color-text-muted)' }}>
                        Connections
                      </span>
                    </div>
                  </div>

                  {/* Side-by-Side Sources & Targets Sections (Showing ALL datasets directly) */}
                  <div style={{
                    display: 'grid',
                    gridTemplateColumns: 'repeat(auto-fit, minmax(340px, 1fr))',
                    gap: '28px',
                    background: 'var(--color-surface-secondary)',
                    padding: '20px',
                    borderRadius: '8px',
                    border: '1px solid var(--color-border-subtle)',
                  }}>
                    {/* Left Column: ALL Sources */}
                    <div>
                      <div style={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: '6px',
                        fontSize: '11px',
                        fontWeight: '700',
                        textTransform: 'uppercase',
                        letterSpacing: '0.1em',
                        color: 'var(--color-text-muted)',
                        marginBottom: '12px',
                      }}>
                        <Database size={13} color="var(--color-text-muted)" />
                        <span>SOURCES</span>
                        <span style={{
                          fontSize: '10px',
                          fontWeight: '700',
                          padding: '1px 6px',
                          borderRadius: '10px',
                          background: 'var(--color-surface)',
                          color: 'var(--color-text-secondary)',
                          border: '1px solid var(--color-border)',
                        }}>
                          {wf.sources?.length || 0}
                        </span>
                      </div>
                      {renderAllDatasetChips(wf.sources, 'None', false)}
                    </div>

                    {/* Right Column: ALL Production Targets */}
                    <div>
                      <div style={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: '6px',
                        fontSize: '11px',
                        fontWeight: '700',
                        textTransform: 'uppercase',
                        letterSpacing: '0.1em',
                        color: 'var(--color-text-muted)',
                        marginBottom: '12px',
                      }}>
                        <Target size={13} color="#22c55e" />
                        <span>PRODUCTION TARGETS</span>
                        <span style={{
                          fontSize: '10px',
                          fontWeight: '700',
                          padding: '1px 6px',
                          borderRadius: '10px',
                          background: 'rgba(34, 197, 94, 0.12)',
                          color: '#22c55e',
                        }}>
                          {wf.targets?.length || 0}
                        </span>
                      </div>
                      {renderAllDatasetChips(wf.targets, 'None', true)}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    );
  }

  // -------------------------------------------------------------------------
  // LEVEL 1: Business Area Portfolio (Executive Landing View)
  // -------------------------------------------------------------------------
  return (
    <div style={{
      maxWidth: '1440px',
      margin: '0 auto',
      display: 'flex',
      flexDirection: 'column',
      gap: '40px',
      position: 'relative',
    }}>
      {/* Executive Hero Header */}
      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'flex-start',
        flexWrap: 'wrap',
        gap: '24px',
        paddingBottom: '8px',
      }}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', maxWidth: '720px' }}>
          <div style={{
            fontSize: '11px',
            fontWeight: '700',
            textTransform: 'uppercase',
            letterSpacing: '0.14em',
            color: 'var(--color-primary)',
          }}>
            ETL PORTFOLIO
          </div>

          <h1 style={{
            fontSize: '34px',
            fontWeight: '800',
            color: 'var(--color-text)',
            letterSpacing: '-0.03em',
            lineHeight: '1.2',
            margin: 0,
          }}>
            {portfolio.portfolio_name || 'ETL Portfolio'}
          </h1>

          <p style={{
            fontSize: '15px',
            color: 'var(--color-text-secondary)',
            lineHeight: '1.5',
            margin: '4px 0 0 0',
          }}>
            Your workflow estate, organised by business domain.
          </p>

          {/* Portfolio Scale Indicator */}
          <div style={{
            display: 'flex',
            alignItems: 'baseline',
            gap: '12px',
            marginTop: '20px',
          }}>
            <div style={{
              fontSize: '48px',
              fontWeight: '800',
              color: 'var(--color-text)',
              letterSpacing: '-0.04em',
              lineHeight: '1',
              fontFeatureSettings: '"tnum"',
            }}>
              {String(metrics.successful_workflows).padStart(2, '0')}
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
              <span style={{
                fontSize: '11px',
                fontWeight: '700',
                textTransform: 'uppercase',
                letterSpacing: '0.12em',
                color: 'var(--color-text-muted)',
              }}>
                WORKFLOWS ANALYSED
              </span>
              <span style={{ fontSize: '12px', color: 'var(--color-text-subtle)' }}>
                Authoritative portfolio baseline
              </span>
            </div>

            {metrics.failed_workflows > 0 && (
              <div style={{
                marginLeft: '16px',
                display: 'inline-flex',
                alignItems: 'center',
                gap: '6px',
                padding: '4px 10px',
                borderRadius: 'var(--radius-sm)',
                background: 'rgba(239, 68, 68, 0.1)',
                border: '1px solid rgba(239, 68, 68, 0.25)',
                color: 'var(--color-error)',
                fontSize: '11px',
                fontWeight: '700',
                letterSpacing: '0.06em',
                textTransform: 'uppercase',
              }}>
                <AlertTriangle size={12} /> {String(metrics.failed_workflows).padStart(2, '0')} FAILED
              </div>
            )}
          </div>
        </div>

        {/* Secondary Utility Action */}
        <button
          onClick={onReset}
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: '8px',
            padding: '8px 14px',
            fontSize: '12px',
            fontWeight: '600',
            borderRadius: 'var(--radius-sm)',
            border: '1px solid var(--color-border)',
            background: 'var(--color-surface)',
            color: 'var(--color-text-secondary)',
            cursor: 'pointer',
            transition: 'all 0.18s ease',
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
          <RefreshCw size={13} /> Upload Different Portfolio
        </button>
      </div>

      {/* Domain Cards Responsive Grid */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))',
        gap: '24px',
      }}>
        {visibleAreas.map((area) => {
          const Icon = area.icon;
          const count = areaCounts[area.name] || 0;
          const isHovered = hoveredDomainCard === area.name;
          const isUnclassified = area.name === 'Other / Unclassified';

          return (
            <div
              key={area.name}
              onClick={() => setCurrentArea(area.name)}
              onMouseEnter={() => setHoveredDomainCard(area.name)}
              onMouseLeave={() => setHoveredDomainCard(null)}
              style={{
                position: 'relative',
                padding: '30px 28px',
                cursor: 'pointer',
                borderRadius: '10px',
                background: isHovered
                  ? 'var(--color-surface-hover)'
                  : 'var(--color-surface)',
                border: isUnclassified
                  ? (isHovered ? '1px dashed #94a3b8' : '1px dashed rgba(148, 163, 184, 0.25)')
                  : (isHovered ? `1px solid ${area.borderColor}` : '1px solid var(--color-border)'),
                boxShadow: isHovered
                  ? `0 14px 28px -10px rgba(0, 0, 0, 0.45)`
                  : '0 2px 6px rgba(0, 0, 0, 0.1)',
                transform: isHovered ? 'translateY(-3px)' : 'none',
                transition: 'all 0.22s cubic-bezier(0.16, 1, 0.3, 1)',
                display: 'flex',
                flexDirection: 'column',
                justifyContent: 'space-between',
                minHeight: '210px',
              }}
            >
              {/* Top Row: Icon + Arrow Indicator */}
              <div>
                <div style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  marginBottom: '20px',
                }}>
                  <div style={{
                    width: '42px',
                    height: '42px',
                    borderRadius: '8px',
                    background: area.subtleBg,
                    border: `1px solid ${area.borderColor}`,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    transition: 'transform 0.2s ease',
                    transform: isHovered ? 'scale(1.05)' : 'scale(1)',
                  }}>
                    <Icon size={20} color={area.color} />
                  </div>

                  <ArrowUpRight
                    size={18}
                    color={isHovered ? area.color : 'var(--color-text-subtle)'}
                    style={{
                      transform: isHovered ? 'translate(2px, -2px)' : 'none',
                      transition: 'all 0.2s ease',
                    }}
                  />
                </div>

                {/* Domain Title */}
                <h3 style={{
                  fontSize: '18px',
                  fontWeight: '700',
                  color: isHovered ? 'var(--color-text)' : 'var(--color-text)',
                  margin: '0 0 6px 0',
                  letterSpacing: '-0.01em',
                }}>
                  {area.name}
                </h3>

                {/* Supporting description */}
                <p style={{
                  fontSize: '12px',
                  color: 'var(--color-text-muted)',
                  lineHeight: '1.45',
                  margin: '0 0 20px 0',
                }}>
                  {area.description}
                </p>
              </div>

              {/* Bottom Row: Scale count + Integrated CTA */}
              <div style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'flex-end',
                paddingTop: '16px',
                borderTop: '1px solid var(--color-border-subtle)',
              }}>
                <div style={{ display: 'flex', alignItems: 'baseline', gap: '6px' }}>
                  <span style={{
                    fontSize: '32px',
                    fontWeight: '800',
                    color: 'var(--color-text)',
                    lineHeight: '1',
                    fontFeatureSettings: '"tnum"',
                  }}>
                    {String(count).padStart(2, '0')}
                  </span>
                  <span style={{
                    fontSize: '11px',
                    fontWeight: '700',
                    color: 'var(--color-text-muted)',
                    textTransform: 'uppercase',
                    letterSpacing: '0.08em',
                  }}>
                    {count === 1 ? 'WORKFLOW' : 'WORKFLOWS'}
                  </span>
                </div>

                <div style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '5px',
                  fontSize: '12px',
                  fontWeight: '700',
                  color: isHovered ? area.color : 'var(--color-text-secondary)',
                  transition: 'color 0.18s ease',
                }}>
                  <span>{isUnclassified ? 'Inspect unclassified' : 'View Portfolio'}</span>
                  <ArrowRight
                    size={13}
                    style={{
                      transform: isHovered ? 'translateX(3px)' : 'none',
                      transition: 'transform 0.18s ease',
                    }}
                  />
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
