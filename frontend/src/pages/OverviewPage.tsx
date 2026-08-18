import React from 'react';
import { AnalysisOverviewDTO } from '../types/workflow';
import { StatCard } from '../components/StatCard';
import { ExecutionOrder } from '../components/ExecutionOrder';

interface OverviewPageProps {
  overview: AnalysisOverviewDTO;
  onSelectTool?: (toolId: number) => void;
}

export const OverviewPage: React.FC<OverviewPageProps> = ({ overview, onSelectTool }) => {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '32px', maxWidth: '1050px' }}>
      {/* Section Header */}
      <div>
        <div style={{
          fontSize: '11px',
          fontWeight: '700',
          letterSpacing: '1.5px',
          color: '#38bdf8',
          textTransform: 'uppercase',
          marginBottom: '4px',
        }}>
          01 Workflow Overview
        </div>
        <h1 style={{ fontSize: '26px', fontWeight: '800', color: '#f8fafc', letterSpacing: '-0.5px' }}>
          Key metrics extracted from the workflow graph
        </h1>
      </div>

      {/* 4 Stat Cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '16px' }}>
        <StatCard
          label="Nodes"
          value={overview.metrics.total_nodes}
          colorClass="stat-card-blue"
          accentColor="#38bdf8"
          subtext="Total Alteryx tools"
        />
        <StatCard
          label="Connections"
          value={overview.metrics.total_connections}
          colorClass="stat-card-cyan"
          accentColor="#22d3ee"
          subtext="Data-flow edges"
        />
        <StatCard
          label="Inputs"
          value={overview.metrics.input_count}
          colorClass="stat-card-green"
          accentColor="#4ade80"
          subtext="Data ingestion nodes"
        />
        <StatCard
          label="Outputs"
          value={overview.metrics.output_count}
          colorClass="stat-card-yellow"
          accentColor="#facc15"
          subtext="Data destination nodes"
        />
      </div>

      {/* Execution Order Section */}
      <div>
        <div style={{
          fontSize: '11px',
          fontWeight: '700',
          letterSpacing: '1px',
          color: '#64748b',
          textTransform: 'uppercase',
          marginBottom: '10px',
        }}>
          Execution Order
        </div>
        <ExecutionOrder steps={overview.execution_order} onSelectStep={onSelectTool} />
      </div>

      {/* Workflow Metadata Table */}
      <div className="glass-card" style={{ overflow: 'hidden' }}>
        <div style={{
          padding: '16px 20px',
          borderBottom: '1px solid rgba(51, 65, 85, 0.5)',
          background: 'rgba(15, 23, 42, 0.8)',
        }}>
          <h3 style={{ fontSize: '13px', fontWeight: '700', color: '#f8fafc', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
            Workflow Metadata
          </h3>
        </div>

        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '13px' }}>
          <tbody>
            <tr style={{ borderBottom: '1px solid rgba(51, 65, 85, 0.3)' }}>
              <td style={{ padding: '14px 20px', width: '220px', color: '#94a3b8', fontWeight: '500' }}>Filename</td>
              <td style={{ padding: '14px 20px', color: '#f8fafc', fontFamily: 'monospace' }}>{overview.source.original_filename}</td>
            </tr>
            <tr style={{ borderBottom: '1px solid rgba(51, 65, 85, 0.3)' }}>
              <td style={{ padding: '14px 20px', color: '#94a3b8', fontWeight: '500' }}>Alteryx Version</td>
              <td style={{ padding: '14px 20px', color: '#38bdf8', fontFamily: 'monospace' }}>{overview.metadata.version || '2025.2'}</td>
            </tr>
            <tr style={{ borderBottom: '1px solid rgba(51, 65, 85, 0.3)' }}>
              <td style={{ padding: '14px 20px', color: '#94a3b8', fontWeight: '500' }}>Author</td>
              <td style={{ padding: '14px 20px', color: '#cbd5e1' }}>{overview.metadata.author || '—'}</td>
            </tr>
            <tr style={{ borderBottom: '1px solid rgba(51, 65, 85, 0.3)' }}>
              <td style={{ padding: '14px 20px', color: '#94a3b8', fontWeight: '500' }}>Description</td>
              <td style={{ padding: '14px 20px', color: '#cbd5e1' }}>{overview.metadata.description || '—'}</td>
            </tr>
            <tr>
              <td style={{ padding: '14px 20px', color: '#94a3b8', fontWeight: '500' }}>Total Nodes</td>
              <td style={{ padding: '14px 20px', color: '#f8fafc', fontWeight: '700' }}>{overview.metrics.total_nodes} nodes in DAG</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  );
};
