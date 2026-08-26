import React, { useState, useMemo } from 'react';
import { AnalysisOverviewDTO, BusinessStageDTO } from '../types/workflow';
import {
  ArrowRight,
  ChevronDown,
  ChevronUp,
  ArrowUpRight,
} from 'lucide-react';

interface OverviewPageProps {
  overview: AnalysisOverviewDTO;
  onSelectTool?: (toolId: number) => void;
  onNavigateToDiagram?: () => void;
}

export const OverviewPage: React.FC<OverviewPageProps> = ({
  overview,
  onSelectTool,
  onNavigateToDiagram,
}) => {
  const bs = overview.business_summary;
  const [expandedStage, setExpandedStage] = useState<number | null>(null);

  // Map tool_id to direct Alteryx tool name and details
  const toolMap = useMemo(() => {
    const map = new Map<number, { name: string; tool_type: string; visual_category: string }>();
    overview.execution_order.forEach((step) => {
      map.set(step.tool_id, {
        name: step.name || step.tool_type,
        tool_type: step.tool_type,
        visual_category: step.visual_category,
      });
    });
    return map;
  }, [overview.execution_order]);

  const toggleStage = (stageNum: number) => {
    setExpandedStage((prev) => (prev === stageNum ? null : stageNum));
  };

  const workflowName = overview.metadata.name || 'Alteryx Workflow';
  const oneLinePurpose = bs?.one_line_purpose || 'Data preparation and reporting workflow';

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px', maxWidth: '1400px', width: '100%' }}>
      {/* 1. Header & Compact Metrics Strip */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
        <div>
          <div style={{
            fontSize: '11px',
            fontWeight: '700',
            letterSpacing: '1px',
            color: 'var(--color-primary)',
            textTransform: 'uppercase',
            marginBottom: '4px',
          }}>
            Workflow Overview
          </div>
          <h1 style={{ fontSize: '24px', fontWeight: '800', color: 'var(--color-text)', letterSpacing: '-0.4px', margin: 0 }}>
            {workflowName}
          </h1>
          <p style={{ fontSize: '14px', color: 'var(--color-text-secondary)', margin: '4px 0 0 0' }}>
            {oneLinePurpose}
          </p>
        </div>

        {/* Compact Metrics Strip */}
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: '16px',
          flexWrap: 'wrap',
          background: 'var(--color-surface-secondary)',
          padding: '10px 16px',
          borderRadius: 'var(--radius-md)',
          border: '1px solid var(--color-border)',
          fontSize: '13px',
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <span style={{ fontWeight: '700', color: 'var(--color-text)' }}>{overview.metrics.total_nodes}</span>
            <span style={{ color: 'var(--color-text-muted)' }}>Tools</span>
          </div>
          <span style={{ color: 'var(--color-border)' }}>|</span>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <span style={{ fontWeight: '700', color: 'var(--color-text)' }}>{overview.metrics.total_connections}</span>
            <span style={{ color: 'var(--color-text-muted)' }}>Connections</span>
          </div>
          <span style={{ color: 'var(--color-border)' }}>|</span>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <span style={{ fontWeight: '700', color: 'var(--color-text)' }}>
              {bs?.source_inputs.length ?? overview.metrics.input_count}
            </span>
            <span style={{ color: 'var(--color-text-muted)' }}>Inputs</span>
          </div>
          <span style={{ color: 'var(--color-border)' }}>|</span>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <span style={{ fontWeight: '700', color: 'var(--color-text)' }}>
              {bs?.business_outputs.length ?? overview.metrics.output_count}
            </span>
            <span style={{ color: 'var(--color-text-muted)' }}>Outputs</span>
          </div>
        </div>
      </div>

      {/* 2. Business Purpose Card (1-2 sentences) */}
      {bs?.business_purpose && (
        <div className="app-card" style={{ padding: '16px 20px', borderLeft: '3px solid var(--color-primary)' }}>
          <div style={{
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            marginBottom: '6px',
          }}>
            <span style={{
              fontSize: '11px',
              fontWeight: '700',
              color: 'var(--color-primary)',
              textTransform: 'uppercase',
              letterSpacing: '0.5px',
            }}>
              Business Purpose
            </span>
            <span style={{
              fontSize: '9.5px',
              fontWeight: '600',
              padding: '1px 6px',
              borderRadius: 'var(--radius-sm, 4px)',
              background: 'var(--color-primary-subtle)',
              color: 'var(--color-primary)',
              border: '1px solid var(--color-primary-border)',
              letterSpacing: '0.3px',
              textTransform: 'none',
              lineHeight: '1.4',
              display: 'inline-flex',
              alignItems: 'center',
            }}>
              AI Generated
            </span>
          </div>
          <p style={{ fontSize: '14px', color: 'var(--color-text)', lineHeight: '1.5', margin: 0, fontWeight: '500' }}>
            {bs.business_purpose}
          </p>
        </div>
      )}

      {/* 3. Visual High-Level Flow: INPUTS ──► PROCESS ──► OUTPUTS (Single Unified Outputs Display) */}
      {bs && (
        <div className="app-card" style={{ padding: '18px 20px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '14px' }}>
            <div style={{ fontSize: '11.5px', fontWeight: '700', color: 'var(--color-text)', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
              High Level Lineage
            </div>
            {onNavigateToDiagram && (
              <button
                onClick={onNavigateToDiagram}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '4px',
                  background: 'none',
                  border: 'none',
                  color: 'var(--color-primary)',
                  fontSize: '12px',
                  fontWeight: '600',
                  cursor: 'pointer',
                  padding: '2px 6px',
                }}
              >
                <span>View End-To-End Lineage</span>
                <ArrowUpRight size={13} />
              </button>
            )}
          </div>

          <div style={{
            display: 'grid',
            gridTemplateColumns: 'minmax(180px, 1fr) auto minmax(180px, 1.2fr) auto minmax(180px, 1fr)',
            gap: '12px',
            alignItems: 'center',
            background: 'var(--color-surface-secondary)',
            padding: '16px',
            borderRadius: 'var(--radius-sm)',
            border: '1px solid var(--color-border)',
          }}>
            {/* Inputs Column */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
              <div style={{ fontSize: '10.5px', fontWeight: '700', color: 'var(--color-text-muted)', textTransform: 'uppercase' }}>
                Sources ({bs.source_inputs.length})
              </div>
              {bs.source_inputs.map((inp, idx) => (
                <div key={idx} style={{
                  fontSize: '12px',
                  fontWeight: '600',
                  color: 'var(--color-text)',
                  background: 'var(--color-surface)',
                  padding: '6px 10px',
                  borderRadius: 'var(--radius-sm)',
                  border: '1px solid var(--color-border)',
                  whiteSpace: 'nowrap',
                  overflow: 'hidden',
                  textOverflow: 'ellipsis',
                }}>
                  {inp.source_filename || inp.name}
                </div>
              ))}
            </div>

            {/* Arrow 1 */}
            <div style={{ color: 'var(--color-primary)', display: 'flex', justifyContent: 'center' }}>
              <ArrowRight size={18} />
            </div>

            {/* Process Column */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
              <div style={{ fontSize: '10.5px', fontWeight: '700', color: 'var(--color-text-muted)', textTransform: 'uppercase' }}>
                Process Stages ({bs.processing_stages.length})
              </div>
              <div style={{
                fontSize: '12px',
                color: 'var(--color-text)',
                background: 'var(--color-surface)',
                padding: '8px 12px',
                borderRadius: 'var(--radius-sm)',
                border: '1px solid var(--color-border)',
                display: 'flex',
                flexDirection: 'column',
                gap: '4px',
              }}>
                <span style={{ fontWeight: '700', color: 'var(--color-primary)' }}>Multi-Stage Processing</span>
                <span style={{ fontSize: '11px', color: 'var(--color-text-secondary)' }}>
                  {bs.processing_stages.map((s) => s.name).slice(0, 3).join(' · ') || 'Multi-step data pipeline'}
                </span>
              </div>
            </div>

            {/* Arrow 2 */}
            <div style={{ color: 'var(--color-primary)', display: 'flex', justifyContent: 'center' }}>
              <ArrowRight size={18} />
            </div>

            {/* Outputs Column */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
              <div style={{ fontSize: '10.5px', fontWeight: '700', color: 'var(--color-text-muted)', textTransform: 'uppercase' }}>
                Deliverables ({bs.business_outputs.length})
              </div>
              {bs.business_outputs.map((out, idx) => (
                <div key={idx} style={{
                  fontSize: '12px',
                  fontWeight: '600',
                  color: 'var(--color-text)',
                  background: 'var(--color-surface)',
                  padding: '6px 10px',
                  borderRadius: 'var(--radius-sm)',
                  border: '1px solid var(--color-border)',
                  whiteSpace: 'nowrap',
                  overflow: 'hidden',
                  textOverflow: 'ellipsis',
                }}>
                  {out.name}
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* 4. Process Stages (Showing Direct Alteryx Tool Names) */}
      {bs && bs.processing_stages && bs.processing_stages.length > 0 && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <h3 style={{ fontSize: '12.5px', fontWeight: '700', color: 'var(--color-text)', textTransform: 'uppercase', letterSpacing: '0.5px', margin: 0 }}>
              Process Stages ({bs.processing_stages.length})
            </h3>
            <span style={{ fontSize: '11px', color: 'var(--color-text-muted)' }}>
              Click any stage to inspect underlying tools and transformations
            </span>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: '10px' }}>
            {bs.processing_stages.map((stage: BusinessStageDTO) => {
              const isExpanded = expandedStage === stage.stage_number;

              return (
                <div
                  key={stage.stage_number}
                  className="app-card"
                  style={{
                    padding: '14px 16px',
                    cursor: 'pointer',
                    transition: 'border-color 0.15s ease, background-color 0.15s ease',
                    border: isExpanded ? '1px solid var(--color-primary)' : '1px solid var(--color-border)',
                    backgroundColor: isExpanded ? 'var(--color-surface-hover)' : 'var(--color-surface)',
                  }}
                  onClick={() => toggleStage(stage.stage_number)}
                >
                  <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between' }}>
                    <div>
                      <span style={{
                        fontSize: '10.5px',
                        fontFamily: 'var(--font-mono)',
                        fontWeight: '700',
                        color: 'var(--color-primary)',
                        display: 'block',
                        marginBottom: '2px',
                      }}>
                        {stage.short_title || `STAGE ${String(stage.stage_number).padStart(2, '0')}`}
                      </span>
                      <h4 style={{ fontSize: '13.5px', fontWeight: '700', color: 'var(--color-text)', margin: '0 0 4px 0' }}>
                        {stage.name}
                      </h4>
                    </div>
                    {isExpanded ? (
                      <ChevronUp size={16} color="var(--color-primary)" />
                    ) : (
                      <ChevronDown size={16} color="var(--color-text-muted)" />
                    )}
                  </div>

                  <p style={{ fontSize: '12px', color: 'var(--color-text-secondary)', margin: '0 0 8px 0', lineHeight: '1.4' }}>
                    {stage.summary || stage.description}
                  </p>

                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '11px', color: 'var(--color-text-muted)' }}>
                    <span>{stage.tool_count} steps</span>
                  </div>

                  {/* Progressive Disclosure Details */}
                  {isExpanded && (
                    <div
                      style={{
                        marginTop: '12px',
                        paddingTop: '12px',
                        borderTop: '1px solid var(--color-border)',
                        display: 'flex',
                        flexDirection: 'column',
                        gap: '8px',
                        fontSize: '11.5px',
                      }}
                      onClick={(e) => e.stopPropagation()}
                    >
                      {stage.business_purpose && (
                        <div>
                          <span style={{ fontWeight: '700', color: 'var(--color-text)' }}>Purpose: </span>
                          <span style={{ color: 'var(--color-text-secondary)' }}>{stage.business_purpose}</span>
                        </div>
                      )}

                      {stage.major_transformation && (
                        <div>
                          <span style={{ fontWeight: '700', color: 'var(--color-text)' }}>Transformation: </span>
                          <span style={{ color: 'var(--color-text-secondary)' }}>{stage.major_transformation}</span>
                        </div>
                      )}

                      {stage.annotations && stage.annotations.length > 0 && (
                        <div>
                          <span style={{ fontWeight: '700', color: 'var(--color-text)' }}>Key Actions:</span>
                          <ul style={{ margin: '4px 0 0 0', paddingLeft: '16px', color: 'var(--color-text-secondary)' }}>
                            {stage.annotations.map((ann, aIdx) => (
                              <li key={aIdx}>{ann}</li>
                            ))}
                          </ul>
                        </div>
                      )}

                      {/* Direct Alteryx Tool Name Chips (No Tool IDs) */}
                      <div style={{ marginTop: '4px' }}>
                        <span style={{ fontWeight: '700', color: 'var(--color-text)', display: 'block', marginBottom: '4px' }}>
                          Tools:
                        </span>
                        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '5px' }}>
                          {stage.tool_ids.map((tid, idx) => {
                            const toolInfo = toolMap.get(tid);
                            const toolDisplayName = toolInfo ? (toolInfo.name || toolInfo.tool_type) : 'Tool';

                            return (
                              <span
                                key={`${tid}-${idx}`}
                                onClick={() => onSelectTool && onSelectTool(tid)}
                                title={onSelectTool ? `Click to inspect ${toolDisplayName}` : undefined}
                                style={{
                                  fontSize: '11px',
                                  fontWeight: '600',
                                  color: 'var(--color-text)',
                                  background: 'var(--color-surface-secondary)',
                                  border: '1px solid var(--color-border)',
                                  padding: '2px 8px',
                                  borderRadius: 'var(--radius-sm)',
                                  cursor: onSelectTool ? 'pointer' : 'default',
                                  display: 'inline-flex',
                                  alignItems: 'center',
                                  transition: 'border-color 0.15s ease, background-color 0.15s ease',
                                }}
                                onMouseEnter={(e) => {
                                  if (onSelectTool) {
                                    e.currentTarget.style.borderColor = 'var(--color-primary)';
                                    e.currentTarget.style.backgroundColor = 'var(--color-surface-hover)';
                                  }
                                }}
                                onMouseLeave={(e) => {
                                  if (onSelectTool) {
                                    e.currentTarget.style.borderColor = 'var(--color-border)';
                                    e.currentTarget.style.backgroundColor = 'var(--color-surface-secondary)';
                                  }
                                }}
                              >
                                {toolDisplayName}
                              </span>
                            );
                          })}
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
};
