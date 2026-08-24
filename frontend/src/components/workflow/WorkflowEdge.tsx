import React, { memo } from 'react';
import { BaseEdge, EdgeProps, getSmoothStepPath, EdgeLabelRenderer } from '@xyflow/react';
import { WorkflowEdgeData } from './types';

export const WorkflowEdgeComponent: React.FC<EdgeProps<any>> = ({
  id,
  sourceX,
  sourceY,
  targetX,
  targetY,
  sourcePosition,
  targetPosition,
  style = {},
  markerEnd,
  selected,
  data,
}) => {
  const edgeData = data as WorkflowEdgeData | undefined;
  const isHighlighted = edgeData?.isHighlighted || selected;
  const isDimmed = edgeData?.isDimmed && !isHighlighted;

  const [edgePath, labelX, labelY] = getSmoothStepPath({
    sourceX,
    sourceY,
    sourcePosition,
    targetX,
    targetY,
    targetPosition,
    borderRadius: 8,
  });

  let stroke = '#64748b';
  let strokeWidth = 1.75;
  let opacity = 0.85;

  if (isHighlighted) {
    stroke = 'var(--color-primary)';
    strokeWidth = 2.5;
    opacity = 1;
  } else if (isDimmed) {
    opacity = 0.15;
  }

  const anchorLabel =
    edgeData &&
    (edgeData.originAnchor !== 'Output' || edgeData.destinationAnchor !== 'Input')
      ? `${edgeData.originAnchor} → ${edgeData.destinationAnchor}`
      : null;

  return (
    <>
      <BaseEdge
        id={id}
        path={edgePath}
        markerEnd={markerEnd}
        style={{
          ...style,
          stroke,
          strokeWidth,
          opacity,
          transition: 'stroke 0.15s ease, stroke-width 0.15s ease, opacity 0.15s ease',
        }}
      />
      {anchorLabel && isHighlighted && (
        <EdgeLabelRenderer>
          <div
            style={{
              position: 'absolute',
              transform: `translate(-50%, -50%) translate(${labelX}px, ${labelY}px)`,
              background: 'var(--color-surface)',
              border: '1px solid var(--color-border)',
              borderRadius: '4px',
              padding: '2px 6px',
              fontSize: '9px',
              fontFamily: 'var(--font-mono)',
              fontWeight: 600,
              color: 'var(--color-text-secondary)',
              boxShadow: '0 1px 3px rgba(0,0,0,0.1)',
              pointerEvents: 'all',
            }}
            className="nodrag nopan"
          >
            {anchorLabel}
          </div>
        </EdgeLabelRenderer>
      )}
    </>
  );
};

export const WorkflowEdge = memo(WorkflowEdgeComponent);
