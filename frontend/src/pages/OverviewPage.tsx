import React from 'react';
import { AnalysisOverviewDTO } from '../types/workflow';
import { StatCard } from '../components/StatCard';
import { ExecutionOrder } from '../components/ExecutionOrder';
import { getCategoryColor } from '../theme/palette';
import { ArrowRight } from 'lucide-react';

interface OverviewPageProps {
  overview: AnalysisOverviewDTO;
  onSelectTool?: (toolId: number) => void;
}

export const OverviewPage: React.FC<OverviewPageProps> = ({ overview, onSelectTool }) => {
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
          Workflow Metrics & Process Overview
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

      {/* Execution Flow Diagram */}
      <ExecutionOrder steps={overview.execution_order} onSelectStep={onSelectTool} />

      {/* Workflow Tools (Business-Friendly Process Steps) */}
      <div className="app-card" style={{ overflow: 'hidden' }}>
        <div style={{
          padding: '14px 18px',
          borderBottom: '1px solid var(--color-border)',
          background: 'var(--color-surface-secondary)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
        }}>
          <div>
            <h3 style={{ fontSize: '12px', fontWeight: '700', color: 'var(--color-text)', textTransform: 'uppercase', letterSpacing: '0.5px', margin: 0 }}>
              Workflow Tools & Business Process Steps
            </h3>
            <span style={{ fontSize: '11px', color: 'var(--color-text-muted)', marginTop: '2px', display: 'block' }}>
              Sequential execution breakdown and business function descriptions ({overview.execution_order.length} tools)
            </span>
          </div>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column' }}>
          {overview.execution_order.map((step, idx) => {
            const catColor = getCategoryColor(step.visual_category);
            const isLast = idx === overview.execution_order.length - 1;

            return (
              <div
                key={step.tool_id}
                onClick={() => onSelectTool && onSelectTool(step.tool_id)}
                style={{
                  padding: '14px 18px',
                  display: 'flex',
                  alignItems: 'flex-start',
                  gap: '16px',
                  borderBottom: isLast ? 'none' : '1px solid var(--color-border-subtle)',
                  cursor: onSelectTool ? 'pointer' : 'default',
                  transition: 'background-color 0.15s ease',
                  backgroundColor: 'var(--color-surface)',
                }}
                onMouseEnter={(e) => {
                  if (onSelectTool) {
                    e.currentTarget.style.backgroundColor = 'var(--color-surface-hover)';
                  }
                }}
                onMouseLeave={(e) => {
                  if (onSelectTool) {
                    e.currentTarget.style.backgroundColor = 'var(--color-surface)';
                  }
                }}
              >
                {/* Step Number Badge */}
                <div style={{
                  fontFamily: 'var(--font-mono)',
                  fontSize: '12px',
                  fontWeight: '700',
                  color: 'var(--color-primary)',
                  background: 'var(--color-primary-subtle)',
                  border: '1px solid rgba(234, 88, 12, 0.25)',
                  padding: '4px 8px',
                  borderRadius: 'var(--radius-sm)',
                  flexShrink: 0,
                  minWidth: '28px',
                  textAlign: 'center',
                }}>
                  {String(step.step_number).padStart(2, '0')}
                </div>

                {/* Tool Details & Summary */}
                <div style={{ display: 'flex', flexDirection: 'column', gap: '4px', flex: 1 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
                    <span style={{ fontSize: '13px', fontWeight: '700', color: 'var(--color-text)' }}>
                      {step.name || step.tool_type}
                    </span>
                    <span style={{
                      fontSize: '10.5px',
                      fontWeight: '600',
                      color: catColor.text,
                      background: catColor.badgeBg,
                      border: `1px solid ${catColor.stroke}`,
                      padding: '1px 6px',
                      borderRadius: 'var(--radius-sm)',
                    }}>
                      {step.tool_type}
                    </span>
                    <span style={{ fontSize: '11px', color: 'var(--color-text-muted)', fontFamily: 'var(--font-mono)' }}>
                      #{step.tool_id}
                    </span>
                  </div>

                  {/* Business Summary */}
                  <div style={{ fontSize: '12.5px', color: 'var(--color-text-secondary)', lineHeight: '1.45' }}>
                    {step.summary || 'Processes records in the workflow data pipeline.'}
                  </div>
                </div>

                {onSelectTool && (
                  <div style={{ alignSelf: 'center', color: 'var(--color-text-muted)', flexShrink: 0 }}>
                    <ArrowRight size={14} />
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>

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
    </div>
  );
};
