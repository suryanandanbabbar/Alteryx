import React from 'react';
import { ExecutionStepDTO } from '../types/workflow';
import { getCategoryColor } from '../theme/palette';
import { ArrowRight } from 'lucide-react';

interface ExecutionOrderProps {
  steps: ExecutionStepDTO[];
  onSelectStep?: (toolId: number) => void;
}

export const ExecutionOrder: React.FC<ExecutionOrderProps> = ({ steps, onSelectStep }) => {
  return (
    <div className="app-card" style={{ padding: '20px' }}>
      <div style={{
        fontSize: '11px',
        fontWeight: '700',
        letterSpacing: '0.8px',
        color: 'var(--color-text-muted)',
        textTransform: 'uppercase',
        marginBottom: '14px',
      }}>
        Topological Execution Order
      </div>

      <div style={{
        display: 'flex',
        alignItems: 'center',
        flexWrap: 'wrap',
        gap: '8px',
      }}>
        {steps.map((step, idx) => {
          const catColor = getCategoryColor(step.visual_category);
          const isLast = idx === steps.length - 1;

          return (
            <React.Fragment key={step.tool_id}>
              <div
                onClick={() => onSelectStep && onSelectStep(step.tool_id)}
                style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '8px',
                  padding: '6px 12px',
                  background: 'var(--color-surface-secondary)',
                  border: '1px solid var(--color-border)',
                  borderRadius: 'var(--radius-sm)',
                  cursor: onSelectStep ? 'pointer' : 'default',
                  transition: 'border-color 0.15s ease, background-color 0.15s ease',
                }}
                onMouseEnter={(e) => {
                  if (onSelectStep) {
                    e.currentTarget.style.borderColor = 'var(--color-primary)';
                    e.currentTarget.style.backgroundColor = 'var(--color-surface-hover)';
                  }
                }}
                onMouseLeave={(e) => {
                  if (onSelectStep) {
                    e.currentTarget.style.borderColor = 'var(--color-border)';
                    e.currentTarget.style.backgroundColor = 'var(--color-surface-secondary)';
                  }
                }}
              >
                {/* Step Index Badge */}
                <span style={{
                  fontFamily: 'var(--font-mono)',
                  fontSize: '11px',
                  fontWeight: '700',
                  color: 'var(--color-text-muted)',
                }}>
                  {String(step.step_number).padStart(2, '0')}
                </span>

                {/* Category Indicator Dot */}
                <div style={{
                  width: '8px',
                  height: '8px',
                  borderRadius: '50%',
                  backgroundColor: catColor.stroke,
                }} />

                {/* Tool Type & Name */}
                <div style={{ display: 'flex', flexDirection: 'column' }}>
                  <span style={{ fontSize: '12px', fontWeight: '600', color: 'var(--color-text)' }}>
                    {step.name || step.tool_type}
                  </span>
                  <span style={{ fontSize: '10px', color: 'var(--color-text-muted)', fontFamily: 'var(--font-mono)' }}>
                    #{step.tool_id} · {step.tool_type}
                  </span>
                </div>
              </div>

              {!isLast && (
                <ArrowRight size={13} color="var(--color-text-subtle)" style={{ flexShrink: 0 }} />
              )}
            </React.Fragment>
          );
        })}
      </div>
    </div>
  );
};
