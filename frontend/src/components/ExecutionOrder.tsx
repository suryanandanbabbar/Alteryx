import React from 'react';
import { ExecutionStepDTO } from '../types/workflow';
import { getCategoryColor } from '../theme/palette';
import { ChevronRight } from 'lucide-react';

interface ExecutionOrderProps {
  steps: ExecutionStepDTO[];
  onSelectStep?: (toolId: number) => void;
}

export const ExecutionOrder: React.FC<ExecutionOrderProps> = ({ steps, onSelectStep }) => {
  return (
    <div style={{
      display: 'flex',
      alignItems: 'center',
      flexWrap: 'wrap',
      gap: '8px',
      padding: '16px 20px',
      background: 'rgba(15, 23, 42, 0.6)',
      border: '1px solid rgba(51, 65, 85, 0.5)',
      borderRadius: '10px',
    }}>
      {steps.map((step, idx) => {
        const catColor = getCategoryColor(step.visual_category);
        const isLast = idx === steps.length - 1;

        return (
          <React.Fragment key={step.tool_id}>
            <div
              onClick={() => onSelectStep?.(step.tool_id)}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                padding: '6px 12px',
                borderRadius: '6px',
                background: catColor.badgeBg,
                border: `1px solid ${catColor.stroke}`,
                cursor: onSelectStep ? 'pointer' : 'default',
                transition: 'all 0.15s ease',
              }}
              onMouseEnter={(e) => {
                if (onSelectStep) {
                  e.currentTarget.style.transform = 'scale(1.03)';
                  e.currentTarget.style.boxShadow = `0 0 10px ${catColor.stroke}40`;
                }
              }}
              onMouseLeave={(e) => {
                if (onSelectStep) {
                  e.currentTarget.style.transform = 'scale(1)';
                  e.currentTarget.style.boxShadow = 'none';
                }
              }}
            >
              <span style={{
                width: '18px',
                height: '18px',
                borderRadius: '50%',
                background: catColor.stroke,
                color: '#090d1a',
                fontSize: '10px',
                fontWeight: '800',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
              }}>
                {step.step_number}
              </span>
              <span style={{
                fontSize: '11px',
                fontWeight: '700',
                letterSpacing: '0.5px',
                color: catColor.text,
                textTransform: 'uppercase',
              }}>
                {step.tool_type}
              </span>
            </div>

            {!isLast && (
              <ChevronRight size={14} color="#64748b" style={{ flexShrink: 0 }} />
            )}
          </React.Fragment>
        );
      })}
    </div>
  );
};
