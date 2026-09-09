import React, { useState, useEffect, useMemo } from 'react';
import {
  ArrowLeft,
  ChevronDown,
  FolderKanban,
  FileText,
  Activity,
  Cpu,
  ExternalLink,
} from 'lucide-react';
import {
  EvaluationModelDTO,
  EvaluationModelsDTO,
  PortfolioOverviewDTO,
  PortfolioWorkflowSummaryDTO,
} from '../types/portfolio';
import { apiClient } from '../api/client';
import { EvaluationModelDonutChart } from '../components/EvaluationModelDonutChart';
import { getLevelBadgeStyle } from './PortfolioPage';

const DEFAULT_COMPLEXITY_MODEL: EvaluationModelDTO = {
  model_name: 'Complexity Evaluation Model',
  description: 'How the overall complexity score is weighted',
  total_weight_pct: 100,
  factors: [
    {
      id: 'size',
      name: 'Structural Size',
      weight_pct: 20,
      description: 'Evaluates total tools, total connections, and distinct tool types.',
    },
    {
      id: 'transformation',
      name: 'Transformation Complexity',
      weight_pct: 25,
      description: 'Evaluates tool operational weights based on transformation semantics.',
    },
    {
      id: 'topology',
      name: 'DAG Topology Complexity',
      weight_pct: 25,
      description: 'Evaluates branch points, merge points, and maximum DAG path depth.',
    },
    {
      id: 'expression',
      name: 'Expression Complexity',
      weight_pct: 15,
      description: 'Evaluates total formula/filter expressions, conditional logic blocks, and expression length.',
    },
    {
      id: 'runtime',
      name: 'Runtime & Integration Complexity',
      weight_pct: 15,
      description: 'Evaluates scripts (Python/R), macro dependencies, dynamic connectors, and database connections.',
    },
  ],
};

const DEFAULT_CRITICALITY_MODEL: EvaluationModelDTO = {
  model_name: 'Criticality Evaluation Model',
  description: 'How the overall criticality score is weighted',
  technical_weight_pct: 60,
  operational_weight_pct: 40,
  total_weight_pct: 100,
  factors: [
    {
      id: 'downstream_outputs',
      name: 'Downstream outputs',
      category: 'Technical',
      weight_pct: 20,
      description: 'Number of production targets produced.',
    },
    {
      id: 'upstream_sources',
      name: 'Upstream sources',
      category: 'Technical',
      weight_pct: 20,
      description: 'Number of distinct source datasets consumed.',
    },
    {
      id: 'etl_consumers',
      name: 'Consuming ETL workflows',
      category: 'Technical',
      weight_pct: 20,
      description: 'Number of other workflows in the estate consuming outputs from this workflow.',
    },
    {
      id: 'last_run',
      name: 'Last Run',
      category: 'Operational',
      weight_pct: 20,
      description: 'Recency in operational metadata.',
    },
    {
      id: 'frequency',
      name: 'Frequency',
      category: 'Operational',
      weight_pct: 20,
      description: 'Scheduled execution interval.',
    },
  ],
};

interface ComplexityCriticalityPageProps {
  portfolio: PortfolioOverviewDTO;
  onBackToPortfolio: () => void;
  onSelectWorkflow?: (workflowId: string, businessArea?: string) => void | Promise<void>;
}

export const ComplexityCriticalityPage: React.FC<ComplexityCriticalityPageProps> = ({
  portfolio,
  onBackToPortfolio,
  onSelectWorkflow,
}) => {
  const [evaluationModels, setEvaluationModels] = useState<EvaluationModelsDTO>({
    complexity: DEFAULT_COMPLEXITY_MODEL,
    criticality: DEFAULT_CRITICALITY_MODEL,
  });

  useEffect(() => {
    apiClient
      .getEvaluationModels()
      .then((models) => {
        if (models && models.complexity && models.criticality) {
          setEvaluationModels(models);
        }
      })
      .catch(() => {
        // Retain canonical defaults
      });
  }, []);

  const successfulWorkflows = useMemo(() => {
    return (portfolio.workflows || []).filter((w) => w.status === 'SUCCESS');
  }, [portfolio.workflows]);

  const [selectedWorkflowId, setSelectedWorkflowId] = useState<string>(
    successfulWorkflows.length > 0 ? successfulWorkflows[0].workflow_id : ''
  );

  const selectedWorkflow: PortfolioWorkflowSummaryDTO | undefined = useMemo(() => {
    return successfulWorkflows.find((w) => w.workflow_id === selectedWorkflowId) || successfulWorkflows[0];
  }, [successfulWorkflows, selectedWorkflowId]);


  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '28px', maxWidth: '1400px', width: '100%', margin: '0 auto' }}>
      {/* 1. Header Hierarchy Section */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '12px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <span
              style={{
                fontSize: '11px',
                fontWeight: '800',
                textTransform: 'uppercase',
                letterSpacing: '0.14em',
                color: 'var(--color-primary)',
              }}
            >
              ETL WORKFLOW INVENTORY
            </span>
            <span style={{ color: 'var(--color-text-muted)', fontSize: '12px' }}>•</span>
            <span
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '5px',
                padding: '2px 8px',
                borderRadius: '20px',
                fontSize: '11px',
                fontWeight: '600',
                background: 'rgba(56, 189, 248, 0.1)',
                color: '#38bdf8',
                border: '1px solid rgba(56, 189, 248, 0.25)',
              }}
            >
              <FolderKanban size={12} />
              {portfolio.portfolio_name || 'Portfolio Estate'}
            </span>
          </div>

          <button
            onClick={onBackToPortfolio}
            className="btn-secondary"
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '6px',
              padding: '6px 12px',
              fontSize: '12px',
              fontWeight: '600',
              borderRadius: 'var(--radius-sm, 6px)',
              cursor: 'pointer',
            }}
          >
            <ArrowLeft size={14} />
            <span>Back to Inventory</span>
          </button>
        </div>

        <h1
          style={{
            fontSize: '24px',
            fontWeight: '800',
            color: 'var(--color-text)',
            letterSpacing: '-0.02em',
            lineHeight: '1.2',
            margin: '2px 0 0 0',
          }}
        >
          Complexity &amp; Criticality
        </h1>

        <p
          style={{
            fontSize: '14px',
            color: 'var(--color-text-secondary)',
            lineHeight: '1.5',
            margin: 0,
            maxWidth: '960px',
          }}
        >
          Understand how the project's actual complexity and criticality classifications are derived from workflow evidence.
        </p>
      </div>

      {/* 2. Dedicated Workflow Selector Card */}
      {successfulWorkflows.length > 0 && (
        <div
          style={{
            background: 'var(--color-surface)',
            border: '1px solid var(--color-border)',
            borderRadius: 'var(--radius-md, 8px)',
            padding: '20px 24px',
            display: 'flex',
            flexDirection: 'column',
            gap: '14px',
            boxShadow: '0 1px 3px rgba(0, 0, 0, 0.05)',
          }}
        >
          <div style={{ display: 'flex', flexDirection: 'column', gap: '3px' }}>
            <span style={{ fontSize: '11px', fontWeight: '800', textTransform: 'uppercase', letterSpacing: '0.1em', color: 'var(--color-primary)' }}>
              WORKFLOW EVIDENCE
            </span>
            <span style={{ fontSize: '13px', color: 'var(--color-text-muted)' }}>
              Select a workflow to see how the actual evaluation logic applies.
            </span>
          </div>

          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              flexWrap: 'wrap',
              gap: '16px',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px', flex: 1, minWidth: '320px', maxWidth: '640px' }}>
              <FileText size={18} color="var(--color-primary)" style={{ flexShrink: 0 }} />
              <div style={{ position: 'relative', width: '100%' }}>
                <select
                  value={selectedWorkflow?.workflow_id || ''}
                  onChange={(e) => setSelectedWorkflowId(e.target.value)}
                  style={{
                    width: '100%',
                    padding: '9px 36px 9px 14px',
                    fontSize: '13.5px',
                    fontWeight: '600',
                    color: 'var(--color-text)',
                    background: 'var(--color-surface-secondary)',
                    border: '1px solid var(--color-border)',
                    borderRadius: 'var(--radius-sm, 6px)',
                    appearance: 'none',
                    cursor: 'pointer',
                    outline: 'none',
                  }}
                >
                  {successfulWorkflows.map((wf) => (
                    <option key={wf.workflow_id} value={wf.workflow_id}>
                      {wf.filename} ({wf.business_area_tag || wf.business_area?.business_area || 'Other / Unclassified'})
                    </option>
                  ))}
                </select>
                <ChevronDown
                  size={14}
                  color="var(--color-text-muted)"
                  style={{ position: 'absolute', right: '12px', top: '50%', transform: 'translateY(-50%)', pointerEvents: 'none' }}
                />
              </div>
            </div>

            {selectedWorkflow && (
              <div style={{ display: 'flex', alignItems: 'center', gap: '14px', flexWrap: 'wrap' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <span style={{ fontSize: '11.5px', fontWeight: '700', color: 'var(--color-text-muted)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
                    Complexity:
                  </span>
                  <span
                    style={{
                      fontSize: '11.5px',
                      fontWeight: '800',
                      letterSpacing: '0.04em',
                      padding: '3px 8px',
                      borderRadius: '4px',
                      ...getLevelBadgeStyle(selectedWorkflow.complexity_level || 'LOW'),
                    }}
                  >
                    {selectedWorkflow.complexity_level || 'LOW'}
                    {selectedWorkflow.complexity_score !== undefined && ` (${selectedWorkflow.complexity_score.toFixed(1)})`}
                  </span>
                </div>

                <div style={{ width: '1px', height: '18px', background: 'var(--color-border)' }} />

                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <span style={{ fontSize: '11.5px', fontWeight: '700', color: 'var(--color-text-muted)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
                    Criticality:
                  </span>
                  <span
                    style={{
                      fontSize: '11.5px',
                      fontWeight: '800',
                      letterSpacing: '0.04em',
                      padding: '3px 8px',
                      borderRadius: '4px',
                      ...getLevelBadgeStyle(selectedWorkflow.criticality_level || 'LOW'),
                    }}
                  >
                    {selectedWorkflow.criticality_level || 'LOW'}
                    {selectedWorkflow.criticality_score !== undefined && ` (${selectedWorkflow.criticality_score.toFixed(1)})`}
                  </span>
                </div>

                {onSelectWorkflow && (
                  <button
                    onClick={() => onSelectWorkflow(selectedWorkflow.workflow_id, selectedWorkflow.business_area_tag || selectedWorkflow.business_area?.business_area)}
                    className="btn-primary"
                    style={{
                      display: 'inline-flex',
                      alignItems: 'center',
                      gap: '6px',
                      padding: '7px 14px',
                      fontSize: '12px',
                      fontWeight: '600',
                      borderRadius: 'var(--radius-sm, 6px)',
                      cursor: 'pointer',
                    }}
                  >
                    <span>Inspect Workflow</span>
                    <ExternalLink size={12} />
                  </button>
                )}
              </div>
            )}
          </div>
        </div>
      )}

      {/* 3. Two-Column Layout: Left = COMPLEXITY, Right = CRITICALITY */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(480px, 1fr))',
          gap: '24px',
          alignItems: 'stretch',
        }}
      >
        {/* ================================================================= */}
        {/* LEFT COLUMN: COMPLEXITY                                          */}
        {/* ================================================================= */}
        <div
          style={{
            background: 'var(--color-surface)',
            border: '1px solid var(--color-border)',
            borderRadius: 'var(--radius-lg, 10px)',
            padding: '24px',
            display: 'flex',
            flexDirection: 'column',
            gap: '20px',
            boxShadow: '0 1px 4px rgba(0, 0, 0, 0.06)',
          }}
        >
          {/* Top Row: Icon, Title, Description, Level Badge */}
          <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: '16px' }}>
            <div style={{ display: 'flex', alignItems: 'flex-start', gap: '12px' }}>
              <div
                style={{
                  width: '36px',
                  height: '36px',
                  borderRadius: 'var(--radius-sm, 6px)',
                  background: 'rgba(249, 115, 22, 0.12)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  color: 'var(--color-primary)',
                  flexShrink: 0,
                }}
              >
                <Cpu size={20} />
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
                <span style={{ fontSize: '11px', fontWeight: '800', letterSpacing: '0.12em', color: 'var(--color-primary)', textTransform: 'uppercase' }}>
                  COMPLEXITY
                </span>
                <span style={{ fontSize: '13px', color: 'var(--color-text-secondary)', fontWeight: '600' }}>
                  Deterministic Multi-Dimensional Architecture Evaluation
                </span>
              </div>
            </div>

            {selectedWorkflow && (
              <span
                style={{
                  fontSize: '11px',
                  fontWeight: '800',
                  letterSpacing: '0.06em',
                  padding: '4px 10px',
                  borderRadius: '4px',
                  whiteSpace: 'nowrap',
                  ...getLevelBadgeStyle(selectedWorkflow.complexity_level || 'LOW'),
                }}
              >
                {selectedWorkflow.complexity_level || 'LOW'} LEVEL
              </span>
            )}
          </div>

          <div style={{ height: '1px', background: 'var(--color-border)', margin: '0' }} />

          {/* Section: Evaluation Model */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
            <span style={{ fontSize: '11px', fontWeight: '800', textTransform: 'uppercase', letterSpacing: '0.08em', color: 'var(--color-text-muted)' }}>
              EVALUATION MODEL
            </span>

            <ul style={{ margin: 0, paddingLeft: '18px', display: 'flex', flexDirection: 'column', gap: '8px', fontSize: '13px', color: 'var(--color-text-secondary)', lineHeight: '1.5' }}>
              <li>
                <strong style={{ color: 'var(--color-text)' }}>Zero LLM involvement:</strong> Purely deterministic, objective, and reproducible evaluation calculated directly from workflow AST and canonical IR.
              </li>
              <li>
                <strong style={{ color: 'var(--color-text)' }}>Structural Size (20% weight):</strong> Evaluates total tools, total connections and distinct tool types.
              </li>
              <li>
                <strong style={{ color: 'var(--color-text)' }}>Transformation Complexity (25% weight):</strong> Evaluates tool operational weights based on transformation semantics:
                <ul style={{ margin: '4px 0 0 0', paddingLeft: '16px', display: 'flex', flexDirection: 'column', gap: '2px', fontSize: '12px', color: 'var(--color-text-muted)' }}>
                  <li>Weight 1: Basic pass-through, field renaming, sorting, sampling (Select, Filter, Sort, Sample, Unique, DbFileInput, DbFileOutput, Browse)</li>
                  <li>Weight 2: Expressions, formatting, and aggregations (Formula, Summarize, RegEx, DateTime, TextToColumns, AutoField)</li>
                  <li>Weight 3: Relational restructuring &amp; multi-stream joins (Join, Union, JoinMultiple, AppendFields, FindReplace, RunningTotal)</li>
                  <li>Weight 4: Pivoting, transpose, and advanced multi-row/field logic (CrossTab, Transpose, MultiRowFormula, MultiFieldFormula, Tile)</li>
                  <li>Weight 5: Dynamic execution, macros &amp; scripting (DynamicInput, DynamicOutput, Macro, Python, R)</li>
                </ul>
              </li>
              <li>
                <strong style={{ color: 'var(--color-text)' }}>DAG Topology Complexity (25% weight):</strong> Evaluates branch points, merge points and maximum DAG path depth.
              </li>
              <li>
                <strong style={{ color: 'var(--color-text)' }}>Expression Complexity (15% weight):</strong> Evaluates total formula/filter expressions, conditional logic blocks and expression character length.
              </li>
              <li>
                <strong style={{ color: 'var(--color-text)' }}>Runtime &amp; Integration Complexity (15% weight):</strong> Evaluates Python / R scripts, macro dependencies, dynamic data connectors and database connections.
              </li>
              <li>
                <strong style={{ color: 'var(--color-text)' }}>Calibration Thresholds:</strong> Normalized score bounded between [0.0, 100.0]:
                <ul style={{ margin: '4px 0 0 0', paddingLeft: '16px', display: 'flex', flexDirection: 'column', gap: '2px', fontSize: '12px', color: 'var(--color-text-muted)' }}>
                  <li><span style={{ color: '#22c55e', fontWeight: '700' }}>HIGH</span></li>
                  <li><span style={{ color: '#fbbf24', fontWeight: '700' }}>MEDIUM</span></li>
                  <li><span style={{ color: '#ef4444', fontWeight: '700' }}>LOW</span></li>
                </ul>
              </li>
            </ul>

            {/* Complexity Evaluation Model Donut Chart */}
            <EvaluationModelDonutChart
              title={evaluationModels.complexity.model_name}
              subtitle={evaluationModels.complexity.description || 'How the overall complexity score is weighted'}
              factors={evaluationModels.complexity.factors}
              totalWeightPct={evaluationModels.complexity.total_weight_pct}
              themeVariant="complexity"
            />
          </div>

          <div style={{ height: '1px', background: 'var(--color-border)', margin: '0' }} />

          {/* Section: Selected Workflow Evidence */}
          {selectedWorkflow && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '14px', flex: 1 }}>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
                <span style={{ fontSize: '11px', fontWeight: '800', textTransform: 'uppercase', letterSpacing: '0.08em', color: 'var(--color-text-muted)' }}>
                  SELECTED WORKFLOW EVIDENCE
                </span>
                <span style={{ fontSize: '12.5px', fontWeight: '700', color: 'var(--color-text)' }}>
                  {selectedWorkflow.filename}
                </span>
              </div>

              {/* Group A: Structural Evidence */}
              <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                <span style={{ fontSize: '11px', fontWeight: '700', textTransform: 'uppercase', letterSpacing: '0.06em', color: 'var(--color-text-muted)' }}>
                  Structural Evidence
                </span>
                <ul style={{ margin: 0, paddingLeft: '18px', display: 'flex', flexDirection: 'column', gap: '4px', fontSize: '12.5px', color: 'var(--color-text-secondary)', lineHeight: '1.45' }}>
                  <li><strong style={{ color: 'var(--color-text)' }}>Assessed Level:</strong> {selectedWorkflow.complexity_level || 'LOW'}</li>
                  <li><strong style={{ color: 'var(--color-text)' }}>Tool Count:</strong> {selectedWorkflow.node_count} tools</li>
                  <li><strong style={{ color: 'var(--color-text)' }}>Connection Count:</strong> {selectedWorkflow.connection_count} connections</li>
                  <li><strong style={{ color: 'var(--color-text)' }}>I/O Metrics:</strong> {selectedWorkflow.source_count} input source(s), {selectedWorkflow.target_count} production target(s)</li>
                </ul>
              </div>

              {/* Group B: Transformation & Topology Evidence */}
              <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                <span style={{ fontSize: '11px', fontWeight: '700', textTransform: 'uppercase', letterSpacing: '0.06em', color: 'var(--color-text-muted)' }}>
                  Transformation &amp; Topology Evidence
                </span>
                <ul style={{ margin: 0, paddingLeft: '18px', display: 'flex', flexDirection: 'column', gap: '4px', fontSize: '12.5px', color: 'var(--color-text-secondary)', lineHeight: '1.45' }}>
                  {selectedWorkflow.complexity_factors && selectedWorkflow.complexity_factors.length > 0 ? (
                    selectedWorkflow.complexity_factors.map((factor, idx) => (
                      <li key={idx}>
                        <strong style={{ color: 'var(--color-text)' }}>Extracted Factor:</strong> {factor}
                      </li>
                    ))
                  ) : (
                    <li>
                      <strong style={{ color: 'var(--color-text)' }}>Extracted Factors:</strong> Standard linear ETL pipeline structure.
                    </li>
                  )}
                  {selectedWorkflow.tool_types && selectedWorkflow.tool_types.length > 0 && (
                    <li>
                      <strong style={{ color: 'var(--color-text)' }}>Tool Distribution:</strong> {Array.from(new Set(selectedWorkflow.tool_types)).join(', ')} ({selectedWorkflow.tool_types.length} total instances)
                    </li>
                  )}
                </ul>
              </div>
            </div>
          )}

          <div style={{ height: '1px', background: 'var(--color-border)', margin: '0' }} />

          {/* Restrained Score Footer Bar */}
          {selectedWorkflow && (
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                padding: '12px 16px',
                background: 'var(--color-surface-secondary)',
                borderRadius: 'var(--radius-sm, 6px)',
                border: '1px solid var(--color-border)',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'baseline', gap: '6px' }}>
                <span style={{ fontSize: '11px', fontWeight: '700', textTransform: 'uppercase', letterSpacing: '0.08em', color: 'var(--color-text-muted)' }}>
                  SCORE:
                </span>
                <span style={{ fontSize: '16px', fontWeight: '800', color: 'var(--color-text)' }}>
                  {selectedWorkflow.complexity_score !== undefined ? selectedWorkflow.complexity_score.toFixed(1) : '0.0'} / 100
                </span>
              </div>

              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <span style={{ fontSize: '11px', fontWeight: '700', textTransform: 'uppercase', letterSpacing: '0.08em', color: 'var(--color-text-muted)' }}>
                  CLASSIFICATION:
                </span>
                <span
                  style={{
                    fontSize: '11px',
                    fontWeight: '800',
                    letterSpacing: '0.06em',
                    padding: '3px 8px',
                    borderRadius: '4px',
                    ...getLevelBadgeStyle(selectedWorkflow.complexity_level || 'LOW'),
                  }}
                >
                  {selectedWorkflow.complexity_level || 'LOW'}
                </span>
              </div>
            </div>
          )}
        </div>

        {/* ================================================================= */}
        {/* RIGHT COLUMN: CRITICALITY                                         */}
        {/* ================================================================= */}
        <div
          style={{
            background: 'var(--color-surface)',
            border: '1px solid var(--color-border)',
            borderRadius: 'var(--radius-lg, 10px)',
            padding: '24px',
            display: 'flex',
            flexDirection: 'column',
            gap: '20px',
            boxShadow: '0 1px 4px rgba(0, 0, 0, 0.06)',
          }}
        >
          {/* Top Row: Icon, Title, Description, Level Badge */}
          <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: '16px' }}>
            <div style={{ display: 'flex', alignItems: 'flex-start', gap: '12px' }}>
              <div
                style={{
                  width: '36px',
                  height: '36px',
                  borderRadius: 'var(--radius-sm, 6px)',
                  background: 'rgba(56, 189, 248, 0.12)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  color: '#38bdf8',
                  flexShrink: 0,
                }}
              >
                <Activity size={20} />
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
                <span style={{ fontSize: '11px', fontWeight: '800', letterSpacing: '0.12em', color: '#38bdf8', textTransform: 'uppercase' }}>
                  CRITICALITY
                </span>
                <span style={{ fontSize: '13px', color: 'var(--color-text-secondary)', fontWeight: '600' }}>
                  Deterministic 5-Factor Technical &amp; Operational Framework
                </span>
              </div>
            </div>

            {selectedWorkflow && (
              <span
                style={{
                  fontSize: '11px',
                  fontWeight: '800',
                  letterSpacing: '0.06em',
                  padding: '4px 10px',
                  borderRadius: '4px',
                  whiteSpace: 'nowrap',
                  ...getLevelBadgeStyle(selectedWorkflow.criticality_level || 'LOW'),
                }}
              >
                {selectedWorkflow.criticality_level || 'LOW'} LEVEL
              </span>
            )}
          </div>

          <div style={{ height: '1px', background: 'var(--color-border)', margin: '0' }} />

          {/* Section: Evaluation Model */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
            <span style={{ fontSize: '11px', fontWeight: '800', textTransform: 'uppercase', letterSpacing: '0.08em', color: 'var(--color-text-muted)' }}>
              EVALUATION MODEL
            </span>

            <ul style={{ margin: 0, paddingLeft: '18px', display: 'flex', flexDirection: 'column', gap: '8px', fontSize: '13px', color: 'var(--color-text-secondary)', lineHeight: '1.5' }}>
              <li>
                <strong style={{ color: 'var(--color-text)' }}>Zero LLM involvement:</strong> 100% deterministic, reproducible, and auditable calculation across exactly 5 factors.
              </li>
              <li>
                <strong style={{ color: 'var(--color-text)' }}>Technical Factors (60% Subtotal):</strong>
                <ul style={{ margin: '4px 0 0 0', paddingLeft: '16px', display: 'flex', flexDirection: 'column', gap: '2px', fontSize: '12px', color: 'var(--color-text-muted)' }}>
                  <li><strong style={{ color: 'var(--color-text)' }}>Downstream outputs (20% weight):</strong> Number of production targets produced.</li>
                  <li><strong style={{ color: 'var(--color-text)' }}>Upstream sources (20% weight):</strong> Number of distinct source datasets consumed.</li>
                  <li><strong style={{ color: 'var(--color-text)' }}>Consuming ETL workflows (20% weight):</strong> Number of other workflows in the estate consuming outputs from this workflow.</li>
                </ul>
              </li>
              <li>
                <strong style={{ color: 'var(--color-text)' }}>Operational Factors (40% Subtotal):</strong>
                <ul style={{ margin: '4px 0 0 0', paddingLeft: '16px', display: 'flex', flexDirection: 'column', gap: '2px', fontSize: '12px', color: 'var(--color-text-muted)' }}>
                  <li><strong style={{ color: 'var(--color-text)' }}>Last Run (20% weight):</strong> Recency in operational metadata.</li>
                  <li><strong style={{ color: 'var(--color-text)' }}>Frequency (20% weight):</strong> Scheduled interval.</li>
                </ul>
              </li>
              <li>
                <strong style={{ color: 'var(--color-text)' }}>Evidence Integrity:</strong> Missing or undocumented operational metadata is never fabricated and defaults strictly to 0.0 with clear label.
              </li>
              <li>
                <strong style={{ color: 'var(--color-text)' }}>Calibration Thresholds:</strong> Bounded score between [0.0, 100.0]:
                <ul style={{ margin: '4px 0 0 0', paddingLeft: '16px', display: 'flex', flexDirection: 'column', gap: '2px', fontSize: '12px', color: 'var(--color-text-muted)' }}>
                  <li><span style={{ color: '#22c55e', fontWeight: '700' }}>HIGH</span></li>
                  <li><span style={{ color: '#fbbf24', fontWeight: '700' }}>MEDIUM</span></li>
                  <li><span style={{ color: '#ef4444', fontWeight: '700' }}>LOW</span></li>
                </ul>
              </li>
              <li>
                <em style={{ color: 'var(--color-text)', fontSize: '12px' }}>
                  * Business impact factors can be added further once the information about downstream targets/consumers is available
                </em>
              </li>
            </ul>

            {/* Criticality Evaluation Model Donut Chart */}
            <EvaluationModelDonutChart
              title={evaluationModels.criticality.model_name}
              subtitle={evaluationModels.criticality.description || 'How the overall criticality score is weighted'}
              factors={evaluationModels.criticality.factors}
              totalWeightPct={evaluationModels.criticality.total_weight_pct}
              technicalWeightPct={evaluationModels.criticality.technical_weight_pct || 60}
              operationalWeightPct={evaluationModels.criticality.operational_weight_pct || 40}
              themeVariant="criticality"
            />
          </div>

          <div style={{ height: '1px', background: 'var(--color-border)', margin: '0' }} />

          {/* Section: Selected Workflow Evidence */}
          {selectedWorkflow && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '14px', flex: 1 }}>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
                <span style={{ fontSize: '11px', fontWeight: '800', textTransform: 'uppercase', letterSpacing: '0.08em', color: 'var(--color-text-muted)' }}>
                  SELECTED WORKFLOW EVIDENCE
                </span>
                <span style={{ fontSize: '12.5px', fontWeight: '700', color: 'var(--color-text)' }}>
                  {selectedWorkflow.filename}
                </span>
              </div>

              {/* Group A: Technical Evidence */}
              <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                <span style={{ fontSize: '11px', fontWeight: '700', textTransform: 'uppercase', letterSpacing: '0.06em', color: 'var(--color-text-muted)' }}>
                  Technical Factor Evidence
                </span>
                <ul style={{ margin: 0, paddingLeft: '18px', display: 'flex', flexDirection: 'column', gap: '4px', fontSize: '12.5px', color: 'var(--color-text-secondary)', lineHeight: '1.45' }}>
                  <li><strong style={{ color: 'var(--color-text)' }}>Assessed Level:</strong> {selectedWorkflow.criticality_level || 'LOW'}</li>
                  <li><strong style={{ color: 'var(--color-text)' }}>Downstream Outputs:</strong> {selectedWorkflow.target_count} production target(s) ({selectedWorkflow.targets?.join(', ') || 'None'})</li>
                  <li><strong style={{ color: 'var(--color-text)' }}>Upstream Sources:</strong> {selectedWorkflow.source_count} source dataset(s) ({selectedWorkflow.sources?.join(', ') || 'None'})</li>
                  <li><strong style={{ color: 'var(--color-text)' }}>Inspection Sinks:</strong> {selectedWorkflow.inspection_sinks?.length || 0} sink(s) ({selectedWorkflow.inspection_sinks?.join(', ') || 'None'})</li>
                </ul>
              </div>

              {/* Group B: Operational Evidence */}
              <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                <span style={{ fontSize: '11px', fontWeight: '700', textTransform: 'uppercase', letterSpacing: '0.06em', color: 'var(--color-text-muted)' }}>
                  Operational Factor Evidence
                </span>
                <ul style={{ margin: 0, paddingLeft: '18px', display: 'flex', flexDirection: 'column', gap: '4px', fontSize: '12.5px', color: 'var(--color-text-secondary)', lineHeight: '1.45' }}>
                  <li><strong style={{ color: 'var(--color-text)' }}>Last Run:</strong> {selectedWorkflow.last_run || 'Not documented'}</li>
                  <li><strong style={{ color: 'var(--color-text)' }}>Frequency:</strong> {selectedWorkflow.frequency || 'Not documented'}</li>
                </ul>
              </div>

              {/* Group C: Dependency & Impact Context */}
              {(selectedWorkflow.business_consequence || selectedWorkflow.dependency_impact || selectedWorkflow.migration_implication) && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                  <span style={{ fontSize: '11px', fontWeight: '700', textTransform: 'uppercase', letterSpacing: '0.06em', color: 'var(--color-text-muted)' }}>
                    Dependency &amp; Impact Context
                  </span>
                  <ul style={{ margin: 0, paddingLeft: '18px', display: 'flex', flexDirection: 'column', gap: '4px', fontSize: '12.5px', color: 'var(--color-text-secondary)', lineHeight: '1.45' }}>
                    {selectedWorkflow.business_consequence && (
                      <li><strong style={{ color: 'var(--color-text)' }}>Business Consequence:</strong> {selectedWorkflow.business_consequence}</li>
                    )}
                    {selectedWorkflow.dependency_impact && (
                      <li><strong style={{ color: 'var(--color-text)' }}>Dependency Impact:</strong> {selectedWorkflow.dependency_impact}</li>
                    )}
                    {selectedWorkflow.migration_implication && (
                      <li><strong style={{ color: 'var(--color-text)' }}>Migration Implication:</strong> {selectedWorkflow.migration_implication}</li>
                    )}
                  </ul>
                </div>
              )}
            </div>
          )}

          <div style={{ height: '1px', background: 'var(--color-border)', margin: '0' }} />

          {/* Restrained Score Footer Bar */}
          {selectedWorkflow && (
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                padding: '12px 16px',
                background: 'var(--color-surface-secondary)',
                borderRadius: 'var(--radius-sm, 6px)',
                border: '1px solid var(--color-border)',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'baseline', gap: '6px' }}>
                <span style={{ fontSize: '11px', fontWeight: '700', textTransform: 'uppercase', letterSpacing: '0.08em', color: 'var(--color-text-muted)' }}>
                  SCORE:
                </span>
                <span style={{ fontSize: '16px', fontWeight: '800', color: 'var(--color-text)' }}>
                  {selectedWorkflow.criticality_score !== undefined ? selectedWorkflow.criticality_score.toFixed(1) : '0.0'} / 100
                </span>
              </div>

              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <span style={{ fontSize: '11px', fontWeight: '700', textTransform: 'uppercase', letterSpacing: '0.08em', color: 'var(--color-text-muted)' }}>
                  CLASSIFICATION:
                </span>
                <span
                  style={{
                    fontSize: '11px',
                    fontWeight: '800',
                    letterSpacing: '0.06em',
                    padding: '3px 8px',
                    borderRadius: '4px',
                    ...getLevelBadgeStyle(selectedWorkflow.criticality_level || 'LOW'),
                  }}
                >
                  {selectedWorkflow.criticality_level || 'LOW'}
                </span>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
