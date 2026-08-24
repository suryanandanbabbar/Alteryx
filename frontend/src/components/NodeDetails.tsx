import React, { useState } from 'react';
import { NodeDTO } from '../types/workflow';
import { getCategoryColor } from '../theme/palette';
import { ChevronDown, ChevronRight } from 'lucide-react';

interface NodeDetailsProps {
  nodes: NodeDTO[];
  selectedToolId?: number | null;
  hideHeader?: boolean;
}

export const NodeDetails: React.FC<NodeDetailsProps> = ({ nodes, selectedToolId, hideHeader = false }) => {
  const [expandedNodes, setExpandedNodes] = useState<Record<number, boolean>>(() => {
    const initial: Record<number, boolean> = {};
    nodes.forEach((n) => {
      // Default to expanded if selected or for first few nodes
      initial[n.tool_id] = selectedToolId ? n.tool_id === selectedToolId : true;
    });
    return initial;
  });

  // Ensure selected tool is expanded if selectedToolId changes
  React.useEffect(() => {
    if (selectedToolId) {
      setExpandedNodes((prev) => ({
        ...prev,
        [selectedToolId]: true,
      }));
    }
  }, [selectedToolId]);

  const toggleNode = (toolId: number) => {
    setExpandedNodes((prev) => ({
      ...prev,
      [toolId]: !prev[toolId],
    }));
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
      {!hideHeader && (
        <div style={{
          fontSize: '11px',
          fontWeight: '700',
          letterSpacing: '0.8px',
          color: 'var(--color-text-muted)',
          textTransform: 'uppercase',
          marginBottom: '2px',
        }}>
          Tool Specifications & Configuration ({nodes.length} tools)
        </div>
      )}

      {nodes.map((node) => {
        const isExpanded = !!expandedNodes[node.tool_id];
        const isSelected = selectedToolId === node.tool_id;
        const catColor = getCategoryColor(node.visual_category);

        return (
          <div
            key={node.tool_id}
            id={`tool-detail-${node.tool_id}`}
            className="app-card"
            style={{
              overflow: 'hidden',
              borderColor: isSelected ? 'var(--color-primary)' : 'var(--color-border)',
              transition: 'border-color 0.15s ease',
            }}
          >
            {/* Header / Accordion Bar */}
            <div
              onClick={() => toggleNode(node.tool_id)}
              style={{
                padding: '12px 16px',
                background: isExpanded ? 'var(--color-surface-secondary)' : 'var(--color-surface)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                cursor: 'pointer',
                userSelect: 'none',
                borderBottom: isExpanded ? '1px solid var(--color-border)' : 'none',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                <span style={{ color: 'var(--color-text-muted)' }}>
                  {isExpanded ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
                </span>

                {/* Tool ID Badge */}
                <span style={{
                  fontFamily: 'var(--font-mono)',
                  fontSize: '11px',
                  fontWeight: '700',
                  color: 'var(--color-text-muted)',
                  background: 'var(--color-surface)',
                  border: '1px solid var(--color-border)',
                  padding: '2px 6px',
                  borderRadius: 'var(--radius-sm)',
                }}>
                  #{node.tool_id}
                </span>

                {/* Category & Type */}
                <span style={{
                  fontSize: '11px',
                  fontWeight: '600',
                  color: catColor.text,
                  background: catColor.badgeBg,
                  border: `1px solid ${catColor.stroke}`,
                  padding: '2px 8px',
                  borderRadius: 'var(--radius-sm)',
                }}>
                  {node.tool_type}
                </span>

                {/* Name */}
                <span style={{ fontSize: '13px', fontWeight: '600', color: 'var(--color-text)' }}>
                  {node.name || node.tool_type}
                </span>
              </div>
            </div>

            {/* Expanded Content */}
            {isExpanded && (
              <div style={{ padding: '16px 20px', display: 'flex', flexDirection: 'column', gap: '14px' }}>
                {/* Business Summary Box */}
                {node.summary && (
                  <div style={{
                    padding: '10px 14px',
                    background: 'var(--color-surface-secondary)',
                    border: '1px solid var(--color-border)',
                    borderRadius: 'var(--radius-sm)',
                    fontSize: '12.5px',
                    color: 'var(--color-text)',
                    lineHeight: '1.45',
                  }}>
                    <span style={{ fontWeight: '600', color: 'var(--color-text-muted)', marginRight: '6px' }}>Function:</span>
                    {node.summary}
                  </div>
                )}

                {/* Meta Table */}
                <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '12px' }}>
                  <tbody>
                    {node.position && (
                      <tr style={{ borderBottom: '1px solid var(--color-border-subtle)' }}>
                        <td style={{ padding: '6px 0', width: '150px', color: 'var(--color-text-muted)', fontWeight: '500' }}>Canvas Position</td>
                        <td style={{ padding: '6px 0', color: 'var(--color-text)', fontFamily: 'var(--font-mono)' }}>
                          x={node.position.x}, y={node.position.y}
                        </td>
                      </tr>
                    )}
                    {node.container_name && (
                      <tr style={{ borderBottom: '1px solid var(--color-border-subtle)' }}>
                        <td style={{ padding: '6px 0', width: '150px', color: 'var(--color-text-muted)', fontWeight: '500' }}>Tool Container</td>
                        <td style={{ padding: '6px 0', color: 'var(--color-text)', fontWeight: '600' }}>
                          📁 {node.container_name} {node.container_id ? `(#${node.container_id})` : ''}
                        </td>
                      </tr>
                    )}
                    {node.annotation && (
                      <tr style={{ borderBottom: '1px solid var(--color-border-subtle)' }}>
                        <td style={{ padding: '6px 0', width: '150px', color: 'var(--color-text-muted)', fontWeight: '500' }}>Annotation</td>
                        <td style={{ padding: '6px 0', color: 'var(--color-text)' }}>{node.annotation}</td>
                      </tr>
                    )}
                  </tbody>
                </table>

                {/* Configuration Table */}
                {Object.keys(node.configuration).length > 0 && (
                  <div>
                    <div style={{
                      fontSize: '11px',
                      fontWeight: '700',
                      letterSpacing: '0.5px',
                      color: 'var(--color-text-muted)',
                      textTransform: 'uppercase',
                      marginBottom: '8px',
                    }}>
                      Tool Configuration
                    </div>
                    <div style={{
                      background: 'var(--color-surface-secondary)',
                      border: '1px solid var(--color-border)',
                      borderRadius: 'var(--radius-sm)',
                      overflow: 'hidden',
                    }}>
                      <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '12.5px' }}>
                        <tbody>
                          {Object.entries(node.configuration).map(([k, v], idx) => (
                            <tr key={k} style={{ borderBottom: idx < Object.keys(node.configuration).length - 1 ? '1px solid var(--color-border)' : 'none' }}>
                              <td style={{ padding: '8px 14px', width: '200px', color: 'var(--color-text-muted)', fontWeight: '600' }}>
                                {k}
                              </td>
                              <td style={{ padding: '8px 14px', color: 'var(--color-text)', wordBreak: 'break-word', lineHeight: '1.4' }}>
                                {typeof v === 'object' ? JSON.stringify(v) : String(v)}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                )}

                {/* Engine Settings (Technical Metadata) */}
                {node.engine_settings && Object.keys(node.engine_settings).length > 0 && (
                  <div>
                    <div style={{
                      fontSize: '11px',
                      fontWeight: '700',
                      letterSpacing: '0.5px',
                      color: 'var(--color-text-muted)',
                      textTransform: 'uppercase',
                      marginBottom: '8px',
                    }}>
                      Technical Engine Settings
                    </div>
                    <div style={{
                      background: 'var(--color-surface-secondary)',
                      border: '1px solid var(--color-border)',
                      borderRadius: 'var(--radius-sm)',
                      overflow: 'hidden',
                    }}>
                      <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '12px' }}>
                        <tbody>
                          {Object.entries(node.engine_settings).map(([k, v], idx) => (
                            <tr key={k} style={{ borderBottom: idx < Object.keys(node.engine_settings!).length - 1 ? '1px solid var(--color-border)' : 'none' }}>
                              <td style={{ padding: '6px 12px', width: '200px', color: 'var(--color-text-muted)', fontFamily: 'var(--font-mono)' }}>
                                {k}
                              </td>
                              <td style={{ padding: '6px 12px', color: 'var(--color-text)', fontFamily: 'var(--font-mono)' }}>
                                {v}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
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
