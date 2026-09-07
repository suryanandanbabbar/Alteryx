import React, { useState, useEffect, useMemo } from 'react';
import {
  GitFork,
  Database,
  Target,
  ArrowRight,
  Cpu,
  Sparkles,
  FileSpreadsheet,
  FileCode,
  FileText,
  FolderKanban,
  BrainCircuit,
  Sliders,
  Share2,
  Boxes,
  LucideIcon,
  X,
  ChevronDown,
  ChevronUp,
  CheckCircle2,
  ExternalLink,
  Layers,
  ArrowLeft,
  Search,
} from 'lucide-react';
import { AnalysisOverviewDTO, BusinessStageDTO } from '../types/workflow';
import {
  PortfolioOverviewDTO,
  SharedDatasetDTO,
} from '../types/portfolio';

export interface ImpactAtAGlancePageProps {
  mode: 'workflow' | 'portfolio';
  overview?: AnalysisOverviewDTO | null;
  portfolio?: PortfolioOverviewDTO | null;
  onNavigateToSection?: (section: string) => void;
  onSelectWorkflow?: (workflowId: string, businessArea?: string) => void;
  onBackToPortfolio?: () => void;
  onOpenRationalisation?: () => void;
}

export type ModalType =
  | { kind: 'step'; stepNumber: 1 | 2 | 3 | 4 | 5 | 6 }
  | { kind: 'migration' }
  | { kind: 'workflows' }
  | { kind: 'targets' }
  | null;

export const ImpactAtAGlancePage: React.FC<ImpactAtAGlancePageProps> = ({
  mode,
  overview,
  portfolio,
  onNavigateToSection,
  onSelectWorkflow,
  onBackToPortfolio,
  onOpenRationalisation,
}) => {
  const [activeModal, setActiveModal] = useState<ModalType>(null);

  if (mode === 'workflow') {
    return (
      <WorkflowImpactView
        overview={overview}
        onNavigateToSection={onNavigateToSection}
        onBackToPortfolio={onBackToPortfolio}
      />
    );
  }

  return (
    <>
      <PortfolioImpactView
        portfolio={portfolio}
        onOpenRationalisation={onOpenRationalisation}
        onOpenModal={(modal) => setActiveModal(modal)}
      />

      {activeModal && portfolio && (
        <EvidenceModal
          activeModal={activeModal}
          portfolio={portfolio}
          onClose={() => setActiveModal(null)}
          onOpenRationalisation={onOpenRationalisation}
          onSelectWorkflow={onSelectWorkflow}
        />
      )}
    </>
  );
};

// ============================================================================
// PORTFOLIO ESTATE IMPACT VIEW
// ============================================================================

interface PortfolioImpactViewProps {
  portfolio?: PortfolioOverviewDTO | null;
  onOpenRationalisation?: () => void;
  onOpenModal: (modal: ModalType) => void;
}

const PortfolioImpactView: React.FC<PortfolioImpactViewProps> = ({
  portfolio,
  onOpenModal,
}) => {
  if (!portfolio) {
    return (
      <div style={{ padding: '40px', textAlign: 'center', color: 'var(--color-text-muted)' }}>
        No portfolio estate data available.
      </div>
    );
  }

  const { metrics, workflows = [], rationalisation_candidates = [], shared_sources = [], shared_targets = [] } = portfolio;
  const totalWorkflows = metrics?.total_workflows ?? workflows.length;
  const successfulWorkflows = metrics?.successful_workflows ?? workflows.filter((w) => w.status === 'SUCCESS').length;
  const totalTools = metrics?.total_tools ?? workflows.reduce((acc, w) => acc + (w.node_count || 0), 0);
  const totalConnections = workflows.reduce((acc, w) => acc + (w.connection_count || 0), 0);
  const totalSources = metrics?.total_sources ?? workflows.reduce((acc, w) => acc + (w.source_count || 0), 0);
  const uniqueSources = metrics?.unique_sources ?? totalSources;
  const totalTargets = metrics?.total_targets ?? workflows.reduce((acc, w) => acc + (w.target_count || 0), 0);
  const uniqueTargets = metrics?.unique_targets ?? totalTargets;
  const rationalisationCount = rationalisation_candidates.length;
  const totalSttmMappings = workflows.reduce((acc, w) => acc + (w.sttm_mappings_count || 0), 0);

  // Derive total process stages across all workflows
  const totalProcessStages = useMemo(() => {
    return workflows.reduce((acc, w) => {
      const stageCount = w.processing_stages && w.processing_stages.length > 0 ? w.processing_stages.length : (w.node_count > 0 ? 1 : 0);
      return acc + stageCount;
    }, 0);
  }, [workflows]);

  // Migration asset counts derived from runtime successful workflows
  const pythonAssetCount = successfulWorkflows;
  const jsonAssetCount = successfulWorkflows;
  const sttmAssetCount = workflows.filter((w) => (w.sttm_mappings_count || 0) > 0 || w.status === 'SUCCESS').length;
  const businessReportCount = successfulWorkflows;
  const toolSpecCount = successfulWorkflows;
  const completePackagesCount = successfulWorkflows;
  const totalArtifactsCount = pythonAssetCount + jsonAssetCount + sttmAssetCount + businessReportCount + toolSpecCount;

  // Tool distribution
  const toolDist = metrics?.tool_distribution || {};

  // Find strongest rationalisation candidate
  const strongestCandidate = useMemo(() => {
    return [...rationalisation_candidates].sort((a, b) => {
      if (a.recommendation_type === 'CONSOLIDATE' && b.recommendation_type !== 'CONSOLIDATE') return -1;
      if (b.recommendation_type === 'CONSOLIDATE' && a.recommendation_type !== 'CONSOLIDATE') return 1;
      return (b.opportunity_score || 0) - (a.opportunity_score || 0);
    })[0];
  }, [rationalisation_candidates]);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '28px', maxWidth: '1400px', margin: '0 auto' }}>
      {/* 1. Header / Hero Section (Restrained Enterprise Dashboard) */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
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
            IMPACT AT A GLANCE
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

        <h1
          style={{
            fontSize: '30px',
            fontWeight: '800',
            color: 'var(--color-text)',
            letterSpacing: '-0.02em',
            lineHeight: '1.2',
            margin: '2px 0 0 0',
          }}
        >
          ETL Portfolio Impact Summary
        </h1>

        <p
          style={{
            fontSize: '14.5px',
            lineHeight: '1.6',
            color: 'var(--color-text-secondary)',
            margin: '2px 0 0 0',
            maxWidth: '960px',
          }}
        >
          Quantitative synthesis of deep technical discovery, data ingestion, processing machinery, process stages, and migration assets automatically extracted across the entire workflow estate.
        </p>
      </div>

      {/* 2. Primary Impact — 6 Large KPI Cards */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(190px, 1fr))',
          gap: '14px',
        }}
      >
        <KpiCard
          label="Workflows Analysed"
          value={successfulWorkflows}
          subtext={`of ${totalWorkflows} Total Workflows`}
          icon={FolderKanban}
          color="#38bdf8"
          onClick={() => onOpenModal({ kind: 'workflows' })}
        />
        <KpiCard
          label="Tool Instances"
          value={totalTools}
          subtext="Extracted Operations"
          icon={Sliders}
          color="#fb923c"
          onClick={() => onOpenModal({ kind: 'step', stepNumber: 2 })}
        />
        <KpiCard
          label="Process Stages"
          value={totalProcessStages}
          subtext="Logical Pipelines"
          icon={Layers}
          color="#a855f7"
          onClick={() => onOpenModal({ kind: 'step', stepNumber: 3 })}
        />
        <KpiCard
          label="Input Sources"
          value={totalSources}
          subtext={`${uniqueSources} Unique Datasets`}
          icon={Database}
          color="#34d399"
          onClick={() => onOpenModal({ kind: 'step', stepNumber: 1 })}
        />
        <KpiCard
          label="Output Targets"
          value={totalTargets}
          subtext={`${uniqueTargets} Unique Outputs`}
          icon={Target}
          color="#eab308"
          onClick={() => onOpenModal({ kind: 'targets' })}
        />
        <KpiCard
          label="Rationalisation"
          value={rationalisationCount}
          subtext="Opportunities Identified"
          icon={Sparkles}
          color="#34d399"
          onClick={() => onOpenModal({ kind: 'step', stepNumber: 5 })}
        />
      </div>

      {/* 3. Migration & Documentation Assets Generated (Quantitative Strip) */}
      <div
        style={{
          background: 'var(--color-surface)',
          border: '1px solid var(--color-border)',
          borderRadius: 'var(--radius-md, 8px)',
          padding: '20px 24px',
          display: 'flex',
          flexDirection: 'column',
          gap: '16px',
        }}
      >
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '12px' }}>
          <div>
            <div style={{ fontSize: '11px', fontWeight: '800', color: 'var(--color-primary)', textTransform: 'uppercase', letterSpacing: '0.1em', marginBottom: '3px' }}>
              MIGRATION &amp; DOCUMENTATION OUTPUT
            </div>
            <div style={{ fontSize: '15px', fontWeight: '700', color: 'var(--color-text)' }}>
              {totalArtifactsCount} Structured Assets Generated Across {completePackagesCount} Workflows
            </div>
          </div>
          <button
            onClick={() => onOpenModal({ kind: 'migration' })}
            style={{
              background: 'var(--color-surface-secondary)',
              border: '1px solid var(--color-border)',
              borderRadius: 'var(--radius-sm, 4px)',
              padding: '6px 12px',
              fontSize: '12px',
              fontWeight: '600',
              color: 'var(--color-text)',
              cursor: 'pointer',
              display: 'inline-flex',
              alignItems: 'center',
              gap: '6px',
            }}
          >
            <span>View Asset Breakdown</span>
            <ArrowRight size={13} color="var(--color-primary)" />
          </button>
        </div>

        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(170px, 1fr))',
            gap: '10px',
          }}
        >
          <AssetCountCard count={pythonAssetCount} label="Python Translations" sub="Pandas / PySpark" icon={FileCode} />
          <AssetCountCard count={jsonAssetCount} label="JSON Graph IR" sub="Executable AST" icon={Boxes} />
          <AssetCountCard count={sttmAssetCount} label="STTM Matrices" sub="Source-to-Target XLSX" icon={FileSpreadsheet} />
          <AssetCountCard count={businessReportCount} label="Business Reports" sub="Executive DOCX" icon={FileText} />
          <AssetCountCard count={toolSpecCount} label="Tool Specifications" sub="Node Configuration DOCX" icon={Sliders} />
          <AssetCountCard
            count={completePackagesCount}
            label="Complete Packages"
            sub={`${completePackagesCount} of ${totalWorkflows} Workflows`}
            icon={CheckCircle2}
            highlight={true}
          />
        </div>
      </div>

      {/* 4. End-to-End Portfolio Discovery Lifecycle (6 Interactive Cards) */}
      <div
        style={{
          background: 'var(--color-surface)',
          border: '1px solid var(--color-border)',
          borderRadius: 'var(--radius-md, 8px)',
          padding: '24px',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '18px' }}>
          <div>
            <div style={{ fontSize: '11px', fontWeight: '800', color: 'var(--color-primary)', textTransform: 'uppercase', letterSpacing: '0.1em', marginBottom: '3px' }}>
              DISCOVERY LIFECYCLE
            </div>
            <h2 style={{ fontSize: '16px', fontWeight: '700', color: 'var(--color-text)', margin: 0 }}>
              End-to-End Portfolio Discovery Lifecycle
            </h2>
          </div>
          <span style={{ fontSize: '12px', color: 'var(--color-text-muted)' }}>
            Click any step to inspect workflow-level evidence
          </span>
        </div>

        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
            gap: '12px',
          }}
        >
          <InteractiveLifecycleStep
            stepNumber="01"
            title="Estate Data Ingestion"
            count={totalSources}
            countLabel="Input Sources"
            description="Catalogues all upstream databases, files, and incoming feeds across workflows"
            color="#38bdf8"
            onClick={() => onOpenModal({ kind: 'step', stepNumber: 1 })}
          />
          <InteractiveLifecycleStep
            stepNumber="02"
            title="Processing & Joins"
            count={totalTools}
            countLabel="Total Tools"
            description="Analyzes all join, formula, filter, and transformation nodes across files"
            color="#818cf8"
            onClick={() => onOpenModal({ kind: 'step', stepNumber: 2 })}
          />
          <InteractiveLifecycleStep
            stepNumber="03"
            title="Process Stages"
            count={totalProcessStages}
            countLabel="Process Stages"
            description="Logical processing stages and functional pipelines extracted from each workflow"
            color="#a855f7"
            onClick={() => onOpenModal({ kind: 'step', stepNumber: 3 })}
          />
          <InteractiveLifecycleStep
            stepNumber="04"
            title="Shared Overlaps"
            count={shared_sources.length + shared_targets.length}
            countLabel="Shared Datasets"
            description="Identifies identical datasets consumed or produced across multiple workflows"
            color="#fbbf24"
            onClick={() => onOpenModal({ kind: 'step', stepNumber: 4 })}
          />
          <InteractiveLifecycleStep
            stepNumber="05"
            title="Rationalisation"
            count={rationalisationCount}
            countLabel="Consolidations"
            description="Pinpoints duplicate pipelines and candidate merge opportunities deterministically"
            color="#34d399"
            onClick={() => onOpenModal({ kind: 'step', stepNumber: 5 })}
          />
          <InteractiveLifecycleStep
            stepNumber="06"
            title="Target Migration"
            count={completePackagesCount}
            countLabel="Migration Packages"
            description="Generates complete Python, JSON, STTM, and specification asset bundles"
            color="#10b981"
            onClick={() => onOpenModal({ kind: 'step', stepNumber: 6 })}
          />
        </div>
      </div>

      {/* 5. Domain Summary Cards (Summary Cards Only — No Popups / No Modal Triggers) */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(340px, 1fr))', gap: '16px' }}>
        {/* Domain 1: Technical Discovery */}
        <DomainSummaryCard
          domainNumber="01"
          title="Technical Discovery"
          icon={Cpu}
          color="#38bdf8"
          metrics={[
            { label: 'Analysed Workflows', value: `${successfulWorkflows} of ${totalWorkflows}`, detail: '100% automated AST workflow graph parsing' },
            { label: 'Total Tool Instances', value: `${totalTools} tools`, detail: 'Complete tool inventory across all files' },
            { label: 'Graph Dependencies', value: `${totalConnections} connections`, detail: 'Directed acyclic graph data pipelines' },
          ]}
        />

        {/* Domain 2: Data Flow & Lineage */}
        <DomainSummaryCard
          domainNumber="02"
          title="Data Flow & Lineage"
          icon={Share2}
          color="#a855f7"
          metrics={[
            { label: 'Unique Source Datasets', value: `${uniqueSources} sources`, detail: `${metrics?.shared_sources_count || shared_sources.length} shared across workflows` },
            { label: 'Unique Target Outputs', value: `${uniqueTargets} targets`, detail: `${metrics?.shared_targets_count || shared_targets.length} shared destination targets` },
            { label: 'Derived STTM Lineage', value: `${totalSttmMappings} mappings`, detail: 'Column-level transformation matrices' },
          ]}
        />

        {/* Domain 3: Rationalisation & Value */}
        <DomainSummaryCard
          domainNumber="03"
          title="Rationalisation & Value"
          icon={Sparkles}
          color="#34d399"
          metrics={[
            { label: 'Consolidation Opportunities', value: `${rationalisationCount} candidates`, detail: 'Strict deterministic rule matching' },
            { label: 'Highest Opportunity Score', value: `${strongestCandidate?.opportunity_score ?? 0}/100`, detail: 'Top candidate deduplication match' },
            { label: 'Estate XLSX Document', value: 'Ready for Export', detail: 'Full portfolio summary & lineage matrix' },
          ]}
        />
      </div>

      {/* 6. Processing Landscape (Tool Occurrence Distribution) */}
      {Object.keys(toolDist).length > 0 && (
        <div
          style={{
            background: 'var(--color-surface)',
            border: '1px solid var(--color-border)',
            borderRadius: 'var(--radius-md, 8px)',
            padding: '24px',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '16px' }}>
            <div>
              <div style={{ fontSize: '11px', fontWeight: '800', color: 'var(--color-primary)', textTransform: 'uppercase', letterSpacing: '0.1em', marginBottom: '3px' }}>
                PROCESSING LANDSCAPE
              </div>
              <h2 style={{ fontSize: '16px', fontWeight: '700', color: 'var(--color-text)', margin: 0 }}>
                Estate Tool Occurrence Distribution
              </h2>
            </div>
            <span style={{ fontSize: '12px', color: 'var(--color-text-muted)' }}>
              {Object.keys(toolDist).length} Distinct Tool Types
            </span>
          </div>

          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fill, minmax(160px, 1fr))',
              gap: '10px',
            }}
          >
            {Object.entries(toolDist)
              .sort((a, b) => b[1] - a[1])
              .map(([toolType, count]) => {
                const pct = Math.round((count / (totalTools || 1)) * 100);
                return (
                  <div
                    key={toolType}
                    style={{
                      background: 'var(--color-surface-secondary)',
                      border: '1px solid var(--color-border)',
                      borderRadius: 'var(--radius-sm, 6px)',
                      padding: '12px 14px',
                      display: 'flex',
                      flexDirection: 'column',
                      gap: '6px',
                    }}
                  >
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <span style={{ fontSize: '12.5px', fontWeight: '600', color: 'var(--color-text)' }}>
                        {toolType}
                      </span>
                      <span style={{ fontSize: '13px', fontWeight: '700', color: 'var(--color-primary)' }}>
                        {count}
                      </span>
                    </div>
                    <div style={{ width: '100%', height: '4px', background: 'var(--color-border)', borderRadius: '2px', overflow: 'hidden' }}>
                      <div
                        style={{
                          width: `${Math.min(100, Math.max(8, pct))}%`,
                          height: '100%',
                          background: 'var(--color-primary)',
                        }}
                      />
                    </div>
                    <div style={{ fontSize: '10.5px', color: 'var(--color-text-muted)', textAlign: 'right' }}>
                      {pct}% of estate
                    </div>
                  </div>
                );
              })}
          </div>
        </div>
      )}
    </div>
  );
};

// ============================================================================
// SINGLE WORKFLOW IMPACT VIEW
// ============================================================================

interface WorkflowImpactViewProps {
  overview?: AnalysisOverviewDTO | null;
  onNavigateToSection?: (section: string) => void;
  onBackToPortfolio?: () => void;
}

const WorkflowImpactView: React.FC<WorkflowImpactViewProps> = ({
  overview,
  onNavigateToSection,
  onBackToPortfolio,
}) => {
  if (!overview) {
    return (
      <div style={{ padding: '40px', textAlign: 'center', color: 'var(--color-text-muted)' }}>
        No workflow analysis data available.
      </div>
    );
  }

  const { metrics, business_summary, execution_order, source } = overview;
  const toolSupport = metrics.support_summary || {};
  const fullySupported = toolSupport['FULL'] || 0;
  const passThrough = toolSupport['PASS_THROUGH'] || 0;
  const totalTools = metrics.total_nodes || 0;
  const totalConnections = metrics.total_connections || 0;
  const inputCount = metrics.input_count || business_summary?.source_inputs?.length || 0;
  const outputCount = metrics.business_output_count || metrics.output_count || business_summary?.business_outputs?.length || 0;
  const stageCount = business_summary?.processing_stages?.length || metrics.container_count || 1;
  const lineageCount = business_summary?.lineage?.length || 0;
  const transformationCount = business_summary?.transformations?.length || 0;
  const businessRuleCount = business_summary?.business_rules?.length || 0;

  // Tool type counts derived from execution order
  const toolTypeCounts: Record<string, number> = {};
  (execution_order || []).forEach((step) => {
    const type = step.tool_type || 'Unknown';
    toolTypeCounts[type] = (toolTypeCounts[type] || 0) + 1;
  });

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '28px', maxWidth: '1400px', margin: '0 auto' }}>
      {/* 1. Header Navigation & Title */}
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
              WORKFLOW IMPACT AT A GLANCE
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
              <Sparkles size={12} />
              Deterministic Discovery + AI Semantics
            </span>
          </div>

          {onBackToPortfolio && (
            <button
              onClick={onBackToPortfolio}
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '6px',
                padding: '6px 12px',
                borderRadius: 'var(--radius-sm)',
                border: '1px solid var(--color-border)',
                background: 'var(--color-surface)',
                color: 'var(--color-text-secondary)',
                fontSize: '12px',
                fontWeight: '600',
                cursor: 'pointer',
              }}
            >
              <ArrowLeft size={14} /> Back to Portfolio
            </button>
          )}
        </div>

        <h1
          style={{
            fontSize: '30px',
            fontWeight: '800',
            color: 'var(--color-text)',
            letterSpacing: '-0.02em',
            lineHeight: '1.2',
            margin: '2px 0 0 0',
          }}
        >
          {source.original_filename}
        </h1>

        <p
          style={{
            fontSize: '14.5px',
            lineHeight: '1.6',
            color: 'var(--color-text-secondary)',
            margin: '2px 0 0 0',
            maxWidth: '960px',
          }}
        >
          {business_summary?.one_line_purpose ||
            'Deep technical discovery extracted node-level data transformations, end-to-end lineage links, business rules, and AI-assisted migration documentation.'}
        </p>
      </div>

      {/* 2. Top Quantity KPI Cards */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))',
          gap: '14px',
        }}
      >
        <KpiCard
          label="Data Sources"
          value={inputCount}
          subtext="Raw Ingest Feeds"
          icon={Database}
          color="#38bdf8"
          onClick={() => onNavigateToSection?.('overview')}
        />
        <KpiCard
          label="Processing Tools"
          value={totalTools}
          subtext="Node Graph Entities"
          icon={Sliders}
          color="#fb923c"
          onClick={() => onNavigateToSection?.('tools')}
        />
        <KpiCard
          label="Process Stages"
          value={stageCount}
          subtext="Logical Stages / Pipelines"
          icon={Layers}
          color="#a855f7"
          onClick={() => onNavigateToSection?.('overview')}
        />
        <KpiCard
          label="Lineage Mappings"
          value={lineageCount}
          subtext="Column-Level STTM"
          icon={Share2}
          color="#f43f5e"
          onClick={() => onNavigateToSection?.('overview')}
        />
        <KpiCard
          label="Business Outputs"
          value={outputCount}
          subtext="Published Deliverables"
          icon={Target}
          color="#eab308"
          onClick={() => onNavigateToSection?.('overview')}
        />
        <KpiCard
          label="Connections"
          value={totalConnections}
          subtext="Data-Flow Edges"
          icon={GitFork}
          color="#34d399"
          onClick={() => onNavigateToSection?.('diagram')}
        />
      </div>

      {/* 3. Single-Workflow Migration & Documentation Assets (Concrete Quantities) */}
      <div
        style={{
          background: 'var(--color-surface)',
          border: '1px solid var(--color-border)',
          borderRadius: 'var(--radius-md, 8px)',
          padding: '20px 24px',
          display: 'flex',
          flexDirection: 'column',
          gap: '16px',
        }}
      >
        <div>
          <div style={{ fontSize: '11px', fontWeight: '800', color: 'var(--color-primary)', textTransform: 'uppercase', letterSpacing: '0.1em', marginBottom: '3px' }}>
            MIGRATION &amp; DOCUMENTATION ASSETS
          </div>
          <div style={{ fontSize: '15px', fontWeight: '700', color: 'var(--color-text)' }}>
            5 Complete Workflow Assets Generated for Immediate Deployment
          </div>
        </div>

        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(170px, 1fr))',
            gap: '10px',
          }}
        >
          <AssetCountCard
            count={1}
            label="Python Translation"
            sub="Executable Pandas / PySpark"
            icon={FileCode}
            onClick={() => onNavigateToSection?.('python')}
          />
          <AssetCountCard
            count={1}
            label="JSON Representation"
            sub="Standard Intermediate Graph"
            icon={Boxes}
            onClick={() => onNavigateToSection?.('json')}
          />
          <AssetCountCard
            count={1}
            label="STTM Matrix"
            sub={`${lineageCount} Mappings in XLSX`}
            icon={FileSpreadsheet}
            onClick={() => onNavigateToSection?.('downloads')}
          />
          <AssetCountCard
            count={1}
            label="Business Report"
            sub="Executive Summary & Rules DOCX"
            icon={FileText}
            onClick={() => onNavigateToSection?.('downloads')}
          />
          <AssetCountCard
            count={1}
            label="Tool Specification"
            sub="Technical Node Inventory DOCX"
            icon={Sliders}
            onClick={() => onNavigateToSection?.('downloads')}
          />
        </div>
      </div>

      {/* 4. Concrete Value Chain: From Raw Data to Information */}
      <div
        style={{
          background: 'var(--color-surface)',
          border: '1px solid var(--color-border)',
          borderRadius: 'var(--radius-md, 8px)',
          padding: '24px',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '18px' }}>
          <div>
            <div style={{ fontSize: '11px', fontWeight: '800', color: 'var(--color-primary)', textTransform: 'uppercase', letterSpacing: '0.1em', marginBottom: '3px' }}>
              VALUE PROGRESSION
            </div>
            <h2 style={{ fontSize: '16px', fontWeight: '700', color: 'var(--color-text)', margin: 0 }}>
              From Raw Data to Business Information &amp; Migration Assets
            </h2>
          </div>
          <span style={{ fontSize: '12px', color: 'var(--color-text-muted)' }}>
            {stageCount} Logical Processing {stageCount === 1 ? 'Stage' : 'Stages'}
          </span>
        </div>

        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))',
            gap: '10px',
          }}
        >
          <ChainNode step="01" label={`${inputCount} Sources`} desc="Raw Ingest Feeds" color="#38bdf8" />
          <ChainNode step="02" label={`${totalTools} Tools`} desc="Extracted Operations" color="#818cf8" />
          <ChainNode step="03" label={`${stageCount} Process Stages`} desc="Functional Pipelines" color="#a855f7" />
          <ChainNode step="04" label={`${lineageCount} STTM Mappings`} desc="Column-Level Lineage" color="#f43f5e" />
          <ChainNode step="05" label={`${outputCount} Outputs`} desc="Business Deliverables" color="#eab308" />
          <ChainNode step="06" label="5 Migration Assets" desc="Python, JSON, Docs" color="#10b981" />
        </div>
      </div>

      {/* 5. Two-Column Intelligence Breakdown */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(450px, 1fr))', gap: '16px' }}>
        {/* Deterministic Discovery */}
        <div
          style={{
            background: 'var(--color-surface)',
            border: '1px solid var(--color-border)',
            borderRadius: 'var(--radius-md, 8px)',
            padding: '22px',
            display: 'flex',
            flexDirection: 'column',
            gap: '14px',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <div
              style={{
                width: '32px',
                height: '32px',
                borderRadius: '6px',
                background: 'rgba(56, 189, 248, 0.12)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: '#38bdf8',
              }}
            >
              <Cpu size={16} />
            </div>
            <div>
              <div style={{ fontSize: '11px', fontWeight: '800', color: '#38bdf8', textTransform: 'uppercase', letterSpacing: '0.06em' }}>
                Deterministic Discovery
              </div>
              <div style={{ fontSize: '14px', fontWeight: '700', color: 'var(--color-text)' }}>
                Exact AST Graph &amp; Node Topology
              </div>
            </div>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            <MetricRow label="Native Tool Support" value={`${fullySupported} Full / ${passThrough} Pass-Through`} detail={`${Math.round((fullySupported / (totalTools || 1)) * 100)}% native tool support`} />
            <MetricRow label="Graph Topology" value={`${totalTools} Nodes · ${totalConnections} Edges`} detail="Complete directed acyclic graph topology parsed" />
            <MetricRow label="Topological Pipeline" value={`${execution_order?.length || totalTools} Steps`} detail="Deterministic execution order computed" />
            <MetricRow label="Container Groupings" value={`${metrics.container_count || 0} Containers`} detail="Scope boundaries preserved" />
          </div>

          <div style={{ marginTop: 'auto', paddingTop: '12px', borderTop: '1px solid var(--color-border)' }}>
            <div style={{ fontSize: '11.5px', fontWeight: '600', color: 'var(--color-text-secondary)', marginBottom: '8px' }}>
              Extracted Tool Types
            </div>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
              {Object.entries(toolTypeCounts)
                .sort((a, b) => b[1] - a[1])
                .slice(0, 8)
                .map(([toolType, count]) => (
                  <span
                    key={toolType}
                    style={{
                      display: 'inline-flex',
                      alignItems: 'center',
                      gap: '5px',
                      padding: '3px 8px',
                      borderRadius: '4px',
                      background: 'var(--color-surface-secondary)',
                      border: '1px solid var(--color-border)',
                      fontSize: '11px',
                      color: 'var(--color-text)',
                    }}
                  >
                    <span>{toolType}</span>
                    <strong style={{ color: 'var(--color-primary)' }}>{count}</strong>
                  </span>
                ))}
            </div>
          </div>
        </div>

        {/* AI-Assisted Semantic Intelligence */}
        <div
          style={{
            background: 'var(--color-surface)',
            border: '1px solid var(--color-border)',
            borderRadius: 'var(--radius-md, 8px)',
            padding: '22px',
            display: 'flex',
            flexDirection: 'column',
            gap: '14px',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <div
              style={{
                width: '32px',
                height: '32px',
                borderRadius: '6px',
                background: 'rgba(168, 85, 247, 0.12)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: '#a855f7',
              }}
            >
              <Sparkles size={16} />
            </div>
            <div>
              <div style={{ fontSize: '11px', fontWeight: '800', color: '#a855f7', textTransform: 'uppercase', letterSpacing: '0.06em' }}>
                AI-Assisted Semantic Intelligence
              </div>
              <div style={{ fontSize: '14px', fontWeight: '700', color: 'var(--color-text)' }}>
                Functional Interpretation &amp; Lineage Semantics
              </div>
            </div>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            <MetricRow label="STTM Column Mappings" value={`${lineageCount} Mappings`} detail="Semantic column-level transformation rules mapped" />
            <MetricRow label="Business Purpose Synthesis" value="Generated" detail={business_summary?.one_line_purpose || 'Synthesized functional interpretation'} />
            <MetricRow label="Business Rules Discovered" value={`${businessRuleCount} Rules`} detail="Extracted decision rules and filter conditions" />
            <MetricRow label="Transformations Summarized" value={`${transformationCount} Transforms`} detail="Aggregated business logic interpretation" />
          </div>

          <div style={{ marginTop: 'auto', paddingTop: '12px', borderTop: '1px solid var(--color-border)' }}>
            <div style={{ fontSize: '11.5px', fontWeight: '600', color: 'var(--color-text-secondary)', marginBottom: '8px' }}>
              Instant Deliverables Ready
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(130px, 1fr))', gap: '6px' }}>
              <div style={{ fontSize: '11px', padding: '5px 8px', background: 'var(--color-surface-secondary)', borderRadius: '4px', border: '1px solid var(--color-border)' }}>
                Executive Summary
              </div>
              <div style={{ fontSize: '11px', padding: '5px 8px', background: 'var(--color-surface-secondary)', borderRadius: '4px', border: '1px solid var(--color-border)' }}>
                STTM Matrix (.xlsx)
              </div>
              <div style={{ fontSize: '11px', padding: '5px 8px', background: 'var(--color-surface-secondary)', borderRadius: '4px', border: '1px solid var(--color-border)' }}>
                Python Code (.py)
              </div>
              <div style={{ fontSize: '11px', padding: '5px 8px', background: 'var(--color-surface-secondary)', borderRadius: '4px', border: '1px solid var(--color-border)' }}>
                Tool Specs (.docx)
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* 6. Dynamic Executive Narrative */}
      <div
        style={{
          background: 'var(--color-surface-secondary)',
          border: '1px solid var(--color-border)',
          borderRadius: 'var(--radius-md, 8px)',
          padding: '16px 20px',
          display: 'flex',
          alignItems: 'center',
          gap: '14px',
        }}
      >
        <BrainCircuit size={22} color="var(--color-primary)" style={{ flexShrink: 0 }} />
        <div style={{ fontSize: '13px', color: 'var(--color-text-secondary)', lineHeight: 1.5 }}>
          From <strong style={{ color: 'var(--color-text)' }}>{totalTools}</strong> extracted processing tools across{' '}
          <strong style={{ color: 'var(--color-text)' }}>{inputCount}</strong> data inputs, the platform automatically derived{' '}
          <strong style={{ color: 'var(--color-text)' }}>{totalConnections}</strong> data-flow dependencies,{' '}
          <strong style={{ color: 'var(--color-text)' }}>{stageCount}</strong> logical process stages,{' '}
          <strong style={{ color: 'var(--color-text)' }}>{lineageCount}</strong> column-level lineage mappings, and{' '}
          <strong style={{ color: 'var(--color-text)' }}>{outputCount}</strong> final business deliverables with full AI-assisted semantic documentation.
        </div>
      </div>
    </div>
  );
};

// ============================================================================
// REUSABLE EVIDENCE MODAL (Centered, Accessible, Scrollable Evidence)
// ============================================================================

interface EvidenceModalProps {
  activeModal: NonNullable<ModalType>;
  portfolio: PortfolioOverviewDTO;
  onClose: () => void;
  onOpenRationalisation?: () => void;
  onSelectWorkflow?: (workflowId: string, businessArea?: string) => void;
}

const EvidenceModal: React.FC<EvidenceModalProps> = ({
  activeModal,
  portfolio,
  onClose,
  onOpenRationalisation,
  onSelectWorkflow,
}) => {
  const [expandedWorkflows, setExpandedWorkflows] = useState<Record<string, boolean>>({});
  const [expandedStages, setExpandedStages] = useState<Record<string, boolean>>({});
  const [showAllWorkflows, setShowAllWorkflows] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');

  // Close modal on Escape key
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        onClose();
      }
    };
    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [onClose]);

  const toggleWorkflow = (id: string) => {
    setExpandedWorkflows((prev) => ({ ...prev, [id]: !prev[id] }));
  };

  const toggleStage = (stageKey: string) => {
    setExpandedStages((prev) => ({ ...prev, [stageKey]: !prev[stageKey] }));
  };

  const { metrics, workflows = [], rationalisation_candidates = [], shared_sources = [], shared_targets = [] } = portfolio;
  const totalTools = metrics?.total_tools ?? workflows.reduce((acc, w) => acc + (w.node_count || 0), 0);
  const totalSources = metrics?.total_sources ?? workflows.reduce((acc, w) => acc + (w.source_count || 0), 0);
  const uniqueSources = metrics?.unique_sources ?? totalSources;
  const successfulWorkflows = metrics?.successful_workflows ?? workflows.filter((w) => w.status === 'SUCCESS').length;

  const totalProcessStages = useMemo(() => {
    return workflows.reduce((acc, w) => {
      const stageCount = w.processing_stages && w.processing_stages.length > 0 ? w.processing_stages.length : (w.node_count > 0 ? 1 : 0);
      return acc + stageCount;
    }, 0);
  }, [workflows]);

  const totalTargets = metrics?.total_targets ?? workflows.reduce((acc, w) => acc + (w.target_count || 0), 0);
  const uniqueTargets = metrics?.unique_targets ?? totalTargets;
  const totalWorkflows = metrics?.total_workflows ?? workflows.length;

  // Contextual search placeholder
  let searchPlaceholder = 'Filter evidence by workflow...';
  if (activeModal.kind === 'step') {
    switch (activeModal.stepNumber) {
      case 1:
        searchPlaceholder = 'Filter by workflow or source...';
        break;
      case 2:
        searchPlaceholder = 'Filter by workflow or tool...';
        break;
      case 3:
        searchPlaceholder = 'Filter by workflow or process stage...';
        break;
      case 4:
        searchPlaceholder = 'Filter by dataset or workflow...';
        break;
      case 5:
        searchPlaceholder = 'Filter by workflow or recommendation...';
        break;
      case 6:
        searchPlaceholder = 'Filter by workflow or asset...';
        break;
    }
  } else if (activeModal.kind === 'migration') {
    searchPlaceholder = 'Filter by workflow or asset...';
  } else if (activeModal.kind === 'workflows') {
    searchPlaceholder = 'Filter by workflow or business area...';
  } else if (activeModal.kind === 'targets') {
    searchPlaceholder = 'Filter by workflow or target output...';
  }

  // Filter workflows by search query depending on modal context
  const filteredWorkflows = useMemo(() => {
    if (!searchQuery.trim()) return workflows;
    const q = searchQuery.toLowerCase().trim();

    return workflows.filter((w) => {
      const nameMatch = w.filename.toLowerCase().includes(q) || (w.business_area_tag && w.business_area_tag.toLowerCase().includes(q));
      if (nameMatch) return true;

      if (activeModal.kind === 'step') {
        if (activeModal.stepNumber === 1) {
          return w.sources && w.sources.some((s) => s.toLowerCase().includes(q));
        }
        if (activeModal.stepNumber === 2) {
          return w.tool_types && w.tool_types.some((t) => t.toLowerCase().includes(q));
        }
        if (activeModal.stepNumber === 3) {
          return w.processing_stages && w.processing_stages.some((s) =>
            s.name.toLowerCase().includes(q) || (s.summary && s.summary.toLowerCase().includes(q)) || (s.description && s.description.toLowerCase().includes(q))
          );
        }
      }
      if (activeModal.kind === 'targets') {
        return w.targets && w.targets.some((t) => t.toLowerCase().includes(q));
      }
      return false;
    });
  }, [workflows, searchQuery, activeModal]);

  const WORKFLOW_PAGE_SIZE = 6;
  const displayedWorkflows = showAllWorkflows ? filteredWorkflows : filteredWorkflows.slice(0, WORKFLOW_PAGE_SIZE);
  const hasMoreWorkflows = filteredWorkflows.length > WORKFLOW_PAGE_SIZE;

  // Render modal content metadata depending on activeModal
  let modalTitle = '';
  let modalBadge = '';
  let headlineMetric = '';
  let headlineExplanation = '';

  if (activeModal.kind === 'step') {
    switch (activeModal.stepNumber) {
      case 1:
        modalBadge = 'STEP 01 · ESTATE DATA INGESTION';
        modalTitle = 'Discovered Input Sources Evidence';
        headlineMetric = `${totalSources} Input Sources across ${workflows.length} Workflows / ${uniqueSources} Unique Datasets`;
        headlineExplanation = 'All upstream files, databases, and ingest feeds identified across portfolio workflows.';
        break;
      case 2:
        modalBadge = 'STEP 02 · PROCESSING & JOINS';
        modalTitle = 'Workflow Tool Footprint & Operations';
        headlineMetric = `${totalTools} Tool Instances across ${workflows.length} Workflows`;
        headlineExplanation = 'Complete tool and data operation footprint used across the portfolio estate.';
        break;
      case 3:
        modalBadge = 'STEP 03 · PROCESS STAGES';
        modalTitle = 'Portfolio Process Stages';
        headlineMetric = `${totalProcessStages} Process Stages across ${workflows.length} Workflows`;
        headlineExplanation = 'Logical processing stages and functional pipelines extracted from each workflow AST.';
        break;
      case 4:
        modalBadge = 'STEP 04 · SHARED OVERLAPS';
        modalTitle = 'Shared Cross-Workflow Datasets';
        headlineMetric = `${shared_sources.length + shared_targets.length} Shared Datasets (${shared_sources.length} Sources, ${shared_targets.length} Targets)`;
        headlineExplanation = 'Common datasets ingested or produced across multiple workflows, indicating integration dependencies.';
        break;
      case 5:
        modalBadge = 'STEP 05 · RATIONALISATION';
        modalTitle = 'Consolidation & Rationalisation Opportunities';
        headlineMetric = `${rationalisation_candidates.length} Opportunities Identified`;
        headlineExplanation = 'Deterministic rule matches and similarity metrics establishing merge, deduplication, and retirement candidates.';
        break;
      case 6:
        modalBadge = 'STEP 06 · TARGET MIGRATION';
        modalTitle = 'Generated Migration & Documentation Packages';
        headlineMetric = `${successfulWorkflows} Complete Migration Packages (${successfulWorkflows * 5} Total Artifacts)`;
        headlineExplanation = 'Executable Python, JSON AST, STTM matrices, and technical documentation generated for each workflow.';
        break;
    }
  } else if (activeModal.kind === 'migration') {
    modalBadge = 'MIGRATION & DOCUMENTATION';
    modalTitle = 'Migration Assets Generated';
    headlineMetric = `${successfulWorkflows} Workflows Migration-Ready`;
    headlineExplanation = 'Complete inventory of generated Python translations, JSON representations, STTM matrices, and documentation.';
  } else if (activeModal.kind === 'workflows') {
    modalBadge = 'ESTATE WORKFLOWS · PORTFOLIO INVENTORY';
    modalTitle = 'Analysed Portfolio Workflows';
    headlineMetric = `${successfulWorkflows} of ${totalWorkflows} Workflows Successfully Analysed`;
    headlineExplanation = 'Complete inventory of workflows parsed into AST graphs, process stages, and migration assets.';
  } else if (activeModal.kind === 'targets') {
    modalBadge = 'ESTATE OUTPUTS · BUSINESS DELIVERABLES';
    modalTitle = 'Discovered Output Targets Evidence';
    headlineMetric = `${totalTargets} Output Targets across ${workflows.length} Workflows / ${uniqueTargets} Unique Outputs`;
    headlineExplanation = 'All downstream output files, database tables, sheets, and target deliverables discovered across the portfolio estate.';
  }

  return (
    <div
      role="dialog"
      aria-modal="true"
      style={{
        position: 'fixed',
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        background: 'rgba(0, 0, 0, 0.75)',
        backdropFilter: 'blur(4px)',
        zIndex: 1000,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '24px',
        boxSizing: 'border-box',
      }}
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div
        style={{
          background: 'var(--color-surface)',
          border: '1px solid var(--color-border)',
          borderRadius: 'var(--radius-md, 8px)',
          width: '100%',
          maxWidth: '920px',
          maxHeight: '85vh',
          display: 'flex',
          flexDirection: 'column',
          overflow: 'hidden',
          boxShadow: '0 20px 40px rgba(0, 0, 0, 0.5)',
        }}
      >
        {/* Modal Header */}
        <div
          style={{
            padding: '20px 24px',
            borderBottom: '1px solid var(--color-border)',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'flex-start',
            gap: '16px',
          }}
        >
          <div>
            <div
              style={{
                fontSize: '11px',
                fontWeight: '800',
                color: 'var(--color-primary)',
                letterSpacing: '0.1em',
                textTransform: 'uppercase',
                marginBottom: '4px',
              }}
            >
              {modalBadge}
            </div>
            <h2 style={{ fontSize: '18px', fontWeight: '800', color: 'var(--color-text)', margin: '0 0 6px 0' }}>
              {modalTitle}
            </h2>
            <div style={{ fontSize: '13.5px', fontWeight: '700', color: 'var(--color-text)', marginBottom: '2px' }}>
              {headlineMetric}
            </div>
            <div style={{ fontSize: '12px', color: 'var(--color-text-secondary)', lineHeight: 1.4 }}>
              {headlineExplanation}
            </div>
          </div>

          <button
            onClick={onClose}
            aria-label="Close dialog"
            style={{
              background: 'transparent',
              border: '1px solid var(--color-border)',
              borderRadius: 'var(--radius-sm, 4px)',
              padding: '6px',
              color: 'var(--color-text-muted)',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
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
            <X size={18} />
          </button>
        </div>

        {/* Modal Contextual Search Bar */}
        {workflows.length > 3 && (
          <div style={{ padding: '12px 24px 0 24px', display: 'flex', alignItems: 'center' }}>
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                width: '100%',
                background: 'var(--color-surface-secondary)',
                border: '1px solid var(--color-border)',
                borderRadius: 'var(--radius-sm, 4px)',
                padding: '6px 10px',
              }}
            >
              <Search size={14} color="var(--color-text-muted)" />
              <input
                type="text"
                placeholder={searchPlaceholder}
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                style={{
                  background: 'transparent',
                  border: 'none',
                  outline: 'none',
                  color: 'var(--color-text)',
                  fontSize: '12.5px',
                  width: '100%',
                }}
              />
              {searchQuery && (
                <button
                  onClick={() => setSearchQuery('')}
                  style={{ background: 'none', border: 'none', color: 'var(--color-text-muted)', cursor: 'pointer', padding: 0 }}
                >
                  <X size={13} />
                </button>
              )}
            </div>
          </div>
        )}

        {/* Modal Scrollable Body */}
        <div style={{ padding: '20px 24px', overflowY: 'auto', flex: 1, display: 'flex', flexDirection: 'column', gap: '14px' }}>
          
          {/* =================================================================== */}
          {/* STEP 1: Discovered Input Sources Evidence (SOURCES ONLY)            */}
          {/* =================================================================== */}
          {activeModal.kind === 'step' && activeModal.stepNumber === 1 && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
              {displayedWorkflows.map((wf) => {
                const isExpanded = Boolean(expandedWorkflows[wf.workflow_id]);
                const sourcesList = wf.sources || [];
                return (
                  <div
                    key={wf.workflow_id}
                    style={{
                      background: 'var(--color-surface-secondary)',
                      border: '1px solid var(--color-border)',
                      borderRadius: 'var(--radius-sm, 6px)',
                      padding: '12px 16px',
                      display: 'flex',
                      flexDirection: 'column',
                      gap: '8px',
                    }}
                  >
                    <div
                      onClick={() => toggleWorkflow(wf.workflow_id)}
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'space-between',
                        cursor: 'pointer',
                        userSelect: 'none',
                      }}
                    >
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <span style={{ fontSize: '13px', fontWeight: '700', color: 'var(--color-text)' }}>
                          {wf.filename}
                        </span>
                        {wf.business_area_tag && (
                          <span
                            style={{
                              fontSize: '10.5px',
                              fontWeight: '600',
                              padding: '2px 6px',
                              borderRadius: '4px',
                              background: 'rgba(56, 189, 248, 0.1)',
                              color: '#38bdf8',
                              border: '1px solid rgba(56, 189, 248, 0.2)',
                            }}
                          >
                            {wf.business_area_tag}
                          </span>
                        )}
                      </div>

                      <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                        <span style={{ fontSize: '11.5px', color: 'var(--color-text-muted)' }}>
                          {sourcesList.length} {sourcesList.length === 1 ? 'source' : 'sources'}
                        </span>
                        {isExpanded ? <ChevronUp size={16} color="var(--color-text-muted)" /> : <ChevronDown size={16} color="var(--color-text-muted)" />}
                      </div>
                    </div>

                    {/* Expanded Sources Detail */}
                    {isExpanded && (
                      <div
                        style={{
                          marginTop: '6px',
                          paddingTop: '10px',
                          borderTop: '1px solid var(--color-border)',
                          display: 'flex',
                          flexDirection: 'column',
                          gap: '8px',
                        }}
                      >
                        {sourcesList.length > 0 ? (
                          <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                            {sourcesList.map((src, i) => (
                              <div
                                key={i}
                                style={{
                                  background: 'var(--color-surface)',
                                  border: '1px solid var(--color-border)',
                                  borderRadius: '4px',
                                  padding: '8px 12px',
                                  display: 'flex',
                                  alignItems: 'center',
                                  justifyContent: 'space-between',
                                  gap: '10px',
                                }}
                              >
                                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', overflow: 'hidden' }}>
                                  <Database size={13} color="#38bdf8" style={{ flexShrink: 0 }} />
                                  <span style={{ fontSize: '12px', fontWeight: '600', color: 'var(--color-text)', wordBreak: 'break-all' }}>
                                    {src}
                                  </span>
                                </div>
                                <span style={{
                                  fontSize: '10.5px',
                                  fontWeight: '600',
                                  padding: '2px 6px',
                                  borderRadius: '3px',
                                  background: 'rgba(56, 189, 248, 0.08)',
                                  color: '#38bdf8',
                                  border: '1px solid rgba(56, 189, 248, 0.2)',
                                  flexShrink: 0,
                                }}>
                                  {src.endsWith('.xlsx') || src.endsWith('.xls') ? 'EXCEL' :
                                   src.endsWith('.csv') ? 'CSV' :
                                   src.endsWith('.yxdb') ? 'YXDB' :
                                   src.includes('dbo.') || src.includes('SELECT') ? 'DATABASE' : 'DATASET'}
                                </span>
                              </div>
                            ))}
                          </div>
                        ) : (
                          <div style={{ fontSize: '11.5px', color: 'var(--color-text-muted)' }}>
                            No external input sources configured.
                          </div>
                        )}

                        {/* Action to Inspect Workflow */}
                        {onSelectWorkflow && (
                          <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: '4px' }}>
                            <button
                              onClick={() => {
                                onClose();
                                onSelectWorkflow(wf.workflow_id, wf.business_area_tag);
                              }}
                              style={{
                                background: 'transparent',
                                border: 'none',
                                color: 'var(--color-primary)',
                                fontSize: '11.5px',
                                fontWeight: '700',
                                cursor: 'pointer',
                                display: 'inline-flex',
                                alignItems: 'center',
                                gap: '4px',
                              }}
                            >
                              <span>Inspect {wf.filename}</span>
                              <ExternalLink size={12} />
                            </button>
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                );
              })}

              {hasMoreWorkflows && (
                <button
                  onClick={() => setShowAllWorkflows((prev) => !prev)}
                  style={{
                    alignSelf: 'center',
                    background: 'var(--color-surface-secondary)',
                    border: '1px solid var(--color-border)',
                    borderRadius: 'var(--radius-sm, 4px)',
                    padding: '8px 16px',
                    fontSize: '12px',
                    fontWeight: '600',
                    color: 'var(--color-primary)',
                    cursor: 'pointer',
                    marginTop: '6px',
                  }}
                >
                  {showAllWorkflows ? 'Show Less' : `Show All ${filteredWorkflows.length} Workflows →`}
                </button>
              )}
            </div>
          )}

          {/* =================================================================== */}
          {/* STEP 2: Processing & Joins (TOOL FOOTPRINT ONLY)                    */}
          {/* =================================================================== */}
          {activeModal.kind === 'step' && activeModal.stepNumber === 2 && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
              {displayedWorkflows.map((wf) => {
                const isExpanded = Boolean(expandedWorkflows[wf.workflow_id]);
                const toolCounts: Record<string, number> = {};
                (wf.tool_types || []).forEach((t) => {
                  toolCounts[t] = (toolCounts[t] || 0) + 1;
                });
                const sortedToolEntries = Object.entries(toolCounts).sort((a, b) => b[1] - a[1]);
                const summaryString = sortedToolEntries
                  .slice(0, 4)
                  .map(([type, count]) => `${type} × ${count}`)
                  .join(' · ');

                return (
                  <div
                    key={wf.workflow_id}
                    style={{
                      background: 'var(--color-surface-secondary)',
                      border: '1px solid var(--color-border)',
                      borderRadius: 'var(--radius-sm, 6px)',
                      padding: '12px 16px',
                      display: 'flex',
                      flexDirection: 'column',
                      gap: '8px',
                    }}
                  >
                    <div
                      onClick={() => toggleWorkflow(wf.workflow_id)}
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'space-between',
                        cursor: 'pointer',
                        userSelect: 'none',
                      }}
                    >
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <span style={{ fontSize: '13px', fontWeight: '700', color: 'var(--color-text)' }}>
                          {wf.filename}
                        </span>
                        {wf.business_area_tag && (
                          <span
                            style={{
                              fontSize: '10.5px',
                              fontWeight: '600',
                              padding: '2px 6px',
                              borderRadius: '4px',
                              background: 'rgba(56, 189, 248, 0.1)',
                              color: '#38bdf8',
                              border: '1px solid rgba(56, 189, 248, 0.2)',
                            }}
                          >
                            {wf.business_area_tag}
                          </span>
                        )}
                      </div>

                      <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                        <span style={{ fontSize: '11.5px', color: 'var(--color-text-muted)' }}>
                          {wf.node_count || 0} tools
                        </span>
                        {isExpanded ? <ChevronUp size={16} color="var(--color-text-muted)" /> : <ChevronDown size={16} color="var(--color-text-muted)" />}
                      </div>
                    </div>

                    {/* Grouped summary preview line */}
                    {summaryString && (
                      <div style={{ fontSize: '11.5px', color: 'var(--color-text-secondary)' }}>
                        {summaryString}
                        {sortedToolEntries.length > 4 ? ` · +${sortedToolEntries.length - 4} more` : ''}
                      </div>
                    )}

                    {/* Expanded Tool Operations Detail */}
                    {isExpanded && (
                      <div
                        style={{
                          marginTop: '6px',
                          paddingTop: '10px',
                          borderTop: '1px solid var(--color-border)',
                          display: 'flex',
                          flexDirection: 'column',
                          gap: '8px',
                        }}
                      >
                        <div style={{ fontSize: '11px', fontWeight: '700', color: 'var(--color-primary)', textTransform: 'uppercase', marginBottom: '4px' }}>
                          Tool Inventory ({sortedToolEntries.length} Distinct Operations):
                        </div>
                        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(140px, 1fr))', gap: '6px' }}>
                          {sortedToolEntries.map(([toolType, count]) => (
                            <div
                              key={toolType}
                              style={{
                                background: 'var(--color-surface)',
                                border: '1px solid var(--color-border)',
                                borderRadius: '4px',
                                padding: '6px 10px',
                                display: 'flex',
                                alignItems: 'center',
                                justifyContent: 'space-between',
                              }}
                            >
                              <span style={{ fontSize: '11.5px', color: 'var(--color-text)' }}>{toolType}</span>
                              <strong style={{ fontSize: '12px', color: 'var(--color-primary)' }}>{count}</strong>
                            </div>
                          ))}
                        </div>

                        {/* Action to Inspect Workflow */}
                        {onSelectWorkflow && (
                          <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: '4px' }}>
                            <button
                              onClick={() => {
                                onClose();
                                onSelectWorkflow(wf.workflow_id, wf.business_area_tag);
                              }}
                              style={{
                                background: 'transparent',
                                border: 'none',
                                color: 'var(--color-primary)',
                                fontSize: '11.5px',
                                fontWeight: '700',
                                cursor: 'pointer',
                                display: 'inline-flex',
                                alignItems: 'center',
                                gap: '4px',
                              }}
                            >
                              <span>Inspect Tools in {wf.filename}</span>
                              <ExternalLink size={12} />
                            </button>
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                );
              })}

              {hasMoreWorkflows && (
                <button
                  onClick={() => setShowAllWorkflows((prev) => !prev)}
                  style={{
                    alignSelf: 'center',
                    background: 'var(--color-surface-secondary)',
                    border: '1px solid var(--color-border)',
                    borderRadius: 'var(--radius-sm, 4px)',
                    padding: '8px 16px',
                    fontSize: '12px',
                    fontWeight: '600',
                    color: 'var(--color-primary)',
                    cursor: 'pointer',
                    marginTop: '6px',
                  }}
                >
                  {showAllWorkflows ? 'Show Less' : `Show All ${filteredWorkflows.length} Workflows →`}
                </button>
              )}
            </div>
          )}

          {/* =================================================================== */}
          {/* STEP 3: Process Stages (WORKFLOW PROCESS STAGES ONLY)               */}
          {/* =================================================================== */}
          {activeModal.kind === 'step' && activeModal.stepNumber === 3 && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
              {displayedWorkflows.map((wf) => {
                const isExpanded = Boolean(expandedWorkflows[wf.workflow_id]);
                const stages = wf.processing_stages || [];
                const stageCountDisplay = stages.length > 0 ? stages.length : 1;

                return (
                  <div
                    key={wf.workflow_id}
                    style={{
                      background: 'var(--color-surface-secondary)',
                      border: '1px solid var(--color-border)',
                      borderRadius: 'var(--radius-sm, 6px)',
                      padding: '12px 16px',
                      display: 'flex',
                      flexDirection: 'column',
                      gap: '8px',
                    }}
                  >
                    <div
                      onClick={() => toggleWorkflow(wf.workflow_id)}
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'space-between',
                        cursor: 'pointer',
                        userSelect: 'none',
                      }}
                    >
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <span style={{ fontSize: '13px', fontWeight: '700', color: 'var(--color-text)' }}>
                          {wf.filename}
                        </span>
                        {wf.business_area_tag && (
                          <span
                            style={{
                              fontSize: '10.5px',
                              fontWeight: '600',
                              padding: '2px 6px',
                              borderRadius: '4px',
                              background: 'rgba(168, 85, 247, 0.1)',
                              color: '#a855f7',
                              border: '1px solid rgba(168, 85, 247, 0.2)',
                            }}
                          >
                            {wf.business_area_tag}
                          </span>
                        )}
                      </div>

                      <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                        <span style={{ fontSize: '11.5px', color: 'var(--color-text-muted)' }}>
                          {stageCountDisplay} {stageCountDisplay === 1 ? 'stage' : 'stages'}
                        </span>
                        {isExpanded ? <ChevronUp size={16} color="var(--color-text-muted)" /> : <ChevronDown size={16} color="var(--color-text-muted)" />}
                      </div>
                    </div>

                    {/* Preview summary of first few stages */}
                    {stages.length > 0 && (
                      <div style={{ fontSize: '11.5px', color: 'var(--color-text-secondary)' }}>
                        {stages.slice(0, 3).map((s) => s.name).join(' · ')}
                        {stages.length > 3 ? ` · +${stages.length - 3} more` : ''}
                      </div>
                    )}

                    {/* Expanded Process Stages Detail */}
                    {isExpanded && (
                      <div
                        style={{
                          marginTop: '6px',
                          paddingTop: '10px',
                          borderTop: '1px solid var(--color-border)',
                          display: 'flex',
                          flexDirection: 'column',
                          gap: '8px',
                        }}
                      >
                        {stages.length > 0 ? (
                          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(260px, 1fr))', gap: '8px' }}>
                            {stages.map((stage: BusinessStageDTO) => {
                              const stageKey = `${wf.workflow_id}_stage_${stage.stage_number}`;
                              const isStageExpanded = Boolean(expandedStages[stageKey]);
                              return (
                                <div
                                  key={stage.stage_number}
                                  onClick={() => toggleStage(stageKey)}
                                  style={{
                                    background: 'var(--color-surface)',
                                    border: isStageExpanded ? '1px solid var(--color-primary)' : '1px solid var(--color-border)',
                                    borderRadius: '6px',
                                    padding: '10px 12px',
                                    cursor: 'pointer',
                                    display: 'flex',
                                    flexDirection: 'column',
                                    gap: '4px',
                                  }}
                                >
                                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                                    <span style={{
                                      fontSize: '10px',
                                      fontFamily: 'var(--font-mono)',
                                      fontWeight: '700',
                                      color: '#a855f7',
                                    }}>
                                      {stage.short_title || `STAGE ${String(stage.stage_number).padStart(2, '0')}`}
                                    </span>
                                    <span style={{ fontSize: '10.5px', color: 'var(--color-text-muted)' }}>
                                      {stage.tool_count} steps
                                    </span>
                                  </div>
                                  <h4 style={{ fontSize: '12.5px', fontWeight: '700', color: 'var(--color-text)', margin: '0 0 2px 0' }}>
                                    {stage.name}
                                  </h4>
                                  <p style={{ fontSize: '11.5px', color: 'var(--color-text-secondary)', margin: 0, lineHeight: 1.35 }}>
                                    {stage.summary || stage.description}
                                  </p>

                                  {/* Deep stage detail disclosure */}
                                  {isStageExpanded && (
                                    <div
                                      style={{
                                        marginTop: '6px',
                                        paddingTop: '6px',
                                        borderTop: '1px solid var(--color-border)',
                                        fontSize: '11px',
                                        display: 'flex',
                                        flexDirection: 'column',
                                        gap: '4px',
                                      }}
                                      onClick={(e) => e.stopPropagation()}
                                    >
                                      {stage.business_purpose && (
                                        <div>
                                          <strong style={{ color: 'var(--color-text)' }}>Purpose: </strong>
                                          <span style={{ color: 'var(--color-text-secondary)' }}>{stage.business_purpose}</span>
                                        </div>
                                      )}
                                      {stage.major_transformation && (
                                        <div>
                                          <strong style={{ color: 'var(--color-text)' }}>Transformation: </strong>
                                          <span style={{ color: 'var(--color-text-secondary)' }}>{stage.major_transformation}</span>
                                        </div>
                                      )}
                                    </div>
                                  )}
                                </div>
                              );
                            })}
                          </div>
                        ) : (
                          <div style={{ fontSize: '11.5px', color: 'var(--color-text-secondary)', padding: '6px 0' }}>
                            1 Stage (Core Ingestion &amp; Transformation Pipeline) · {wf.node_count} steps
                          </div>
                        )}

                        {/* Action to Inspect Workflow */}
                        {onSelectWorkflow && (
                          <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: '4px' }}>
                            <button
                              onClick={() => {
                                onClose();
                                onSelectWorkflow(wf.workflow_id, wf.business_area_tag);
                              }}
                              style={{
                                background: 'transparent',
                                border: 'none',
                                color: 'var(--color-primary)',
                                fontSize: '11.5px',
                                fontWeight: '700',
                                cursor: 'pointer',
                                display: 'inline-flex',
                                alignItems: 'center',
                                gap: '4px',
                              }}
                            >
                              <span>Inspect Stages in {wf.filename}</span>
                              <ExternalLink size={12} />
                            </button>
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                );
              })}

              {hasMoreWorkflows && (
                <button
                  onClick={() => setShowAllWorkflows((prev) => !prev)}
                  style={{
                    alignSelf: 'center',
                    background: 'var(--color-surface-secondary)',
                    border: '1px solid var(--color-border)',
                    borderRadius: 'var(--radius-sm, 4px)',
                    padding: '8px 16px',
                    fontSize: '12px',
                    fontWeight: '600',
                    color: 'var(--color-primary)',
                    cursor: 'pointer',
                    marginTop: '6px',
                  }}
                >
                  {showAllWorkflows ? 'Show Less' : `Show All ${filteredWorkflows.length} Workflows →`}
                </button>
              )}
            </div>
          )}

          {/* =================================================================== */}
          {/* STEP 4: Shared Overlaps Evidence                                    */}
          {/* =================================================================== */}
          {activeModal.kind === 'step' && activeModal.stepNumber === 4 && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
              <div style={{ fontSize: '13px', fontWeight: '700', color: 'var(--color-text)' }}>
                Cross-Workflow Shared Datasets ({shared_sources.length + shared_targets.length})
              </div>

              {shared_sources.length === 0 && shared_targets.length === 0 ? (
                <div style={{ color: 'var(--color-text-muted)', fontSize: '12.5px' }}>
                  No shared datasets identified across current workflows.
                </div>
              ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                  {shared_sources.map((ds, idx) => (
                    <SharedDatasetCard key={`src-${idx}`} dataset={ds} />
                  ))}
                  {shared_targets.map((ds, idx) => (
                    <SharedDatasetCard key={`tgt-${idx}`} dataset={ds} />
                  ))}
                </div>
              )}
            </div>
          )}

          {/* =================================================================== */}
          {/* STEP 5: Rationalisation Candidates Evidence                         */}
          {/* =================================================================== */}
          {activeModal.kind === 'step' && activeModal.stepNumber === 5 && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div style={{ fontSize: '13px', fontWeight: '700', color: 'var(--color-text)' }}>
                  Identified Rationalisation Opportunities ({rationalisation_candidates.length})
                </div>
                {onOpenRationalisation && (
                  <button
                    onClick={() => {
                      onClose();
                      onOpenRationalisation();
                    }}
                    style={{
                      background: 'none',
                      border: 'none',
                      color: '#34d399',
                      fontSize: '12px',
                      fontWeight: '700',
                      cursor: 'pointer',
                      display: 'inline-flex',
                      alignItems: 'center',
                      gap: '4px',
                    }}
                  >
                    <span>View ETL Rationalisation</span>
                    <ArrowRight size={13} />
                  </button>
                )}
              </div>

              {rationalisation_candidates.map((cand) => (
                <div
                  key={cand.candidate_id}
                  style={{
                    background: 'var(--color-surface-secondary)',
                    border: '1px solid var(--color-border)',
                    borderRadius: 'var(--radius-sm, 6px)',
                    padding: '14px 16px',
                    display: 'flex',
                    flexDirection: 'column',
                    gap: '8px',
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <div style={{ fontSize: '13.5px', fontWeight: '700', color: 'var(--color-text)' }}>
                      {cand.workflow_names?.join(' ↔ ') || 'Candidate Workflow Pair'}
                    </div>
                    <span
                      style={{
                        background: cand.recommendation_type === 'CONSOLIDATE' ? 'rgba(52, 211, 153, 0.2)' : 'rgba(249, 115, 22, 0.2)',
                        color: cand.recommendation_type === 'CONSOLIDATE' ? '#34d399' : 'var(--color-primary)',
                        padding: '2px 8px',
                        borderRadius: '4px',
                        fontWeight: '700',
                        fontSize: '11px',
                        textTransform: 'uppercase',
                      }}
                    >
                      {cand.recommendation_type} ({cand.opportunity_score}/100)
                    </span>
                  </div>

                  <div style={{ fontSize: '12px', color: 'var(--color-text-secondary)', lineHeight: 1.4 }}>
                    {cand.consolidation_decision?.matched_rule || cand.proposed_strategy || 'Candidate for workflow consolidation.'}
                  </div>

                  {cand.deterministic_metrics && (
                    <div style={{ display: 'flex', gap: '12px', fontSize: '11px', color: 'var(--color-text-muted)', paddingTop: '6px', borderTop: '1px solid var(--color-border)' }}>
                      <span>Source Overlap: {Math.round((cand.deterministic_metrics.source_overlap || 0) * 100)}%</span>
                      <span>·</span>
                      <span>Transform Similarity: {Math.round((cand.deterministic_metrics.transformation_similarity || 0) * 100)}%</span>
                      <span>·</span>
                      <span>DAG Similarity: {Math.round((cand.deterministic_metrics.dag_similarity || 0) * 100)}%</span>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}

          {/* =================================================================== */}
          {/* STEP 6 / MIGRATION: Target Migration Assets Evidence               */}
          {/* =================================================================== */}
          {((activeModal.kind === 'step' && activeModal.stepNumber === 6) || activeModal.kind === 'migration') && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
              <div style={{ fontSize: '13px', fontWeight: '700', color: 'var(--color-text)' }}>
                Migration Readiness per Workflow ({successfulWorkflows} of {workflows.length} Complete)
              </div>

              <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                {workflows.map((wf) => (
                  <div
                    key={wf.workflow_id}
                    style={{
                      background: 'var(--color-surface-secondary)',
                      border: '1px solid var(--color-border)',
                      borderRadius: 'var(--radius-sm, 6px)',
                      padding: '12px 16px',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'space-between',
                      flexWrap: 'wrap',
                      gap: '10px',
                    }}
                  >
                    <div>
                      <div style={{ fontSize: '13px', fontWeight: '700', color: 'var(--color-text)' }}>
                        {wf.filename}
                      </div>
                      <div style={{ fontSize: '11px', color: 'var(--color-text-muted)', marginTop: '2px' }}>
                        {wf.node_count} nodes · {wf.connection_count} edges · {wf.sttm_mappings_count} STTM mappings
                      </div>
                    </div>

                    {/* 5 Asset Badges */}
                    <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap' }}>
                      <AssetStatusBadge label="Python" available={wf.status === 'SUCCESS'} />
                      <AssetStatusBadge label="JSON" available={wf.status === 'SUCCESS'} />
                      <AssetStatusBadge label="STTM" available={Boolean(wf.sttm_mappings_count || wf.status === 'SUCCESS')} />
                      <AssetStatusBadge label="Business Report" available={wf.status === 'SUCCESS'} />
                      <AssetStatusBadge label="Tool Spec" available={wf.status === 'SUCCESS'} />
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* =================================================================== */}
          {/* WORKFLOWS: Analysed Portfolio Workflows Evidence                    */}
          {/* =================================================================== */}
          {activeModal.kind === 'workflows' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
              {displayedWorkflows.map((wf) => {
                const isExpanded = Boolean(expandedWorkflows[wf.workflow_id]);
                const stagesCount = wf.processing_stages && wf.processing_stages.length > 0 ? wf.processing_stages.length : (wf.node_count > 0 ? 1 : 0);
                const sourcesList = wf.sources || [];
                const targetsList = wf.targets || [];

                return (
                  <div
                    key={wf.workflow_id}
                    style={{
                      background: 'var(--color-surface-secondary)',
                      border: '1px solid var(--color-border)',
                      borderRadius: 'var(--radius-sm, 6px)',
                      padding: '14px 16px',
                      display: 'flex',
                      flexDirection: 'column',
                      gap: '8px',
                    }}
                  >
                    <div
                      onClick={() => toggleWorkflow(wf.workflow_id)}
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'space-between',
                        cursor: 'pointer',
                        userSelect: 'none',
                        flexWrap: 'wrap',
                        gap: '8px',
                      }}
                    >
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <span style={{ fontSize: '13.5px', fontWeight: '700', color: 'var(--color-text)' }}>
                          {wf.filename}
                        </span>
                        {wf.business_area_tag && (
                          <span
                            style={{
                              fontSize: '10.5px',
                              fontWeight: '600',
                              padding: '2px 6px',
                              borderRadius: '4px',
                              background: 'rgba(56, 189, 248, 0.1)',
                              color: '#38bdf8',
                              border: '1px solid rgba(56, 189, 248, 0.2)',
                            }}
                          >
                            {wf.business_area_tag}
                          </span>
                        )}
                        <span
                          style={{
                            fontSize: '10.5px',
                            fontWeight: '700',
                            padding: '2px 6px',
                            borderRadius: '4px',
                            background: wf.status === 'SUCCESS' ? 'rgba(52, 211, 153, 0.15)' : 'rgba(239, 68, 68, 0.15)',
                            color: wf.status === 'SUCCESS' ? '#34d399' : '#f87171',
                            border: `1px solid ${wf.status === 'SUCCESS' ? 'rgba(52, 211, 153, 0.3)' : 'rgba(239, 68, 68, 0.3)'}`,
                            textTransform: 'uppercase',
                          }}
                        >
                          {wf.status || 'SUCCESS'}
                        </span>
                      </div>

                      <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                        <div style={{ display: 'flex', gap: '8px', fontSize: '11.5px', color: 'var(--color-text-muted)' }}>
                          <span>{wf.node_count || 0} tools</span>
                          <span>·</span>
                          <span>{wf.source_count || sourcesList.length} sources</span>
                          <span>·</span>
                          <span>{wf.target_count || targetsList.length} targets</span>
                          <span>·</span>
                          <span>{stagesCount} stages</span>
                        </div>
                        {isExpanded ? <ChevronUp size={16} color="var(--color-text-muted)" /> : <ChevronDown size={16} color="var(--color-text-muted)" />}
                      </div>
                    </div>

                    {/* Expanded Workflow Detail */}
                    {isExpanded && (
                      <div
                        style={{
                          marginTop: '6px',
                          paddingTop: '10px',
                          borderTop: '1px solid var(--color-border)',
                          display: 'flex',
                          flexDirection: 'column',
                          gap: '10px',
                        }}
                      >
                        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '8px' }}>
                          <div style={{ background: 'var(--color-surface)', padding: '8px 10px', borderRadius: '4px', border: '1px solid var(--color-border)' }}>
                            <div style={{ fontSize: '10px', fontWeight: '700', color: 'var(--color-text-muted)', textTransform: 'uppercase' }}>Graph Footprint</div>
                            <div style={{ fontSize: '12px', fontWeight: '600', color: 'var(--color-text)', marginTop: '2px' }}>
                              {wf.node_count} nodes · {wf.connection_count} edges · {wf.sttm_mappings_count} STTM mappings
                            </div>
                          </div>
                          <div style={{ background: 'var(--color-surface)', padding: '8px 10px', borderRadius: '4px', border: '1px solid var(--color-border)' }}>
                            <div style={{ fontSize: '10px', fontWeight: '700', color: 'var(--color-text-muted)', textTransform: 'uppercase' }}>Process Stages ({stagesCount})</div>
                            <div style={{ fontSize: '12px', fontWeight: '600', color: 'var(--color-text)', marginTop: '2px' }}>
                              {wf.processing_stages && wf.processing_stages.length > 0
                                ? wf.processing_stages.map((s) => s.name).join(' → ')
                                : '1 Ingestion & Transformation Stage'}
                            </div>
                          </div>
                        </div>

                        {sourcesList.length > 0 && (
                          <div>
                            <div style={{ fontSize: '11px', fontWeight: '700', color: '#38bdf8', marginBottom: '4px', textTransform: 'uppercase' }}>
                              Input Sources ({sourcesList.length}):
                            </div>
                            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
                              {sourcesList.map((src, i) => (
                                <span key={i} style={{ fontSize: '11.5px', background: 'var(--color-surface)', border: '1px solid var(--color-border)', borderRadius: '4px', padding: '3px 8px', color: 'var(--color-text)' }}>
                                  {src}
                                </span>
                              ))}
                            </div>
                          </div>
                        )}

                        {targetsList.length > 0 && (
                          <div>
                            <div style={{ fontSize: '11px', fontWeight: '700', color: '#eab308', marginBottom: '4px', textTransform: 'uppercase' }}>
                              Output Targets ({targetsList.length}):
                            </div>
                            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
                              {targetsList.map((tgt, i) => (
                                <span key={i} style={{ fontSize: '11.5px', background: 'var(--color-surface)', border: '1px solid var(--color-border)', borderRadius: '4px', padding: '3px 8px', color: 'var(--color-text)' }}>
                                  {tgt}
                                </span>
                              ))}
                            </div>
                          </div>
                        )}

                        {/* Action to Inspect Workflow */}
                        {onSelectWorkflow && (
                          <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: '4px' }}>
                            <button
                              onClick={() => {
                                onClose();
                                onSelectWorkflow(wf.workflow_id, wf.business_area_tag);
                              }}
                              style={{
                                background: 'transparent',
                                border: 'none',
                                color: 'var(--color-primary)',
                                fontSize: '11.5px',
                                fontWeight: '700',
                                cursor: 'pointer',
                                display: 'inline-flex',
                                alignItems: 'center',
                                gap: '4px',
                              }}
                            >
                              <span>Inspect {wf.filename}</span>
                              <ExternalLink size={12} />
                            </button>
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                );
              })}

              {hasMoreWorkflows && (
                <button
                  onClick={() => setShowAllWorkflows((prev) => !prev)}
                  style={{
                    alignSelf: 'center',
                    background: 'var(--color-surface-secondary)',
                    border: '1px solid var(--color-border)',
                    borderRadius: 'var(--radius-sm, 4px)',
                    padding: '8px 16px',
                    fontSize: '12px',
                    fontWeight: '600',
                    color: 'var(--color-primary)',
                    cursor: 'pointer',
                    marginTop: '6px',
                  }}
                >
                  {showAllWorkflows ? 'Show Less' : `Show All ${filteredWorkflows.length} Workflows →`}
                </button>
              )}
            </div>
          )}

          {/* =================================================================== */}
          {/* TARGETS: Discovered Output Targets Evidence                         */}
          {/* =================================================================== */}
          {activeModal.kind === 'targets' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
              {displayedWorkflows.map((wf) => {
                const isExpanded = Boolean(expandedWorkflows[wf.workflow_id]);
                const targetsList = wf.targets || [];

                return (
                  <div
                    key={wf.workflow_id}
                    style={{
                      background: 'var(--color-surface-secondary)',
                      border: '1px solid var(--color-border)',
                      borderRadius: 'var(--radius-sm, 6px)',
                      padding: '12px 16px',
                      display: 'flex',
                      flexDirection: 'column',
                      gap: '8px',
                    }}
                  >
                    <div
                      onClick={() => toggleWorkflow(wf.workflow_id)}
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'space-between',
                        cursor: 'pointer',
                        userSelect: 'none',
                      }}
                    >
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <span style={{ fontSize: '13px', fontWeight: '700', color: 'var(--color-text)' }}>
                          {wf.filename}
                        </span>
                        {wf.business_area_tag && (
                          <span
                            style={{
                              fontSize: '10.5px',
                              fontWeight: '600',
                              padding: '2px 6px',
                              borderRadius: '4px',
                              background: 'rgba(234, 179, 8, 0.1)',
                              color: '#eab308',
                              border: '1px solid rgba(234, 179, 8, 0.2)',
                            }}
                          >
                            {wf.business_area_tag}
                          </span>
                        )}
                      </div>

                      <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                        <span style={{ fontSize: '11.5px', color: 'var(--color-text-muted)' }}>
                          {targetsList.length} {targetsList.length === 1 ? 'target output' : 'target outputs'}
                        </span>
                        {isExpanded ? <ChevronUp size={16} color="var(--color-text-muted)" /> : <ChevronDown size={16} color="var(--color-text-muted)" />}
                      </div>
                    </div>

                    {/* Expanded Targets Detail */}
                    {isExpanded && (
                      <div
                        style={{
                          marginTop: '6px',
                          paddingTop: '10px',
                          borderTop: '1px solid var(--color-border)',
                          display: 'flex',
                          flexDirection: 'column',
                          gap: '8px',
                        }}
                      >
                        {targetsList.length > 0 ? (
                          <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                            {targetsList.map((tgt, i) => {
                              const formatBadge =
                                tgt.endsWith('.xlsx') || tgt.endsWith('.xls')
                                  ? 'EXCEL'
                                  : tgt.endsWith('.csv')
                                  ? 'CSV'
                                  : tgt.endsWith('.yxdb')
                                  ? 'YXDB'
                                  : tgt.includes('dbo.') || tgt.includes('INSERT') || tgt.includes('UPDATE')
                                  ? 'DATABASE'
                                  : 'DELIVERABLE';

                              return (
                                <div
                                  key={i}
                                  style={{
                                    background: 'var(--color-surface)',
                                    border: '1px solid var(--color-border)',
                                    borderRadius: '4px',
                                    padding: '8px 12px',
                                    display: 'flex',
                                    alignItems: 'center',
                                    justifyContent: 'space-between',
                                    gap: '10px',
                                  }}
                                >
                                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px', overflow: 'hidden' }}>
                                    <Target size={13} color="#eab308" style={{ flexShrink: 0 }} />
                                    <span style={{ fontSize: '12px', fontWeight: '600', color: 'var(--color-text)', wordBreak: 'break-all' }}>
                                      {tgt}
                                    </span>
                                  </div>
                                  <span
                                    style={{
                                      fontSize: '10.5px',
                                      fontWeight: '600',
                                      padding: '2px 6px',
                                      borderRadius: '3px',
                                      background: 'rgba(234, 179, 8, 0.08)',
                                      color: '#eab308',
                                      border: '1px solid rgba(234, 179, 8, 0.2)',
                                      flexShrink: 0,
                                    }}
                                  >
                                    {formatBadge}
                                  </span>
                                </div>
                              );
                            })}
                          </div>
                        ) : (
                          <div style={{ fontSize: '11.5px', color: 'var(--color-text-muted)' }}>
                            No output targets configured.
                          </div>
                        )}

                        {/* Action to Inspect Workflow */}
                        {onSelectWorkflow && (
                          <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: '4px' }}>
                            <button
                              onClick={() => {
                                onClose();
                                onSelectWorkflow(wf.workflow_id, wf.business_area_tag);
                              }}
                              style={{
                                background: 'transparent',
                                border: 'none',
                                color: 'var(--color-primary)',
                                fontSize: '11.5px',
                                fontWeight: '700',
                                cursor: 'pointer',
                                display: 'inline-flex',
                                alignItems: 'center',
                                gap: '4px',
                              }}
                            >
                              <span>Inspect Targets in {wf.filename}</span>
                              <ExternalLink size={12} />
                            </button>
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                );
              })}

              {hasMoreWorkflows && (
                <button
                  onClick={() => setShowAllWorkflows((prev) => !prev)}
                  style={{
                    alignSelf: 'center',
                    background: 'var(--color-surface-secondary)',
                    border: '1px solid var(--color-border)',
                    borderRadius: 'var(--radius-sm, 4px)',
                    padding: '8px 16px',
                    fontSize: '12px',
                    fontWeight: '600',
                    color: 'var(--color-primary)',
                    cursor: 'pointer',
                    marginTop: '6px',
                  }}
                >
                  {showAllWorkflows ? 'Show Less' : `Show All ${filteredWorkflows.length} Workflows →`}
                </button>
              )}
            </div>
          )}
        </div>

        {/* Modal Footer */}
        <div
          style={{
            padding: '14px 24px',
            borderTop: '1px solid var(--color-border)',
            display: 'flex',
            justifyContent: 'flex-end',
            background: 'var(--color-surface-secondary)',
          }}
        >
          <button
            onClick={onClose}
            style={{
              background: 'var(--color-surface)',
              border: '1px solid var(--color-border)',
              borderRadius: 'var(--radius-sm, 4px)',
              padding: '6px 16px',
              fontSize: '12.5px',
              fontWeight: '600',
              color: 'var(--color-text)',
              cursor: 'pointer',
            }}
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
};

// ============================================================================
// HELPER CARD & BADGE COMPONENTS
// ============================================================================

interface KpiCardProps {
  label: string;
  value: number | string;
  subtext: string;
  icon: LucideIcon;
  color: string;
  onClick?: () => void;
}

const KpiCard: React.FC<KpiCardProps> = ({
  label,
  value,
  subtext,
  icon: Icon,
  color,
  onClick,
}) => {
  return (
    <div
      onClick={onClick}
      role={onClick ? 'button' : undefined}
      tabIndex={onClick ? 0 : undefined}
      style={{
        background: 'var(--color-surface)',
        border: '1px solid var(--color-border)',
        borderRadius: 'var(--radius-md, 8px)',
        padding: '18px 20px',
        display: 'flex',
        flexDirection: 'column',
        gap: '10px',
        cursor: onClick ? 'pointer' : 'default',
        transition: 'all 0.15s ease',
      }}
      onMouseEnter={(e) => {
        if (onClick) {
          e.currentTarget.style.borderColor = color;
          e.currentTarget.style.transform = 'translateY(-2px)';
        }
      }}
      onMouseLeave={(e) => {
        if (onClick) {
          e.currentTarget.style.borderColor = 'var(--color-border)';
          e.currentTarget.style.transform = 'none';
        }
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <span style={{ fontSize: '11px', fontWeight: '800', color: 'var(--color-text-secondary)', textTransform: 'uppercase', letterSpacing: '0.06em' }}>
          {label}
        </span>
        <div
          style={{
            width: '28px',
            height: '28px',
            borderRadius: '6px',
            background: `${color}18`,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
          }}
        >
          <Icon size={15} color={color} />
        </div>
      </div>
      <div>
        <div style={{ fontSize: '28px', fontWeight: '800', color: 'var(--color-text)', lineHeight: 1 }}>
          {value}
        </div>
        <div style={{ fontSize: '11px', color: 'var(--color-text-muted)', marginTop: '4px' }}>
          {subtext}
        </div>
      </div>
    </div>
  );
};

interface AssetCountCardProps {
  count: number;
  label: string;
  sub: string;
  icon: LucideIcon;
  highlight?: boolean;
  onClick?: () => void;
}

const AssetCountCard: React.FC<AssetCountCardProps> = ({ count, label, sub, icon: Icon, highlight, onClick }) => {
  return (
    <div
      onClick={onClick}
      style={{
        background: highlight ? 'rgba(52, 211, 153, 0.08)' : 'var(--color-surface-secondary)',
        border: highlight ? '1px solid rgba(52, 211, 153, 0.3)' : '1px solid var(--color-border)',
        borderRadius: 'var(--radius-sm, 6px)',
        padding: '12px 14px',
        display: 'flex',
        flexDirection: 'column',
        gap: '4px',
        cursor: onClick ? 'pointer' : 'default',
        transition: 'all 0.15s ease',
      }}
      onMouseEnter={(e) => {
        if (onClick) {
          e.currentTarget.style.borderColor = 'var(--color-primary)';
          e.currentTarget.style.transform = 'translateY(-1px)';
        }
      }}
      onMouseLeave={(e) => {
        if (onClick) {
          e.currentTarget.style.borderColor = highlight ? 'rgba(52, 211, 153, 0.3)' : 'var(--color-border)';
          e.currentTarget.style.transform = 'none';
        }
      }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <span style={{ fontSize: '18px', fontWeight: '800', color: highlight ? '#34d399' : 'var(--color-text)' }}>
          {count}
        </span>
        <Icon size={14} color={highlight ? '#34d399' : 'var(--color-primary)'} />
      </div>
      <div style={{ fontSize: '12px', fontWeight: '700', color: 'var(--color-text)' }}>
        {label}
      </div>
      <div style={{ fontSize: '10.5px', color: 'var(--color-text-muted)' }}>
        {sub}
      </div>
    </div>
  );
};

interface InteractiveLifecycleStepProps {
  stepNumber: string;
  title: string;
  count: number;
  countLabel: string;
  description: string;
  color: string;
  onClick: () => void;
}

const InteractiveLifecycleStep: React.FC<InteractiveLifecycleStepProps> = ({
  stepNumber,
  title,
  count,
  countLabel,
  description,
  color,
  onClick,
}) => {
  return (
    <div
      onClick={onClick}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          onClick();
        }
      }}
      style={{
        background: 'var(--color-surface-secondary)',
        border: '1px solid var(--color-border)',
        borderRadius: 'var(--radius-sm, 6px)',
        padding: '16px',
        display: 'flex',
        flexDirection: 'column',
        gap: '10px',
        position: 'relative',
        overflow: 'hidden',
        cursor: 'pointer',
        transition: 'all 0.15s ease',
      }}
      onMouseEnter={(e) => {
        e.currentTarget.style.borderColor = color;
        e.currentTarget.style.transform = 'translateY(-2px)';
      }}
      onMouseLeave={(e) => {
        e.currentTarget.style.borderColor = 'var(--color-border)';
        e.currentTarget.style.transform = 'none';
      }}
    >
      <div
        style={{
          position: 'absolute',
          top: 0,
          left: 0,
          width: '3px',
          height: '100%',
          background: color,
        }}
      />
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <span style={{ fontSize: '10.5px', fontWeight: '800', color: color, letterSpacing: '0.06em' }}>
          STEP {stepNumber}
        </span>
        <span
          style={{
            fontSize: '11px',
            fontWeight: '700',
            color: 'var(--color-text)',
            background: 'var(--color-surface)',
            border: '1px solid var(--color-border)',
            padding: '2px 8px',
            borderRadius: '999px',
          }}
        >
          {count} {countLabel}
        </span>
      </div>
      <div>
        <div style={{ fontSize: '13px', fontWeight: '700', color: 'var(--color-text)', marginBottom: '4px' }}>
          {title}
        </div>
        <div style={{ fontSize: '11.5px', color: 'var(--color-text-muted)', lineHeight: 1.4 }}>
          {description}
        </div>
      </div>
      <div style={{ display: 'flex', alignItems: 'center', gap: '4px', color: color, fontSize: '11px', fontWeight: '700', marginTop: 'auto', paddingTop: '6px' }}>
        <span>Inspect evidence</span>
        <ArrowRight size={12} />
      </div>
    </div>
  );
};

interface DomainSummaryCardProps {
  domainNumber: string;
  title: string;
  icon: LucideIcon;
  color: string;
  metrics: Array<{ label: string; value: string; detail: string }>;
}

const DomainSummaryCard: React.FC<DomainSummaryCardProps> = ({
  domainNumber,
  title,
  icon: Icon,
  color,
  metrics,
}) => {
  return (
    <div
      style={{
        background: 'var(--color-surface)',
        border: '1px solid var(--color-border)',
        borderRadius: 'var(--radius-md, 8px)',
        padding: '20px',
        display: 'flex',
        flexDirection: 'column',
        gap: '14px',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
        <div
          style={{
            width: '32px',
            height: '32px',
            borderRadius: '6px',
            background: `${color}18`,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            color: color,
          }}
        >
          <Icon size={16} />
        </div>
        <div>
          <div style={{ fontSize: '10.5px', fontWeight: '800', color: color, textTransform: 'uppercase', letterSpacing: '0.06em' }}>
            DOMAIN {domainNumber}
          </div>
          <div style={{ fontSize: '14.5px', fontWeight: '700', color: 'var(--color-text)' }}>
            {title}
          </div>
        </div>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
        {metrics.map((m, i) => (
          <MetricRow key={i} label={m.label} value={m.value} detail={m.detail} />
        ))}
      </div>
    </div>
  );
};

const SharedDatasetCard: React.FC<{ dataset: SharedDatasetDTO }> = ({ dataset }) => {
  return (
    <div
      style={{
        background: 'var(--color-surface-secondary)',
        border: '1px solid var(--color-border)',
        borderRadius: 'var(--radius-sm, 6px)',
        padding: '12px 16px',
        display: 'flex',
        flexDirection: 'column',
        gap: '6px',
      }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <span style={{ fontSize: '13px', fontWeight: '700', color: 'var(--color-text)' }}>
          {dataset.dataset_name}
        </span>
        <span
          style={{
            fontSize: '10.5px',
            fontWeight: '700',
            padding: '2px 6px',
            borderRadius: '4px',
            background: dataset.dataset_type === 'SOURCE' ? 'rgba(56, 189, 248, 0.15)' : 'rgba(234, 179, 8, 0.15)',
            color: dataset.dataset_type === 'SOURCE' ? '#38bdf8' : '#eab308',
            textTransform: 'uppercase',
          }}
        >
          {dataset.dataset_type}
        </span>
      </div>
      <div style={{ fontSize: '11.5px', color: 'var(--color-text-muted)' }}>
        Used by {dataset.workflow_names?.length || 0} workflows: {dataset.workflow_names?.join(', ')}
      </div>
    </div>
  );
};

const AssetStatusBadge: React.FC<{ label: string; available: boolean }> = ({ label, available }) => {
  return (
    <span
      style={{
        fontSize: '11px',
        fontWeight: '600',
        padding: '3px 8px',
        borderRadius: '4px',
        background: available ? 'rgba(52, 211, 153, 0.12)' : 'rgba(148, 163, 184, 0.1)',
        color: available ? '#34d399' : 'var(--color-text-muted)',
        border: available ? '1px solid rgba(52, 211, 153, 0.3)' : '1px solid var(--color-border)',
      }}
    >
      {available ? `✓ ${label}` : `– ${label}`}
    </span>
  );
};

interface MetricRowProps {
  label: string;
  value: string | number;
  detail: string;
}

const MetricRow: React.FC<MetricRowProps> = ({ label, value, detail }) => {
  return (
    <div
      style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'flex-start',
        padding: '6px 10px',
        borderRadius: 'var(--radius-sm, 4px)',
        background: 'var(--color-surface-secondary)',
        gap: '12px',
      }}
    >
      <div style={{ flex: 1 }}>
        <div style={{ fontSize: '12px', fontWeight: '600', color: 'var(--color-text)' }}>
          {label}
        </div>
        <div style={{ fontSize: '10.5px', color: 'var(--color-text-muted)', marginTop: '1px' }}>
          {detail}
        </div>
      </div>
      <span
        style={{
          fontSize: '11.5px',
          fontWeight: '700',
          color: 'var(--color-primary)',
          whiteSpace: 'nowrap',
          textAlign: 'right',
        }}
      >
        {value}
      </span>
    </div>
  );
};

const ChainNode: React.FC<{ step: string; label: string; desc: string; color: string }> = ({
  step,
  label,
  desc,
  color,
}) => {
  return (
    <div
      style={{
        background: 'var(--color-surface-secondary)',
        border: '1px solid var(--color-border)',
        borderRadius: 'var(--radius-sm, 6px)',
        padding: '12px',
        display: 'flex',
        flexDirection: 'column',
        gap: '4px',
        position: 'relative',
        overflow: 'hidden',
      }}
    >
      <div
        style={{
          position: 'absolute',
          top: 0,
          left: 0,
          width: '3px',
          height: '100%',
          background: color,
        }}
      />
      <span style={{ fontSize: '10px', fontWeight: '800', color: color, letterSpacing: '0.04em' }}>
        {step}
      </span>
      <div style={{ fontSize: '13px', fontWeight: '700', color: 'var(--color-text)' }}>
        {label}
      </div>
      <div style={{ fontSize: '11px', color: 'var(--color-text-muted)' }}>
        {desc}
      </div>
    </div>
  );
};
