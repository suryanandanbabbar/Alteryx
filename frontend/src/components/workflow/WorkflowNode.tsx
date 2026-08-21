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
    isUpstream,
    isDownstream,
  } = nodeData;

  const categoryColor = getCategoryColor(visualCategory || toolType.toLowerCase());
  const hasDiagnostics = diagnostics && diagnostics.length > 0;
  const isSelected = selected || nodeData.isSelected;

  const subtitle = annotation || summary || '';

  let borderColor = 'var(--color-border)';
  let boxShadow = '0 1px 3px rgba(0, 0, 0, 0.06)';
  let bg = 'var(--color-surface)';
  let opacity = 1;

  if (isDimmed) {
    opacity = 0.3;
  }

  if (isSelected) {
    borderColor = 'var(--color-primary)';
    boxShadow = '0 0 0 2px var(--color-primary-border), 0 4px 12px rgba(251, 78, 11, 0.15)';
  } else if (isSearchMatch) {
    borderColor = '#f59e0b';
    boxShadow = '0 0 0 2px rgba(245, 158, 11, 0.4), 0 2px 8px rgba(245, 158, 11, 0.2)';
  } else if (isUpstream) {
    borderColor = '#0284c7';
    boxShadow = '0 0 0 1.5px rgba(2, 132, 199, 0.35)';
  } else if (isDownstream) {
    borderColor = '#16a34a';
    boxShadow = '0 0 0 1.5px rgba(22, 163, 74, 0.35)';
  } else if (isHighlighted) {
    borderColor = 'var(--color-primary-border)';
  }

  return (
    <div
      style={{
        width: '220px',
        minHeight: '84px',
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
          background: 'var(--color-text-muted)',
          border: '2px solid var(--color-surface)',
          borderRadius: '50%',
        }}
      />

      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '6px 10px',
          background: categoryColor.badgeBg || 'var(--color-surface-secondary)',
          borderBottom: '1px solid var(--color-border-subtle)',
          fontSize: '11px',
          fontWeight: 600,
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px', overflow: 'hidden' }}>
          <span
            style={{
              color: 'var(--color-text-muted)',
              fontSize: '10px',
              fontFamily: 'var(--font-mono)',
              fontWeight: 700,
            }}
          >
            #{toolId}
          </span>
          <span
            style={{
              color: categoryColor.text || 'var(--color-text)',
              fontWeight: 700,
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
                fontWeight: 700,
                padding: '1px 4px',
                borderRadius: '3px',
                background: 'rgba(147, 51, 234, 0.15)',
                color: '#7e22ce',
                textTransform: 'uppercase',
                letterSpacing: '0.3px',
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
            fontSize: '12px',
            fontWeight: 600,
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
              fontSize: '10px',
              color: 'var(--color-text-muted)',
              whiteSpace: 'nowrap',
              overflow: 'hidden',
              textOverflow: 'ellipsis',
              marginTop: '2px',
            }}
            title={subtitle}
          >
            {subtitle}
          </div>
        )}
      </div>

      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '3px 10px',
          background: 'var(--color-surface-secondary)',
          borderTop: '1px solid var(--color-border-subtle)',
          fontSize: '9px',
          color: 'var(--color-text-subtle)',
          fontFamily: 'var(--font-mono)',
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
