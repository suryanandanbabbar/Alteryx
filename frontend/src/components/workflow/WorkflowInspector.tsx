import React from 'react';
import {
  X,
  ArrowRight,
  ArrowLeft,
  Layers,
} from 'lucide-react';
import { NodeDTO, ConnectionDTO } from '../../types/workflow';
import { getCategoryColor } from '../../theme/palette';

interface WorkflowInspectorProps {
  selectedNode: NodeDTO | null;
  selectedConnection: {
    connection: ConnectionDTO;
    sourceNode?: NodeDTO;
    targetNode?: NodeDTO;
  } | null;
  upstreamNodes: NodeDTO[];
  downstreamNodes: NodeDTO[];
  isBusinessOutput?: boolean;
  onSelectTool: (toolId: number) => void;
  onClose: () => void;
}

export const WorkflowInspector: React.FC<WorkflowInspectorProps> = ({
  selectedNode,
  selectedConnection,
  upstreamNodes,
  downstreamNodes,
  isBusinessOutput,
  onSelectTool,
  onClose,
}) => {
  if (!selectedNode && !selectedConnection) {
    return null;
  }

  // If a connection edge is selected:
  if (selectedConnection) {
    const { connection, sourceNode, targetNode } = selectedConnection;
    return (
      <div
        style={{
          width: '320px',
          height: '100%',
          background: 'var(--color-surface)',
          borderLeft: '1px solid var(--color-border)',
          display: 'flex',
          flexDirection: 'column',
          boxShadow: '-2px 0 8px rgba(0, 0, 0, 0.04)',
          overflowY: 'auto',
        }}
      >
        {/* Header */}
        <div
          style={{
            padding: '14px 16px',
            borderBottom: '1px solid var(--color-border)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            background: 'var(--color-surface-secondary)',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Layers size={16} color="var(--color-primary)" />
            <h3 style={{ fontSize: '13px', fontWeight: 700, margin: 0, color: 'var(--color-text)' }}>
              Connection Details
            </h3>
          </div>
          <button
            onClick={onClose}
            style={{
              background: 'transparent',
              border: 'none',
              cursor: 'pointer',
              color: 'var(--color-text-muted)',
              padding: '4px',
              display: 'flex',
              alignItems: 'center',
            }}
          >
            <X size={16} />
          </button>
        </div>

        <div style={{ padding: '16px', display: 'flex', flexDirection: 'column', gap: '16px' }}>
          {/* Source Tool */}
          <div>
            <div style={{ fontSize: '10px', fontWeight: 700, color: 'var(--color-text-muted)', textTransform: 'uppercase', marginBottom: '6px' }}>
              Origin (Source)
            </div>
            <div
              onClick={() => onSelectTool(connection.origin_tool_id)}
              style={{
                padding: '8px 10px',
                background: 'var(--color-surface-secondary)',
                border: '1px solid var(--color-border)',
                borderRadius: 'var(--radius-sm, 4px)',
                cursor: 'pointer',
                transition: 'border-color 0.15s ease',
              }}
              className="app-card-hover"
            >
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <span style={{ fontSize: '12px', fontWeight: 700, color: 'var(--color-text)' }}>
                  #{connection.origin_tool_id} {sourceNode?.name || sourceNode?.tool_type || 'Source Tool'}
                </span>
                <span style={{ fontSize: '10px', color: 'var(--color-primary)', fontFamily: 'var(--font-mono)' }}>
                  Port: {connection.origin_anchor}
                </span>
              </div>
            </div>
          </div>

          <div style={{ display: 'flex', justifyContent: 'center' }}>
            <ArrowRight size={16} color="var(--color-text-muted)" />
          </div>

          {/* Destination Tool */}
          <div>
            <div style={{ fontSize: '10px', fontWeight: 700, color: 'var(--color-text-muted)', textTransform: 'uppercase', marginBottom: '6px' }}>
              Destination (Target)
            </div>
            <div
              onClick={() => onSelectTool(connection.destination_tool_id)}
              style={{
                padding: '8px 10px',
                background: 'var(--color-surface-secondary)',
                border: '1px solid var(--color-border)',
                borderRadius: 'var(--radius-sm, 4px)',
                cursor: 'pointer',
                transition: 'border-color 0.15s ease',
              }}
              className="app-card-hover"
            >
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <span style={{ fontSize: '12px', fontWeight: 700, color: 'var(--color-text)' }}>
                  #{connection.destination_tool_id} {targetNode?.name || targetNode?.tool_type || 'Target Tool'}
                </span>
                <span style={{ fontSize: '10px', color: 'var(--color-primary)', fontFamily: 'var(--font-mono)' }}>
                  Port: {connection.destination_anchor}
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>
    );
  }

  // Node details inspector
  const node = selectedNode!;
  const categoryColor = getCategoryColor(node.visual_category || node.tool_type.toLowerCase());

  return (
    <div
      style={{
        width: '340px',
        height: '100%',
        background: 'var(--color-surface)',
        borderLeft: '1px solid var(--color-border)',
        display: 'flex',
        flexDirection: 'column',
        boxShadow: '-2px 0 8px rgba(0, 0, 0, 0.04)',
        overflowY: 'auto',
      }}
    >
      {/* Header */}
      <div
        style={{
          padding: '12px 16px',
          borderBottom: '1px solid var(--color-border)',
          display: 'flex',
          alignItems: 'flex-start',
          justifyContent: 'space-between',
          background: categoryColor.badgeBg || 'var(--color-surface-secondary)',
        }}
      >
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '2px' }}>
            <span
              style={{
                fontSize: '11px',
                fontWeight: 700,
                fontFamily: 'var(--font-mono)',
                color: 'var(--color-text-muted)',
              }}
            >
              #{node.tool_id}
            </span>
            <span
              style={{
                fontSize: '11px',
                fontWeight: 700,
                color: categoryColor.text || 'var(--color-text)',
                textTransform: 'uppercase',
                letterSpacing: '0.4px',
              }}
            >
              {node.tool_type}
            </span>
            {isBusinessOutput && (
              <span
                style={{
                  fontSize: '9px',
                  fontWeight: 700,
                  padding: '1px 5px',
                  borderRadius: '3px',
                  background: 'rgba(147, 51, 234, 0.15)',
                  color: '#7e22ce',
                  textTransform: 'uppercase',
                }}
              >
                Output Deliverable
              </span>
            )}
          </div>
          <h3 style={{ fontSize: '15px', fontWeight: 800, margin: 0, color: 'var(--color-text)' }}>
            {node.name}
          </h3>
        </div>

        <button
          onClick={onClose}
          style={{
            background: 'transparent',
            border: 'none',
            cursor: 'pointer',
            color: 'var(--color-text-muted)',
            padding: '4px',
            display: 'flex',
            alignItems: 'center',
          }}
          title="Close Inspector"
        >
          <X size={16} />
        </button>
      </div>

      {/* Content body */}
      <div style={{ padding: '16px', display: 'flex', flexDirection: 'column', gap: '16px' }}>

        {/* Section A: Tool Information */}
        <div>
          <div style={{ fontSize: '10px', fontWeight: 700, color: 'var(--color-text-muted)', textTransform: 'uppercase', marginBottom: '8px' }}>
            Tool Information
          </div>
          <div
            style={{
              background: 'var(--color-surface-secondary)',
              borderRadius: 'var(--radius-sm, 4px)',
              border: '1px solid var(--color-border)',
              padding: '10px 12px',
              display: 'flex',
              flexDirection: 'column',
              gap: '6px',
              fontSize: '11px',
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span style={{ color: 'var(--color-text-muted)' }}>Type:</span>
              <span style={{ fontWeight: 600, color: 'var(--color-text)' }}>{node.tool_type}</span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span style={{ color: 'var(--color-text-muted)' }}>Category:</span>
              <span style={{ fontWeight: 600, color: 'var(--color-text)' }}>{node.visual_category || 'General'}</span>
            </div>
            {node.container_name && (
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ color: 'var(--color-text-muted)' }}>Container:</span>
                <span style={{ fontWeight: 600, color: 'var(--color-text)' }}>{node.container_name}</span>
              </div>
            )}
            {node.annotation && (
              <div style={{ borderTop: '1px solid var(--color-border-subtle)', paddingTop: '6px', marginTop: '2px' }}>
                <div style={{ color: 'var(--color-text-muted)', fontSize: '10px', marginBottom: '2px' }}>Annotation:</div>
                <div style={{ color: 'var(--color-text)', fontStyle: 'italic' }}>{node.annotation}</div>
              </div>
            )}
          </div>
        </div>

        {/* Section B: Configuration */}
        {node.configuration && Object.keys(node.configuration).length > 0 && (
          <div>
            <div style={{ fontSize: '10px', fontWeight: 700, color: 'var(--color-text-muted)', textTransform: 'uppercase', marginBottom: '8px' }}>
              Configuration
            </div>
            <div
              style={{
                background: 'var(--color-surface-secondary)',
                borderRadius: 'var(--radius-sm, 4px)',
                border: '1px solid var(--color-border)',
                padding: '10px 12px',
                fontSize: '11px',
                display: 'flex',
                flexDirection: 'column',
                gap: '8px',
              }}
            >
              {Object.entries(node.configuration).map(([key, val]) => {
                const label = key.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
                let displayVal = val;
                if (typeof val === 'object' && val !== null) {
                  if (Array.isArray(val)) {
                    displayVal = val.join(', ');
                  } else {
                    displayVal = JSON.stringify(val, null, 2);
                  }
                }
                return (
                  <div key={key}>
                    <div style={{ fontSize: '10px', color: 'var(--color-text-muted)', fontWeight: 600 }}>{label}:</div>
                    <div
                      style={{
                        fontFamily: typeof val === 'object' || String(val).includes('\n') ? 'var(--font-mono)' : 'inherit',
                        fontSize: '11px',
                        color: 'var(--color-text)',
                        wordBreak: 'break-word',
                        whiteSpace: typeof val === 'object' ? 'pre-wrap' : 'normal',
                      }}
                    >
                      {String(displayVal)}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* Section C: Output Fields */}
        {node.output_fields && node.output_fields.length > 0 && (
          <div>
            <div style={{ fontSize: '10px', fontWeight: 700, color: 'var(--color-text-muted)', textTransform: 'uppercase', marginBottom: '8px' }}>
              Output Fields ({node.output_fields.length})
            </div>
            <div
              style={{
                background: 'var(--color-surface-secondary)',
                borderRadius: 'var(--radius-sm, 4px)',
                border: '1px solid var(--color-border)',
                padding: '8px',
                maxHeight: '140px',
                overflowY: 'auto',
                display: 'flex',
                flexDirection: 'column',
                gap: '4px',
              }}
            >
              {node.output_fields.map((f, i) => (
                <div
                  key={i}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    fontSize: '11px',
                    padding: '2px 4px',
                  }}
                >
                  <span style={{ fontWeight: 600, color: 'var(--color-text)' }}>{f.name}</span>
                  <span style={{ fontSize: '10px', fontFamily: 'var(--font-mono)', color: 'var(--color-text-muted)' }}>
                    {f.type}{f.size ? `(${f.size})` : ''}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Section D: Inputs (Upstream Nodes) */}
        <div>
          <div style={{ fontSize: '10px', fontWeight: 700, color: 'var(--color-text-muted)', textTransform: 'uppercase', marginBottom: '8px' }}>
            Upstream Inputs ({upstreamNodes.length})
          </div>
          {upstreamNodes.length === 0 ? (
            <div style={{ fontSize: '11px', color: 'var(--color-text-muted)', fontStyle: 'italic' }}>
              Source node (no upstream inputs)
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
              {upstreamNodes.map((up) => (
                <div
                  key={up.tool_id}
                  onClick={() => onSelectTool(up.tool_id)}
                  style={{
                    padding: '6px 10px',
                    background: 'var(--color-surface-secondary)',
                    border: '1px solid var(--color-border)',
                    borderRadius: 'var(--radius-sm, 4px)',
                    cursor: 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                  }}
                  className="app-card-hover"
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                    <ArrowLeft size={12} color="#0284c7" />
                    <span style={{ fontSize: '11px', fontWeight: 700, color: 'var(--color-text)' }}>
                      #{up.tool_id} {up.name}
                    </span>
                  </div>
                  <span style={{ fontSize: '10px', color: 'var(--color-text-muted)' }}>{up.tool_type}</span>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Section E: Outputs (Downstream Nodes) */}
        <div>
          <div style={{ fontSize: '10px', fontWeight: 700, color: 'var(--color-text-muted)', textTransform: 'uppercase', marginBottom: '8px' }}>
            Downstream Outputs ({downstreamNodes.length})
          </div>
          {downstreamNodes.length === 0 ? (
            <div style={{ fontSize: '11px', color: 'var(--color-text-muted)', fontStyle: 'italic' }}>
              Terminal node (no downstream outputs)
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
              {downstreamNodes.map((down) => (
                <div
                  key={down.tool_id}
                  onClick={() => onSelectTool(down.tool_id)}
                  style={{
                    padding: '6px 10px',
                    background: 'var(--color-surface-secondary)',
                    border: '1px solid var(--color-border)',
                    borderRadius: 'var(--radius-sm, 4px)',
                    cursor: 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                  }}
                  className="app-card-hover"
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                    <ArrowRight size={12} color="#16a34a" />
                    <span style={{ fontSize: '11px', fontWeight: 700, color: 'var(--color-text)' }}>
                      #{down.tool_id} {down.name}
                    </span>
                  </div>
                  <span style={{ fontSize: '10px', color: 'var(--color-text-muted)' }}>{down.tool_type}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
