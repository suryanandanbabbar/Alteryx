import React, { memo } from 'react';
import { Handle, Position, NodeProps } from '@xyflow/react';
import { WorkflowNodeData } from './types';
import { getCategoryColor } from '../../theme/palette';
import { AlertTriangle } from 'lucide-react';

export const WorkflowNodeComponent: React.FC<NodeProps<any>> = ({
  data,
  selected,
  targetPosition = Position.Left,
  sourcePosition = Position.Right,
}) => {
  const nodeData = data as WorkflowNodeData;
  const {
    toolId,
    toolType,
    name,
    visualCategory,
    summary,
    annotation,
    inputCount,
    outputCount,
    isBusinessOutput,
    diagnostics,
    isHighlighted,
    isDimmed,
    isSearchMatch,
    isActiveSearchMatch,
    isUpstream,
    isDownstream,
  } = nodeData;

  const categoryColor = getCategoryColor(visualCategory || toolType.toLowerCase());
  const hasDiagnostics = diagnostics && diagnostics.length > 0;
  const isSelected = selected || nodeData.isSelected;

  const subtitle = annotation || summary || '';

  let borderColor = 'var(--color-border)';
  let boxShadow = '0 2px 6px rgba(0, 0, 0, 0.15)';
  let bg = 'var(--color-surface)';
  let opacity = 1;

  if (isDimmed) {
    opacity = 0.22;
  }

  if (isSelected) {
    borderColor = 'var(--color-primary)';
    boxShadow = '0 0 0 2.5px var(--color-primary), 0 6px 20px rgba(251, 78, 11, 0.35)';
  } else if (isActiveSearchMatch) {
    borderColor = '#f59e0b';
    boxShadow = '0 0 0 3px #f59e0b, 0 6px 20px rgba(245, 158, 11, 0.45)';
  } else if (isSearchMatch) {
    borderColor = '#f59e0b';
    boxShadow = '0 0 0 2px rgba(245, 158, 11, 0.5)';
  } else if (isUpstream) {
    borderColor = '#0284c7';
    boxShadow = '0 0 0 2px #0284c7, 0 4px 16px rgba(2, 132, 199, 0.35)';
  } else if (isDownstream) {
    borderColor = '#16a34a';
    boxShadow = '0 0 0 2px #16a34a, 0 4px 16px rgba(22, 163, 74, 0.35)';
  } else if (isHighlighted) {
    borderColor = 'var(--color-primary-border)';
  }

  return (
    <div
      style={{
        width: '220px',
        minHeight: '86px',
        background: bg,
        border: `1.5px solid ${borderColor}`,
        borderRadius: 'var(--radius-md, 6px)',
        boxShadow,
        opacity,
        transition: 'all 0.15s ease',
        cursor: 'grab',
        position: 'relative',
        display: 'flex',
        flexDirection: 'column',
        userSelect: 'none',
        overflow: 'hidden',
      }}
      className="app-card-hover"
    >
      <Handle
        type="target"
        position={targetPosition}
        style={{
          width: '8px',
          height: '8px',
          background: 'var(--color-text-secondary)',
          border: '2px solid var(--color-surface)',
          borderRadius: '50%',
        }}
      />

      {/* Card Header with Category Banner */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '6px 10px',
          background: categoryColor.badgeBg || 'var(--color-surface-secondary)',
          borderBottom: '1px solid var(--color-border-subtle)',
          fontSize: '11px',
          fontWeight: 700,
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px', overflow: 'hidden' }}>
          <span
            style={{
              color: 'var(--color-text-secondary)',
              fontSize: '10.5px',
              fontFamily: 'var(--font-mono)',
              fontWeight: 800,
              background: 'var(--color-surface)',
              border: '1px solid var(--color-border)',
              padding: '1px 5px',
              borderRadius: '3px',
            }}
          >
            #{toolId}
          </span>
          <span
            style={{
              color: categoryColor.text || 'var(--color-text)',
              fontWeight: 800,
              fontSize: '11px',
              letterSpacing: '0.2px',
              whiteSpace: 'nowrap',
              overflow: 'hidden',
              textOverflow: 'ellipsis',
            }}
          >
            {toolType}
          </span>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
          {isBusinessOutput && (
            <span
              style={{
                fontSize: '9px',
                fontWeight: 800,
                padding: '1px 5px',
                borderRadius: '3px',
                background: 'rgba(147, 51, 234, 0.2)',
                color: '#9333ea',
                textTransform: 'uppercase',
                letterSpacing: '0.3px',
                border: '1px solid rgba(147, 51, 234, 0.4)',
              }}
              title="Business Deliverable Output"
            >
              Output
            </span>
          )}

          {hasDiagnostics && (
            <span
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '2px',
                color: '#d97706',
                fontSize: '10px',
                fontWeight: 700,
              }}
              title={`${diagnostics.length} diagnostic warning(s)`}
            >
              <AlertTriangle size={12} />
            </span>
          )}
        </div>
      </div>

      {/* Main Tool Name */}
      <div
        style={{
          padding: '8px 10px',
          flex: 1,
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'center',
        }}
      >
        <div
          style={{
            fontSize: '12.5px',
            fontWeight: 700,
            color: 'var(--color-text)',
            whiteSpace: 'nowrap',
            overflow: 'hidden',
            textOverflow: 'ellipsis',
            lineHeight: '1.3',
          }}
          title={name}
        >
          {name}
        </div>

        {subtitle && subtitle !== name && (
          <div
            style={{
              fontSize: '10.5px',
              color: 'var(--color-text-secondary)',
              whiteSpace: 'nowrap',
              overflow: 'hidden',
              textOverflow: 'ellipsis',
              marginTop: '3px',
            }}
            title={subtitle}
          >
            {subtitle}
          </div>
        )}
      </div>

      {/* Footer Info: Ports */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '3px 10px',
          background: 'var(--color-surface-secondary)',
          borderTop: '1px solid var(--color-border-subtle)',
          fontSize: '9.5px',
          color: 'var(--color-text-muted)',
          fontFamily: 'var(--font-mono)',
          fontWeight: 600,
        }}
      >
        <span>{inputCount > 0 ? `${inputCount} in` : 'source'}</span>
        <span>{outputCount > 0 ? `${outputCount} out` : 'terminal'}</span>
      </div>

      <Handle
        type="source"
        position={sourcePosition}
        style={{
          width: '8px',
          height: '8px',
          background: 'var(--color-primary)',
          border: '2px solid var(--color-surface)',
          borderRadius: '50%',
        }}
      />
    </div>
  );
};

export const WorkflowNode = memo(WorkflowNodeComponent);
