import React, { useState } from 'react';
import { PieChart as PieIcon } from 'lucide-react';
import { EvaluationFactorDTO } from '../types/portfolio';

interface EvaluationModelDonutChartProps {
  title: string;
  subtitle: string;
  factors: EvaluationFactorDTO[];
  totalWeightPct?: number;
  technicalWeightPct?: number | null;
  operationalWeightPct?: number | null;
  themeVariant?: 'complexity' | 'criticality';
}

// Monochromatic brand orange palette derived from #FB4E0B
const BRAND_ORANGE_PALETTE = [
  '#FDB08E', // Light Peach Tint (Factor 1)
  '#FC835A', // Coral Orange (Factor 2)
  '#FB4E0B', // Core Brand Orange (Factor 3)
  '#D94008', // Deep Terracotta (Factor 4)
  '#A83208', // Dark Rust Orange (Factor 5)
];

export const EvaluationModelDonutChart: React.FC<EvaluationModelDonutChartProps> = ({
  title,
  subtitle,
  factors,
  totalWeightPct = 100,
  technicalWeightPct,
  operationalWeightPct,
  themeVariant = 'complexity',
}) => {
  const [hoveredId, setHoveredId] = useState<string | null>(null);

  const colors = BRAND_ORANGE_PALETTE;
  const accentColor = '#FB4E0B';
  const accentBg = 'rgba(251, 78, 11, 0.12)';

  // SVG Geometry parameters
  const size = 200;
  const center = size / 2;
  const radius = 82;
  const innerRadius = 52;
  const total = factors.reduce((sum, f) => sum + (f.weight_pct || 0), 0) || totalWeightPct;

  // Calculate slice geometry
  let currentAngle = -90; // Start at 12 o'clock
  const slices = factors.map((factor, index) => {
    const fraction = factor.weight_pct / total;
    const angleSpan = fraction * 360;
    const startAngle = currentAngle;
    const endAngle = currentAngle + angleSpan;
    currentAngle = endAngle;

    // Convert degrees to radians
    const startRad = (startAngle * Math.PI) / 180;
    const endRad = (endAngle * Math.PI) / 180;

    // Outer arc coordinates
    const x1 = center + radius * Math.cos(startRad);
    const y1 = center + radius * Math.sin(startRad);
    const x2 = center + radius * Math.cos(endRad);
    const y2 = center + radius * Math.sin(endRad);

    // Inner arc coordinates
    const x3 = center + innerRadius * Math.cos(endRad);
    const y3 = center + innerRadius * Math.sin(endRad);
    const x4 = center + innerRadius * Math.cos(startRad);
    const y4 = center + innerRadius * Math.sin(startRad);

    const largeArcFlag = angleSpan > 180 ? 1 : 0;

    const pathData = [
      `M ${x1} ${y1}`,
      `A ${radius} ${radius} 0 ${largeArcFlag} 1 ${x2} ${y2}`,
      `L ${x3} ${y3}`,
      `A ${innerRadius} ${innerRadius} 0 ${largeArcFlag} 0 ${x4} ${y4}`,
      'Z',
    ].join(' ');

    // Center of the slice for percentage text placement
    const midAngle = (startAngle + endAngle) / 2;
    const midRad = (midAngle * Math.PI) / 180;
    const labelRadius = (radius + innerRadius) / 2;
    const labelX = center + labelRadius * Math.cos(midRad);
    const labelY = center + labelRadius * Math.sin(midRad);

    const color = colors[index % colors.length];

    return {
      factor,
      pathData,
      color,
      labelX,
      labelY,
      midAngle,
    };
  });

  const activeFactor = factors.find((f) => f.id === hoveredId);

  return (
    <div
      style={{
        background: 'var(--color-surface-secondary)',
        border: '1px solid var(--color-border)',
        borderRadius: 'var(--radius-md, 8px)',
        padding: '18px 20px',
        display: 'flex',
        flexDirection: 'column',
        gap: '16px',
        boxShadow: '0 2px 6px rgba(0, 0, 0, 0.08)',
      }}
    >
      {/* Chart Header */}
      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', flexWrap: 'wrap', gap: '10px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <div
            style={{
              width: '28px',
              height: '28px',
              borderRadius: '6px',
              background: accentBg,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: accentColor,
              flexShrink: 0,
            }}
          >
            <PieIcon size={16} />
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
            <h4
              style={{
                fontSize: '13.5px',
                fontWeight: '800',
                color: 'var(--color-text)',
                margin: 0,
                letterSpacing: '-0.01em',
              }}
            >
              {title}
            </h4>
            <span style={{ fontSize: '11.5px', color: 'var(--color-text-muted)' }}>
              {subtitle}
            </span>
          </div>
        </div>

        {/* Optional Subtotal Category Badges for Criticality (Technical 60% / Operational 40%) */}
        {(technicalWeightPct !== undefined && operationalWeightPct !== undefined) && (
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <span
              style={{
                fontSize: '10.5px',
                fontWeight: '700',
                padding: '2px 7px',
                borderRadius: '4px',
                background: 'rgba(251, 78, 11, 0.1)',
                color: '#FB4E0B',
                border: '1px solid rgba(251, 78, 11, 0.25)',
              }}
            >
              Technical: {technicalWeightPct}%
            </span>
            <span
              style={{
                fontSize: '10.5px',
                fontWeight: '700',
                padding: '2px 7px',
                borderRadius: '4px',
                background: 'rgba(217, 64, 8, 0.1)',
                color: '#D94008',
                border: '1px solid rgba(217, 64, 8, 0.25)',
              }}
            >
              Operational: {operationalWeightPct}%
            </span>
          </div>
        )}
      </div>

      {/* Main Content Area: Donut Chart + Comprehensive Legend */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'auto 1fr',
          gap: '20px',
          alignItems: 'center',
        }}
      >
        {/* SVG Donut Visual */}
        <div style={{ position: 'relative', width: `${size}px`, height: `${size}px`, flexShrink: 0 }}>
          <svg
            width={size}
            height={size}
            viewBox={`0 0 ${size} ${size}`}
            role="img"
            aria-label={`${title} visualization`}
            style={{ overflow: 'visible' }}
          >
            <defs>
              <filter id={`shadow-${themeVariant}`} x="-10%" y="-10%" width="120%" height="120%">
                <feDropShadow dx="0" dy="2" stdDeviation="3" floodOpacity="0.4" />
              </filter>
            </defs>

            {/* Render Donut Slices */}
            {slices.map((s) => {
              const isHovered = hoveredId === s.factor.id;
              const isDimmed = hoveredId !== null && !isHovered;

              return (
                <g key={s.factor.id}>
                  <path
                    d={s.pathData}
                    fill={s.color}
                    stroke="var(--color-surface, #0f172a)"
                    strokeWidth={2}
                    opacity={isDimmed ? 0.45 : 1}
                    filter={isHovered ? `url(#shadow-${themeVariant})` : undefined}
                    style={{
                      cursor: 'pointer',
                      transition: 'all 0.18s ease',
                      transformOrigin: `${center}px ${center}px`,
                      transform: isHovered ? 'scale(1.045)' : 'scale(1)',
                    }}
                    onMouseEnter={() => setHoveredId(s.factor.id)}
                    onMouseLeave={() => setHoveredId(null)}
                  />
                  {/* Percentage on Slice */}
                    <text
                      x={s.labelX}
                      y={s.labelY + 3.5}
                      textAnchor="middle"
                      fill="#ffffff"
                      fontSize="10.5px"
                      fontWeight="800"
                      pointerEvents="none"
                      style={{
                        textShadow: '0 1px 3px rgba(0, 0, 0, 0.85), 0 0 2px rgba(0, 0, 0, 0.85)',
                        opacity: isDimmed ? 0.35 : 1,
                        transition: 'opacity 0.18s ease',
                      }}
                    >
                      {s.factor.weight_pct}%
                    </text>
                </g>
              );
            })}

            {/* Center Hole Information (100% / TOTAL WEIGHT) */}
            <circle
              cx={center}
              cy={center}
              r={innerRadius - 2}
              fill="var(--color-surface, #0b121d)"
              stroke="var(--color-border, #1e293b)"
              strokeWidth={1}
            />
            <text
              x={center}
              y={center - 3}
              textAnchor="middle"
              fill="var(--color-text, #f8fafc)"
              fontSize="16px"
              fontWeight="900"
              letterSpacing="-0.02em"
            >
              {total}%
            </text>
            <text
              x={center}
              y={center + 14}
              textAnchor="middle"
              fill="var(--color-text-muted, #94a3b8)"
              fontSize="8.5px"
              fontWeight="800"
              letterSpacing="0.08em"
            >
              TOTAL WEIGHT
            </text>
          </svg>
        </div>

        {/* Comprehensive Factor Legend */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', minWidth: '220px' }}>
          {factors.map((factor, idx) => {
            const isHovered = hoveredId === factor.id;
            const color = colors[idx % colors.length];

            return (
              <div
                key={factor.id}
                onMouseEnter={() => setHoveredId(factor.id)}
                onMouseLeave={() => setHoveredId(null)}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  padding: '5px 8px',
                  borderRadius: '6px',
                  background: isHovered ? 'rgba(255, 255, 255, 0.05)' : 'transparent',
                  border: `1px solid ${isHovered ? 'var(--color-border)' : 'transparent'}`,
                  cursor: 'pointer',
                  transition: 'all 0.15s ease',
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', minWidth: 0 }}>
                  <div
                    style={{
                      width: '10px',
                      height: '10px',
                      borderRadius: '50%',
                      background: color,
                      flexShrink: 0,
                      boxShadow: isHovered ? `0 0 8px ${color}` : 'none',
                    }}
                  />
                  <div style={{ display: 'flex', flexDirection: 'column', minWidth: 0 }}>
                    <span
                      style={{
                        fontSize: '12px',
                        fontWeight: isHovered ? '700' : '600',
                        color: isHovered ? 'var(--color-text)' : 'var(--color-text-secondary)',
                        whiteSpace: 'nowrap',
                        overflow: 'hidden',
                        textOverflow: 'ellipsis',
                      }}
                      title={factor.name}
                    >
                      {factor.name}
                    </span>
                  </div>
                </div>

                <span
                  style={{
                    fontSize: '11.5px',
                    fontWeight: '800',
                    color: color,
                    background: `${color}18`,
                    border: `1px solid ${color}35`,
                    padding: '1px 6px',
                    borderRadius: '4px',
                    flexShrink: 0,
                    marginLeft: '8px',
                  }}
                >
                  {factor.weight_pct}%
                </span>
              </div>
            );
          })}
        </div>
      </div>

      {/* Interactive Detail Tooltip/Banner when Hovering a Factor */}
      {activeFactor && activeFactor.description && (
        <div
          style={{
            fontSize: '11.5px',
            color: 'var(--color-text-secondary)',
            background: 'var(--color-surface)',
            border: '1px solid var(--color-border)',
            borderRadius: '6px',
            padding: '7px 10px',
            lineHeight: '1.4',
            animation: 'fadeIn 0.15s ease',
          }}
        >
          <strong style={{ color: 'var(--color-text)' }}>{activeFactor.name}:</strong> {activeFactor.description}
        </div>
      )}
    </div>
  );
};
