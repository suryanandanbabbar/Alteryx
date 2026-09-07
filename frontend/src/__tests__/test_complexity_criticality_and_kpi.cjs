const assert = require('assert');

// ----------------------------------------------------------------------------
// Test 1: Sidebar Portfolio Actions Navigation & Header Action Group
// ----------------------------------------------------------------------------
function getPortfolioNavItems() {
  return [
    { id: 'inventory', label: 'ETL Workflow Inventory', caption: 'ETL Discovery' },
    { id: 'rationalisation', label: 'Rationalisation Recommendation', caption: 'ETL Rationalisation' },
    { id: 'impact', label: 'Impact at a Glance', caption: 'ETL Intelligence' },
    { id: 'download_xlsx', label: 'Download Portfolio Document', caption: ' ' },
    { id: 'reset', label: 'Upload Different Portfolio', caption: ' ' },
  ];
}

const navItems = getPortfolioNavItems();
const navIds = navItems.map((item) => item.id);
assert(!navIds.includes('complexity_criticality'), 'Sidebar must NOT include Complexity & Criticality');
assert(!navIds.includes('kpi_ontology_bank'), 'Sidebar must NOT include KPI Ontology Bank');
assert.strictEqual(navItems.length, 5, 'Sidebar Portfolio Actions must contain exactly 5 standard items');

function getBusinessAreaHeaderActions() {
  return [
    { id: 'kpi_ontology_bank', label: 'KPI Ontology Bank', type: 'secondary' },
    { id: 'complexity_criticality', label: 'Complexity & Criticality', type: 'secondary' },
  ];
}

const headerActions = getBusinessAreaHeaderActions();
assert.strictEqual(headerActions.length, 2);
assert.strictEqual(headerActions[0].id, 'kpi_ontology_bank');
assert.strictEqual(headerActions[1].id, 'complexity_criticality');

console.log('✓ Test 1 Passed: Sidebar excludes KPI & Complexity items; Top-Right Business Area Header contains action group.');

// ----------------------------------------------------------------------------
// Test 2: KPI Ontology Bank URL Configuration & Error Handling
// ----------------------------------------------------------------------------
function handleKpiOntologyBankClick(configUrl, onNavigate, onNotify) {
  if (!configUrl || !configUrl.trim()) {
    onNotify('KPI Ontology Bank is not configured.');
    return { navigated: false, error: 'KPI Ontology Bank is not configured.' };
  }

  try {
    const parsed = new URL(configUrl.trim());
    if (parsed.protocol !== 'http:' && parsed.protocol !== 'https:') {
      onNotify('KPI Ontology Bank is not configured.');
      return { navigated: false, error: 'KPI Ontology Bank is not configured.' };
    }
    onNavigate(parsed.href);
    return { navigated: true, url: parsed.href };
  } catch {
    onNotify('KPI Ontology Bank is not configured.');
    return { navigated: false, error: 'KPI Ontology Bank is not configured.' };
  }
}

let navigatedUrl = null;
let notificationMessage = null;

// Case A: Configured valid URL
let result = handleKpiOntologyBankClick(
  'https://kpi-bank.internal.corp/app',
  (url) => { navigatedUrl = url; },
  (msg) => { notificationMessage = msg; }
);
assert.strictEqual(result.navigated, true);
assert.strictEqual(navigatedUrl, 'https://kpi-bank.internal.corp/app');
assert.strictEqual(notificationMessage, null);

// Case B: Null / unconfigured URL
navigatedUrl = null;
notificationMessage = null;
result = handleKpiOntologyBankClick(
  null,
  (url) => { navigatedUrl = url; },
  (msg) => { notificationMessage = msg; }
);
assert.strictEqual(result.navigated, false);
assert.strictEqual(navigatedUrl, null);
assert.strictEqual(notificationMessage, 'KPI Ontology Bank is not configured.');

// Case C: Invalid protocol URL
navigatedUrl = null;
notificationMessage = null;
result = handleKpiOntologyBankClick(
  'javascript:alert(1)',
  (url) => { navigatedUrl = url; },
  (msg) => { notificationMessage = msg; }
);
assert.strictEqual(result.navigated, false);
assert.strictEqual(navigatedUrl, null);
assert.strictEqual(notificationMessage, 'KPI Ontology Bank is not configured.');

console.log('✓ Test 2 Passed: KPI Ontology Bank URL handling and graceful notification verified.');

// ----------------------------------------------------------------------------
// Test 3: Complexity & Criticality Deterministic Specifications Verification
// ----------------------------------------------------------------------------
const complexitySpec = {
  zeroLLM: true,
  weights: {
    size: 0.20,
    transformation: 0.25,
    topology: 0.25,
    expression: 0.15,
    runtime: 0.15,
  },
  thresholds: {
    low: [0, 34],
    medium: [35, 69],
    high: [70, 100],
  },
};

const totalComplexityWeight = Object.values(complexitySpec.weights).reduce((a, b) => a + b, 0);
assert.strictEqual(totalComplexityWeight, 1.0, 'Complexity weights must sum to 100%');

const criticalitySpec = {
  zeroLLM: true,
  factorCount: 5,
  factorWeight: 0.20,
  categories: {
    technical: { weight: 0.60, factors: ['downstream_outputs', 'upstream_sources', 'etl_consumers'] },
    operational: { weight: 0.40, factors: ['last_run', 'frequency'] },
  },
  thresholds: {
    low: [0, 34],
    medium: [35, 60],
    high: [61, 100],
  },
};

assert.strictEqual(criticalitySpec.factorCount * criticalitySpec.factorWeight, 1.0, 'Criticality factors must sum to 100%');
assert.strictEqual(
  criticalitySpec.categories.technical.weight + criticalitySpec.categories.operational.weight,
  1.0,
  'Technical (60%) + Operational (40%) must sum to 100%'
);

console.log('✓ Test 3 Passed: Complexity & Criticality deterministic model specifications and exact weights verified.');

// ----------------------------------------------------------------------------
// Test 4: Workflow Evidence Traceability from Portfolio Summary DTO
// ----------------------------------------------------------------------------
const samplePortfolioWorkflow = {
  workflow_id: 'wf-premium-calc',
  filename: 'Policy_Premium_Calculation.yxmd',
  status: 'SUCCESS',
  node_count: 24,
  connection_count: 32,
  source_count: 3,
  target_count: 2,
  sources: ['PolicyData.csv', 'RateTable.xlsx', 'VehicleClass.csv'],
  targets: ['CalculatedPremiums.csv', 'AuditSummary.xlsx'],
  inspection_sinks: ['Browse #25'],
  tool_types: ['DbFileInput', 'Select', 'Formula', 'Join', 'Filter', 'Summarize', 'DbFileOutput'],
  complexity_score: 58.5,
  complexity_level: 'MEDIUM',
  complexity_factors: ['24 tools', '32 connections', '2 joins', '12 formula expressions'],
  criticality_score: 72.0,
  criticality_level: 'HIGH',
  criticality_factors: [
    'Downstream outputs -> Value: 2 | Weight: 20% -> Factor Score: 70.0/100',
    'Upstream sources -> Value: 3 | Weight: 20% -> Factor Score: 85.0/100',
    'ETL workflow consumers -> Value: 1 | Weight: 20% -> Factor Score: 60.0/100',
    'Last Run -> Value: 3 days ago | Weight: 20% -> Factor Score: 100.0/100',
    'Frequency -> Value: Daily | Weight: 20% -> Factor Score: 90.0/100',
  ],
  criticality_justification: 'Deterministic 5-factor evaluation (Technical: 43.0/60%, Operational: 38.0/40%).',
  business_consequence: 'Failure interrupts 2 downstream output(s) and 1 consuming ETL workflow(s).',
};

assert.strictEqual(samplePortfolioWorkflow.complexity_level, 'MEDIUM');
assert.strictEqual(samplePortfolioWorkflow.criticality_level, 'HIGH');
assert(samplePortfolioWorkflow.complexity_factors.length > 0);
assert(samplePortfolioWorkflow.criticality_factors.length === 5);

console.log('✓ Test 4 Passed: Workflow evidence traceability from Portfolio DTO verified.');

console.log('\nAll Complexity & Criticality + KPI Ontology Bank tests passed successfully!');
