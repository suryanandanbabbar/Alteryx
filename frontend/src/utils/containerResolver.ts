import { NodeDTO } from '../types/workflow';

/**
 * Deterministic mapping derived from docs/tool-support-matrix.md categories.
 * Maps Alteryx tool types and visual categories to canonical Tool Support Matrix categories.
 */
const MATRIX_CATEGORY_MAP: Record<string, string> = {
  // In/Out
  dbfileinput: 'In/Out',
  dbfileoutput: 'In/Out',
  browsev2: 'In/Out',
  browse: 'In/Out',
  textinput: 'In/Out',
  directory: 'In/Out',
  datetimenow: 'In/Out',
  fileinput: 'In/Out',
  fileoutput: 'In/Out',
  input: 'In/Out',
  output: 'In/Out',

  // Preparation
  autofield: 'Preparation',
  datacleansepro: 'Preparation',
  cleanse: 'Preparation',
  filter: 'Preparation',
  formula: 'Preparation',
  generaterows: 'Preparation',
  multifieldformula: 'Preparation',
  multirowformula: 'Preparation',
  recordid: 'Preparation',
  sample: 'Preparation',
  select: 'Preparation',
  alteryxselect: 'Preparation',
  selectrecords: 'Preparation',
  sort: 'Preparation',
  tile: 'Preparation',
  unique: 'Preparation',
  rank: 'Preparation',
  randomsamplesize: 'Preparation',
  createsamples: 'Preparation',
  multifieldbinning: 'Preparation',

  // Join
  appendfields: 'Join',
  findreplace: 'Join',
  fuzzymatch: 'Join',
  join: 'Join',
  joinmultiple: 'Join',
  makegroup: 'Join',
  union: 'Join',

  // Parse
  datetime: 'Parse',
  regex: 'Parse',
  texttocolumns: 'Parse',
  xmlparse: 'Parse',
  parse: 'Parse',

  // Transform
  arrange: 'Transform',
  countrecords: 'Transform',
  crosstab: 'Transform',
  makecolumns: 'Transform',
  runningtotal: 'Transform',
  summarize: 'Transform',
  transpose: 'Transform',
  reshape: 'Transform',

  // Developer
  blockuntildone: 'Developer',
  detour: 'Developer',
  detourend: 'Developer',
  download: 'Developer',
  dynamicinput: 'Developer',
  dynamicrename: 'Developer',
  dynamicreplace: 'Developer',
  dynamicselect: 'Developer',
  fieldinfo: 'Developer',
  jsonbuild: 'Developer',
  jsonparse: 'Developer',
  message: 'Developer',
  python: 'Developer',
  r: 'Developer',
  runcommand: 'Developer',
  developer: 'Developer',

  // Documentation
  textbox: 'Documentation',
  toolcontainer: 'Documentation',
  comment: 'Documentation',
  documentation: 'Documentation',

  // Reporting
  email: 'Reporting',
  layout: 'Reporting',
  render: 'Reporting',
  reportfooter: 'Reporting',
  reportheader: 'Reporting',
  reportmap: 'Reporting',
  reporttext: 'Reporting',
  table: 'Reporting',
  interactivechart: 'Reporting',
  chart: 'Reporting',
  image: 'Reporting',
  reporting: 'Reporting',

  // Spatial
  buffer: 'Spatial',
  createpoints: 'Spatial',
  distance: 'Spatial',
  findnearest: 'Spatial',
  generalize: 'Spatial',
  heatmap: 'Spatial',
  makegrid: 'Spatial',
  polybuild: 'Spatial',
  polysplit: 'Spatial',
  smooth: 'Spatial',
  spatialinfo: 'Spatial',
  spatialmatch: 'Spatial',
  spatialprocess: 'Spatial',
  tradearea: 'Spatial',
  spatial: 'Spatial',

  // In-Database
  lockininput: 'In-Database',
  lockinstreamin: 'In-Database',
  lockinstreamout: 'In-Database',
  lockinfilter: 'In-Database',
  lockinformula: 'In-Database',
  lockinjoin: 'In-Database',
  lockinselect: 'In-Database',
  in_database: 'In-Database',

  // Connectors
  amazons3download: 'Connectors',
  amazons3upload: 'Connectors',
  sharepointfilesinput: 'Connectors',
  connector: 'Connectors',
  connectors: 'Connectors',
};

/**
 * Resolves the container for a given tool through the deterministic fallback chain:
 * 1. Primary: Actual .yxmd ToolContainer caption (authoritative from workflow structure)
 * 2. Secondary: Matrix-defined category/group fallback from docs/tool-support-matrix.md
 * 3. Final fallback: 'Not specified'
 */
export function resolveToolContainer(node: NodeDTO | null | undefined): string {
  if (!node) return 'Not specified';

  // 1. Primary: actual .yxmd ToolContainer caption
  if (node.container_name && node.container_name.trim().length > 0) {
    return node.container_name.trim();
  }

  // 2. Secondary fallback: matrix-defined category from docs/tool-support-matrix.md
  const typeKey = (node.tool_type || '').toLowerCase().replace(/[^a-z0-9]/g, '');
  if (typeKey && MATRIX_CATEGORY_MAP[typeKey]) {
    return MATRIX_CATEGORY_MAP[typeKey];
  }

  const catKey = (node.visual_category || '').toLowerCase().replace(/[^a-z0-9]/g, '');
  if (catKey && MATRIX_CATEGORY_MAP[catKey]) {
    return MATRIX_CATEGORY_MAP[catKey];
  }

  // 3. Final fallback
  return 'Not specified';
}
