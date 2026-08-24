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

/**
 * Generic deterministic taxonomy mapping tool types and categories to canonical workflow roles.
 */
export const getWorkflowRole = (toolType: string, visualCategory?: string, isBusinessOutput?: boolean): string => {
  if (isBusinessOutput) {
    return 'Deliverable Output';
  }

  const type = (toolType || '').toLowerCase();
  const category = (visualCategory || '').toLowerCase();

  // Precise Tool Type matching
  if (type.includes('crosstab') || type.includes('transpose')) return 'Reshaping';
  if (type.includes('summarize') || type.includes('countrecords')) return 'Aggregation';
  if (type.includes('formula')) return 'Data Transformation';
  if (type.includes('filter')) return 'Data Filtering';
  if (type.includes('join') || type.includes('appendfields') || type.includes('findreplace')) return 'Data Integration';
  if (type.includes('union')) return 'Data Consolidation';
  if (type.includes('sort')) return 'Ordering';
  if (type.includes('select')) return 'Field Selection';
  if (type.includes('unique')) return 'Deduplication';
  if (type.includes('sample')) return 'Sampling';
  if (type.includes('datetime')) return 'Temporal Formatting';
  if (type.includes('regex') || type.includes('texttocolumns') || type.includes('xmlparse') || type.includes('jsonparse')) return 'Data Parsing';
  if (type.includes('input') || type.includes('fileinput') || type.includes('directory')) return 'Data Input';
  if (type.includes('output') || type.includes('browse')) return 'Data Output';
  if (type.includes('blockuntildone') || type.includes('message') || type.includes('test')) return 'Execution Control';
  if (type.includes('macro')) return 'Macro Interface';

  // Category fallback matching
  if (category === 'input') return 'Data Input';
  if (category === 'output') return 'Data Output';
  if (category === 'join') return 'Data Integration';
  if (category === 'union') return 'Data Consolidation';
  if (category === 'filter') return 'Data Filtering';
  if (category === 'formula') return 'Data Transformation';
  if (category === 'summarize') return 'Aggregation';
  if (category === 'reshape') return 'Reshaping';
  if (category === 'sort') return 'Ordering';
  if (category === 'select') return 'Field Selection';
  if (category === 'unique') return 'Deduplication';
  if (category === 'datetime') return 'Temporal Formatting';
  if (category === 'regex' || category === 'parse') return 'Data Parsing';
  if (category === 'developer') return 'Execution Control';
  if (category === 'reporting') return 'Reporting';
  if (category === 'spatial') return 'Spatial Processing';
  if (category === 'transform' || category === 'preparation') return 'Data Transformation';

  return 'Tool Operation';
};

export const WORKFLOW_ROLE_COLORS: Record<string, string> = {
  'Data Input': '#0284c7',
  'Data Output': '#9333ea',
  'Deliverable Output': '#9333ea',
  'Data Filtering': '#d97706',
  'Data Transformation': '#ea580c',
  'Aggregation': '#16a34a',
  'Reshaping': '#64748b',
  'Ordering': '#0891b2',
  'Data Integration': '#0d9488',
  'Data Consolidation': '#059669',
  'Field Selection': '#64748b',
  'Deduplication': '#059669',
  'Sampling': '#8b5cf6',
  'Temporal Formatting': '#7c3aed',
  'Data Parsing': '#0891b2',
  'Execution Control': '#475569',
  'Macro Interface': '#6366f1',
  'Spatial Processing': '#2563eb',
  'Reporting': '#db2777',
  'Tool Operation': '#64748b',
};

export const getWorkflowRoleColor = (role: string): string => {
  return WORKFLOW_ROLE_COLORS[role] || '#64748b';
};
