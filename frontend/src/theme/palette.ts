/**
 * Semantic tool category styling for node badges and graph indicators.
 */

export interface CategoryColor {
  fill: string;
  stroke: string;
  badge: string;
  badgeBg: string;
  text: string;
}

export const CATEGORY_COLORS: Record<string, CategoryColor> = {
  input: {
    fill: '#e0f2fe',
    stroke: '#0284c7',
    badge: '#0284c7',
    badgeBg: 'rgba(2, 132, 199, 0.12)',
    text: '#0369a1',
  },
  output: {
    fill: '#f3e8ff',
    stroke: '#9333ea',
    badge: '#9333ea',
    badgeBg: 'rgba(147, 51, 234, 0.12)',
    text: '#7e22ce',
  },
  filter: {
    fill: '#fffbeb',
    stroke: '#d97706',
    badge: '#d97706',
    badgeBg: 'rgba(217, 119, 6, 0.12)',
    text: '#b45309',
  },
  datetime: {
    fill: '#ede9fe',
    stroke: '#7c3aed',
    badge: '#7c3aed',
    badgeBg: 'rgba(124, 58, 237, 0.12)',
    text: '#6d28d9',
  },
  summarize: {
    fill: '#dcfce7',
    stroke: '#16a34a',
    badge: '#16a34a',
    badgeBg: 'rgba(22, 163, 74, 0.12)',
    text: '#15803d',
  },
  join: {
    fill: '#ccfbf1',
    stroke: '#0d9488',
    badge: '#0d9488',
    badgeBg: 'rgba(13, 148, 136, 0.12)',
    text: '#0f766e',
  },
  sort: {
    fill: '#cffafe',
    stroke: '#0891b2',
    badge: '#0891b2',
    badgeBg: 'rgba(8, 145, 178, 0.12)',
    text: '#0e7490',
  },
  unique: {
    fill: '#d1fae5',
    stroke: '#059669',
    badge: '#059669',
    badgeBg: 'rgba(5, 150, 105, 0.12)',
    text: '#047857',
  },
  select: {
    fill: '#f1f5f9',
    stroke: '#64748b',
    badge: '#64748b',
    badgeBg: 'rgba(100, 116, 139, 0.12)',
    text: '#475569',
  },
  formula: {
    fill: '#ffedd5',
    stroke: '#ea580c',
    badge: '#ea580c',
    badgeBg: 'rgba(234, 88, 12, 0.12)',
    text: '#c2410c',
  },
  transform: {
    fill: '#f1f5f9',
    stroke: '#475569',
    badge: '#475569',
    badgeBg: 'rgba(71, 85, 105, 0.12)',
    text: '#334155',
  },
};

export const getCategoryColor = (category: string): CategoryColor => {
  return CATEGORY_COLORS[category] || CATEGORY_COLORS.transform;
};
