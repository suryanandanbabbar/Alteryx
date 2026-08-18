import React from 'react';
import { AnalysisOverviewDTO } from '../types/workflow';
import { StatCard } from '../components/StatCard';
import { ExecutionOrder } from '../components/ExecutionOrder';
import { AlertCircle, CheckCircle2 } from 'lucide-react';

interface OverviewPageProps {
  overview: AnalysisOverviewDTO;
  onSelectTool?: (toolId: number) => void;
}

export const OverviewPage: React.FC<OverviewPageProps> = ({ overview, onSelectTool }) => {
  const hasDiagnostics = overview.diagnostics && overview.diagnostics.length > 0;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px', maxWidth: '1000px' }}>
      {/* Section Subtitle */}
      <div>
        <div style={{
          fontSize: '11px',
          fontWeight: '700',
          letterSpacing: '1px',
          color: 'var(--color-primary)',
          textTransform: 'uppercase',
          marginBottom: '4px',
        }}>
          01 Overview
        </div>
        <h2 style={{ fontSize: '20px', fontWeight: '800', color: 'var(--color-text)', letterSpacing: '-0.3px', margin: 0 }}>
          Workflow Metrics & Execution Graph
        </h2>
      </div>

      {/* 4 Stat Cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '12px' }}>
        <StatCard
          label="Total Tools"
          value={overview.metrics.total_nodes}
          subtext="Workflow nodes"
          accentColor="var(--color-primary)"
        />
        <StatCard
          label="Connections"
          value={overview.metrics.total_connections}
          subtext="Data-flow edges"
        />
        <StatCard
          label="Data Inputs"
          value={overview.metrics.input_count}
          subtext="Source nodes"
        />
        <StatCard
          label="Data Outputs"
          value={overview.metrics.output_count}
          subtext="Destination nodes"
        />
      </div>

      {/* Execution Order */}
      <ExecutionOrder steps={overview.execution_order} onSelectStep={onSelectTool} />

      {/* Workflow Metadata Table */}
      <div className="app-card" style={{ overflow: 'hidden' }}>
        <div style={{
          padding: '12px 16px',
          borderBottom: '1px solid var(--color-border)',
          background: 'var(--color-surface-secondary)',
        }}>
          <h3 style={{ fontSize: '12px', fontWeight: '700', color: 'var(--color-text)', textTransform: 'uppercase', letterSpacing: '0.5px', margin: 0 }}>
            Workflow Properties
          </h3>
        </div>

        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '13px' }}>
          <tbody>
            <tr style={{ borderBottom: '1px solid var(--color-border-subtle)' }}>
              <td style={{ padding: '10px 16px', width: '200px', color: 'var(--color-text-muted)', fontWeight: '500' }}>Original Filename</td>
              <td style={{ padding: '10px 16px', color: 'var(--color-text)', fontFamily: 'var(--font-mono)' }}>{overview.source.original_filename}</td>
            </tr>
            <tr style={{ borderBottom: '1px solid var(--color-border-subtle)' }}>
              <td style={{ padding: '10px 16px', color: 'var(--color-text-muted)', fontWeight: '500' }}>Source Format</td>
              <td style={{ padding: '10px 16px', color: 'var(--color-text)', fontFamily: 'var(--font-mono)' }}>.{overview.source.source_format}</td>
            </tr>
            <tr style={{ borderBottom: '1px solid var(--color-border-subtle)' }}>
              <td style={{ padding: '10px 16px', color: 'var(--color-text-muted)', fontWeight: '500' }}>Alteryx Version</td>
              <td style={{ padding: '10px 16px', color: 'var(--color-text)', fontFamily: 'var(--font-mono)' }}>{overview.metadata.version || '2024.1'}</td>
            </tr>
            <tr style={{ borderBottom: '1px solid var(--color-border-subtle)' }}>
              <td style={{ padding: '10px 16px', color: 'var(--color-text-muted)', fontWeight: '500' }}>Author</td>
              <td style={{ padding: '10px 16px', color: 'var(--color-text-secondary)' }}>{overview.metadata.author || '—'}</td>
            </tr>
            <tr>
              <td style={{ padding: '10px 16px', color: 'var(--color-text-muted)', fontWeight: '500' }}>Description</td>
              <td style={{ padding: '10px 16px', color: 'var(--color-text-secondary)' }}>{overview.metadata.description || '—'}</td>
            </tr>
          </tbody>
        </table>
      </div>

      {/* Diagnostics Summary Card */}
      <div className="app-card" style={{ padding: '16px 20px' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '10px' }}>
          <div style={{ fontSize: '12px', fontWeight: '700', color: 'var(--color-text)', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
            Analysis Diagnostics & Tool Support
          </div>
          <div style={{ display: 'flex', gap: '8px' }}>
            {Object.entries(overview.metrics.support_summary).map(([level, count]) => (
              <span
                key={level}
                style={{
                  fontSize: '11px',
                  fontWeight: '600',
                  color: level === 'supported' ? 'var(--color-success)' : 'var(--color-warning)',
                  background: level === 'supported' ? 'var(--color-success-subtle)' : 'var(--color-warning-subtle)',
                  padding: '2px 8px',
                  borderRadius: 'var(--radius-sm)',
                  border: `1px solid ${level === 'supported' ? 'rgba(34, 197, 94, 0.3)' : 'rgba(245, 158, 11, 0.3)'}`,
                }}
              >
                {count} {level}
              </span>
            ))}
          </div>
        </div>

        {hasDiagnostics ? (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', marginTop: '12px' }}>
            {overview.diagnostics.map((diag, idx) => (
              <div
                key={idx}
                style={{
                  display: 'flex',
                  alignItems: 'flex-start',
                  gap: '10px',
                  padding: '10px 12px',
                  background: 'var(--color-surface-secondary)',
                  border: '1px solid var(--color-border)',
                  borderRadius: 'var(--radius-sm)',
                  fontSize: '12px',
                }}
              >
                <AlertCircle size={15} color="var(--color-warning)" style={{ marginTop: '2px', flexShrink: 0 }} />
                <div style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
                  <div style={{ color: 'var(--color-text)', fontWeight: '600' }}>
                    {diag.message}
                  </div>
                  {diag.detail && (
                    <div style={{ color: 'var(--color-text-muted)', fontSize: '11px' }}>
                      {diag.detail}
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: 'var(--color-success)', fontSize: '12px', marginTop: '6px' }}>
            <CheckCircle2 size={14} />
            <span>All workflow tools are supported with deterministic Python translations.</span>
          </div>
        )}
      </div>
    </div>
  );
};
