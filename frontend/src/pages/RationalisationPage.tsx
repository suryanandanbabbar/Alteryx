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
  CheckCircle2,
  ExternalLink,
  X,
  RefreshCw,
  Cpu,
  Database,
  Target,
  Check,
  Sparkles,
} from 'lucide-react';
import {
  RationalisationAnalysisDTO,
  RationalisationCandidateDTO,
  PortfolioWorkflowSummaryDTO,
} from '../types/portfolio';
import { apiClient } from '../api/client';
import { getLevelBadgeStyle } from './PortfolioPage';

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
      if (activeTab !== 'ALL' && c.recommendation_type !== activeTab) {
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

  const counts = analysis?.recommendation_counts || {
    CONSOLIDATE: 0,
    RETIRE_CANDIDATE: 0,
    SHARED_LOGIC: 0,
    REVIEW: 0,
  };

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

  const getScoreColor = (score: number) => {
    if (score >= 70) return '#34d399';
    if (score >= 45) return '#fbbf24';
    return '#38bdf8';
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
          ETL RATIONALISATION
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
                  SHARED LOGIC
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
                { key: 'SHARED_LOGIC', label: 'Shared Logic', count: counts.SHARED_LOGIC || 0 },
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
                const scoreColor = getScoreColor(cand.opportunity_score);

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

                        {/* Opportunity Score Chip */}
                        <span
                          style={{
                            display: 'inline-flex',
                            alignItems: 'center',
                            gap: '6px',
                            padding: '4px 10px',
                            borderRadius: '6px',
                            fontSize: '11px',
                            fontWeight: '700',
                            background: 'var(--color-surface-secondary)',
                            border: '1px solid var(--color-border)',
                            color: 'var(--color-text-secondary)',
                          }}
                        >
                          <span style={{ color: 'var(--color-text-muted)' }}>Opportunity Score:</span>
                          <span style={{ color: scoreColor, fontWeight: '800' }}>
                            {cand.opportunity_score.toFixed(0)}/100
                          </span>
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
                                    C: {summary.complexity_level || 'LOW'}
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
                                    K: {summary.criticality_level || 'LOW'}
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
                        { label: 'Source Overlap', value: cand.deterministic_metrics.source_overlap },
                        { label: 'Target Overlap', value: cand.deterministic_metrics.target_overlap },
                        { label: 'Logic Similarity', value: cand.deterministic_metrics.transformation_similarity },
                        { label: 'DAG Similarity', value: cand.deterministic_metrics.dag_similarity },
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
                        WHY IT MATTERS
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

                    {/* Proposed Action */}
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
                        PROPOSED ACTION
                      </div>
                      <p
                        style={{
                          fontSize: '13px',
                          lineHeight: '1.5',
                          color: 'var(--color-text)',
                          fontWeight: '500',
                          margin: 0,
                        }}
                      >
                        {cand.proposed_strategy}
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

                        {cand.shared_logic.length > 0 && (
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
                            {cand.shared_logic.length} Shared Operation
                            {cand.shared_logic.length > 1 ? 's' : ''}
                          </span>
                        )}
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

                  <span
                    style={{
                      fontSize: '11px',
                      fontWeight: '700',
                      color: getScoreColor(selectedCandidate.opportunity_score),
                    }}
                  >
                    Score: {selectedCandidate.opportunity_score.toFixed(0)}/100
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
                            Complexity: {summary.complexity_level || 'LOW'} ({summary.complexity_score ?? 0}/100)
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
                            Criticality: {summary.criticality_level || 'LOW'} ({summary.criticality_score ?? 0}/100)
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

            {/* Similarity Metrics Breakdown */}
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
                CANONICAL SIMILARITY EVIDENCE
              </div>
              <div
                style={{
                  display: 'grid',
                  gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))',
                  gap: '12px',
                  padding: '16px',
                  borderRadius: '8px',
                  background: 'var(--color-surface-secondary)',
                  border: '1px solid var(--color-border-subtle)',
                }}
              >
                {[
                  {
                    label: 'Source Overlap',
                    val: selectedCandidate.deterministic_metrics.source_overlap,
                  },
                  {
                    label: 'Target Overlap',
                    val: selectedCandidate.deterministic_metrics.target_overlap,
                  },
                  {
                    label: 'Transformation Logic',
                    val: selectedCandidate.deterministic_metrics.transformation_similarity,
                  },
                  {
                    label: 'Output Schema Overlap',
                    val: selectedCandidate.deterministic_metrics.schema_similarity,
                  },
                  {
                    label: 'Output Grain Alignment',
                    val: selectedCandidate.deterministic_metrics.grain_similarity,
                  },
                  {
                    label: 'DAG Topology Similarity',
                    val: selectedCandidate.deterministic_metrics.dag_similarity,
                  },
                ].map((m) => {
                  const pct = Math.round(m.val * 100);
                  const fillColor = pct >= 70 ? '#34d399' : pct >= 40 ? '#fbbf24' : '#38bdf8';
                  return (
                    <div key={m.label} style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                      <div
                        style={{
                          display: 'flex',
                          justifyContent: 'space-between',
                          fontSize: '11px',
                          color: 'var(--color-text-secondary)',
                        }}
                      >
                        <span>{m.label}</span>
                        <span style={{ fontWeight: '700', color: 'var(--color-text)' }}>{pct}%</span>
                      </div>
                      <div
                        style={{
                          height: '5px',
                          borderRadius: '3px',
                          background: 'rgba(255, 255, 255, 0.08)',
                          overflow: 'hidden',
                        }}
                      >
                        <div
                          style={{
                            width: `${pct}%`,
                            height: '100%',
                            background: fillColor,
                            borderRadius: '3px',
                          }}
                        />
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Shared Logic Operations */}
            {selectedCandidate.shared_logic.length > 0 && (
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
                  SHARED OPERATIONAL LOGIC
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
                  {selectedCandidate.shared_logic.map((item, idx) => (
                    <div
                      key={idx}
                      style={{
                        display: 'flex',
                        alignItems: 'flex-start',
                        gap: '8px',
                        fontSize: '13px',
                        color: 'var(--color-text)',
                      }}
                    >
                      <CheckCircle2 size={15} color="#34d399" style={{ flexShrink: 0, marginTop: '2px' }} />
                      <span>{item}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Unique Functionality Breakdown */}
            {Object.keys(selectedCandidate.unique_functionality).length > 0 && (
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
                  {Object.entries(selectedCandidate.unique_functionality).map(([wfName, items]) => (
                    <div
                      key={wfName}
                      style={{
                        padding: '12px 16px',
                        borderRadius: '8px',
                        background: 'var(--color-surface-secondary)',
                        border: '1px solid var(--color-border-subtle)',
                      }}
                    >
                      <div
                        style={{
                          fontSize: '12.5px',
                          fontWeight: '700',
                          color: 'var(--color-primary)',
                          marginBottom: '6px',
                        }}
                      >
                        {wfName} Unique Operations:
                      </div>
                      {items.length > 0 ? (
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                          {items.map((it, i) => (
                            <div
                              key={i}
                              style={{
                                fontSize: '12.5px',
                                color: 'var(--color-text-secondary)',
                                paddingLeft: '12px',
                                position: 'relative',
                              }}
                            >
                              • {it}
                            </div>
                          ))}
                        </div>
                      ) : (
                        <div style={{ fontSize: '12px', color: 'var(--color-text-muted)', fontStyle: 'italic' }}>
                          No unique transformation operations detected. All logic is duplicated or shared.
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}

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
                EXECUTIVE RATIONALE
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

            {/* Proposed Strategy */}
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
                PROPOSED MIGRATION & RATIONALISATION STRATEGY
              </div>
              <p
                style={{
                  fontSize: '13.5px',
                  lineHeight: '1.55',
                  color: 'var(--color-text)',
                  fontWeight: '500',
                  margin: 0,
                  padding: '14px 16px',
                  borderRadius: '8px',
                  background: 'var(--color-surface-secondary)',
                  border: '1px solid var(--color-border-subtle)',
                }}
              >
                {selectedCandidate.proposed_strategy}
              </p>
            </div>

            {/* Retirement Safety Warning (if RETIRE_CANDIDATE) */}
            {selectedCandidate.recommendation_type === 'RETIRE_CANDIDATE' && (
              <div
                style={{
                  padding: '16px 20px',
                  borderRadius: '8px',
                  background: 'rgba(245, 158, 11, 0.1)',
                  border: '1px solid rgba(245, 158, 11, 0.35)',
                  display: 'flex',
                  alignItems: 'flex-start',
                  gap: '12px',
                }}
              >
                <AlertTriangle size={20} color="#fbbf24" style={{ flexShrink: 0, marginTop: '2px' }} />
                <div>
                  <div
                    style={{
                      fontSize: '13px',
                      fontWeight: '800',
                      color: '#fbbf24',
                      marginBottom: '4px',
                    }}
                  >
                    Retirement is not authorised.
                  </div>
                  <div
                    style={{
                      fontSize: '12.5px',
                      lineHeight: '1.5',
                      color: 'var(--color-text-secondary)',
                    }}
                  >
                    This is a retirement candidate only. Validate scheduling, ownership, downstream consumers,
                    and operational dependencies before retiring the workflow.
                  </div>
                </div>
              </div>
            )}

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
