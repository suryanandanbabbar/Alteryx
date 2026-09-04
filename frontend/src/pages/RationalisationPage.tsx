import React, { useState, useEffect, useMemo } from 'react';
import {
  ArrowLeft,
  ArrowRight,
  Search,
  ShieldCheck,
  Layers,
  Trash2,
  GitMerge,
  AlertTriangle,
  ExternalLink,
  X,
  RefreshCw,
  Cpu,
  Database,
  Target,
  Check,
  Sparkles,
  Copy,
  Clock,
} from 'lucide-react';
import {
  RationalisationAnalysisDTO,
  RationalisationCandidateDTO,
  PortfolioWorkflowSummaryDTO,
} from '../types/portfolio';
import { apiClient } from '../api/client';
import { getLevelBadgeStyle } from './PortfolioPage';

export function isMeaningfulEvidence(item: string | null | undefined): boolean {
  if (!item || typeof item !== 'string') return false;
  const clean = item.trim();
  if (!clean || clean === '=' || clean === ':' || clean === '=:' || clean === ':=') return false;

  const lower = clean.toLowerCase();
  const disallowed = [
    '=',
    ':',
    '=:',
    ':=',
    'join on =',
    'join on :',
    'join on:',
    'join on',
    'shared join key: =',
    'shared join key:',
    'shared join key',
    'formula: =',
    'formula:',
    'filter: =',
    'filter:',
    'summarize: =',
    'summarize:',
    'summarize aggregations',
    'aggregation: =',
    'aggregation:',
    'target: =',
    'target:',
    'join operation',
    'filter operation',
    'summarize operation',
    'formula calculation',
    'multirowformula calculation',
  ];

  if (disallowed.includes(lower)) {
    return false;
  }

  const prefixes = [
    'shared join key:',
    'shared join key',
    'join on:',
    'join on',
    'formula:',
    'formula',
    'filter:',
    'filter',
    'shared filter predicate:',
    'summarize:',
    'summarize aggregations',
    'aggregation:',
    'target:',
  ];

  for (const prefix of prefixes) {
    if (lower.startsWith(prefix)) {
      const val = clean.slice(prefix.length).trim();
      if (!val || val === '=' || val === ':' || val.replace(/[=:]/g, '').trim() === '') {
        return false;
      }
      if (['operation', 'calculation', 'aggregations'].includes(val.toLowerCase())) {
        return false;
      }
    }
  }

  return true;
}

const EvidenceItemRow: React.FC<{ item: string; icon?: React.ReactNode }> = ({ item, icon }) => {
  const [expanded, setExpanded] = useState(false);
  const [copied, setCopied] = useState(false);

  const prefixMatch = item.match(/^(Formula|Filter|Join on|Shared join key|Summarize|Shared filter predicate):\s*(.*)$/i);
  const prefix = prefixMatch ? prefixMatch[1] : '';
  const expr = prefixMatch ? prefixMatch[2] : item;

  const isLong = expr.length > 100;
  const displayExpr = isLong && !expanded ? `${expr.slice(0, 95)}...` : expr;

  const handleCopy = (e: React.MouseEvent) => {
    e.stopPropagation();
    navigator.clipboard.writeText(expr);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        gap: '4px',
        fontSize: '12.5px',
        color: 'var(--color-text)',
        padding: '6px 10px',
        background: 'var(--color-surface)',
        borderRadius: '6px',
        border: '1px solid var(--color-border-subtle)',
        overflowWrap: 'anywhere',
        wordBreak: 'break-word',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: '8px' }}>
        <div style={{ display: 'flex', alignItems: 'flex-start', gap: '8px', flex: 1, minWidth: 0 }}>
          {icon && <span style={{ flexShrink: 0, marginTop: '2px' }}>{icon}</span>}
          <div style={{ flex: 1, minWidth: 0 }}>
            {prefix && (
              <span
                style={{
                  fontWeight: '700',
                  fontSize: '11px',
                  textTransform: 'uppercase',
                  letterSpacing: '0.04em',
                  color: 'var(--color-text-secondary)',
                  marginRight: '6px',
                  display: 'inline-block',
                }}
              >
                {prefix}:
              </span>
            )}
            <span
              style={{
                fontFamily:
                  prefix.toLowerCase().includes('formula') ||
                  prefix.toLowerCase().includes('filter') ||
                  prefix.toLowerCase().includes('join')
                    ? 'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace'
                    : 'inherit',
                fontSize: prefix.toLowerCase().includes('formula') ? '12px' : '12.5px',
                lineHeight: '1.5',
                color: prefix.toLowerCase().includes('formula') ? 'var(--color-primary)' : 'var(--color-text)',
              }}
            >
              {displayExpr}
            </span>
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '4px', flexShrink: 0 }}>
          {isLong && (
            <button
              onClick={() => setExpanded((prev) => !prev)}
              style={{
                background: 'none',
                border: 'none',
                cursor: 'pointer',
                fontSize: '11px',
                fontWeight: '600',
                color: 'var(--color-primary)',
                padding: '2px 6px',
                borderRadius: '4px',
                display: 'inline-flex',
                alignItems: 'center',
                gap: '2px',
              }}
              title={expanded ? 'Show less' : 'Show full expression'}
            >
              {expanded ? 'Collapse' : 'Expand'}
            </button>
          )}
          <button
            onClick={handleCopy}
            style={{
              background: 'none',
              border: 'none',
              cursor: 'pointer',
              color: copied ? '#34d399' : 'var(--color-text-muted)',
              padding: '2px 4px',
              borderRadius: '4px',
              display: 'inline-flex',
              alignItems: 'center',
            }}
            title="Copy full expression"
          >
            {copied ? <Check size={13} /> : <Copy size={13} />}
          </button>
        </div>
      </div>
    </div>
  );
};

const UniqueWorkflowList: React.FC<{ wfName: string; items: string[] }> = ({ wfName, items }) => {
  const [showAll, setShowAll] = useState(false);
  const INITIAL_LIMIT = 6;
  const hasMore = items.length > INITIAL_LIMIT;
  const displayed = showAll ? items : items.slice(0, INITIAL_LIMIT);

  return (
    <div
      style={{
        padding: '12px 16px',
        borderRadius: '8px',
        background: 'var(--color-surface-secondary)',
        border: '1px solid var(--color-border-subtle)',
      }}
    >
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          marginBottom: '8px',
        }}
      >
        <div
          style={{
            fontSize: '12.5px',
            fontWeight: '700',
            color: 'var(--color-primary)',
          }}
        >
          {wfName} Unique Operations ({items.length}):
        </div>
        {hasMore && (
          <button
            onClick={() => setShowAll((prev) => !prev)}
            style={{
              background: 'none',
              border: 'none',
              cursor: 'pointer',
              fontSize: '11.5px',
              fontWeight: '600',
              color: 'var(--color-primary)',
              display: 'inline-flex',
              alignItems: 'center',
              gap: '4px',
            }}
          >
            {showAll ? 'Show fewer' : `+ Show ${items.length - INITIAL_LIMIT} more`}
          </button>
        )}
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
        {displayed.map((it, i) => (
          <EvidenceItemRow key={i} item={it} />
        ))}
      </div>
    </div>
  );
};

interface RationalisationPageProps {
  portfolioId: string;
  onBackToPortfolio: () => void;
  onSelectWorkflow: (workflowId: string, businessArea?: string) => void | Promise<void>;
  workflows: PortfolioWorkflowSummaryDTO[];
}

export const RationalisationPage: React.FC<RationalisationPageProps> = ({
  portfolioId,
  onBackToPortfolio,
  onSelectWorkflow,
  workflows,
}) => {
  const [analysis, setAnalysis] = useState<RationalisationAnalysisDTO | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<string>('ALL');
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [selectedCandidate, setSelectedCandidate] = useState<RationalisationCandidateDTO | null>(null);
  const [activeEvidenceMetric, setActiveEvidenceMetric] = useState<'source' | 'target' | 'frequency' | 'logic' | 'dag'>('source');
  const [loadingStage, setLoadingStage] = useState<number>(0);

  const LOADING_STAGES = [
    'Reading canonical workflow fingerprints...',
    'Evaluating source and production target overlap...',
    'Comparing transformation logic & output schemas...',
    'Evaluating DAG topology and data grain...',
    'Applying safety gates & compiling recommendations...',
  ];

  // Rotate loading stage smoothly while fetching
  useEffect(() => {
    if (!loading) return;
    const interval = setInterval(() => {
      setLoadingStage((prev) => (prev < LOADING_STAGES.length - 1 ? prev + 1 : prev));
    }, 1800);
    return () => clearInterval(interval);
  }, [loading]);

  const fetchRationalisation = async () => {
    setLoading(true);
    setError(null);
    setLoadingStage(0);
    try {
      const data = await apiClient.getPortfolioRationalisation(portfolioId, true);
      setAnalysis(data);
    } catch (err: any) {
      console.error('Failed to load rationalisation analysis:', err);
      setError(
        err?.message ||
          'Unable to load ETL rationalisation analysis. Please ensure the portfolio analysis is complete.'
      );
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchRationalisation();
  }, [portfolioId]);

  // Map workflow ID to summary object for direct navigation & metadata
  const workflowMap = useMemo(() => {
    const map = new Map<string, PortfolioWorkflowSummaryDTO>();
    workflows.forEach((w) => map.set(w.workflow_id, w));
    return map;
  }, [workflows]);

  // Filter candidates based on tab and search
  const filteredCandidates = useMemo(() => {
    if (!analysis) return [];
    return analysis.candidates.filter((c) => {
      // Tab filter
      if (activeTab === 'CONSOLIDATE') {
        if (c.recommendation_type !== 'CONSOLIDATE' || c.consolidation_decision?.recommendation !== 'MERGE') {
          return false;
        }
      } else if (activeTab !== 'ALL' && c.recommendation_type !== activeTab) {
        return false;
      }

      // Search filter
      if (searchQuery.trim()) {
        const q = searchQuery.toLowerCase();
        const matchesName = c.workflow_names.some((n) => n.toLowerCase().includes(q));
        const matchesReason = c.reasoning.toLowerCase().includes(q);
        const matchesRec = c.recommendation_type.toLowerCase().includes(q);
        const matchesStrategy = c.proposed_strategy.toLowerCase().includes(q);
        const matchesEvidence = c.evidence.some((e) => e.toLowerCase().includes(q));
        const matchesSharedLogic = c.shared_logic.some((l) => l.toLowerCase().includes(q));
        const matchesSources = c.dependency_evidence.shared_sources.some((s) => s.toLowerCase().includes(q));
        const matchesTargets = c.dependency_evidence.shared_targets.some((t) => t.toLowerCase().includes(q));

        if (
          !matchesName &&
          !matchesReason &&
          !matchesRec &&
          !matchesStrategy &&
          !matchesEvidence &&
          !matchesSharedLogic &&
          !matchesSources &&
          !matchesTargets
        ) {
          return false;
        }
      }
      return true;
    });
  }, [analysis, activeTab, searchQuery]);

  const counts = useMemo(() => {
    if (!analysis?.candidates) {
      return { CONSOLIDATE: 0, RETIRE_CANDIDATE: 0, SHARED_LOGIC: 0, REVIEW: 0 };
    }
    return {
      CONSOLIDATE: analysis.candidates.filter((c) => c.recommendation_type === 'CONSOLIDATE' && c.consolidation_decision?.recommendation === 'MERGE').length,
      RETIRE_CANDIDATE: analysis.candidates.filter((c) => c.recommendation_type === 'RETIRE_CANDIDATE').length,
      SHARED_LOGIC: analysis.candidates.filter((c) => c.recommendation_type === 'SHARED_LOGIC').length,
      REVIEW: analysis.candidates.filter((c) => c.recommendation_type === 'REVIEW').length,
    };
  }, [analysis]);

  const totalOpportunities = analysis?.total_opportunities || 0;

  // Recommendation Badge Config
  const getRecommendationBadge = (type: string) => {
    switch (type) {
      case 'CONSOLIDATE':
        return {
          label: 'Consolidate',
          icon: GitMerge,
          color: '#34d399',
          bg: 'rgba(16, 185, 129, 0.12)',
          border: '1px solid rgba(16, 185, 129, 0.35)',
        };
      case 'RETIRE_CANDIDATE':
        return {
          label: 'Retire Candidate',
          icon: Trash2,
          color: '#fbbf24',
          bg: 'rgba(245, 158, 11, 0.12)',
          border: '1px solid rgba(245, 158, 11, 0.35)',
        };
      case 'SHARED_LOGIC':
        return {
          label: 'Shared Logic',
          icon: Layers,
          color: '#38bdf8',
          bg: 'rgba(56, 189, 248, 0.12)',
          border: '1px solid rgba(56, 189, 248, 0.35)',
        };
      case 'REVIEW':
      default:
        return {
          label: 'Review Needed',
          icon: AlertTriangle,
          color: '#c084fc',
          bg: 'rgba(192, 132, 252, 0.12)',
          border: '1px solid rgba(192, 132, 252, 0.35)',
        };
    }
  };

  const getConfidenceBadge = (confidence: string) => {
    switch (confidence) {
      case 'HIGH':
        return {
          label: 'HIGH CONFIDENCE',
          color: '#34d399',
          bg: 'rgba(16, 185, 129, 0.1)',
          border: '1px solid rgba(16, 185, 129, 0.25)',
        };
      case 'MEDIUM':
        return {
          label: 'MEDIUM CONFIDENCE',
          color: '#fbbf24',
          bg: 'rgba(245, 158, 11, 0.1)',
          border: '1px solid rgba(245, 158, 11, 0.25)',
        };
      case 'LOW':
      default:
        return {
          label: 'LOW CONFIDENCE',
          color: '#94a3b8',
          bg: 'rgba(148, 163, 184, 0.1)',
          border: '1px solid rgba(148, 163, 184, 0.25)',
        };
    }
  };

  const handleInspectClick = (wid: string) => {
    const summary = workflowMap.get(wid);
    onSelectWorkflow(wid, summary?.business_area?.business_area);
  };

  return (
    <div
      style={{
        maxWidth: '1440px',
        margin: '0 auto',
        padding: '0 24px 64px 24px',
        display: 'flex',
        flexDirection: 'column',
        gap: '28px',
        fontFamily: 'var(--font-sans)',
        color: 'var(--color-text)',
      }}
    >
      {/* 1. Top Navigation Strip */}
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          flexWrap: 'wrap',
          gap: '16px',
        }}
      >
        <button
          onClick={onBackToPortfolio}
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

        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <span
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '6px',
              padding: '4px 10px',
              borderRadius: '20px',
              fontSize: '11px',
              fontWeight: '700',
              background: 'rgba(56, 189, 248, 0.1)',
              color: '#38bdf8',
              border: '1px solid rgba(56, 189, 248, 0.25)',
              letterSpacing: '0.04em',
            }}
          >
            <Sparkles size={12} />
            Deterministic Evidence + AI Qualified
          </span>
        </div>
      </div>

      {/* 2. Executive Page Header */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
        <div
          style={{
            fontSize: '11px',
            fontWeight: '800',
            textTransform: 'uppercase',
            letterSpacing: '0.14em',
            color: 'var(--color-primary)',
          }}
        >
          RATIONALISATION RECOMMENDATION
        </div>

        <h1
          style={{
            fontSize: '34px',
            fontWeight: '800',
            color: 'var(--color-text)',
            letterSpacing: '-0.02em',
            lineHeight: '1.2',
            margin: '2px 0 0 0',
          }}
        >
          ETL Rationalisation
        </h1>

        <p
          style={{
            fontSize: '15px',
            lineHeight: '1.6',
            color: 'var(--color-text-secondary)',
            margin: '4px 0 0 0',
            maxWidth: '960px',
          }}
        >
          Identify opportunities to consolidate, simplify and retire redundant workflows across the ETL
          estate using deterministic workflow evidence and AI-qualified analysis.
        </p>

        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginTop: '6px' }}>
          <span style={{ fontSize: '13.5px', fontWeight: '600', color: 'var(--color-text-muted)' }}>
            {analysis?.analysed_workflow_count ?? workflows.length}{' '}
            {(analysis?.analysed_workflow_count ?? workflows.length) === 1
              ? 'Workflow Analysed'
              : 'Workflows Analysed'}
          </span>
        </div>
      </div>

      {/* 3. Loading State */}
      {loading && (
        <div
          style={{
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            padding: '64px 24px',
            borderRadius: '12px',
            background: 'var(--color-surface)',
            border: '1px solid var(--color-border)',
            gap: '20px',
            textAlign: 'center',
          }}
        >
          <div
            style={{
              width: '48px',
              height: '48px',
              borderRadius: '50%',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              background: 'rgba(251, 78, 11, 0.1)',
              color: 'var(--color-primary)',
              border: '1px solid rgba(251, 78, 11, 0.3)',
            }}
          >
            <RefreshCw
              size={24}
              style={{
                animation: 'spin 1.4s linear infinite',
              }}
            />
          </div>
          <style>{`
            @keyframes spin {
              from { transform: rotate(0deg); }
              to { transform: rotate(360deg); }
            }
          `}</style>

          <div>
            <h3
              style={{
                fontSize: '18px',
                fontWeight: '700',
                color: 'var(--color-text)',
                margin: '0 0 6px 0',
              }}
            >
              Analysing ETL Estate Rationalisation...
            </h3>
            <p
              style={{
                fontSize: '14px',
                color: 'var(--color-text-secondary)',
                margin: 0,
                maxWidth: '540px',
                lineHeight: '1.5',
              }}
            >
              {LOADING_STAGES[loadingStage]}
            </p>
          </div>

          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              marginTop: '8px',
            }}
          >
            {LOADING_STAGES.map((_, i) => (
              <div
                key={i}
                style={{
                  width: i === loadingStage ? '24px' : '8px',
                  height: '6px',
                  borderRadius: '3px',
                  background:
                    i === loadingStage
                      ? 'var(--color-primary)'
                      : i < loadingStage
                      ? 'rgba(251, 78, 11, 0.4)'
                      : 'var(--color-border)',
                  transition: 'all 0.3s ease',
                }}
              />
            ))}
          </div>
        </div>
      )}

      {/* 4. Error State */}
      {error && !loading && (
        <div
          style={{
            padding: '32px',
            borderRadius: '12px',
            background: 'var(--color-surface)',
            border: '1px solid rgba(239, 68, 68, 0.4)',
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            textAlign: 'center',
            gap: '16px',
          }}
        >
          <div
            style={{
              width: '48px',
              height: '48px',
              borderRadius: '50%',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              background: 'rgba(239, 68, 68, 0.1)',
              color: '#ef4444',
              border: '1px solid rgba(239, 68, 68, 0.3)',
            }}
          >
            <AlertTriangle size={24} />
          </div>
          <div>
            <h3 style={{ fontSize: '18px', fontWeight: '700', color: 'var(--color-text)', margin: '0 0 6px 0' }}>
              Unable to load ETL rationalisation analysis
            </h3>
            <p style={{ fontSize: '14px', color: 'var(--color-text-secondary)', margin: 0, maxWidth: '500px' }}>
              {error}
            </p>
          </div>
          <button
            onClick={fetchRationalisation}
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '8px',
              padding: '9px 18px',
              borderRadius: 'var(--radius-sm)',
              background: 'var(--color-primary)',
              color: '#ffffff',
              fontSize: '13px',
              fontWeight: '700',
              border: 'none',
              cursor: 'pointer',
              boxShadow: '0 2px 8px rgba(251, 78, 11, 0.3)',
            }}
          >
            <RefreshCw size={14} /> Retry Analysis
          </button>
        </div>
      )}

      {/* 5. Loaded Rationalisation Dashboard */}
      {!loading && !error && analysis && (
        <>
          {/* Executive Summary Metric Strip */}
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '24px',
              padding: '16px 24px',
              borderRadius: 'var(--radius-md)',
              background: 'var(--color-surface)',
              border: '1px solid var(--color-border)',
              flexWrap: 'wrap',
            }}
          >
            {/* Estate Workflows */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '2px', minWidth: '130px' }}>
              <span
                style={{
                  fontSize: '10.5px',
                  fontWeight: '700',
                  color: 'var(--color-text-muted)',
                  textTransform: 'uppercase',
                  letterSpacing: '0.08em',
                }}
              >
                ESTATE WORKFLOWS
              </span>
              <span
                style={{
                  fontSize: '22px',
                  fontWeight: '800',
                  color: 'var(--color-text)',
                  fontVariantNumeric: 'tabular-nums',
                }}
              >
                {String(analysis.analysed_workflow_count).padStart(2, '0')}
              </span>
            </div>

            <div style={{ width: '1px', height: '36px', background: 'var(--color-border)' }} />

            {/* Total Opportunities */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '2px', minWidth: '140px' }}>
              <span
                style={{
                  fontSize: '10.5px',
                  fontWeight: '700',
                  color: 'var(--color-text-muted)',
                  textTransform: 'uppercase',
                  letterSpacing: '0.08em',
                }}
              >
                TOTAL OPPORTUNITIES
              </span>
              <span
                style={{
                  fontSize: '22px',
                  fontWeight: '800',
                  color: totalOpportunities > 0 ? 'var(--color-primary)' : 'var(--color-text)',
                  fontVariantNumeric: 'tabular-nums',
                }}
              >
                {String(totalOpportunities).padStart(2, '0')}
              </span>
            </div>

            <div style={{ width: '1px', height: '36px', background: 'var(--color-border)' }} />

            {/* Consolidate */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '2px', minWidth: '120px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                <span
                  style={{
                    width: '7px',
                    height: '7px',
                    borderRadius: '50%',
                    background: '#34d399',
                  }}
                />
                <span
                  style={{
                    fontSize: '10.5px',
                    fontWeight: '700',
                    color: 'var(--color-text-muted)',
                    textTransform: 'uppercase',
                    letterSpacing: '0.08em',
                  }}
                >
                  CONSOLIDATE
                </span>
              </div>
              <span
                style={{
                  fontSize: '22px',
                  fontWeight: '800',
                  color: '#34d399',
                  fontVariantNumeric: 'tabular-nums',
                }}
              >
                {String(counts.CONSOLIDATE || 0).padStart(2, '0')}
              </span>
            </div>

            <div style={{ width: '1px', height: '36px', background: 'var(--color-border)' }} />

            {/* Retire Candidates */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '2px', minWidth: '130px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                <span
                  style={{
                    width: '7px',
                    height: '7px',
                    borderRadius: '50%',
                    background: '#fbbf24',
                  }}
                />
                <span
                  style={{
                    fontSize: '10.5px',
                    fontWeight: '700',
                    color: 'var(--color-text-muted)',
                    textTransform: 'uppercase',
                    letterSpacing: '0.08em',
                  }}
                >
                  RETIRE CANDIDATES
                </span>
              </div>
              <span
                style={{
                  fontSize: '22px',
                  fontWeight: '800',
                  color: '#fbbf24',
                  fontVariantNumeric: 'tabular-nums',
                }}
              >
                {String(counts.RETIRE_CANDIDATE || 0).padStart(2, '0')}
              </span>
            </div>

            <div style={{ width: '1px', height: '36px', background: 'var(--color-border)' }} />

            {/* Shared Logic */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '2px', minWidth: '120px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                <span
                  style={{
                    width: '7px',
                    height: '7px',
                    borderRadius: '50%',
                    background: '#38bdf8',
                  }}
                />
                <span
                  style={{
                    fontSize: '10.5px',
                    fontWeight: '700',
                    color: 'var(--color-text-muted)',
                    textTransform: 'uppercase',
                    letterSpacing: '0.08em',
                  }}
                >
                  SHARED FORMULAE
                </span>
              </div>
              <span
                style={{
                  fontSize: '22px',
                  fontWeight: '800',
                  color: '#38bdf8',
                  fontVariantNumeric: 'tabular-nums',
                }}
              >
                {String(counts.SHARED_LOGIC || 0).padStart(2, '0')}
              </span>
            </div>

            <div style={{ width: '1px', height: '36px', background: 'var(--color-border)' }} />

            {/* Review Needed */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '2px', minWidth: '120px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                <span
                  style={{
                    width: '7px',
                    height: '7px',
                    borderRadius: '50%',
                    background: '#c084fc',
                  }}
                />
                <span
                  style={{
                    fontSize: '10.5px',
                    fontWeight: '700',
                    color: 'var(--color-text-muted)',
                    textTransform: 'uppercase',
                    letterSpacing: '0.08em',
                  }}
                >
                  REVIEW NEEDED
                </span>
              </div>
              <span
                style={{
                  fontSize: '22px',
                  fontWeight: '800',
                  color: '#c084fc',
                  fontVariantNumeric: 'tabular-nums',
                }}
              >
                {String(counts.REVIEW || 0).padStart(2, '0')}
              </span>
            </div>
          </div>

          {/* Filter Tabs & Search Controls */}
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              flexWrap: 'wrap',
              gap: '16px',
            }}
          >
            {/* Filter Tabs */}
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                flexWrap: 'wrap',
              }}
            >
              {[
                { key: 'ALL', label: 'All Opportunities', count: totalOpportunities },
                { key: 'CONSOLIDATE', label: 'Consolidate', count: counts.CONSOLIDATE || 0 },
                { key: 'RETIRE_CANDIDATE', label: 'Retire Candidates', count: counts.RETIRE_CANDIDATE || 0 },
                { key: 'SHARED_LOGIC', label: 'Shared Formulae', count: counts.SHARED_LOGIC || 0 },
                { key: 'REVIEW', label: 'Review', count: counts.REVIEW || 0 },
              ].map((tab) => {
                const isSelected = activeTab === tab.key;
                return (
                  <button
                    key={tab.key}
                    onClick={() => setActiveTab(tab.key)}
                    style={{
                      display: 'inline-flex',
                      alignItems: 'center',
                      gap: '8px',
                      padding: '8px 16px',
                      borderRadius: '20px',
                      fontSize: '12.5px',
                      fontWeight: isSelected ? '700' : '500',
                      border: isSelected
                        ? '1px solid var(--color-primary)'
                        : '1px solid var(--color-border)',
                      background: isSelected
                        ? 'var(--color-primary)'
                        : 'var(--color-surface)',
                      color: isSelected ? '#ffffff' : 'var(--color-text-secondary)',
                      cursor: 'pointer',
                      transition: 'all 0.18s ease',
                    }}
                    onMouseEnter={(e) => {
                      if (!isSelected) {
                        e.currentTarget.style.color = 'var(--color-text)';
                        e.currentTarget.style.borderColor = 'var(--color-text-muted)';
                        e.currentTarget.style.background = 'var(--color-surface-hover)';
                      }
                    }}
                    onMouseLeave={(e) => {
                      if (!isSelected) {
                        e.currentTarget.style.color = 'var(--color-text-secondary)';
                        e.currentTarget.style.borderColor = 'var(--color-border)';
                        e.currentTarget.style.background = 'var(--color-surface)';
                      }
                    }}
                  >
                    <span>{tab.label}</span>
                    <span
                      style={{
                        fontSize: '11px',
                        padding: '1px 6px',
                        borderRadius: '10px',
                        background: isSelected
                          ? 'rgba(255, 255, 255, 0.25)'
                          : 'var(--color-surface-secondary)',
                        color: isSelected ? '#ffffff' : 'var(--color-text-muted)',
                      }}
                    >
                      {tab.count}
                    </span>
                  </button>
                );
              })}
            </div>

            {/* Search Input */}
            <div style={{ position: 'relative', minWidth: '320px', flex: '1', maxWidth: '440px' }}>
              <div
                style={{
                  position: 'absolute',
                  left: '12px',
                  top: '50%',
                  transform: 'translateY(-50%)',
                  color: 'var(--color-text-muted)',
                  display: 'flex',
                  alignItems: 'center',
                  pointerEvents: 'none',
                }}
              >
                <Search size={15} />
              </div>
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search workflows, datasets, evidence..."
                style={{
                  width: '100%',
                  padding: '9px 36px 9px 34px',
                  borderRadius: 'var(--radius-sm)',
                  border: '1px solid var(--color-border)',
                  background: 'var(--color-surface)',
                  color: 'var(--color-text)',
                  fontSize: '13px',
                  outline: 'none',
                  boxSizing: 'border-box',
                  transition: 'border-color 0.18s ease',
                }}
                onFocus={(e) => {
                  e.currentTarget.style.borderColor = 'var(--color-primary)';
                }}
                onBlur={(e) => {
                  e.currentTarget.style.borderColor = 'var(--color-border)';
                }}
              />
              {searchQuery && (
                <button
                  onClick={() => setSearchQuery('')}
                  style={{
                    position: 'absolute',
                    right: '10px',
                    top: '50%',
                    transform: 'translateY(-50%)',
                    background: 'transparent',
                    border: 'none',
                    color: 'var(--color-text-muted)',
                    cursor: 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    padding: '2px',
                  }}
                  title="Clear search"
                >
                  <X size={14} />
                </button>
              )}
            </div>
          </div>

          {/* 6. Opportunity Cards List */}
          {filteredCandidates.length > 0 ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
              {filteredCandidates.map((cand) => {
                const badge = getRecommendationBadge(cand.recommendation_type);
                const confBadge = getConfidenceBadge(cand.confidence);
                const BadgeIcon = badge.icon;

                return (
                  <div
                    key={cand.candidate_id}
                    style={{
                      background: 'var(--color-surface)',
                      border: '1px solid var(--color-border)',
                      borderRadius: '10px',
                      padding: '24px',
                      display: 'flex',
                      flexDirection: 'column',
                      gap: '18px',
                      boxShadow: '0 2px 10px rgba(0, 0, 0, 0.15)',
                      transition: 'border-color 0.2s ease, transform 0.2s ease, box-shadow 0.2s ease',
                    }}
                    onMouseEnter={(e) => {
                      e.currentTarget.style.borderColor = 'var(--color-primary-border)';
                      e.currentTarget.style.transform = 'translateY(-1px)';
                      e.currentTarget.style.boxShadow = '0 6px 20px rgba(0, 0, 0, 0.25)';
                    }}
                    onMouseLeave={(e) => {
                      e.currentTarget.style.borderColor = 'var(--color-border)';
                      e.currentTarget.style.transform = 'none';
                      e.currentTarget.style.boxShadow = '0 2px 10px rgba(0, 0, 0, 0.15)';
                    }}
                  >
                    {/* Top Row: Recommendation, Score, Confidence */}
                    <div
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'space-between',
                        flexWrap: 'wrap',
                        gap: '12px',
                      }}
                    >
                      <div style={{ display: 'flex', alignItems: 'center', gap: '10px', flexWrap: 'wrap' }}>
                        {/* Recommendation Badge */}
                        <span
                          style={{
                            display: 'inline-flex',
                            alignItems: 'center',
                            gap: '6px',
                            padding: '4px 12px',
                            borderRadius: '20px',
                            fontSize: '11px',
                            fontWeight: '800',
                            textTransform: 'uppercase',
                            letterSpacing: '0.06em',
                            background: badge.bg,
                            color: badge.color,
                            border: badge.border,
                          }}
                        >
                          <BadgeIcon size={13} />
                          {badge.label}
                        </span>

                        {/* LLM Status Indicator */}
                        <span
                          style={{
                            fontSize: '10.5px',
                            fontWeight: '700',
                            padding: '3px 8px',
                            borderRadius: '4px',
                            background:
                              cand.llm_enrichment_status === 'ENRICHED'
                                ? 'rgba(56, 189, 248, 0.1)'
                                : 'var(--color-surface-secondary)',
                            color:
                              cand.llm_enrichment_status === 'ENRICHED'
                                ? '#38bdf8'
                                : 'var(--color-text-muted)',
                            border: '1px solid var(--color-border-subtle)',
                          }}
                        >
                          {cand.llm_enrichment_status === 'ENRICHED'
                            ? 'AI Qualified'
                            : 'Deterministic Baseline'}
                        </span>
                      </div>

                      {/* Confidence Badge */}
                      <span
                        style={{
                          fontSize: '11px',
                          fontWeight: '800',
                          letterSpacing: '0.06em',
                          padding: '3px 10px',
                          borderRadius: '4px',
                          background: confBadge.bg,
                          color: confBadge.color,
                          border: confBadge.border,
                        }}
                      >
                        {confBadge.label}
                      </span>
                    </div>

                    {/* Workflows Involved Strip */}
                    <div
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: '16px',
                        padding: '14px 18px',
                        borderRadius: '8px',
                        background: 'var(--color-surface-secondary)',
                        border: '1px solid var(--color-border-subtle)',
                        flexWrap: 'wrap',
                      }}
                    >
                      {cand.workflow_names.map((name, idx) => {
                        const wid = cand.workflow_ids[idx];
                        const summary = wid ? workflowMap.get(wid) : null;
                        const complexityStyle = getLevelBadgeStyle(summary?.complexity_level || 'LOW');
                        const criticalityStyle = getLevelBadgeStyle(summary?.criticality_level || 'LOW');

                        return (
                          <React.Fragment key={wid || idx}>
                            {idx > 0 && (
                              <div
                                style={{
                                  display: 'flex',
                                  alignItems: 'center',
                                  color: 'var(--color-text-muted)',
                                  fontSize: '13px',
                                  fontWeight: '700',
                                }}
                              >
                                ↔
                              </div>
                            )}

                            <div
                              style={{
                                display: 'flex',
                                alignItems: 'center',
                                gap: '10px',
                                flexWrap: 'wrap',
                              }}
                            >
                              <span
                                style={{
                                  fontSize: '14px',
                                  fontWeight: '700',
                                  color: 'var(--color-text)',
                                  wordBreak: 'break-word',
                                }}
                              >
                                {name}
                              </span>

                              {/* Complexity & Criticality Pills */}
                              {summary && (
                                <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                                  <span
                                    style={{
                                      fontSize: '10.5px',
                                      fontWeight: '700',
                                      padding: '2px 7px',
                                      borderRadius: '4px',
                                      ...complexityStyle,
                                    }}
                                    title={`Complexity: ${summary.complexity_level || 'LOW'}`}
                                  >
                                    Complexity: {summary.complexity_level || 'LOW'}
                                  </span>

                                  <span
                                    style={{
                                      fontSize: '10.5px',
                                      fontWeight: '700',
                                      padding: '2px 7px',
                                      borderRadius: '4px',
                                      ...criticalityStyle,
                                    }}
                                    title={`Criticality: ${summary.criticality_level || 'LOW'}`}
                                  >
                                    Criticality: {summary.criticality_level || 'LOW'}
                                  </span>
                                </div>
                              )}
                            </div>
                          </React.Fragment>
                        );
                      })}
                    </div>

                    {/* Deterministic Similarity Metrics Progress Bars */}
                    <div
                      style={{
                        display: 'grid',
                        gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))',
                        gap: '14px',
                      }}
                    >
                      {[
                        { label: 'Source Metadata Overlap', value: cand.deterministic_metrics.source_overlap },
                        { label: 'Target Metadata Overlap', value: cand.deterministic_metrics.target_overlap },
                        { label: 'Frequency Overlap', value: cand.deterministic_metrics.frequency_overlap ?? 0 },
                        { label: 'Logic Overlap', value: cand.deterministic_metrics.transformation_similarity },
                        { label: 'DAG Overlap', value: cand.deterministic_metrics.dag_similarity },
                      ].map((m) => {
                        const pct = Math.round(m.value * 100);
                        const fillColor = pct >= 70 ? '#34d399' : pct >= 40 ? '#fbbf24' : '#38bdf8';

                        return (
                          <div
                            key={m.label}
                            style={{
                              display: 'flex',
                              flexDirection: 'column',
                              gap: '4px',
                            }}
                          >
                            <div
                              style={{
                                display: 'flex',
                                justifyContent: 'space-between',
                                fontSize: '11px',
                                fontWeight: '600',
                                color: 'var(--color-text-secondary)',
                              }}
                            >
                              <span>{m.label}</span>
                              <span style={{ fontWeight: '700', color: 'var(--color-text)' }}>{pct}%</span>
                            </div>
                            <div
                              style={{
                                width: '100%',
                                height: '5px',
                                borderRadius: '3px',
                                background: 'var(--color-surface-secondary)',
                                overflow: 'hidden',
                              }}
                            >
                              <div
                                style={{
                                  width: `${pct}%`,
                                  height: '100%',
                                  background: fillColor,
                                  borderRadius: '3px',
                                  transition: 'width 0.4s ease',
                                }}
                              />
                            </div>
                          </div>
                        );
                      })}
                    </div>

                    {/* Why It Matters (Reasoning) */}
                    <div>
                      <div
                        style={{
                          fontSize: '11px',
                          fontWeight: '700',
                          textTransform: 'uppercase',
                          letterSpacing: '0.08em',
                          color: 'var(--color-text-muted)',
                          marginBottom: '4px',
                        }}
                      >
                        RECOMMENDATION RATIONALE
                      </div>
                      <p
                        style={{
                          fontSize: '13.5px',
                          lineHeight: '1.55',
                          color: 'var(--color-text-secondary)',
                          margin: 0,
                        }}
                      >
                        {cand.reasoning}
                      </p>
                    </div>

                    {/* Card Footer Strip: Evidence Summary & Action Button */}
                    <div
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'space-between',
                        borderTop: '1px solid var(--color-border-subtle)',
                        paddingTop: '16px',
                        flexWrap: 'wrap',
                        gap: '12px',
                      }}
                    >
                      {/* Evidence Tags */}
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
                        {cand.dependency_evidence.shared_sources.length > 0 && (
                          <span
                            style={{
                              display: 'inline-flex',
                              alignItems: 'center',
                              gap: '5px',
                              fontSize: '11px',
                              fontWeight: '600',
                              color: 'var(--color-text-secondary)',
                              background: 'var(--color-surface-secondary)',
                              padding: '3px 8px',
                              borderRadius: '4px',
                            }}
                          >
                            <Database size={11} />
                            {cand.dependency_evidence.shared_sources.length} Shared Source
                            {cand.dependency_evidence.shared_sources.length > 1 ? 's' : ''}
                          </span>
                        )}

                        {cand.dependency_evidence.shared_targets.length > 0 && (
                          <span
                            style={{
                              display: 'inline-flex',
                              alignItems: 'center',
                              gap: '5px',
                              fontSize: '11px',
                              fontWeight: '600',
                              color: 'var(--color-text-secondary)',
                              background: 'var(--color-surface-secondary)',
                              padding: '3px 8px',
                              borderRadius: '4px',
                            }}
                          >
                            <Target size={11} />
                            {cand.dependency_evidence.shared_targets.length} Shared Target
                            {cand.dependency_evidence.shared_targets.length > 1 ? 's' : ''}
                          </span>
                        )}

                        {(() => {
                          const validCount = (cand.shared_logic || []).filter(isMeaningfulEvidence).length;
                          if (validCount === 0) return null;
                          return (
                            <span
                              style={{
                                display: 'inline-flex',
                                alignItems: 'center',
                                gap: '5px',
                                fontSize: '11px',
                                fontWeight: '600',
                                color: 'var(--color-text-secondary)',
                                background: 'var(--color-surface-secondary)',
                                padding: '3px 8px',
                                borderRadius: '4px',
                              }}
                            >
                              <Cpu size={11} />
                              {validCount} Shared Operation{validCount > 1 ? 's' : ''}
                            </span>
                          );
                        })()}
                      </div>

                      {/* Detail CTA Button */}
                      <button
                        onClick={() => setSelectedCandidate(cand)}
                        style={{
                          display: 'inline-flex',
                          alignItems: 'center',
                          gap: '6px',
                          padding: '7px 14px',
                          borderRadius: 'var(--radius-sm)',
                          background: 'var(--color-surface-secondary)',
                          border: '1px solid var(--color-border)',
                          color: 'var(--color-text)',
                          fontSize: '12.5px',
                          fontWeight: '700',
                          cursor: 'pointer',
                          transition: 'all 0.18s ease',
                        }}
                        onMouseEnter={(e) => {
                          e.currentTarget.style.background = 'var(--color-surface-hover)';
                          e.currentTarget.style.borderColor = 'var(--color-primary-border)';
                          e.currentTarget.style.color = 'var(--color-primary)';
                        }}
                        onMouseLeave={(e) => {
                          e.currentTarget.style.background = 'var(--color-surface-secondary)';
                          e.currentTarget.style.borderColor = 'var(--color-border)';
                          e.currentTarget.style.color = 'var(--color-text)';
                        }}
                      >
                        <span>View Detailed Analysis</span>
                        <ArrowRight size={13} />
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>
          ) : (
            /* Empty State */
            <div
              style={{
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                justifyContent: 'center',
                padding: '64px 24px',
                borderRadius: '12px',
                background: 'var(--color-surface)',
                border: '1px solid var(--color-border)',
                textAlign: 'center',
                gap: '16px',
              }}
            >
              {totalOpportunities === 0 ? (
                // Estate-level zero opportunities
                <>
                  <div
                    style={{
                      width: '48px',
                      height: '48px',
                      borderRadius: '50%',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      background: 'rgba(34, 197, 94, 0.1)',
                      color: 'var(--color-success)',
                      border: '1px solid rgba(34, 197, 94, 0.25)',
                    }}
                  >
                    <ShieldCheck size={28} />
                  </div>
                  <div>
                    <h3
                      style={{
                        fontSize: '18px',
                        fontWeight: '700',
                        color: 'var(--color-text)',
                        margin: '0 0 6px 0',
                      }}
                    >
                      No rationalisation opportunities identified
                    </h3>
                    <p
                      style={{
                        fontSize: '14px',
                        color: 'var(--color-text-secondary)',
                        margin: 0,
                        maxWidth: '520px',
                        lineHeight: '1.55',
                      }}
                    >
                      The current workflow estate does not contain sufficient deterministic evidence for a
                      rationalisation recommendation. All workflows have distinct datasets, unique schemas,
                      and independent operational deliverables.
                    </p>
                  </div>
                </>
              ) : (
                // Filter / Search zero matches
                <>
                  <div
                    style={{
                      width: '48px',
                      height: '48px',
                      borderRadius: '50%',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      background: 'var(--color-surface-secondary)',
                      color: 'var(--color-text-muted)',
                      border: '1px solid var(--color-border)',
                    }}
                  >
                    <Search size={22} />
                  </div>
                  <div>
                    <h3
                      style={{
                        fontSize: '18px',
                        fontWeight: '700',
                        color: 'var(--color-text)',
                        margin: '0 0 6px 0',
                      }}
                    >
                      No rationalisation opportunities match your criteria
                    </h3>
                    <p
                      style={{
                        fontSize: '14px',
                        color: 'var(--color-text-secondary)',
                        margin: 0,
                        maxWidth: '460px',
                        lineHeight: '1.5',
                      }}
                    >
                      Try switching filter tabs or clearing your search query to inspect other rationalisation
                      opportunities.
                    </p>
                  </div>
                  {(activeTab !== 'ALL' || searchQuery) && (
                    <button
                      onClick={() => {
                        setActiveTab('ALL');
                        setSearchQuery('');
                      }}
                      style={{
                        display: 'inline-flex',
                        alignItems: 'center',
                        gap: '6px',
                        padding: '7px 14px',
                        borderRadius: 'var(--radius-sm)',
                        background: 'var(--color-surface-secondary)',
                        border: '1px solid var(--color-border)',
                        color: 'var(--color-text)',
                        fontSize: '12.5px',
                        fontWeight: '600',
                        cursor: 'pointer',
                      }}
                    >
                      Reset Filters
                    </button>
                  )}
                </>
              )}
            </div>
          )}
        </>
      )}

      {/* 7. Candidate Detail Modal */}
      {selectedCandidate && (
        <div
          role="dialog"
          aria-modal="true"
          style={{
            position: 'fixed',
            inset: 0,
            background: 'rgba(0, 0, 0, 0.78)',
            backdropFilter: 'blur(5px)',
            zIndex: 9999,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            padding: '24px',
            boxSizing: 'border-box',
          }}
          onClick={() => setSelectedCandidate(null)}
        >
          <div
            style={{
              maxWidth: '920px',
              width: '100%',
              maxHeight: '88vh',
              overflowY: 'auto',
              background: 'var(--color-surface)',
              border: '1px solid var(--color-border)',
              borderRadius: '12px',
              padding: '32px',
              boxShadow: '0 24px 60px rgba(0, 0, 0, 0.7)',
              display: 'flex',
              flexDirection: 'column',
              gap: '24px',
              boxSizing: 'border-box',
            }}
            onClick={(e) => e.stopPropagation()}
          >
            {/* Modal Header */}
            <div
              style={{
                display: 'flex',
                alignItems: 'flex-start',
                justifyContent: 'space-between',
                borderBottom: '1px solid var(--color-border-subtle)',
                paddingBottom: '20px',
                gap: '16px',
              }}
            >
              <div>
                <div
                  style={{
                    fontSize: '10.5px',
                    fontWeight: '800',
                    textTransform: 'uppercase',
                    letterSpacing: '0.12em',
                    color: 'var(--color-primary)',
                    marginBottom: '4px',
                  }}
                >
                  DETAILED OPPORTUNITY ANALYSIS
                </div>
                <h2
                  style={{
                    fontSize: '22px',
                    fontWeight: '800',
                    color: 'var(--color-text)',
                    margin: 0,
                    letterSpacing: '-0.01em',
                  }}
                >
                  Rationalisation Candidate Analysis
                </h2>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginTop: '8px' }}>
                  {(() => {
                    const badge = getRecommendationBadge(selectedCandidate.recommendation_type);
                    const BadgeIcon = badge.icon;
                    return (
                      <span
                        style={{
                          display: 'inline-flex',
                          alignItems: 'center',
                          gap: '5px',
                          padding: '3px 10px',
                          borderRadius: '20px',
                          fontSize: '11px',
                          fontWeight: '800',
                          background: badge.bg,
                          color: badge.color,
                          border: badge.border,
                        }}
                      >
                        <BadgeIcon size={12} />
                        {badge.label}
                      </span>
                    );
                  })()}

                  <span
                    style={{
                      fontSize: '11px',
                      fontWeight: '800',
                      padding: '3px 8px',
                      borderRadius: '4px',
                      ...getConfidenceBadge(selectedCandidate.confidence),
                    }}
                  >
                    {selectedCandidate.confidence} CONFIDENCE
                  </span>
                </div>
              </div>

              <button
                onClick={() => setSelectedCandidate(null)}
                style={{
                  background: 'var(--color-surface-secondary)',
                  border: '1px solid var(--color-border)',
                  borderRadius: '6px',
                  padding: '6px',
                  color: 'var(--color-text-secondary)',
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                }}
                title="Close modal"
              >
                <X size={18} />
              </button>
            </div>

            {/* In-Scope Workflows Side-by-Side */}
            <div>
              <div
                style={{
                  fontSize: '11px',
                  fontWeight: '700',
                  textTransform: 'uppercase',
                  letterSpacing: '0.08em',
                  color: 'var(--color-text-muted)',
                  marginBottom: '10px',
                }}
              >
                IN-SCOPE WORKFLOWS
              </div>
              <div
                style={{
                  display: 'grid',
                  gridTemplateColumns:
                    selectedCandidate.workflow_names.length > 1 ? '1fr 1fr' : '1fr',
                  gap: '16px',
                }}
              >
                {selectedCandidate.workflow_names.map((name, idx) => {
                  const wid = selectedCandidate.workflow_ids[idx];
                  const summary = wid ? workflowMap.get(wid) : null;
                  const compStyle = getLevelBadgeStyle(summary?.complexity_level || 'LOW');
                  const critStyle = getLevelBadgeStyle(summary?.criticality_level || 'LOW');

                  return (
                    <div
                      key={wid || idx}
                      style={{
                        padding: '16px',
                        borderRadius: '8px',
                        background: 'var(--color-surface-secondary)',
                        border: '1px solid var(--color-border)',
                        display: 'flex',
                        flexDirection: 'column',
                        gap: '12px',
                      }}
                    >
                      <div
                        style={{
                          fontSize: '14px',
                          fontWeight: '700',
                          color: 'var(--color-text)',
                          wordBreak: 'break-word',
                        }}
                      >
                        {name}
                      </div>

                      {summary && (
                        <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
                          <span
                            style={{
                              fontSize: '10.5px',
                              fontWeight: '700',
                              padding: '2px 8px',
                              borderRadius: '4px',
                              ...compStyle,
                            }}
                          >
                            Complexity: {summary.complexity_level || 'LOW'} 
                          </span>
                          <span
                            style={{
                              fontSize: '10.5px',
                              fontWeight: '700',
                              padding: '2px 8px',
                              borderRadius: '4px',
                              ...critStyle,
                            }}
                          >
                            Criticality: {summary.criticality_level || 'LOW'}
                          </span>
                        </div>
                      )}

                      {wid && (
                        <div>
                          <button
                            onClick={() => handleInspectClick(wid)}
                            style={{
                              display: 'inline-flex',
                              alignItems: 'center',
                              gap: '6px',
                              padding: '6px 12px',
                              borderRadius: 'var(--radius-sm)',
                              background: 'var(--color-surface)',
                              border: '1px solid var(--color-border)',
                              color: 'var(--color-primary)',
                              fontSize: '12px',
                              fontWeight: '700',
                              cursor: 'pointer',
                            }}
                          >
                            <span>Inspect Workflow</span>
                            <ExternalLink size={12} />
                          </button>
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Overlap Evidence Interactive Metric Selector */}
            <div>
              <div
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  marginBottom: '10px',
                }}
              >
                <div
                  style={{
                    fontSize: '11px',
                    fontWeight: '700',
                    textTransform: 'uppercase',
                    letterSpacing: '0.08em',
                    color: 'var(--color-text-muted)',
                  }}
                >
                  OVERLAP EVIDENCE (CLICK TO INSPECT)
                </div>
                <div style={{ fontSize: '11px', color: '#facc15', fontWeight: '600' }}>
                  Select metric to inspect matching evidence
                </div>
              </div>

              <div
                style={{
                  display: 'grid',
                  gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))',
                  gap: '10px',
                  marginBottom: '16px',
                }}
              >
                {[
                  {
                    key: 'source' as const,
                    label: 'Source Metadata Overlap',
                    val: selectedCandidate.deterministic_metrics.source_overlap,
                    icon: Database,
                  },
                  {
                    key: 'target' as const,
                    label: 'Target Metadata Overlap',
                    val: selectedCandidate.deterministic_metrics.target_overlap,
                    icon: Target,
                  },
                  {
                    key: 'frequency' as const,
                    label: 'Frequency Overlap',
                    val: selectedCandidate.deterministic_metrics.frequency_overlap ?? 0,
                    icon: Clock,
                  },
                  {
                    key: 'logic' as const,
                    label: 'Logic Overlap',
                    val: selectedCandidate.deterministic_metrics.transformation_similarity,
                    icon: Cpu,
                  },
                  {
                    key: 'dag' as const,
                    label: 'DAG Overlap',
                    val: selectedCandidate.deterministic_metrics.dag_similarity,
                    icon: Layers,
                  },
                ].map((m) => {
                  const isSelected = activeEvidenceMetric === m.key;
                  const Icon = m.icon;

                  return (
                    <button
                      key={m.key}
                      onClick={() => setActiveEvidenceMetric(m.key)}
                      style={{
                        display: 'flex',
                        flexDirection: 'column',
                        gap: '6px',
                        padding: '12px',
                        borderRadius: '8px',
                        background: isSelected ? 'rgba(234, 179, 8, 0.09)' : 'var(--color-surface-secondary)',
                        border: isSelected ? '1.5px solid #facc15' : '1px solid var(--color-border-subtle)',
                        boxShadow: isSelected ? '0 0 12px rgba(234, 179, 8, 0.18)' : 'none',
                        cursor: 'pointer',
                        textAlign: 'left',
                        transition: 'all 0.2s ease',
                      }}
                    >
                      <div
                        style={{
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'space-between',
                          width: '100%',
                        }}
                      >
                        <div style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
                          <Icon size={12} color={isSelected ? '#facc15' : 'var(--color-text-muted)'} />
                          <span
                            style={{
                              fontSize: '11px',
                              fontWeight: isSelected ? '700' : '600',
                              color: isSelected ? '#facc15' : 'var(--color-text-secondary)',
                            }}
                          >
                            {m.label}
                          </span>
                        </div>
                        {/* <span
                          style={{
                            fontSize: '12px',
                            fontWeight: '800',
                            color: isSelected ? '#facc15' : 'var(--color-text)',
                          }}
                        >
                          {pct}%
                        </span> */}
                      </div>


                    </button>
                  );
                })}
              </div>
            </div>

            {/* Interactive Side-by-Side Evidence Inspection Panel */}
            {(() => {
              const wfA_name = selectedCandidate.workflow_names[0] || 'Workflow A';
              const wfB_name = selectedCandidate.workflow_names[1] || 'Workflow B';
              const wfA_id = selectedCandidate.workflow_ids[0] || '';
              const wfB_id = selectedCandidate.workflow_ids[1] || '';

              const normalizeItem = (s: string) =>
                s
                  ? s
                      .replace(/\\/g, '/')
                      .split('/')
                      .pop()
                      ?.toLowerCase()
                      .replace(/\.[a-z0-9]+$/, '')
                      .replace(/[^a-z0-9_]/g, '_')
                      .replace(/^_+|_+$/g, '') || ''
                  : '';

              if (activeEvidenceMetric === 'source') {
                const sourcesA = selectedCandidate.sources_by_workflow?.[wfA_name] || workflowMap.get(wfA_id)?.sources || [];
                const sourcesB = selectedCandidate.sources_by_workflow?.[wfB_name] || workflowMap.get(wfB_id)?.sources || [];
                const normB = new Set(sourcesB.map(normalizeItem));
                const normA = new Set(sourcesA.map(normalizeItem));

                const fieldsMapA = selectedCandidate.source_fields_by_workflow?.[wfA_name] || {};
                const fieldsMapB = selectedCandidate.source_fields_by_workflow?.[wfB_name] || {};
                const allFieldsA = Object.values(fieldsMapA).flat();
                const allFieldsB = Object.values(fieldsMapB).flat();
                const setFieldsA = new Set(allFieldsA.map((f) => f.toLowerCase()));
                const setFieldsB = new Set(allFieldsB.map((f) => f.toLowerCase()));

                return (
                  <div>
                    <div
                      style={{
                        fontSize: '11px',
                        fontWeight: '700',
                        textTransform: 'uppercase',
                        letterSpacing: '0.08em',
                        color: 'var(--color-text-muted)',
                        marginBottom: '8px',
                      }}
                    >
                      SOURCE DATASETS & COLUMN HEADERS (YELLOW = MATCHING)
                    </div>
                    <div style={{ display: 'grid', gridTemplateColumns: 'minmax(0, 1fr) minmax(0, 1fr)', gap: '16px' }}>
                      {/* Left side: Workflow A */}
                      <div
                        style={{
                          padding: '16px',
                          borderRadius: '8px',
                          background: 'var(--color-surface-secondary)',
                          border: '1px solid var(--color-border-subtle)',
                          display: 'flex',
                          flexDirection: 'column',
                          gap: '12px',
                          minWidth: 0,
                          maxWidth: '100%',
                          boxSizing: 'border-box',
                        }}
                      >
                        <div style={{ fontSize: '13px', fontWeight: '700', color: 'var(--color-text)', minWidth: 0, wordBreak: 'break-word', overflowWrap: 'anywhere' }}>
                          {wfA_name} ({sourcesA.length} source{sourcesA.length !== 1 ? 's' : ''})
                        </div>
                        {sourcesA.length === 0 ? (
                          <div style={{ fontSize: '12px', color: 'var(--color-text-muted)' }}>No physical sources configured</div>
                        ) : (
                          sourcesA.map((src, idx) => {
                            const isMatch = normB.has(normalizeItem(src));
                            const fields = fieldsMapA[src] || fieldsMapA['sources'] || [];

                            return (
                              <div
                                key={idx}
                                style={{
                                  padding: '10px 12px',
                                  borderRadius: '6px',
                                  background: isMatch ? 'rgba(234, 179, 8, 0.08)' : 'var(--color-surface)',
                                  border: isMatch ? '1.5px solid rgba(234, 179, 8, 0.45)' : '1px solid var(--color-border-subtle)',
                                  display: 'flex',
                                  flexDirection: 'column',
                                  gap: '6px',
                                  minWidth: 0,
                                  maxWidth: '100%',
                                  boxSizing: 'border-box',
                                }}
                              >
                                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '8px', minWidth: 0 }}>
                                  <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontWeight: '700', fontSize: '12.5px', color: isMatch ? '#facc15' : 'var(--color-text)', minWidth: 0, flex: 1, wordBreak: 'break-word', overflowWrap: 'anywhere' }}>
                                    <Database size={13} style={{ flexShrink: 0 }} color={isMatch ? '#facc15' : 'var(--color-text-muted)'} />
                                    <span style={{ minWidth: 0, wordBreak: 'break-word', overflowWrap: 'anywhere' }}>{src}</span>
                                  </div>
                                  {isMatch ? (
                                    <span style={{ flexShrink: 0, fontSize: '10px', fontWeight: '800', background: 'rgba(234, 179, 8, 0.22)', color: '#facc15', padding: '2px 6px', borderRadius: '4px', textTransform: 'uppercase' }}>
                                      Matching Source
                                    </span>
                                  ) : (
                                    <span style={{ flexShrink: 0, fontSize: '10px', fontWeight: '600', color: 'var(--color-text-muted)' }}>
                                      Distinct
                                    </span>
                                  )}
                                </div>
                                {fields.length > 0 && (
                                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: '5px', marginTop: '2px', minWidth: 0 }}>
                                    {fields.map((fld) => {
                                      const isColMatch = setFieldsB.has(fld.toLowerCase());
                                      return (
                                        <span
                                          key={fld}
                                          style={{
                                            fontSize: '10.5px',
                                            fontWeight: isColMatch ? '700' : '500',
                                            padding: '2px 6px',
                                            borderRadius: '4px',
                                            background: isColMatch ? 'rgba(234, 179, 8, 0.18)' : 'var(--color-surface-secondary)',
                                            color: isColMatch ? '#facc15' : 'var(--color-text-secondary)',
                                            border: isColMatch ? '1px solid rgba(234, 179, 8, 0.4)' : '1px solid var(--color-border-subtle)',
                                            maxWidth: '100%',
                                            wordBreak: 'break-word',
                                            overflowWrap: 'anywhere',
                                          }}
                                        >
                                          {fld}
                                        </span>
                                      );
                                    })}
                                  </div>
                                )}
                              </div>
                            );
                          })
                        )}
                      </div>

                      {/* Right side: Workflow B */}
                      <div
                        style={{
                          padding: '16px',
                          borderRadius: '8px',
                          background: 'var(--color-surface-secondary)',
                          border: '1px solid var(--color-border-subtle)',
                          display: 'flex',
                          flexDirection: 'column',
                          gap: '12px',
                          minWidth: 0,
                          maxWidth: '100%',
                          boxSizing: 'border-box',
                        }}
                      >
                        <div style={{ fontSize: '13px', fontWeight: '700', color: 'var(--color-text)', minWidth: 0, wordBreak: 'break-word', overflowWrap: 'anywhere' }}>
                          {wfB_name} ({sourcesB.length} source{sourcesB.length !== 1 ? 's' : ''})
                        </div>
                        {sourcesB.length === 0 ? (
                          <div style={{ fontSize: '12px', color: 'var(--color-text-muted)' }}>No physical sources configured</div>
                        ) : (
                          sourcesB.map((src, idx) => {
                            const isMatch = normA.has(normalizeItem(src));
                            const fields = fieldsMapB[src] || fieldsMapB['sources'] || [];

                            return (
                              <div
                                key={idx}
                                style={{
                                  padding: '10px 12px',
                                  borderRadius: '6px',
                                  background: isMatch ? 'rgba(234, 179, 8, 0.08)' : 'var(--color-surface)',
                                  border: isMatch ? '1.5px solid rgba(234, 179, 8, 0.45)' : '1px solid var(--color-border-subtle)',
                                  display: 'flex',
                                  flexDirection: 'column',
                                  gap: '6px',
                                  minWidth: 0,
                                  maxWidth: '100%',
                                  boxSizing: 'border-box',
                                }}
                              >
                                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '8px', minWidth: 0 }}>
                                  <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontWeight: '700', fontSize: '12.5px', color: isMatch ? '#facc15' : 'var(--color-text)', minWidth: 0, flex: 1, wordBreak: 'break-word', overflowWrap: 'anywhere' }}>
                                    <Database size={13} style={{ flexShrink: 0 }} color={isMatch ? '#facc15' : 'var(--color-text-muted)'} />
                                    <span style={{ minWidth: 0, wordBreak: 'break-word', overflowWrap: 'anywhere' }}>{src}</span>
                                  </div>
                                  {isMatch ? (
                                    <span style={{ flexShrink: 0, fontSize: '10px', fontWeight: '800', background: 'rgba(234, 179, 8, 0.22)', color: '#facc15', padding: '2px 6px', borderRadius: '4px', textTransform: 'uppercase' }}>
                                      Matching Source
                                    </span>
                                  ) : (
                                    <span style={{ flexShrink: 0, fontSize: '10px', fontWeight: '600', color: 'var(--color-text-muted)' }}>
                                      Distinct
                                    </span>
                                  )}
                                </div>
                                {fields.length > 0 && (
                                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: '5px', marginTop: '2px', minWidth: 0 }}>
                                    {fields.map((fld) => {
                                      const isColMatch = setFieldsA.has(fld.toLowerCase());
                                      return (
                                        <span
                                          key={fld}
                                          style={{
                                            fontSize: '10.5px',
                                            fontWeight: isColMatch ? '700' : '500',
                                            padding: '2px 6px',
                                            borderRadius: '4px',
                                            background: isColMatch ? 'rgba(234, 179, 8, 0.18)' : 'var(--color-surface-secondary)',
                                            color: isColMatch ? '#facc15' : 'var(--color-text-secondary)',
                                            border: isColMatch ? '1px solid rgba(234, 179, 8, 0.4)' : '1px solid var(--color-border-subtle)',
                                            maxWidth: '100%',
                                            wordBreak: 'break-word',
                                            overflowWrap: 'anywhere',
                                          }}
                                        >
                                          {fld}
                                        </span>
                                      );
                                    })}
                                  </div>
                                )}
                              </div>
                            );
                          })
                        )}
                      </div>
                    </div>
                  </div>
                );
              }

              if (activeEvidenceMetric === 'target') {
                const targetsA = selectedCandidate.output_evidence.production_targets[wfA_id] || [];
                const targetsB = selectedCandidate.output_evidence.production_targets[wfB_id] || [];
                const normB = new Set(targetsB.map(normalizeItem));
                const normA = new Set(targetsA.map(normalizeItem));

                return (
                  <div>
                    <div
                      style={{
                        fontSize: '11px',
                        fontWeight: '700',
                        textTransform: 'uppercase',
                        letterSpacing: '0.08em',
                        color: 'var(--color-text-muted)',
                        marginBottom: '8px',
                      }}
                    >
                      PRODUCTION TARGETS (YELLOW = MATCHING DESTINATIONS)
                    </div>
                    <div style={{ display: 'grid', gridTemplateColumns: 'minmax(0, 1fr) minmax(0, 1fr)', gap: '16px' }}>
                      {/* Left: Targets A */}
                      <div
                        style={{
                          padding: '16px',
                          borderRadius: '8px',
                          background: 'var(--color-surface-secondary)',
                          border: '1px solid var(--color-border-subtle)',
                          display: 'flex',
                          flexDirection: 'column',
                          gap: '10px',
                          minWidth: 0,
                          maxWidth: '100%',
                          boxSizing: 'border-box',
                        }}
                      >
                        <div style={{ fontSize: '13px', fontWeight: '700', color: 'var(--color-text)', minWidth: 0, wordBreak: 'break-word', overflowWrap: 'anywhere' }}>
                          {wfA_name} ({targetsA.length} target{targetsA.length !== 1 ? 's' : ''})
                        </div>
                        {targetsA.length === 0 ? (
                          <div style={{ fontSize: '12px', color: 'var(--color-text-muted)' }}>No production deliverables configured</div>
                        ) : (
                          targetsA.map((tgt, idx) => {
                            const isMatch = normB.has(normalizeItem(tgt));
                            const schema = selectedCandidate.output_evidence.output_schemas[tgt] || [];
                            return (
                              <div
                                key={idx}
                                style={{
                                  padding: '10px 12px',
                                  borderRadius: '6px',
                                  background: isMatch ? 'rgba(234, 179, 8, 0.08)' : 'var(--color-surface)',
                                  border: isMatch ? '1.5px solid rgba(234, 179, 8, 0.45)' : '1px solid var(--color-border-subtle)',
                                  display: 'flex',
                                  flexDirection: 'column',
                                  gap: '6px',
                                  minWidth: 0,
                                  maxWidth: '100%',
                                  boxSizing: 'border-box',
                                }}
                              >
                                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '8px', minWidth: 0 }}>
                                  <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontWeight: '700', fontSize: '12.5px', color: isMatch ? '#facc15' : 'var(--color-text)', minWidth: 0, flex: 1, wordBreak: 'break-word', overflowWrap: 'anywhere' }}>
                                    <Target size={13} style={{ flexShrink: 0 }} color={isMatch ? '#facc15' : 'var(--color-text-muted)'} />
                                    <span style={{ minWidth: 0, wordBreak: 'break-word', overflowWrap: 'anywhere' }}>{tgt}</span>
                                  </div>
                                  {isMatch ? (
                                    <span style={{ flexShrink: 0, fontSize: '10px', fontWeight: '800', background: 'rgba(234, 179, 8, 0.22)', color: '#facc15', padding: '2px 6px', borderRadius: '4px' }}>
                                      Matching Target
                                    </span>
                                  ) : (
                                    <span style={{ flexShrink: 0, fontSize: '10px', fontWeight: '600', color: 'var(--color-text-muted)' }}>
                                      Distinct Output
                                    </span>
                                  )}
                                </div>
                                {schema.length > 0 && (
                                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: '5px', marginTop: '2px', minWidth: 0 }}>
                                    {schema.map((col) => (
                                      <span
                                        key={col}
                                        style={{
                                          fontSize: '10.5px',
                                          padding: '2px 6px',
                                          borderRadius: '4px',
                                          background: 'var(--color-surface-secondary)',
                                          color: 'var(--color-text-secondary)',
                                          border: '1px solid var(--color-border-subtle)',
                                          maxWidth: '100%',
                                          wordBreak: 'break-word',
                                          overflowWrap: 'anywhere',
                                        }}
                                      >
                                        {col}
                                      </span>
                                    ))}
                                  </div>
                                )}
                              </div>
                            );
                          })
                        )}
                      </div>

                      {/* Right: Targets B */}
                      <div
                        style={{
                          padding: '16px',
                          borderRadius: '8px',
                          background: 'var(--color-surface-secondary)',
                          border: '1px solid var(--color-border-subtle)',
                          display: 'flex',
                          flexDirection: 'column',
                          gap: '10px',
                          minWidth: 0,
                          maxWidth: '100%',
                          boxSizing: 'border-box',
                        }}
                      >
                        <div style={{ fontSize: '13px', fontWeight: '700', color: 'var(--color-text)', minWidth: 0, wordBreak: 'break-word', overflowWrap: 'anywhere' }}>
                          {wfB_name} ({targetsB.length} target{targetsB.length !== 1 ? 's' : ''})
                        </div>
                        {targetsB.length === 0 ? (
                          <div style={{ fontSize: '12px', color: 'var(--color-text-muted)' }}>No production deliverables configured</div>
                        ) : (
                          targetsB.map((tgt, idx) => {
                            const isMatch = normA.has(normalizeItem(tgt));
                            const schema = selectedCandidate.output_evidence.output_schemas[tgt] || [];
                            return (
                              <div
                                key={idx}
                                style={{
                                  padding: '10px 12px',
                                  borderRadius: '6px',
                                  background: isMatch ? 'rgba(234, 179, 8, 0.08)' : 'var(--color-surface)',
                                  border: isMatch ? '1.5px solid rgba(234, 179, 8, 0.45)' : '1px solid var(--color-border-subtle)',
                                  display: 'flex',
                                  flexDirection: 'column',
                                  gap: '6px',
                                  minWidth: 0,
                                  maxWidth: '100%',
                                  boxSizing: 'border-box',
                                }}
                              >
                                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '8px', minWidth: 0 }}>
                                  <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontWeight: '700', fontSize: '12.5px', color: isMatch ? '#facc15' : 'var(--color-text)', minWidth: 0, flex: 1, wordBreak: 'break-word', overflowWrap: 'anywhere' }}>
                                    <Target size={13} style={{ flexShrink: 0 }} color={isMatch ? '#facc15' : 'var(--color-text-muted)'} />
                                    <span style={{ minWidth: 0, wordBreak: 'break-word', overflowWrap: 'anywhere' }}>{tgt}</span>
                                  </div>
                                  {isMatch ? (
                                    <span style={{ flexShrink: 0, fontSize: '10px', fontWeight: '800', background: 'rgba(234, 179, 8, 0.22)', color: '#facc15', padding: '2px 6px', borderRadius: '4px' }}>
                                      Matching Target
                                    </span>
                                  ) : (
                                    <span style={{ flexShrink: 0, fontSize: '10px', fontWeight: '600', color: 'var(--color-text-muted)' }}>
                                      Distinct Output
                                    </span>
                                  )}
                                </div>
                                {schema.length > 0 && (
                                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: '5px', marginTop: '2px', minWidth: 0 }}>
                                    {schema.map((col) => (
                                      <span
                                        key={col}
                                        style={{
                                          fontSize: '10.5px',
                                          padding: '2px 6px',
                                          borderRadius: '4px',
                                          background: 'var(--color-surface-secondary)',
                                          color: 'var(--color-text-secondary)',
                                          border: '1px solid var(--color-border-subtle)',
                                          maxWidth: '100%',
                                          wordBreak: 'break-word',
                                          overflowWrap: 'anywhere',
                                        }}
                                      >
                                        {col}
                                      </span>
                                    ))}
                                  </div>
                                )}
                              </div>
                            );
                          })
                        )}
                      </div>
                    </div>
                  </div>
                );
              }

              if (activeEvidenceMetric === 'frequency') {
                const freqA = selectedCandidate.frequencies_by_workflow?.[wfA_name] || workflowMap.get(wfA_id)?.frequency || 'Not documented';
                const freqB = selectedCandidate.frequencies_by_workflow?.[wfB_name] || workflowMap.get(wfB_id)?.frequency || 'Not documented';
                const isMatchingFreq = freqA.toLowerCase() === freqB.toLowerCase() && freqA.toLowerCase() !== 'not documented';

                return (
                  <div>
                    <div
                      style={{
                        fontSize: '11px',
                        fontWeight: '700',
                        textTransform: 'uppercase',
                        letterSpacing: '0.08em',
                        color: 'var(--color-text-muted)',
                        marginBottom: '8px',
                      }}
                    >
                      OPERATIONAL EXECUTION FREQUENCY (YELLOW = MATCHING SCHEDULE)
                    </div>
                    <div style={{ display: 'grid', gridTemplateColumns: 'minmax(0, 1fr) minmax(0, 1fr)', gap: '16px' }}>
                      {/* Workflow A Frequency */}
                      <div
                        style={{
                          padding: '16px',
                          borderRadius: '8px',
                          background: isMatchingFreq ? 'rgba(234, 179, 8, 0.08)' : 'var(--color-surface-secondary)',
                          border: isMatchingFreq ? '1.5px solid rgba(234, 179, 8, 0.45)' : '1px solid var(--color-border-subtle)',
                          display: 'flex',
                          flexDirection: 'column',
                          gap: '8px',
                          minWidth: 0,
                          maxWidth: '100%',
                          boxSizing: 'border-box',
                        }}
                      >
                        <div style={{ fontSize: '13px', fontWeight: '700', color: 'var(--color-text)', minWidth: 0, wordBreak: 'break-word', overflowWrap: 'anywhere' }}>
                          {wfA_name}
                        </div>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', minWidth: 0 }}>
                          <Clock size={16} style={{ flexShrink: 0 }} color={isMatchingFreq ? '#facc15' : 'var(--color-text-muted)'} />
                          <span style={{ fontSize: '15px', fontWeight: '700', color: isMatchingFreq ? '#facc15' : 'var(--color-text)', minWidth: 0, wordBreak: 'break-word', overflowWrap: 'anywhere' }}>
                            {freqA}
                          </span>
                        </div>
                        <div style={{ fontSize: '11px', color: isMatchingFreq ? '#facc15' : 'var(--color-text-muted)' }}>
                          {isMatchingFreq ? 'Matching Operational Schedule' : 'Schedule Mismatch'}
                        </div>
                      </div>

                      {/* Workflow B Frequency */}
                      <div
                        style={{
                          padding: '16px',
                          borderRadius: '8px',
                          background: isMatchingFreq ? 'rgba(234, 179, 8, 0.08)' : 'var(--color-surface-secondary)',
                          border: isMatchingFreq ? '1.5px solid rgba(234, 179, 8, 0.45)' : '1px solid var(--color-border-subtle)',
                          display: 'flex',
                          flexDirection: 'column',
                          gap: '8px',
                          minWidth: 0,
                          maxWidth: '100%',
                          boxSizing: 'border-box',
                        }}
                      >
                        <div style={{ fontSize: '13px', fontWeight: '700', color: 'var(--color-text)', minWidth: 0, wordBreak: 'break-word', overflowWrap: 'anywhere' }}>
                          {wfB_name}
                        </div>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', minWidth: 0 }}>
                          <Clock size={16} style={{ flexShrink: 0 }} color={isMatchingFreq ? '#facc15' : 'var(--color-text-muted)'} />
                          <span style={{ fontSize: '15px', fontWeight: '700', color: isMatchingFreq ? '#facc15' : 'var(--color-text)', minWidth: 0, wordBreak: 'break-word', overflowWrap: 'anywhere' }}>
                            {freqB}
                          </span>
                        </div>
                        <div style={{ fontSize: '11px', color: isMatchingFreq ? '#facc15' : 'var(--color-text-muted)' }}>
                          {isMatchingFreq ? 'Matching Operational Schedule' : 'Schedule Mismatch'}
                        </div>
                      </div>
                    </div>
                  </div>
                );
              }

              if (activeEvidenceMetric === 'logic') {
                const transA = (selectedCandidate.transformations_by_workflow?.[wfA_name] || []).filter(isMeaningfulEvidence);
                const transB = (selectedCandidate.transformations_by_workflow?.[wfB_name] || []).filter(isMeaningfulEvidence);
                const sharedList = (selectedCandidate.shared_logic || []).filter(isMeaningfulEvidence);
                const sharedSet = new Set(sharedList.map((s) => s.toLowerCase().trim()));

                const validUnique: Record<string, string[]> = {};
                for (const [wfName, items] of Object.entries(selectedCandidate.unique_functionality || {})) {
                  if (Array.isArray(items)) {
                    const filtered = items.filter(isMeaningfulEvidence);
                    if (filtered.length > 0) {
                      validUnique[wfName] = filtered;
                    }
                  }
                }

                return (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                    <div>
                      <div
                        style={{
                          fontSize: '11px',
                          fontWeight: '700',
                          textTransform: 'uppercase',
                          letterSpacing: '0.08em',
                          color: 'var(--color-text-muted)',
                          marginBottom: '8px',
                        }}
                      >
                        OPERATIONAL LOGIC & TRANSFORMATIONS (YELLOW = SHARED / EQUIVALENT)
                      </div>

                      <div style={{ display: 'grid', gridTemplateColumns: 'minmax(0, 1fr) minmax(0, 1fr)', gap: '16px' }}>
                        {/* Left: Logic A */}
                        <div
                          style={{
                            padding: '16px',
                            borderRadius: '8px',
                            background: 'var(--color-surface-secondary)',
                            border: '1px solid var(--color-border-subtle)',
                            display: 'flex',
                            flexDirection: 'column',
                            gap: '8px',
                            minWidth: 0,
                            maxWidth: '100%',
                            boxSizing: 'border-box',
                          }}
                        >
                          <div style={{ fontSize: '13px', fontWeight: '700', color: 'var(--color-text)', minWidth: 0, wordBreak: 'break-word', overflowWrap: 'anywhere' }}>
                            {wfA_name} ({transA.length} operation{transA.length !== 1 ? 's' : ''})
                          </div>
                          {transA.length === 0 ? (
                            <div style={{ fontSize: '12px', color: 'var(--color-text-muted)' }}>No transformation steps recorded</div>
                          ) : (
                            transA.map((op, idx) => {
                              const isMatch = sharedSet.has(op.toLowerCase().trim()) || transB.some((b) => b.toLowerCase().trim() === op.toLowerCase().trim());
                              return (
                                <div
                                  key={idx}
                                  style={{
                                    padding: '8px 12px',
                                    borderRadius: '6px',
                                    background: isMatch ? 'rgba(234, 179, 8, 0.08)' : 'var(--color-surface)',
                                    border: isMatch ? '1.5px solid rgba(234, 179, 8, 0.45)' : '1px solid var(--color-border-subtle)',
                                    display: 'flex',
                                    alignItems: 'center',
                                    justifyContent: 'space-between',
                                    gap: '8px',
                                    minWidth: 0,
                                    maxWidth: '100%',
                                    boxSizing: 'border-box',
                                  }}
                                >
                                  <span style={{ fontSize: '12px', color: isMatch ? '#facc15' : 'var(--color-text)', fontWeight: isMatch ? '700' : '400', minWidth: 0, wordBreak: 'break-word', overflowWrap: 'anywhere' }}>
                                    {op}
                                  </span>
                                  {isMatch && (
                                    <span style={{ flexShrink: 0, fontSize: '10px', fontWeight: '800', background: 'rgba(234, 179, 8, 0.22)', color: '#facc15', padding: '2px 6px', borderRadius: '4px' }}>
                                      Shared
                                    </span>
                                  )}
                                </div>
                              );
                            })
                          )}
                        </div>

                        {/* Right: Logic B */}
                        <div
                          style={{
                            padding: '16px',
                            borderRadius: '8px',
                            background: 'var(--color-surface-secondary)',
                            border: '1px solid var(--color-border-subtle)',
                            display: 'flex',
                            flexDirection: 'column',
                            gap: '8px',
                            minWidth: 0,
                            maxWidth: '100%',
                            boxSizing: 'border-box',
                          }}
                        >
                          <div style={{ fontSize: '13px', fontWeight: '700', color: 'var(--color-text)', minWidth: 0, wordBreak: 'break-word', overflowWrap: 'anywhere' }}>
                            {wfB_name} ({transB.length} operation{transB.length !== 1 ? 's' : ''})
                          </div>
                          {transB.length === 0 ? (
                            <div style={{ fontSize: '12px', color: 'var(--color-text-muted)' }}>No transformation steps recorded</div>
                          ) : (
                            transB.map((op, idx) => {
                              const isMatch = sharedSet.has(op.toLowerCase().trim()) || transA.some((a) => a.toLowerCase().trim() === op.toLowerCase().trim());
                              return (
                                <div
                                  key={idx}
                                  style={{
                                    padding: '8px 12px',
                                    borderRadius: '6px',
                                    background: isMatch ? 'rgba(234, 179, 8, 0.08)' : 'var(--color-surface)',
                                    border: isMatch ? '1.5px solid rgba(234, 179, 8, 0.45)' : '1px solid var(--color-border-subtle)',
                                    display: 'flex',
                                    alignItems: 'center',
                                    justifyContent: 'space-between',
                                    gap: '8px',
                                    minWidth: 0,
                                    maxWidth: '100%',
                                    boxSizing: 'border-box',
                                  }}
                                >
                                  <span style={{ fontSize: '12px', color: isMatch ? '#facc15' : 'var(--color-text)', fontWeight: isMatch ? '700' : '400', minWidth: 0, wordBreak: 'break-word', overflowWrap: 'anywhere' }}>
                                    {op}
                                  </span>
                                  {isMatch && (
                                    <span style={{ flexShrink: 0, fontSize: '10px', fontWeight: '800', background: 'rgba(234, 179, 8, 0.22)', color: '#facc15', padding: '2px 6px', borderRadius: '4px' }}>
                                      Shared
                                    </span>
                                  )}
                                </div>
                              );
                            })
                          )}
                        </div>
                      </div>
                    </div>

                    {/* Unique Functionality Breakdown */}
                    {Object.keys(validUnique).length > 0 && (
                      <div>
                        <div
                          style={{
                            fontSize: '11px',
                            fontWeight: '700',
                            textTransform: 'uppercase',
                            letterSpacing: '0.08em',
                            color: 'var(--color-text-muted)',
                            marginBottom: '8px',
                          }}
                        >
                          UNIQUE WORKFLOW FUNCTIONALITY
                        </div>
                        <div
                          style={{
                            display: 'flex',
                            flexDirection: 'column',
                            gap: '10px',
                          }}
                        >
                          {Object.entries(validUnique).map(([wfName, items]) => (
                            <UniqueWorkflowList key={wfName} wfName={wfName} items={items} />
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                );
              }

              if (activeEvidenceMetric === 'dag') {
                const summaryA = wfA_id ? workflowMap.get(wfA_id) : null;
                const summaryB = wfB_id ? workflowMap.get(wfB_id) : null;

                return (
                  <div>
                    <div
                      style={{
                        fontSize: '11px',
                        fontWeight: '700',
                        textTransform: 'uppercase',
                        letterSpacing: '0.08em',
                        color: 'var(--color-text-muted)',
                        marginBottom: '8px',
                      }}
                    >
                      DAG TOPOLOGY & COMPLEXITY ATTRIBUTES
                    </div>
                    <div style={{ display: 'grid', gridTemplateColumns: 'minmax(0, 1fr) minmax(0, 1fr)', gap: '16px' }}>
                      {/* Left: DAG A */}
                      <div
                        style={{
                          padding: '16px',
                          borderRadius: '8px',
                          background: 'var(--color-surface-secondary)',
                          border: '1px solid var(--color-border-subtle)',
                          display: 'flex',
                          flexDirection: 'column',
                          gap: '10px',
                          minWidth: 0,
                          maxWidth: '100%',
                          boxSizing: 'border-box',
                        }}
                      >
                        <div style={{ fontSize: '13px', fontWeight: '700', color: 'var(--color-text)', minWidth: 0, wordBreak: 'break-word', overflowWrap: 'anywhere' }}>
                          {wfA_name}
                        </div>
                        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px' }}>
                          <div style={{ padding: '8px', background: 'var(--color-surface)', borderRadius: '6px' }}>
                            <div style={{ fontSize: '11px', color: 'var(--color-text-muted)' }}>Nodes / Tools</div>
                            <div style={{ fontSize: '15px', fontWeight: '700', color: 'var(--color-text)' }}>{summaryA?.node_count ?? 'N/A'}</div>
                          </div>
                          <div style={{ padding: '8px', background: 'var(--color-surface)', borderRadius: '6px' }}>
                            <div style={{ fontSize: '11px', color: 'var(--color-text-muted)' }}>Connections</div>
                            <div style={{ fontSize: '15px', fontWeight: '700', color: 'var(--color-text)' }}>{summaryA?.connection_count ?? 'N/A'}</div>
                          </div>
                          <div style={{ padding: '8px', background: 'var(--color-surface)', borderRadius: '6px' }}>
                            <div style={{ fontSize: '11px', color: 'var(--color-text-muted)' }}>Complexity</div>
                            <div style={{ fontSize: '13px', fontWeight: '700', color: 'var(--color-text)' }}>{summaryA?.complexity_level ?? 'LOW'}</div>
                          </div>
                          <div style={{ padding: '8px', background: 'var(--color-surface)', borderRadius: '6px' }}>
                            <div style={{ fontSize: '11px', color: 'var(--color-text-muted)' }}>Criticality</div>
                            <div style={{ fontSize: '13px', fontWeight: '700', color: 'var(--color-text)' }}>{summaryA?.criticality_level ?? 'LOW'}</div>
                          </div>
                        </div>
                      </div>

                      {/* Right: DAG B */}
                      <div
                        style={{
                          padding: '16px',
                          borderRadius: '8px',
                          background: 'var(--color-surface-secondary)',
                          border: '1px solid var(--color-border-subtle)',
                          display: 'flex',
                          flexDirection: 'column',
                          gap: '10px',
                          minWidth: 0,
                          maxWidth: '100%',
                          boxSizing: 'border-box',
                        }}
                      >
                        <div style={{ fontSize: '13px', fontWeight: '700', color: 'var(--color-text)', minWidth: 0, wordBreak: 'break-word', overflowWrap: 'anywhere' }}>
                          {wfB_name}
                        </div>
                        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px' }}>
                          <div style={{ padding: '8px', background: 'var(--color-surface)', borderRadius: '6px' }}>
                            <div style={{ fontSize: '11px', color: 'var(--color-text-muted)' }}>Nodes / Tools</div>
                            <div style={{ fontSize: '15px', fontWeight: '700', color: 'var(--color-text)' }}>{summaryB?.node_count ?? 'N/A'}</div>
                          </div>
                          <div style={{ padding: '8px', background: 'var(--color-surface)', borderRadius: '6px' }}>
                            <div style={{ fontSize: '11px', color: 'var(--color-text-muted)' }}>Connections</div>
                            <div style={{ fontSize: '15px', fontWeight: '700', color: 'var(--color-text)' }}>{summaryB?.connection_count ?? 'N/A'}</div>
                          </div>
                          <div style={{ padding: '8px', background: 'var(--color-surface)', borderRadius: '6px' }}>
                            <div style={{ fontSize: '11px', color: 'var(--color-text-muted)' }}>Complexity</div>
                            <div style={{ fontSize: '13px', fontWeight: '700', color: 'var(--color-text)' }}>{summaryB?.complexity_level ?? 'LOW'}</div>
                          </div>
                          <div style={{ padding: '8px', background: 'var(--color-surface)', borderRadius: '6px' }}>
                            <div style={{ fontSize: '11px', color: 'var(--color-text-muted)' }}>Criticality</div>
                            <div style={{ fontSize: '13px', fontWeight: '700', color: 'var(--color-text)' }}>{summaryB?.criticality_level ?? 'LOW'}</div>
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                );
              }

              return null;
            })()}

            {/* Why This Recommendation */}
            <div>
              <div
                style={{
                  fontSize: '11px',
                  fontWeight: '700',
                  textTransform: 'uppercase',
                  letterSpacing: '0.08em',
                  color: 'var(--color-text-muted)',
                  marginBottom: '6px',
                }}
              >
                RECOMMENDATION RATIONALE
              </div>
              <p
                style={{
                  fontSize: '14px',
                  lineHeight: '1.6',
                  color: 'var(--color-text)',
                  margin: 0,
                  padding: '14px 16px',
                  borderRadius: '8px',
                  background: 'var(--color-surface-secondary)',
                  border: '1px solid var(--color-border-subtle)',
                }}
              >
                {selectedCandidate.reasoning}
              </p>
            </div>

            {/* Validation Requirements Checklist */}
            {selectedCandidate.validation_requirements.length > 0 && (
              <div>
                <div
                  style={{
                    fontSize: '11px',
                    fontWeight: '700',
                    textTransform: 'uppercase',
                    letterSpacing: '0.08em',
                    color: 'var(--color-text-muted)',
                    marginBottom: '8px',
                  }}
                >
                  PRE-DECOMMISSIONING & EXECUTION VALIDATION CHECKLIST
                </div>
                <div
                  style={{
                    display: 'flex',
                    flexDirection: 'column',
                    gap: '6px',
                    padding: '14px 16px',
                    borderRadius: '8px',
                    background: 'var(--color-surface-secondary)',
                    border: '1px solid var(--color-border-subtle)',
                  }}
                >
                  {selectedCandidate.validation_requirements.map((req, idx) => (
                    <div
                      key={idx}
                      style={{
                        display: 'flex',
                        alignItems: 'flex-start',
                        gap: '8px',
                        fontSize: '12.5px',
                        color: 'var(--color-text-secondary)',
                      }}
                    >
                      <Check size={14} color="var(--color-primary)" style={{ flexShrink: 0, marginTop: '2px' }} />
                      <span>{req}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Modal Footer */}
            <div
              style={{
                display: 'flex',
                justifyContent: 'flex-end',
                borderTop: '1px solid var(--color-border-subtle)',
                paddingTop: '16px',
              }}
            >
              <button
                onClick={() => setSelectedCandidate(null)}
                style={{
                  padding: '8px 20px',
                  borderRadius: 'var(--radius-sm)',
                  background: 'var(--color-surface-secondary)',
                  border: '1px solid var(--color-border)',
                  color: 'var(--color-text)',
                  fontSize: '13px',
                  fontWeight: '700',
                  cursor: 'pointer',
                }}
              >
                Close Analysis
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
