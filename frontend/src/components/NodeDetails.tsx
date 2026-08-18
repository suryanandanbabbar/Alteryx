import React, { useState } from 'react';
import { NodeDTO } from '../types/workflow';
import { getCategoryColor } from '../theme/palette';
import { ChevronDown, ChevronRight } from 'lucide-react';

interface NodeDetailsProps {
  nodes: NodeDTO[];
  selectedToolId?: number | null;
}

export const NodeDetails: React.FC<NodeDetailsProps> = ({ nodes, selectedToolId }) => {
  const [expandedIds, setExpandedIds] = useState<Set<number>>(
    new Set(selectedToolId ? [selectedToolId] : [nodes[0]?.tool_id])
  );

  const toggleExpand = (toolId: number) => {
    setExpandedIds((prev) => {
      const next = new Set(prev);
      if (next.has(toolId)) {
        next.delete(toolId);
      } else {
        next.add(toolId);
      }
      return next;
    });
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
      <div style={{
        fontSize: '11px',
        fontWeight: '700',
        letterSpacing: '1px',
        color: '#64748b',
        textTransform: 'uppercase',
        marginBottom: '4px',
      }}>
        Node Details — Click any row to expand
      </div>

      {nodes.map((node) => {
        const isExpanded = expandedIds.has(node.tool_id);
        const catColor = getCategoryColor(node.visual_category);
        const hasConfig = Object.keys(node.configuration).length > 0;

        return (
          <div
            key={node.tool_id}
            className="glass-card"
            style={{
              overflow: 'hidden',
              border: isExpanded ? `1px solid ${catColor.stroke}` : '1px solid rgba(51, 65, 85, 0.5)',
              transition: 'all 0.2s ease',
            }}
          >
            {/* Header Row */}
            <div
              onClick={() => toggleExpand(node.tool_id)}
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                padding: '14px 18px',
                cursor: 'pointer',
                background: isExpanded ? 'rgba(30, 41, 59, 0.4)' : 'transparent',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                {/* Numbered circle */}
                <div style={{
                  width: '24px',
                  height: '24px',
                  borderRadius: '50%',
                  background: catColor.stroke,
                  color: '#090d1a',
                  fontSize: '11px',
                  fontWeight: '800',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                }}>
                  {node.tool_id}
                </div>

                {/* Type badge */}
                <span style={{
                  padding: '4px 10px',
                  borderRadius: '4px',
                  background: catColor.badgeBg,
                  border: `1px solid ${catColor.stroke}60`,
                  color: catColor.text,
                  fontSize: '11px',
                  fontWeight: '700',
                  letterSpacing: '0.5px',
                  textTransform: 'uppercase',
                }}>
                  {node.tool_type}
                </span>

                {/* Tool Name / Annotation */}
                <span style={{ fontSize: '13px', fontWeight: '600', color: '#f8fafc' }}>
                  {node.name || node.annotation || node.tool_type}
                </span>
              </div>

              <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                <span style={{
                  fontSize: '11px',
                  color: node.support_level === 'supported' ? '#4ade80' : '#fbbf24',
                  fontWeight: '600',
                  textTransform: 'uppercase',
                }}>
                  {node.support_level}
                </span>
                {isExpanded ? <ChevronDown size={16} color="#94a3b8" /> : <ChevronRight size={16} color="#94a3b8" />}
              </div>
            </div>

            {/* Expanded Config Body */}
            {isExpanded && (
              <div style={{
                padding: '16px 20px',
                background: 'rgba(7, 11, 25, 0.8)',
                borderTop: '1px solid rgba(51, 65, 85, 0.4)',
              }}>
                {hasConfig ? (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                    {Object.entries(node.configuration).map(([k, v]) => {
                      const displayVal = typeof v === 'object' ? JSON.stringify(v) : String(v);
                      return (
                        <div
                          key={k}
                          style={{
                            display: 'grid',
                            gridTemplateColumns: '180px 1fr',
                            gap: '12px',
                            fontSize: '12px',
                            fontFamily: 'monospace',
                            padding: '4px 0',
                            borderBottom: '1px solid rgba(51, 65, 85, 0.2)',
                          }}
                        >
                          <span style={{ color: '#94a3b8', fontWeight: '500' }}>{k}</span>
                          <span style={{ color: '#38bdf8', wordBreak: 'break-all' }}>{displayVal}</span>
                        </div>
                      );
                    })}
                  </div>
                ) : (
                  <div style={{ fontSize: '12px', color: '#64748b', fontStyle: 'italic' }}>
                    No custom configuration properties parsed for this tool.
                  </div>
                )}

                {/* Output Schema Fields */}
                {node.output_fields.length > 0 && (
                  <div style={{ marginTop: '16px' }}>
                    <div style={{ fontSize: '11px', fontWeight: '700', color: '#94a3b8', marginBottom: '6px', textTransform: 'uppercase' }}>
                      Output Fields ({node.output_fields.length})
                    </div>
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
                      {node.output_fields.map((f, i) => (
                        <span
                          key={i}
                          style={{
                            padding: '3px 8px',
                            background: 'rgba(30, 41, 59, 0.7)',
                            border: '1px solid rgba(51, 65, 85, 0.5)',
                            borderRadius: '4px',
                            fontSize: '11px',
                            fontFamily: 'monospace',
                            color: '#cbd5e1',
                          }}
                        >
                          {f.name} <span style={{ color: '#64748b' }}>({f.type})</span>
                        </span>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
};
