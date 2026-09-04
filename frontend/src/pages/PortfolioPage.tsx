import React, { useState, useMemo, useEffect } from 'react';
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
  Calculator,
  Database,
  Target,
  LucideIcon,
  X,
  Info,
  Layers,
  ChevronDown,
  ChevronUp,
} from 'lucide-react';
import { PortfolioOverviewDTO, PortfolioWorkflowSummaryDTO, FactorAssessmentDTO } from '../types/portfolio';
import { AnalysisLoadingScreen } from '../components/AnalysisLoadingScreen';
import { RationalisationPage } from './RationalisationPage';

export type InfoPanel =
  | { type: 'complexity'; workflowId: string }
  | { type: 'criticality'; workflowId: string }
  | null;

interface PortfolioPageProps {
  portfolio: PortfolioOverviewDTO;
  selectedBusinessArea?: string | null;
  onSelectBusinessArea?: (area: string | null) => void;
  selectedToolType?: string | null;
  onSelectToolType?: (toolType: string | null) => void;
  onSelectWorkflow: (workflowId: string, businessArea?: string) => void | Promise<void>;
  onReset: () => void;
  showRationalisation?: boolean;
  setShowRationalisation?: (show: boolean) => void;
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
  {
    name: 'Actuarial',
    icon: Calculator,
    color: '#f43f5e',
    subtleBg: 'rgba(244, 63, 94, 0.08)',
    borderColor: 'rgba(244, 63, 94, 0.25)',
    description: 'Loss reserving, rate indications, capital modeling & experience studies',
  },
];

const OTHER_BUSINESS_AREA: DomainConfig = {
  name: 'Other / Unclassified',
  icon: Layers,
  color: '#94a3b8',
  subtleBg: 'rgba(148, 163, 184, 0.08)',
  borderColor: 'rgba(148, 163, 184, 0.25)',
  description: 'These workflows could not be confidently associated with a recognised business area based on the available workflow output evidence.',
};

const DEFAULT_BUSINESS_AREA_DESCRIPTIONS: Record<string, string> = {
  'Claims & Risk':
    'Claims & Risk business area encompasses multiple workflows that collectively analyse claims performance, exposure, policy information, payments, and litigation or risk-related outcomes.',
  'Sales & Distribution':
    'Sales & Distribution business area encompasses workflows that support customer, product, sales performance, distribution, pipeline, and commercial reporting activities.',
  'Legal':
    'Legal business area encompasses workflows supporting legal operations, case-related information, regulatory analysis, legal reporting, and compliance-oriented data processing.',
  'Underwriting':
    'Underwriting business area encompasses workflows that support risk assessment, policy evaluation, underwriting decisions, pricing inputs, and portfolio analysis.',
  'Actuarial':
    'Actuarial business area encompasses workflows that support actuarial valuation, loss reserving methodologies (e.g. triangulation, IBNR development), capital modeling, experience studies, and rate filing indications.',
  'Other / Unclassified':
    'These workflows could not be confidently associated with a recognised business area based on the available workflow output evidence.',
};

// Color styling for deterministic complexity and criticality levels (HIGH -> Green, MEDIUM -> Yellow, LOW -> Red)
export const getLevelBadgeStyle = (level?: 'HIGH' | 'MEDIUM' | 'LOW') => {
  switch (level) {
    case 'HIGH':
      return {
        color: '#22c55e',
        background: 'rgba(34, 197, 94, 0.1)',
        border: '1px solid rgba(34, 197, 94, 0.3)',
      };
    case 'MEDIUM':
      return {
        color: '#fbbf24',
        background: 'rgba(251, 191, 36, 0.1)',
        border: '1px solid rgba(251, 191, 36, 0.3)',
      };
    case 'LOW':
    default:
      return {
        color: '#ef4444',
        background: 'rgba(239, 68, 68, 0.1)',
        border: '1px solid rgba(239, 68, 68, 0.3)',
      };
  }
};

interface DeterministicInfoPopoverProps {
  type: 'complexity' | 'criticality';
  score?: number;
  level?: 'HIGH' | 'MEDIUM' | 'LOW';
  factors?: string[];
  justification?: string;
  consequence?: string;
  dependencyImpact?: string;
  migrationImplication?: string;
  source?: string;
  factorAssessments?: Record<string, FactorAssessmentDTO>;
  onClose: () => void;
}

interface CriticalityItem {
  key: string;
  name: string;
  category: 'Technical' | 'Operational';
  firstViewDisplay: string;
  value: string | number;
  weight: string;
  score: string;
  contribution: string;
}

const DeterministicInfoPopover: React.FC<DeterministicInfoPopoverProps> = ({
  type,
  score = 0,
  level = 'LOW',
  factors = [],
  justification: _justification,
  consequence: _consequence,
  dependencyImpact: _dependencyImpact,
  migrationImplication: _migrationImplication,
  source: _source,
  factorAssessments,
  onClose,
}) => {
  const isComplexity = type === 'complexity';
  const title = isComplexity ? 'DETERMINISTIC COMPLEXITY' : 'CRITICALITY ASSESSMENT';
  const [showTechnicalAudit, setShowTechnicalAudit] = useState(false);

  const getCriticalityItems = (): CriticalityItem[] => {
    if (factorAssessments && Object.keys(factorAssessments).length > 0) {
      const dOut = factorAssessments.downstream_outputs;
      const uSrc = factorAssessments.upstream_sources;
      const eCon = factorAssessments.etl_consumers;
      const lRun = factorAssessments.last_run;
      const freq = factorAssessments.frequency;

      const outCount = dOut?.raw_value ?? 0;
      const srcCount = uSrc?.raw_value ?? 0;
      const etlCount = eCon?.raw_value ?? 0;

      return [
        {
          key: 'downstream_outputs',
          name: dOut?.name || 'Downstream outputs',
          category: 'Technical',
          firstViewDisplay: dOut?.display_value || `${outCount} downstream output${outCount === 1 ? '' : 's'}`,
          value: outCount,
          weight: `${dOut?.weight_pct ?? 20}%`,
          score: `${Number(dOut?.factor_score ?? 0).toFixed(1)}/100`,
          contribution: `${Number(dOut?.weighted_contribution_pct ?? 0).toFixed(1)}%`,
        },
        {
          key: 'upstream_sources',
          name: uSrc?.name || 'Upstream sources',
          category: 'Technical',
          firstViewDisplay: uSrc?.display_value || `${srcCount} upstream source${srcCount === 1 ? '' : 's'}`,
          value: srcCount,
          weight: `${uSrc?.weight_pct ?? 20}%`,
          score: `${Number(uSrc?.factor_score ?? 0).toFixed(1)}/100`,
          contribution: `${Number(uSrc?.weighted_contribution_pct ?? 0).toFixed(1)}%`,
        },
        {
          key: 'etl_consumers',
          name: eCon?.name || 'ETL workflow consumers',
          category: 'Technical',
          firstViewDisplay: eCon?.display_value || `${etlCount} consuming ETL workflow${etlCount === 1 ? '' : 's'}`,
          value: etlCount,
          weight: `${eCon?.weight_pct ?? 20}%`,
          score: `${Number(eCon?.factor_score ?? 0).toFixed(1)}/100`,
          contribution: `${Number(eCon?.weighted_contribution_pct ?? 0).toFixed(1)}%`,
        },
        {
          key: 'last_run',
          name: lRun?.name || 'Last Run',
          category: 'Operational',
          firstViewDisplay: `Last Run: ${lRun?.display_value || (lRun?.raw_value ? String(lRun.raw_value) : 'Not documented')}`,
          value: lRun?.raw_value ? String(lRun.raw_value) : 'Not documented',
          weight: `${lRun?.weight_pct ?? 20}%`,
          score: `${Number(lRun?.factor_score ?? 0).toFixed(1)}/100`,
          contribution: `${Number(lRun?.weighted_contribution_pct ?? 0).toFixed(1)}%`,
        },
        {
          key: 'frequency',
          name: freq?.name || 'Frequency',
          category: 'Operational',
          firstViewDisplay: `Frequency: ${freq?.display_value || (freq?.raw_value ? String(freq.raw_value) : 'Not documented')}`,
          value: freq?.raw_value ? String(freq.raw_value) : 'Not documented',
          weight: `${freq?.weight_pct ?? 20}%`,
          score: `${Number(freq?.factor_score ?? 0).toFixed(1)}/100`,
          contribution: `${Number(freq?.weighted_contribution_pct ?? 0).toFixed(1)}%`,
        },
      ];
    }

    // Fallback parsing from factors array
    return factors.map((f, idx) => {
      const parts = f.split(' -> ');
      const name = parts[0] || `Factor ${idx + 1}`;
      let val: string | number = '0';
      let scoreStr = '0.0/100';
      let contribStr = '0.0%';
      let fvDisplay = name;

      if (parts.length >= 3) {
        const valPart = parts[1];
        const valMatch = valPart.match(/Value:\s*([^|]+)/i);
        if (valMatch) val = valMatch[1].trim();

        const scorePart = parts[2];
        const scoreMatch = scorePart.match(/Factor Score:\s*([^|]+)/i);
        if (scoreMatch) scoreStr = scoreMatch[1].trim();
        const contribMatch = scorePart.match(/Contribution:\s*([^\s)]+)/i);
        if (contribMatch) contribStr = contribMatch[1].trim();
      }

      if (name.toLowerCase().includes('downstream')) {
        fvDisplay = `${val} downstream output${String(val) === '1' ? '' : 's'}`;
      } else if (name.toLowerCase().includes('upstream')) {
        fvDisplay = `${val} upstream source${String(val) === '1' ? '' : 's'}`;
      } else if (name.toLowerCase().includes('etl') || name.toLowerCase().includes('consumer')) {
        fvDisplay = `${val} consuming ETL workflow${String(val) === '1' ? '' : 's'}`;
      } else {
        fvDisplay = val ? String(val) : 'Not documented';
      }

      const category: 'Technical' | 'Operational' = idx < 3 ? 'Technical' : 'Operational';
      return {
        key: `factor_${idx}`,
        name,
        category,
        firstViewDisplay: fvDisplay,
        value: val,
        weight: '20%',
        score: scoreStr,
        contribution: contribStr,
      };
    });
  };

  const criticalityItems = getCriticalityItems();

  return (
    <div
      role="dialog"
      aria-label={`${title} explanation`}
      onClick={(e) => e.stopPropagation()}
      style={{
        position: 'absolute',
        bottom: 'calc(100% + 12px)',
        left: '50%',
        transform: 'translateX(-50%)',
        width: isComplexity ? '320px' : '400px',
        maxWidth: 'calc(100vw - 48px)',
        background: '#0d1527',
        border: '1px solid var(--color-border)',
        borderRadius: '8px',
        boxShadow: '0 16px 36px -4px rgba(0, 0, 0, 0.75), 0 4px 12px rgba(0, 0, 0, 0.5)',
        padding: '16px 18px',
        zIndex: 100,
        cursor: 'default',
        display: 'flex',
        flexDirection: 'column',
        gap: '12px',
        textAlign: 'left',
      }}
    >
      {/* Downward Anchor Arrow */}
      <div
        style={{
          position: 'absolute',
          bottom: '-6px',
          left: '50%',
          transform: 'translateX(-50%) rotate(45deg)',
          width: '10px',
          height: '10px',
          background: '#0d1527',
          borderRight: '1px solid var(--color-border)',
          borderBottom: '1px solid var(--color-border)',
        }}
      />

      {/* Header Row: Title & Close Button */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span
            style={{
              fontSize: '10.5px',
              fontWeight: '800',
              textTransform: 'uppercase',
              letterSpacing: '0.1em',
              color: 'var(--color-text-subtle)',
            }}
          >
            {title}
          </span>
          {!isComplexity && (
            <span
              style={{
                fontSize: '9.5px',
                fontWeight: '700',
                padding: '2px 6px',
                borderRadius: '3px',
                background: 'rgba(59, 130, 246, 0.15)',
                color: '#60a5fa',
                textTransform: 'uppercase',
                letterSpacing: '0.04em',
              }}
            >
              Deterministic
            </span>
          )}
        </div>
        <button
          type="button"
          aria-label="Close popover"
          onClick={(e) => {
            e.preventDefault();
            e.stopPropagation();
            onClose();
          }}
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            justifyContent: 'center',
            width: '20px',
            height: '20px',
            borderRadius: '4px',
            background: 'transparent',
            border: 'none',
            color: 'var(--color-text-subtle)',
            cursor: 'pointer',
            padding: 0,
            transition: 'all 0.15s ease',
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.color = 'var(--color-text)';
            e.currentTarget.style.background = 'rgba(255, 255, 255, 0.1)';
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.color = 'var(--color-text-subtle)';
            e.currentTarget.style.background = 'transparent';
          }}
        >
          <X size={13} />
        </button>
      </div>

      {/* Score & Level Row */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <span
          style={{
            fontSize: '12px',
            fontWeight: '800',
            letterSpacing: '0.08em',
            padding: '3px 10px',
            borderRadius: '4px',
            ...getLevelBadgeStyle(level),
          }}
        >
          {level}
        </span>
        <span style={{ fontSize: '15px', fontWeight: '800', color: 'var(--color-text)', letterSpacing: '-0.01em' }}>
          {Number(score).toFixed(1)} <span style={{ fontSize: '11px', color: 'var(--color-text-subtle)', fontWeight: '600' }}>/ 100</span>
        </span>
      </div>

      {/* Hairline Divider */}
      <div style={{ height: '1px', background: 'var(--color-border-subtle)' }} />

      {/* Criticality 5-Factor Definition & Contributor View */}
      {!isComplexity && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
          <div
            style={{
              background: 'rgba(255, 255, 255, 0.03)',
              border: '1px solid var(--color-border-subtle)',
              borderRadius: '6px',
              padding: '10px 12px',
              display: 'flex',
              flexDirection: 'column',
              gap: '6px',
            }}
          >
            <div
              style={{
                fontSize: '11px',
                fontWeight: '800',
                color: 'var(--color-text)',
                letterSpacing: '0.04em',
                marginBottom: '2px',
              }}
            >
              Criticality
            </div>

            {/* Technical Factors */}
            <div>
              <div
                style={{
                  fontSize: '11px',
                  fontWeight: '700',
                  color: '#60a5fa',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px',
                }}
              >
                <span>•</span>
                <span>Technical Factors</span>
              </div>
              <ul
                style={{
                  margin: '3px 0 0 14px',
                  padding: 0,
                  listStyle: 'none',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '2px',
                }}
              >
                {criticalityItems
                  .filter((item) => item.category === 'Technical')
                  .map((item) => (
                    <li
                      key={item.key}
                      style={{
                        fontSize: '11px',
                        color: 'var(--color-text-secondary)',
                        display: 'flex',
                        gap: '6px',
                      }}
                    >
                      <span style={{ color: 'var(--color-text-muted)' }}>•</span>
                      <span>{item.firstViewDisplay}</span>
                    </li>
                  ))}
              </ul>
            </div>

            {/* Operational Factors */}
            <div style={{ marginTop: '2px' }}>
              <div
                style={{
                  fontSize: '11px',
                  fontWeight: '700',
                  color: '#f59e0b',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px',
                }}
              >
                <span>•</span>
                <span>Operational Factors</span>
              </div>
              <ul
                style={{
                  margin: '3px 0 0 14px',
                  padding: 0,
                  listStyle: 'none',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '2px',
                }}
              >
                {criticalityItems
                  .filter((item) => item.category === 'Operational')
                  .map((item) => (
                    <li
                      key={item.key}
                      style={{
                        fontSize: '11px',
                        color: 'var(--color-text-secondary)',
                        display: 'flex',
                        gap: '6px',
                      }}
                    >
                      <span style={{ color: 'var(--color-text-muted)' }}>•</span>
                      <span>{item.firstViewDisplay}</span>
                    </li>
                  ))}
              </ul>
            </div>
          </div>
        </div>
      )}

      {/* Factors / Audit Evidence */}
      {isComplexity ? (
        <div>
          <div
            style={{
              fontSize: '11px',
              fontWeight: '700',
              color: 'var(--color-text-muted)',
              textTransform: 'uppercase',
              letterSpacing: '0.06em',
              marginBottom: '8px',
            }}
          >
            Key Contributing Factors
          </div>

          {factors && factors.length > 0 ? (
            <ul
              style={{
                margin: 0,
                padding: 0,
                listStyle: 'none',
                display: 'flex',
                flexDirection: 'column',
                gap: '6px',
              }}
            >
              {factors.map((f, i) => (
                <li
                  key={i}
                  style={{
                    display: 'flex',
                    alignItems: 'flex-start',
                    gap: '7px',
                    fontSize: '12px',
                    lineHeight: '1.45',
                    color: 'var(--color-text-secondary)',
                  }}
                >
                  <span style={{ color: 'var(--color-primary)', fontWeight: '700', lineHeight: '1.4' }}>•</span>
                  <span>{f}</span>
                </li>
              ))}
            </ul>
          ) : (
            <div style={{ fontSize: '12px', color: 'var(--color-text-subtle)', fontStyle: 'italic' }}>
              No specific contributing factors recorded.
            </div>
          )}
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
          <div>
            <button
              type="button"
              onClick={() => setShowTechnicalAudit(!showTechnicalAudit)}
              style={{
                background: 'transparent',
                border: 'none',
                padding: '4px 0',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                width: '100%',
                color: 'var(--color-text-muted)',
                fontSize: '11px',
                fontWeight: '700',
                textTransform: 'uppercase',
                letterSpacing: '0.06em',
                cursor: 'pointer',
              }}
            >
              <span>FACTOR EVIDENCE BREAKDOWN ({criticalityItems.length || 5})</span>
              {showTechnicalAudit ? <ChevronUp size={13} /> : <ChevronDown size={13} />}
            </button>

            {showTechnicalAudit && (
              <ul
                style={{
                  margin: '6px 0 0 0',
                  padding: 0,
                  listStyle: 'none',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '6px',
                }}
              >
                {criticalityItems.map((item) => (
                  <li
                    key={item.key}
                    style={{
                      display: 'flex',
                      flexDirection: 'column',
                      gap: '2px',
                      fontSize: '11.5px',
                      lineHeight: '1.4',
                      color: 'var(--color-text-secondary)',
                      background: 'rgba(255, 255, 255, 0.02)',
                      padding: '6px 8px',
                      borderRadius: '4px',
                      border: '1px solid rgba(255, 255, 255, 0.04)',
                    }}
                  >
                    <div style={{ display: 'flex', alignItems: 'flex-start', gap: '6px', color: 'var(--color-text)', fontWeight: '600' }}>
                      <span style={{ color: 'var(--color-primary)', fontWeight: '700' }}>•</span>
                      <span>{item.name}</span>
                    </div>
                    <div style={{ paddingLeft: '14px', fontSize: '11px', color: 'var(--color-text-secondary)' }}>
                      Value: <span style={{ color: 'var(--color-text)', fontWeight: '600' }}>{item.value}</span> | Weight: <span style={{ color: 'var(--color-text)', fontWeight: '600' }}>{item.weight}</span>
                    </div>
                    <div style={{ paddingLeft: '14px', fontSize: '10.5px', color: 'var(--color-text-muted)', fontWeight: '500' }}>
                      Factor Score: <span style={{ color: 'var(--color-text-secondary)', fontWeight: '600' }}>{item.score}</span> | Contribution: <span style={{ color: 'var(--color-text-secondary)', fontWeight: '600' }}>{item.contribution}</span>
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </div>

          {/* Business Impact Note */}
          <div
            style={{
              fontSize: '10px',
              lineHeight: '1.4',
              color: 'var(--color-text-muted)',
              fontStyle: 'italic',
              marginTop: '4px',
              borderTop: '1px solid var(--color-border-subtle)',
              paddingTop: '6px',
            }}
          >
            * Business impact factors can be added further once the information about downstream targets/consumers is available
          </div>
        </div>
      )}
    </div>
  );
};

export const PortfolioPage: React.FC<PortfolioPageProps> = ({
  portfolio,
  selectedBusinessArea,
  onSelectBusinessArea,
  selectedToolType,
  onSelectToolType,
  onSelectWorkflow,
  onReset,
  showRationalisation: showRationalisationProp,
  setShowRationalisation: setShowRationalisationProp,
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
  const [inspectingWorkflow, setInspectingWorkflow] = useState<PortfolioWorkflowSummaryDTO | null>(null);
  const [inspectError, setInspectError] = useState<string | null>(null);
  const [activeInfoPanel, setActiveInfoPanel] = useState<InfoPanel>(null);
  
  const [localShowRationalisation, setLocalShowRationalisation] = useState<boolean>(false);
  const isRationalisationVisible = showRationalisationProp !== undefined ? showRationalisationProp : localShowRationalisation;
  const setRationalisationVisible = setShowRationalisationProp || setLocalShowRationalisation;

  // Close active info popover on Escape or click outside
  useEffect(() => {
    if (!activeInfoPanel) return;

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        setActiveInfoPanel(null);
      }
    };

    const handleClickOutside = (e: MouseEvent) => {
      const target = e.target as HTMLElement | null;
      if (target && !target.closest('.workflow-info-popover-container')) {
        setActiveInfoPanel(null);
      }
    };

    document.addEventListener('keydown', handleKeyDown);
    document.addEventListener('mousedown', handleClickOutside);
    return () => {
      document.removeEventListener('keydown', handleKeyDown);
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [activeInfoPanel]);

  const handleInspect = async (wf: PortfolioWorkflowSummaryDTO) => {
    if (inspectingWorkflow) return; // Prevent double clicks / concurrent requests
    setInspectingWorkflow(wf);
    setInspectError(null);
    try {
      await onSelectWorkflow(wf.workflow_id, currentArea || undefined);
    } catch (err: any) {
      console.error('Workflow inspection error:', err);
      setInspectError(
        err?.message || `We couldn't complete the analysis for ${wf.filename}. Please try again.`
      );
    }
  };

  const { metrics } = portfolio;

  // Derive business area counts reactively from canonical workflow tags
  const areaCounts: Record<string, number> = useMemo(() => {
    const counts: Record<string, number> = {
      'Claims & Risk': 0,
      'Legal': 0,
      'Underwriting': 0,
      'Sales & Distribution': 0,
      'Actuarial': 0,
      'Other / Unclassified': 0,
    };

    const primaryKeys = new Set(['Claims & Risk', 'Legal', 'Underwriting', 'Sales & Distribution', 'Actuarial']);

    for (const w of portfolio.workflows) {
      if (w.status === 'SUCCESS') {
        if (selectedToolType) {
          const hasTool = (w.tool_types || []).some(
            (t) => t.toLowerCase() === selectedToolType.toLowerCase()
          );
          if (!hasTool) continue;
        }
        const rawTag = w.business_area_tag || w.business_area?.business_area;
        if (rawTag && primaryKeys.has(rawTag)) {
          counts[rawTag]++;
        } else {
          counts['Other / Unclassified']++;
        }
      }
    }

    return counts;
  }, [portfolio.workflows, selectedToolType]);

  // Determine visible business area cards: Exactly the 5 configured business areas, plus Other ONLY if count > 0
  const visibleAreas = useMemo(() => {
    if (areaCounts['Other / Unclassified'] > 0) {
      return [...CONFIGURED_BUSINESS_AREAS, OTHER_BUSINESS_AREA];
    }
    return CONFIGURED_BUSINESS_AREAS;
  }, [areaCounts]);

  // Workflows for currently selected domain (Level 2)
  const currentAreaWorkflows = useMemo(() => {
    if (!currentArea) return [];
    const primaryKeys = new Set(['Claims & Risk', 'Legal', 'Underwriting', 'Sales & Distribution', 'Actuarial']);
    return portfolio.workflows.filter((w) => {
      const rawTag = w.business_area_tag || w.business_area?.business_area;
      if (currentArea === 'Other / Unclassified') {
        return !rawTag || rawTag === 'Other / Unclassified' || !primaryKeys.has(rawTag);
      }
      return rawTag === currentArea;
    });
  }, [portfolio.workflows, currentArea]);

  // Contextual summary strip metrics for Level 2 (Business Area Page)
  const areaMetrics = useMemo(() => {
    const criticality = { HIGH: 0, MEDIUM: 0, LOW: 0 };
    const complexity = { HIGH: 0, MEDIUM: 0, LOW: 0 };
    const uniqueSources = new Set<string>();
    const uniqueTargets = new Set<string>();

    for (const w of currentAreaWorkflows) {
      if (w.status === 'SUCCESS') {
        const crit = w.criticality_level || 'LOW';
        if (crit === 'HIGH') criticality.HIGH++;
        else if (crit === 'MEDIUM') criticality.MEDIUM++;
        else criticality.LOW++;

        const comp = w.complexity_level || 'LOW';
        if (comp === 'HIGH') complexity.HIGH++;
        else if (comp === 'MEDIUM') complexity.MEDIUM++;
        else complexity.LOW++;
      }

      (w.sources || []).forEach((s) => uniqueSources.add(s));
      (w.targets || []).forEach((t) => uniqueTargets.add(t));
    }

    return {
      workflows: currentAreaWorkflows.length,
      criticality,
      complexity,
      sources: uniqueSources.size,
      targets: uniqueTargets.size,
    };
  }, [currentAreaWorkflows]);

  // Filtered workflows for Level 2 Dashboard Summary search & tool filter
  const filteredAreaWorkflows = useMemo(() => {
    let result = currentAreaWorkflows;
    if (selectedToolType) {
      result = result.filter((w) =>
        (w.tool_types || []).some((t) => t.toLowerCase() === selectedToolType.toLowerCase())
      );
    }
    if (!searchQuery) return result;
    const q = searchQuery.toLowerCase();
    return result.filter((w) => (
      w.filename.toLowerCase().includes(q) ||
      w.relative_path.toLowerCase().includes(q) ||
      w.sources.some((s) => s.toLowerCase().includes(q)) ||
      w.targets.some((t) => t.toLowerCase().includes(q)) ||
      (w.business_purpose && w.business_purpose.toLowerCase().includes(q))
    ));
  }, [currentAreaWorkflows, searchQuery, selectedToolType]);

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
  // ETL RATIONALISATION: Whole-Estate Portfolio Intelligence Screen
  // -------------------------------------------------------------------------
  if (isRationalisationVisible) {
    return (
      <>
        {inspectingWorkflow && (
          <AnalysisLoadingScreen
            fileName={inspectingWorkflow.filename}
            isOverlay={true}
            error={inspectError}
            onRetry={() => handleInspect(inspectingWorkflow)}
            onCancel={() => {
              setInspectingWorkflow(null);
              setInspectError(null);
            }}
          />
        )}
        <RationalisationPage
          portfolioId={portfolio.portfolio_id}
          onBackToPortfolio={() => setRationalisationVisible(false)}
          onSelectWorkflow={(wid, area) => {
            const wf = portfolio.workflows.find((w) => w.workflow_id === wid);
            if (wf) {
              handleInspect(wf);
            } else {
              onSelectWorkflow(wid, area);
            }
          }}
          workflows={portfolio.workflows}
        />
      </>
    );
  }

  // -------------------------------------------------------------------------
  // LEVEL 2: Dashboard Summary — Wide Horizontal Workflow Intelligence Cards
  // -------------------------------------------------------------------------
  if (currentArea) {
    const currentAreaDescription =
      portfolio.business_area_descriptions?.[currentArea] ||
      DEFAULT_BUSINESS_AREA_DESCRIPTIONS[currentArea] ||
      `${currentArea} business area encompasses multiple workflows that support analytical operations and data pipelines.`;

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

        {/* Business Area Contextual Header */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
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
            letterSpacing: '-0.02em',
            lineHeight: '1.2',
            margin: '2px 0 0 0',
          }}>
            {currentArea}
          </h1>

          <p style={{
            fontSize: '15px',
            lineHeight: '1.6',
            color: 'var(--color-text-secondary)',
            margin: '4px 0 0 0',
            maxWidth: '960px',
          }}>
            {currentAreaDescription}
          </p>

          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginTop: '6px' }}>
            <span style={{ fontSize: '14px', fontWeight: '600', color: 'var(--color-text-muted)' }}>
              {currentAreaWorkflows.length} {currentAreaWorkflows.length === 1 ? 'Workflow' : 'Workflows'}
            </span>
          </div>
        </div>

        {/* Restrained Contextual Executive Metric Strip for Business Area */}
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
          {/* Workflows */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span style={{ fontSize: '18px', fontWeight: '800', color: 'var(--color-text)' }}>
              {String(areaMetrics.workflows).padStart(2, '0')}
            </span>
            <span style={{ fontSize: '11px', fontWeight: '600', color: 'var(--color-text-muted)', textTransform: 'uppercase', letterSpacing: '0.08em' }}>
              Workflows
            </span>
          </div>

          <div style={{ width: '1px', height: '18px', background: 'var(--color-border)' }} />

          {/* Criticality H/M/L */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span style={{ fontSize: '11px', fontWeight: '700', textTransform: 'uppercase', letterSpacing: '0.08em', color: 'var(--color-text-muted)' }}>
              CRITICALITY
            </span>
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '13px', fontWeight: '700' }}>
              <span style={{ color: '#22c55e' }}>H: {areaMetrics.criticality.HIGH}</span>
              <span style={{ color: 'var(--color-border)' }}>|</span>
              <span style={{ color: '#eab308' }}>M: {areaMetrics.criticality.MEDIUM}</span>
              <span style={{ color: 'var(--color-border)' }}>|</span>
              <span style={{ color: '#ef4444' }}>L: {areaMetrics.criticality.LOW}</span>
            </div>
          </div>

          <div style={{ width: '1px', height: '18px', background: 'var(--color-border)' }} />

          {/* Complexity H/M/L */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span style={{ fontSize: '11px', fontWeight: '700', textTransform: 'uppercase', letterSpacing: '0.08em', color: 'var(--color-text-muted)' }}>
              COMPLEXITY
            </span>
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '13px', fontWeight: '700' }}>
              <span style={{ color: '#22c55e' }}>H: {areaMetrics.complexity.HIGH}</span>
              <span style={{ color: 'var(--color-border)' }}>|</span>
              <span style={{ color: '#eab308' }}>M: {areaMetrics.complexity.MEDIUM}</span>
              <span style={{ color: 'var(--color-border)' }}>|</span>
              <span style={{ color: '#ef4444' }}>L: {areaMetrics.complexity.LOW}</span>
            </div>
          </div>

          <div style={{ width: '1px', height: '18px', background: 'var(--color-border)' }} />

          {/* Production Targets */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span style={{ fontSize: '18px', fontWeight: '800', color: '#22c55e' }}>
              {String(areaMetrics.targets).padStart(2, '0')}
            </span>
            <span style={{ fontSize: '11px', fontWeight: '600', color: 'var(--color-text-muted)', textTransform: 'uppercase', letterSpacing: '0.08em' }}>
              Production Targets
            </span>
          </div>

          <div style={{ width: '1px', height: '18px', background: 'var(--color-border)' }} />

          {/* Sources */}
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

          {selectedToolType && (
            <div style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '6px',
              padding: '6px 12px',
              background: 'rgba(56, 189, 248, 0.1)',
              border: '1px solid rgba(56, 189, 248, 0.25)',
              borderRadius: '6px',
              fontSize: '12px',
              color: '#38bdf8',
              fontWeight: 600,
            }}>
              <span>Tool: {selectedToolType}</span>
              {onSelectToolType && (
                <button
                  onClick={() => onSelectToolType(null)}
                  style={{
                    background: 'none',
                    border: 'none',
                    color: '#38bdf8',
                    cursor: 'pointer',
                    padding: '0',
                    display: 'flex',
                    alignItems: 'center',
                  }}
                  title="Clear tool filter"
                >
                  <X size={13} />
                </button>
              )}
            </div>
          )}

          <span style={{ fontSize: '12px', color: 'var(--color-text-muted)' }}>
            Showing {filteredAreaWorkflows.length} of {currentAreaWorkflows.length} workflows
          </span>
        </div>

        {/* Horizontal Workflow Intelligence Cards (One wide card per row) */}
        {filteredAreaWorkflows.length === 0 ? (
          currentAreaWorkflows.length === 0 ? (
            <div style={{
              padding: '60px 24px',
              textAlign: 'center',
              background: 'var(--color-surface)',
              border: '1px solid var(--color-border)',
              borderRadius: '10px',
            }}>
              <Layers size={36} color="var(--color-text-muted)" style={{ margin: '0 auto 16px' }} />
              <h3 style={{ fontSize: '18px', fontWeight: '700', color: 'var(--color-text)', margin: '0 0 8px 0' }}>
                No workflows in {currentArea}
              </h3>
              <p style={{ fontSize: '13px', color: 'var(--color-text-secondary)', margin: '0 0 20px 0', maxWidth: '500px', marginInline: 'auto' }}>
                This business area currently has 0 workflows assigned in the analysed portfolio.
              </p>
              <button
                onClick={() => setCurrentArea(null)}
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
                ← Return to Business Areas
              </button>
            </div>
          ) : (
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
          )
        ) : (
          <div style={{
            display: 'flex',
            flexDirection: 'column',
            gap: '24px',
          }}>
            {filteredAreaWorkflows.map((wf: PortfolioWorkflowSummaryDTO) => {
              const isSuccess = wf.status === 'SUCCESS';
              const isHovered = hoveredWorkflowId === wf.workflow_id;
              const isComplexityOpen = activeInfoPanel?.type === 'complexity' && activeInfoPanel.workflowId === wf.workflow_id;
              const isCriticalityOpen = activeInfoPanel?.type === 'criticality' && activeInfoPanel.workflowId === wf.workflow_id;
              const isPopoverActive = isComplexityOpen || isCriticalityOpen;

              return (
                <div
                  key={wf.workflow_id}
                  onClick={() => isSuccess && !inspectingWorkflow && handleInspect(wf)}
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
                    cursor: isSuccess && !inspectingWorkflow ? 'pointer' : 'default',
                    display: 'flex',
                    flexDirection: 'column',
                    gap: '20px',
                    zIndex: isPopoverActive ? 30 : (isHovered ? 2 : 1),
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
                        disabled={!!inspectingWorkflow}
                        onClick={(e) => {
                          e.stopPropagation();
                          if (!inspectingWorkflow) {
                            handleInspect(wf);
                          }
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
                          cursor: inspectingWorkflow ? 'not-allowed' : 'pointer',
                          opacity: inspectingWorkflow ? (inspectingWorkflow.workflow_id === wf.workflow_id ? 1 : 0.5) : 1,
                          transition: 'all 0.18s ease',
                          whiteSpace: 'nowrap',
                          alignSelf: 'flex-start',
                        }}
                      >
                        {inspectingWorkflow?.workflow_id === wf.workflow_id ? (
                          <>
                            <RefreshCw size={13} style={{ animation: 'spin 1s linear infinite' }} />
                            <span>Analysing...</span>
                          </>
                        ) : (
                          <>
                            <span>Inspect Workflow</span>
                            <ArrowRight
                              size={14}
                              style={{
                                transform: isHovered ? 'translateX(3px)' : 'none',
                                transition: 'transform 0.18s ease',
                              }}
                            />
                          </>
                        )}
                      </button>
                    )}
                  </div>

                  {/* Hairline Divider */}
                  <div style={{ height: '1px', background: 'var(--color-border-subtle)' }} />

                  {/* Metrics & Deterministic Classification Row */}
                  <div style={{ display: 'flex', alignItems: 'center', gap: '14px', flexWrap: 'wrap' }}>
                    {/* Tools */}
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

                    {/* Connections */}
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

                    <div style={{ width: '1px', height: '22px', background: 'var(--color-border)', margin: '0 4px' }} />

                    {/* Deterministic Workflow Complexity */}
                    <div
                      className="workflow-info-popover-container"
                      onClick={(e) => {
                        e.preventDefault();
                        e.stopPropagation();
                        setActiveInfoPanel((prev) =>
                          prev?.type === 'complexity' && prev.workflowId === wf.workflow_id
                            ? null
                            : { type: 'complexity', workflowId: wf.workflow_id }
                        );
                      }}
                      style={{
                        position: 'relative',
                        display: 'inline-flex',
                        alignItems: 'center',
                        gap: '8px',
                        padding: '6px 12px',
                        borderRadius: '6px',
                        background: isComplexityOpen ? 'rgba(249, 115, 22, 0.12)' : 'var(--color-surface-secondary)',
                        border: isComplexityOpen ? '1px solid var(--color-primary)' : '1px solid var(--color-border)',
                        cursor: 'pointer',
                        transition: 'all 0.15s ease',
                      }}
                    >
                      <span style={{ fontSize: '11px', fontWeight: '700', textTransform: 'uppercase', letterSpacing: '0.08em', color: 'var(--color-text-muted)' }}>
                        Complexity:
                      </span>
                      <span style={{
                        fontSize: '11px',
                        fontWeight: '800',
                        letterSpacing: '0.06em',
                        padding: '2px 8px',
                        borderRadius: '4px',
                        ...getLevelBadgeStyle(wf.complexity_level || 'LOW'),
                      }}>
                        {wf.complexity_level || 'LOW'}
                      </span>

                      <button
                        type="button"
                        aria-haspopup="dialog"
                        aria-expanded={isComplexityOpen}
                        aria-label="View deterministic complexity explanation"
                        onClick={(e) => {
                          e.preventDefault();
                          e.stopPropagation();
                          setActiveInfoPanel((prev) =>
                            prev?.type === 'complexity' && prev.workflowId === wf.workflow_id
                              ? null
                              : { type: 'complexity', workflowId: wf.workflow_id }
                          );
                        }}
                        onKeyDown={(e) => {
                          if (e.key === 'Enter' || e.key === ' ') {
                            e.preventDefault();
                            e.stopPropagation();
                            setActiveInfoPanel((prev) =>
                              prev?.type === 'complexity' && prev.workflowId === wf.workflow_id
                                ? null
                                : { type: 'complexity', workflowId: wf.workflow_id }
                            );
                          }
                        }}
                        style={{
                          display: 'inline-flex',
                          alignItems: 'center',
                          justifyContent: 'center',
                          width: '20px',
                          height: '20px',
                          borderRadius: '50%',
                          background: isComplexityOpen ? 'rgba(249, 115, 22, 0.25)' : 'transparent',
                          border: 'none',
                          color: isComplexityOpen ? 'var(--color-primary)' : 'var(--color-text-subtle)',
                          cursor: 'pointer',
                          padding: 0,
                          transition: 'all 0.15s ease',
                        }}
                        onMouseEnter={(e) => {
                          if (!isComplexityOpen) {
                            e.currentTarget.style.color = 'var(--color-text)';
                            e.currentTarget.style.background = 'rgba(255, 255, 255, 0.08)';
                          }
                        }}
                        onMouseLeave={(e) => {
                          if (!isComplexityOpen) {
                            e.currentTarget.style.color = 'var(--color-text-subtle)';
                            e.currentTarget.style.background = 'transparent';
                          }
                        }}
                      >
                        <Info size={13} />
                      </button>

                      {/* Controlled Popover Dialog */}
                      {isComplexityOpen && (
                        <DeterministicInfoPopover
                          type="complexity"
                          score={wf.complexity_score ?? 0}
                          level={wf.complexity_level || 'LOW'}
                          factors={wf.complexity_factors || []}
                          onClose={() => setActiveInfoPanel(null)}
                        />
                      )}
                    </div>

                    {/* Deterministic Workflow Criticality */}
                    <div
                      className="workflow-info-popover-container"
                      onClick={(e) => {
                        e.preventDefault();
                        e.stopPropagation();
                        setActiveInfoPanel((prev) =>
                          prev?.type === 'criticality' && prev.workflowId === wf.workflow_id
                            ? null
                            : { type: 'criticality', workflowId: wf.workflow_id }
                        );
                      }}
                      style={{
                        position: 'relative',
                        display: 'inline-flex',
                        alignItems: 'center',
                        gap: '8px',
                        padding: '6px 12px',
                        borderRadius: '6px',
                        background: isCriticalityOpen ? 'rgba(249, 115, 22, 0.12)' : 'var(--color-surface-secondary)',
                        border: isCriticalityOpen ? '1px solid var(--color-primary)' : '1px solid var(--color-border)',
                        cursor: 'pointer',
                        transition: 'all 0.15s ease',
                      }}
                    >
                      <span style={{ fontSize: '11px', fontWeight: '700', textTransform: 'uppercase', letterSpacing: '0.08em', color: 'var(--color-text-muted)' }}>
                        Criticality:
                      </span>
                      <span style={{
                        fontSize: '11px',
                        fontWeight: '800',
                        letterSpacing: '0.06em',
                        padding: '2px 8px',
                        borderRadius: '4px',
                        ...getLevelBadgeStyle(wf.criticality_level || 'LOW'),
                      }}>
                        {wf.criticality_level || 'LOW'}
                      </span>

                      <button
                        type="button"
                        aria-haspopup="dialog"
                        aria-expanded={isCriticalityOpen}
                        aria-label="View deterministic criticality explanation"
                        onClick={(e) => {
                          e.preventDefault();
                          e.stopPropagation();
                          setActiveInfoPanel((prev) =>
                            prev?.type === 'criticality' && prev.workflowId === wf.workflow_id
                              ? null
                              : { type: 'criticality', workflowId: wf.workflow_id }
                          );
                        }}
                        onKeyDown={(e) => {
                          if (e.key === 'Enter' || e.key === ' ') {
                            e.preventDefault();
                            e.stopPropagation();
                            setActiveInfoPanel((prev) =>
                              prev?.type === 'criticality' && prev.workflowId === wf.workflow_id
                                ? null
                                : { type: 'criticality', workflowId: wf.workflow_id }
                            );
                          }
                        }}
                        style={{
                          display: 'inline-flex',
                          alignItems: 'center',
                          justifyContent: 'center',
                          width: '20px',
                          height: '20px',
                          borderRadius: '50%',
                          background: isCriticalityOpen ? 'rgba(249, 115, 22, 0.25)' : 'transparent',
                          border: 'none',
                          color: isCriticalityOpen ? 'var(--color-primary)' : 'var(--color-text-subtle)',
                          cursor: 'pointer',
                          padding: 0,
                          transition: 'all 0.15s ease',
                        }}
                        onMouseEnter={(e) => {
                          if (!isCriticalityOpen) {
                            e.currentTarget.style.color = 'var(--color-text)';
                            e.currentTarget.style.background = 'rgba(255, 255, 255, 0.08)';
                          }
                        }}
                        onMouseLeave={(e) => {
                          if (!isCriticalityOpen) {
                            e.currentTarget.style.color = 'var(--color-text-subtle)';
                            e.currentTarget.style.background = 'transparent';
                          }
                        }}
                      >
                        <Info size={13} />
                      </button>

                      {/* Controlled Popover Dialog */}
                      {isCriticalityOpen && (
                        <DeterministicInfoPopover
                          type="criticality"
                          score={wf.criticality_score ?? 0}
                          level={wf.criticality_level || 'LOW'}
                          factors={wf.criticality_factors || []}
                          justification={wf.criticality_justification}
                          consequence={wf.business_consequence}
                          dependencyImpact={wf.dependency_impact}
                          migrationImplication={wf.migration_implication}
                          source={wf.criticality_source}
                          factorAssessments={wf.factor_assessments}
                          onClose={() => setActiveInfoPanel(null)}
                        />
                      )}
                    </div>

                    {/* Operational Factor: Last Run */}
                    <div
                      style={{
                        position: 'relative',
                        display: 'inline-flex',
                        alignItems: 'center',
                        gap: '6px',
                        padding: '6px 12px',
                        borderRadius: '6px',
                        background: 'var(--color-surface-secondary)',
                        border: '1px solid var(--color-border)',
                      }}
                    >
                      <span style={{ fontSize: '11px', fontWeight: '700', textTransform: 'uppercase', letterSpacing: '0.08em', color: 'var(--color-text-muted)' }}>
                        Last Run:
                      </span>
                      <span style={{ fontSize: '12px', fontWeight: '600', color: 'var(--color-text)' }}>
                        {wf.last_run || wf.factor_assessments?.last_run?.display_value || (wf.factor_assessments?.last_run?.raw_value ? String(wf.factor_assessments.last_run.raw_value) : 'Not documented')}
                      </span>
                    </div>

                    {/* Operational Factor: Frequency */}
                    <div
                      style={{
                        position: 'relative',
                        display: 'inline-flex',
                        alignItems: 'center',
                        gap: '6px',
                        padding: '6px 12px',
                        borderRadius: '6px',
                        background: 'var(--color-surface-secondary)',
                        border: '1px solid var(--color-border)',
                      }}
                    >
                      <span style={{ fontSize: '11px', fontWeight: '700', textTransform: 'uppercase', letterSpacing: '0.08em', color: 'var(--color-text-muted)' }}>
                        Frequency:
                      </span>
                      <span style={{ fontSize: '12px', fontWeight: '600', color: 'var(--color-text)' }}>
                        {wf.frequency || wf.factor_assessments?.frequency?.display_value || (wf.factor_assessments?.frequency?.raw_value ? String(wf.factor_assessments.frequency.raw_value) : 'Not documented')}
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

        {/* Workflow Inspection Loading / Error Modal */}
        {inspectingWorkflow && (
          <AnalysisLoadingScreen
            fileName={inspectingWorkflow.filename}
            isOverlay={true}
            error={inspectError}
            onRetry={() => handleInspect(inspectingWorkflow)}
            onCancel={() => {
              setInspectingWorkflow(null);
              setInspectError(null);
            }}
          />
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

          {/* Portfolio Scale Indicators */}
          <div style={{
            display: 'flex',
            alignItems: 'center',
            gap: '16px',
            marginTop: '20px',
            flexWrap: 'wrap',
          }}>
            {/* Workflows Analysed Metric */}
            <div style={{ display: 'flex', alignItems: 'baseline', gap: '12px' }}>
              <div style={{
                fontSize: '44px',
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
            </div>

            {metrics.failed_workflows > 0 && (
              <div style={{
                marginLeft: '8px',
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
      </div>

      {/* Tool Filter Active Banner (Level 1) */}
      {selectedToolType && (
        <div style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '12px 18px',
          background: 'rgba(56, 189, 248, 0.08)',
          border: '1px solid rgba(56, 189, 248, 0.25)',
          borderRadius: '10px',
          marginBottom: '24px',
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <span style={{ fontSize: '13px', color: 'var(--color-text-secondary)' }}>
              Filtered by tool usage:
            </span>
            <span style={{
              fontSize: '12px',
              fontWeight: 700,
              color: '#38bdf8',
              background: 'rgba(56, 189, 248, 0.15)',
              padding: '3px 10px',
              borderRadius: '6px',
            }}>
              {selectedToolType}
            </span>
          </div>
          {onSelectToolType && (
            <button
              onClick={() => onSelectToolType(null)}
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '6px',
                padding: '5px 12px',
                background: 'var(--color-surface)',
                border: '1px solid var(--color-border)',
                borderRadius: '6px',
                fontSize: '12px',
                fontWeight: 600,
                color: 'var(--color-text)',
                cursor: 'pointer',
              }}
            >
              <X size={13} /> Clear Tool Filter
            </button>
          )}
        </div>
      )}

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
