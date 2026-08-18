/**
 * Centralized Visual Theme & Palette matching reference screenshots.
 */

export interface CategoryColor {
  fill: string;
  stroke: string;
  badge: string;
  text: string;
  badgeBg: string;
}

export const CATEGORY_COLORS: Record<string, CategoryColor> = {
  input: {
    fill: '#132845',
    stroke: '#38bdf8',
    badge: '#38bdf8',
    badgeBg: 'rgba(56, 189, 248, 0.15)',
    text: '#e0f2fe',
  },
  output: {
    fill: '#2e1245',
    stroke: '#e879f9',
    badge: '#e879f9',
    badgeBg: 'rgba(232, 121, 249, 0.15)',
    text: '#fae8ff',
  },
  filter: {
    fill: '#382a12',
    stroke: '#fbbf24',
    badge: '#fbbf24',
    badgeBg: 'rgba(251, 191, 36, 0.15)',
    text: '#fef3c7',
  },
  datetime: {
    fill: '#221845',
    stroke: '#a78bfa',
    badge: '#a78bfa',
    badgeBg: 'rgba(167, 139, 250, 0.15)',
    text: '#ede9fe',
  },
  summarize: {
    fill: '#123824',
    stroke: '#4ade80',
    badge: '#4ade80',
    badgeBg: 'rgba(74, 222, 128, 0.15)',
    text: '#dcfce7',
  },
  join: {
    fill: '#123338',
    stroke: '#2dd4bf',
    badge: '#2dd4bf',
    badgeBg: 'rgba(45, 212, 191, 0.15)',
    text: '#ccfbf1',
  },
  sort: {
    fill: '#132838',
    stroke: '#22d3ee',
    badge: '#22d3ee',
    badgeBg: 'rgba(34, 211, 238, 0.15)',
    text: '#cffafe',
  },
  unique: {
    fill: '#1a382b',
    stroke: '#34d399',
    badge: '#34d399',
    badgeBg: 'rgba(52, 211, 153, 0.15)',
    text: '#d1fae5',
  },
  select: {
    fill: '#1e293b',
    stroke: '#94a3b8',
    badge: '#94a3b8',
    badgeBg: 'rgba(148, 163, 184, 0.15)',
    text: '#f1f5f9',
  },
  formula: {
    fill: '#382412',
    stroke: '#f97316',
    badge: '#f97316',
    badgeBg: 'rgba(249, 115, 22, 0.15)',
    text: '#ffedd5',
  },
  transform: {
    fill: '#172033',
    stroke: '#64748b',
    badge: '#64748b',
    badgeBg: 'rgba(100, 116, 139, 0.15)',
    text: '#e2e8f0',
  },
};

export const getCategoryColor = (category: string): CategoryColor => {
  return CATEGORY_COLORS[category] || CATEGORY_COLORS.transform;
};
