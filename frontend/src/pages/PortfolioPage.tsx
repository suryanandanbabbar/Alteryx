import React, { useState } from 'react';
import {
  Layers,
  FileCode,
  Database,
  ArrowRight,
  CheckCircle2,
  AlertTriangle,
  RefreshCw,
  Search,
  ExternalLink,
  Split,
  GitMerge,
  Filter,
  Eye,
} from 'lucide-react';
import { PortfolioOverviewDTO } from '../types/portfolio';

interface PortfolioPageProps {
  portfolio: PortfolioOverviewDTO;
  onSelectWorkflow: (workflowId: string) => void;
  onReset: () => void;
}

export const PortfolioPage: React.FC<PortfolioPageProps> = ({
  portfolio,
  onSelectWorkflow,
  onReset,
}) => {
  const [searchQuery, setSearchQuery] = useState('');
  const [activeTab, setActiveTab] = useState<'workflows' | 'datasets' | 'rationalisation'>('workflows');
  const [statusFilter, setStatusFilter] = useState<'ALL' | 'SUCCESS' | 'FAILED'>('ALL');

  const { metrics } = portfolio;

  // Filter workflows
  const filteredWorkflows = portfolio.workflows.filter((w) => {
    if (statusFilter !== 'ALL' && w.status !== statusFilter) return false;
    if (!searchQuery) return true;
    const q = searchQuery.toLowerCase();
    return (
      w.filename.toLowerCase().includes(q) ||
      w.relative_path.toLowerCase().includes(q) ||
      w.sources.some((s) => s.toLowerCase().includes(q)) ||
      w.targets.some((t) => t.toLowerCase().includes(q)) ||
      w.business_purpose.toLowerCase().includes(q)
    );
  });

  return (
    <div style={{ maxWidth: '1400px', margin: '0 auto', display: 'flex', flexDirection: 'column', gap: '32px' }}>
      {/* Portfolio Title & Action Bar */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '16px' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '6px' }}>
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
              ETL Rationalisation
            </span>
            <span style={{ fontSize: '13px', color: 'var(--color-text-muted)' }}>
              Portfolio ID: <code style={{ fontSize: '12px' }}>{portfolio.portfolio_id}</code>
            </span>
          </div>
          <h1 style={{ fontSize: '28px', fontWeight: '800', color: 'var(--color-text)', letterSpacing: '-0.5px', margin: 0 }}>
            {portfolio.portfolio_name}
          </h1>
          <p style={{ fontSize: '14px', color: 'var(--color-text-secondary)', margin: '4px 0 0 0' }}>
            Cross-workflow lineage intelligence, shared data asset analysis, and migration rationalisation foundation.
          </p>
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

      {/* Aggregate KPI Stat Cards */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
          gap: '16px',
        }}
      >
        <div className="app-card" style={{ padding: '20px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', color: 'var(--color-text-muted)', marginBottom: '8px' }}>
            <span style={{ fontSize: '12px', fontWeight: '700', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Workflows</span>
            <Layers size={18} color="var(--color-primary)" />
          </div>
          <div style={{ fontSize: '26px', fontWeight: '800', color: 'var(--color-text)' }}>
            {metrics.total_workflows}
          </div>
          <div style={{ fontSize: '12px', color: 'var(--color-text-secondary)', marginTop: '4px', display: 'flex', gap: '8px' }}>
            <span style={{ color: '#16a34a', fontWeight: '600' }}>✓ {metrics.successful_workflows} Analyzed</span>
            {metrics.failed_workflows > 0 && (
              <span style={{ color: '#dc2626', fontWeight: '600' }}>⚠ {metrics.failed_workflows} Failed</span>
            )}
          </div>
        </div>

        <div className="app-card" style={{ padding: '20px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', color: 'var(--color-text-muted)', marginBottom: '8px' }}>
            <span style={{ fontSize: '12px', fontWeight: '700', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Unique Sources</span>
            <Database size={18} color="#2563eb" />
          </div>
          <div style={{ fontSize: '26px', fontWeight: '800', color: 'var(--color-text)' }}>
            {metrics.unique_sources}
          </div>
          <div style={{ fontSize: '12px', color: 'var(--color-text-secondary)', marginTop: '4px' }}>
            <strong style={{ color: metrics.shared_sources_count > 0 ? 'var(--color-primary)' : 'inherit' }}>
              {metrics.shared_sources_count} shared
            </strong>{' '}
            across workflows
          </div>
        </div>

        <div className="app-card" style={{ padding: '20px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', color: 'var(--color-text-muted)', marginBottom: '8px' }}>
            <span style={{ fontSize: '12px', fontWeight: '700', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Production Targets</span>
            <CheckCircle2 size={18} color="#16a34a" />
          </div>
          <div style={{ fontSize: '26px', fontWeight: '800', color: 'var(--color-text)' }}>
            {metrics.unique_targets}
          </div>
          <div style={{ fontSize: '12px', color: 'var(--color-text-secondary)', marginTop: '4px' }}>
            {metrics.inspection_sinks_count} inspection sink(s)
          </div>
        </div>

        <div className="app-card" style={{ padding: '20px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', color: 'var(--color-text-muted)', marginBottom: '8px' }}>
            <span style={{ fontSize: '12px', fontWeight: '700', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Total Operations</span>
            <FileCode size={18} color="#9333ea" />
          </div>
          <div style={{ fontSize: '26px', fontWeight: '800', color: 'var(--color-text)' }}>
            {metrics.total_tools}
          </div>
          <div style={{ fontSize: '12px', color: 'var(--color-text-secondary)', marginTop: '4px' }}>
            Across {Object.keys(metrics.tool_distribution).length} tool types
          </div>
        </div>

        <div className="app-card" style={{ padding: '20px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', color: 'var(--color-text-muted)', marginBottom: '8px' }}>
            <span style={{ fontSize: '12px', fontWeight: '700', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Rationalisation</span>
            <GitMerge size={18} color="#ea580c" />
          </div>
          <div style={{ fontSize: '26px', fontWeight: '800', color: 'var(--color-text)' }}>
            {portfolio.rationalisation_candidates.length}
          </div>
          <div style={{ fontSize: '12px', color: 'var(--color-text-secondary)', marginTop: '4px' }}>
            {portfolio.relationships.length} candidate relationship(s)
          </div>
        </div>
      </div>

      {/* Navigation Tabs */}
      <div style={{ borderBottom: '1px solid var(--color-border)', display: 'flex', gap: '24px' }}>
        <button
          onClick={() => setActiveTab('workflows')}
          style={{
            padding: '12px 4px',
            fontSize: '14px',
            fontWeight: activeTab === 'workflows' ? '700' : '500',
            color: activeTab === 'workflows' ? 'var(--color-primary)' : 'var(--color-text-secondary)',
            borderBottom: activeTab === 'workflows' ? '2px solid var(--color-primary)' : '2px solid transparent',
            background: 'none',
            border: 'none',
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
          }}
        >
          <Layers size={16} /> Workflows ({portfolio.workflows.length})
        </button>

        <button
          onClick={() => setActiveTab('datasets')}
          style={{
            padding: '12px 4px',
            fontSize: '14px',
            fontWeight: activeTab === 'datasets' ? '700' : '500',
            color: activeTab === 'datasets' ? 'var(--color-primary)' : 'var(--color-text-secondary)',
            borderBottom: activeTab === 'datasets' ? '2px solid var(--color-primary)' : '2px solid transparent',
            background: 'none',
            border: 'none',
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
          }}
        >
          <Database size={16} /> Shared Datasets ({portfolio.shared_sources.length + portfolio.shared_targets.length})
        </button>

        <button
          onClick={() => setActiveTab('rationalisation')}
          style={{
            padding: '12px 4px',
            fontSize: '14px',
            fontWeight: activeTab === 'rationalisation' ? '700' : '500',
            color: activeTab === 'rationalisation' ? 'var(--color-primary)' : 'var(--color-text-secondary)',
            borderBottom: activeTab === 'rationalisation' ? '2px solid var(--color-primary)' : '2px solid transparent',
            background: 'none',
            border: 'none',
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
          }}
        >
          <Split size={16} /> Rationalisation Candidates ({portfolio.rationalisation_candidates.length})
        </button>
      </div>

      {/* Tab 1: Workflows List */}
      {activeTab === 'workflows' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          {/* Search & Filter Toolbar */}
          <div style={{ display: 'flex', gap: '12px', alignItems: 'center', flexWrap: 'wrap' }}>
            <div
              style={{
                flex: 1,
                minWidth: '260px',
                position: 'relative',
                display: 'flex',
                alignItems: 'center',
              }}
            >
              <Search size={16} color="var(--color-text-muted)" style={{ position: 'absolute', left: '12px' }} />
              <input
                type="text"
                placeholder="Search workflows, paths, datasets, or business purpose..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                style={{
                  width: '100%',
                  padding: '9px 12px 9px 36px',
                  borderRadius: 'var(--radius-sm)',
                  border: '1px solid var(--color-border)',
                  background: 'var(--color-surface)',
                  color: 'var(--color-text)',
                  fontSize: '13px',
                }}
              />
            </div>

            <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
              <Filter size={14} color="var(--color-text-muted)" />
              {(['ALL', 'SUCCESS', 'FAILED'] as const).map((s) => (
                <button
                  key={s}
                  onClick={() => setStatusFilter(s)}
                  style={{
                    padding: '6px 12px',
                    fontSize: '12px',
                    fontWeight: statusFilter === s ? '700' : '500',
                    borderRadius: 'var(--radius-sm)',
                    border: '1px solid var(--color-border)',
                    background: statusFilter === s ? 'var(--color-primary-subtle)' : 'var(--color-surface)',
                    color: statusFilter === s ? 'var(--color-primary)' : 'var(--color-text-secondary)',
                    cursor: 'pointer',
                  }}
                >
                  {s}
                </button>
              ))}
            </div>
          </div>

          {/* Workflow Table */}
          <div className="app-card" style={{ overflow: 'hidden', padding: 0 }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '13px' }}>
              <thead>
                <tr style={{ background: 'var(--color-surface-secondary)', borderBottom: '1px solid var(--color-border)' }}>
                  <th style={{ padding: '14px 20px', fontWeight: '700', color: 'var(--color-text-secondary)' }}>Workflow</th>
                  <th style={{ padding: '14px 16px', fontWeight: '700', color: 'var(--color-text-secondary)' }}>Status</th>
                  <th style={{ padding: '14px 16px', fontWeight: '700', color: 'var(--color-text-secondary)' }}>Sources</th>
                  <th style={{ padding: '14px 16px', fontWeight: '700', color: 'var(--color-text-secondary)' }}>Targets / Sinks</th>
                  <th style={{ padding: '14px 16px', fontWeight: '700', color: 'var(--color-text-secondary)' }}>Tools</th>
                  <th style={{ padding: '14px 16px', fontWeight: '700', color: 'var(--color-text-secondary)' }}>Business Purpose</th>
                  <th style={{ padding: '14px 20px', fontWeight: '700', color: 'var(--color-text-secondary)', textAlign: 'right' }}>Action</th>
                </tr>
              </thead>
              <tbody>
                {filteredWorkflows.map((wf) => {
                  const isSuccess = wf.status === 'SUCCESS';
                  return (
                    <tr
                      key={wf.workflow_id}
                      onClick={() => isSuccess && onSelectWorkflow(wf.workflow_id)}
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
                      <td style={{ padding: '14px 20px' }}>
                        <div style={{ fontWeight: '700', color: 'var(--color-text)' }}>{wf.filename}</div>
                        {wf.relative_path && wf.relative_path !== wf.filename && (
                          <div style={{ fontSize: '11px', color: 'var(--color-text-muted)', marginTop: '2px' }}>
                            {wf.relative_path}
                          </div>
                        )}
                      </td>

                      <td style={{ padding: '14px 16px' }}>
                        {isSuccess ? (
                          <span
                            style={{
                              display: 'inline-flex',
                              alignItems: 'center',
                              gap: '4px',
                              padding: '3px 8px',
                              borderRadius: '4px',
                              fontSize: '11px',
                              fontWeight: '700',
                              background: '#dcfce7',
                              color: '#15803d',
                            }}
                          >
                            <CheckCircle2 size={12} /> Analyzed
                          </span>
                        ) : (
                          <span
                            style={{
                              display: 'inline-flex',
                              alignItems: 'center',
                              gap: '4px',
                              padding: '3px 8px',
                              borderRadius: '4px',
                              fontSize: '11px',
                              fontWeight: '700',
                              background: '#fee2e2',
                              color: '#b91c1c',
                            }}
                            title={wf.error_message || 'Analysis failed'}
                          >
                            <AlertTriangle size={12} /> Failed
                          </span>
                        )}
                      </td>

                      <td style={{ padding: '14px 16px' }}>
                        <div style={{ fontWeight: '600' }}>{wf.source_count} source(s)</div>
                        {wf.sources.length > 0 && (
                          <div style={{ fontSize: '11px', color: 'var(--color-text-muted)', marginTop: '2px', maxWidth: '200px', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }} title={wf.sources.join(', ')}>
                            {wf.sources.join(', ')}
                          </div>
                        )}
                      </td>

                      <td style={{ padding: '14px 16px' }}>
                        {wf.target_count > 0 ? (
                          <>
                            <div style={{ fontWeight: '600', color: '#16a34a' }}>{wf.target_count} target(s)</div>
                            <div style={{ fontSize: '11px', color: 'var(--color-text-muted)', marginTop: '2px', maxWidth: '200px', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }} title={wf.targets.join(', ')}>
                              {wf.targets.join(', ')}
                            </div>
                          </>
                        ) : wf.inspection_sinks.length > 0 ? (
                          <div style={{ fontSize: '12px', color: 'var(--color-text-muted)' }}>
                            <Eye size={12} style={{ display: 'inline', marginRight: '4px' }} />
                            {wf.inspection_sinks.length} inspection sink(s)
                          </div>
                        ) : (
                          <span style={{ fontSize: '12px', color: 'var(--color-text-muted)' }}>None</span>
                        )}
                      </td>

                      <td style={{ padding: '14px 16px', fontWeight: '600' }}>
                        {wf.node_count}
                      </td>

                      <td style={{ padding: '14px 16px', maxWidth: '300px' }}>
                        <div
                          style={{
                            fontSize: '12px',
                            color: 'var(--color-text-secondary)',
                            lineHeight: 1.4,
                            display: '-webkit-box',
                            WebkitLineClamp: 2,
                            WebkitBoxOrient: 'vertical',
                            overflow: 'hidden',
                          }}
                          title={wf.business_purpose || (wf.error_message ? `Error: ${wf.error_message}` : 'None')}
                        >
                          {wf.business_purpose || (wf.error_message ? `Error: ${wf.error_message}` : '—')}
                        </div>
                      </td>

                      <td style={{ padding: '14px 20px', textAlign: 'right' }}>
                        {isSuccess && (
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              onSelectWorkflow(wf.workflow_id);
                            }}
                            style={{
                              display: 'inline-flex',
                              alignItems: 'center',
                              gap: '4px',
                              padding: '6px 12px',
                              fontSize: '12px',
                              fontWeight: '600',
                              borderRadius: 'var(--radius-sm)',
                              border: '1px solid var(--color-primary)',
                              background: 'transparent',
                              color: 'var(--color-primary)',
                              cursor: 'pointer',
                            }}
                          >
                            Inspect <ArrowRight size={13} />
                          </button>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Tab 2: Shared Datasets */}
      {activeTab === 'datasets' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
          <div>
            <h2 style={{ fontSize: '18px', fontWeight: '700', color: 'var(--color-text)', marginBottom: '8px' }}>
              Shared Source Datasets
            </h2>
            <p style={{ fontSize: '13px', color: 'var(--color-text-secondary)', marginBottom: '16px' }}>
              Physical input files and tables consumed by two or more workflows across the portfolio.
            </p>

            {portfolio.shared_sources.length === 0 ? (
              <div className="app-card" style={{ padding: '32px', textAlign: 'center', color: 'var(--color-text-muted)' }}>
                No shared source datasets detected across workflows.
              </div>
            ) : (
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(350px, 1fr))', gap: '16px' }}>
                {portfolio.shared_sources.map((src) => (
                  <div key={src.dataset_name} className="app-card" style={{ padding: '18px' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px' }}>
                      <Database size={16} color="var(--color-primary)" />
                      <span style={{ fontWeight: '700', fontSize: '14px', color: 'var(--color-text)' }}>
                        {src.dataset_name}
                      </span>
                    </div>
                    <div style={{ fontSize: '12px', color: 'var(--color-text-muted)', marginBottom: '12px' }}>
                      Consumed by {src.workflow_ids.length} workflows:
                    </div>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                      {src.workflow_names.map((wname, idx) => (
                        <div
                          key={src.workflow_ids[idx]}
                          onClick={() => onSelectWorkflow(src.workflow_ids[idx])}
                          style={{
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'space-between',
                            padding: '6px 10px',
                            background: 'var(--color-surface-secondary)',
                            borderRadius: '4px',
                            fontSize: '12px',
                            color: 'var(--color-text)',
                            cursor: 'pointer',
                          }}
                        >
                          <span>{wname}</span>
                          <ExternalLink size={12} color="var(--color-primary)" />
                        </div>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          <div>
            <h2 style={{ fontSize: '18px', fontWeight: '700', color: 'var(--color-text)', marginBottom: '8px' }}>
              Shared Target Deliverables
            </h2>
            <p style={{ fontSize: '13px', color: 'var(--color-text-secondary)', marginBottom: '16px' }}>
              Deliverable outputs produced or written to by two or more workflows.
            </p>

            {portfolio.shared_targets.length === 0 ? (
              <div className="app-card" style={{ padding: '32px', textAlign: 'center', color: 'var(--color-text-muted)' }}>
                No shared target deliverables detected across workflows.
              </div>
            ) : (
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(350px, 1fr))', gap: '16px' }}>
                {portfolio.shared_targets.map((tgt) => (
                  <div key={tgt.dataset_name} className="app-card" style={{ padding: '18px' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px' }}>
                      <CheckCircle2 size={16} color="#16a34a" />
                      <span style={{ fontWeight: '700', fontSize: '14px', color: 'var(--color-text)' }}>
                        {tgt.dataset_name}
                      </span>
                    </div>
                    <div style={{ fontSize: '12px', color: 'var(--color-text-muted)', marginBottom: '12px' }}>
                      Produced by {tgt.workflow_ids.length} workflows:
                    </div>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                      {tgt.workflow_names.map((wname, idx) => (
                        <div
                          key={tgt.workflow_ids[idx]}
                          onClick={() => onSelectWorkflow(tgt.workflow_ids[idx])}
                          style={{
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'space-between',
                            padding: '6px 10px',
                            background: 'var(--color-surface-secondary)',
                            borderRadius: '4px',
                            fontSize: '12px',
                            color: 'var(--color-text)',
                            cursor: 'pointer',
                          }}
                        >
                          <span>{wname}</span>
                          <ExternalLink size={12} color="var(--color-primary)" />
                        </div>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Tab 3: Rationalisation Candidates */}
      {activeTab === 'rationalisation' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
          <div>
            <h2 style={{ fontSize: '18px', fontWeight: '700', color: 'var(--color-text)', marginBottom: '6px' }}>
              ETL Rationalisation & Consolidation Candidates
            </h2>
            <p style={{ fontSize: '13px', color: 'var(--color-text-secondary)', margin: 0 }}>
              Actionable migration candidates identified by multi-signal deterministic evidence and qualified by semantic architectural analysis.
            </p>
          </div>

          {portfolio.rationalisation_candidates.length === 0 ? (
            <div className="app-card" style={{ padding: '40px', textAlign: 'center', color: 'var(--color-text-muted)' }}>
              No rationalisation candidates identified for this portfolio.
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
              {portfolio.rationalisation_candidates.map((cand, idx) => {
                const isConsolidate = cand.recommendation_type === 'CONSOLIDATE';
                const isRetire = cand.recommendation_type === 'RETIRE_CANDIDATE';
                const isShared = cand.recommendation_type === 'SHARED_LOGIC';

                const badgeBg = isConsolidate ? '#fee2e2' : isRetire ? '#fef3c7' : isShared ? '#e0e7ff' : 'var(--color-surface-secondary)';
                const badgeColor = isConsolidate ? '#b91c1c' : isRetire ? '#b45309' : isShared ? '#4338ca' : 'var(--color-text)';

                return (
                  <div key={idx} className="app-card" style={{ padding: '24px' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '12px' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                        <span
                          style={{
                            padding: '4px 10px',
                            borderRadius: '4px',
                            fontSize: '11px',
                            fontWeight: '800',
                            textTransform: 'uppercase',
                            background: badgeBg,
                            color: badgeColor,
                          }}
                        >
                          {cand.recommendation_type.replace('_', ' ')}
                        </span>
                        <span style={{ fontSize: '12px', fontWeight: '600', color: 'var(--color-text-secondary)' }}>
                          Confidence: {cand.confidence}
                        </span>
                      </div>

                      <div style={{ display: 'flex', gap: '8px' }}>
                        {cand.workflow_ids.map((wid, wIdx) => (
                          <button
                            key={wid}
                            onClick={() => onSelectWorkflow(wid)}
                            style={{
                              display: 'inline-flex',
                              alignItems: 'center',
                              gap: '4px',
                              padding: '5px 10px',
                              borderRadius: '4px',
                              border: '1px solid var(--color-border)',
                              background: 'var(--color-surface)',
                              fontSize: '11px',
                              fontWeight: '600',
                              color: 'var(--color-text)',
                              cursor: 'pointer',
                            }}
                          >
                            {cand.workflow_names[wIdx]} <ArrowRight size={11} />
                          </button>
                        ))}
                      </div>
                    </div>

                    <p style={{ fontSize: '14px', color: 'var(--color-text)', lineHeight: 1.5, margin: '0 0 16px 0', fontWeight: '500' }}>
                      {cand.reasoning}
                    </p>

                    {/* Auditable Deterministic Evidence List */}
                    <div style={{ background: 'var(--color-surface-secondary)', padding: '12px 16px', borderRadius: 'var(--radius-sm)' }}>
                      <div style={{ fontSize: '11px', fontWeight: '700', textTransform: 'uppercase', letterSpacing: '0.06em', color: 'var(--color-text-muted)', marginBottom: '6px' }}>
                        Auditable Deterministic Evidence
                      </div>
                      <ul style={{ margin: 0, paddingLeft: '18px', fontSize: '12px', color: 'var(--color-text-secondary)', lineHeight: 1.5 }}>
                        {cand.evidence.map((ev, eIdx) => (
                          <li key={eIdx}>{ev}</li>
                        ))}
                      </ul>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}
    </div>
  );
};
