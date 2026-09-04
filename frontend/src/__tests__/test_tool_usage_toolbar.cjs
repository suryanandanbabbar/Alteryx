const assert = require('assert');

// Test 1: Tool Occurrence Counting & Stats Generation
function computeToolUsageStats(nodes) {
  const counts = new Map();
  for (const node of nodes) {
    const type = node.tool_type || 'Unknown';
    counts.set(type, (counts.get(type) || 0) + 1);
  }

  const sorted = Array.from(counts.entries())
    .map(([toolType, count]) => ({ toolType, count }))
    .sort((a, b) => b.count - a.count || a.toolType.localeCompare(b.toolType));

  return {
    totalOccurrences: nodes.length,
    distinctTypes: counts.size,
    stats: sorted,
  };
}

const mockNodes = [
  { tool_id: 1, tool_type: 'Input Data', tool_name: 'Input 1', annotation: 'Orders CSV', category: 'In/Out' },
  { tool_id: 2, tool_type: 'Formula', tool_name: 'Formula 1', annotation: 'Calculate Tax', category: 'Preparation' },
  { tool_id: 3, tool_type: 'Formula', tool_name: 'Formula 2', annotation: 'Calculate Total', category: 'Preparation' },
  { tool_id: 4, tool_type: 'Formula', tool_name: 'Formula 3', annotation: 'Format Date', category: 'Preparation' },
  { tool_id: 5, tool_type: 'Join', tool_name: 'Join 1', annotation: 'Join Customers', category: 'Join' },
  { tool_id: 6, tool_type: 'Join', tool_name: 'Join 2', annotation: 'Join Products', category: 'Join' },
  { tool_id: 7, tool_type: 'Filter', tool_name: 'Filter 1', annotation: 'Active Records', category: 'Preparation' },
  { tool_id: 8, tool_type: 'Output Data', tool_name: 'Output 1', annotation: 'Sales Report', category: 'In/Out' },
];

const stats = computeToolUsageStats(mockNodes);
assert.strictEqual(stats.totalOccurrences, 8, 'Total occurrences should be 8');
assert.strictEqual(stats.distinctTypes, 5, 'Distinct types should be 5');
assert.deepStrictEqual(stats.stats[0], { toolType: 'Formula', count: 3 }, 'Top tool should be Formula with count 3');
assert.deepStrictEqual(stats.stats[1], { toolType: 'Join', count: 2 }, 'Second tool should be Join with count 2');
console.log('✓ Test 1 Passed: Tool occurrence stats correctly aggregate counts and sort descending.');

// Test 2: Filtering nodes with AND composition (Tool Type + Search Query)
function filterNodes(nodes, selectedToolType, searchQuery) {
  let result = nodes;
  if (selectedToolType) {
    result = result.filter(n => (n.tool_type || '').toLowerCase() === selectedToolType.toLowerCase());
  }
  if (!searchQuery.trim()) {
    return result;
  }
  const q = searchQuery.toLowerCase().trim();
  return result.filter(node => (
    node.tool_name.toLowerCase().includes(q) ||
    node.tool_type.toLowerCase().includes(q) ||
    (node.annotation && node.annotation.toLowerCase().includes(q)) ||
    (node.category && node.category.toLowerCase().includes(q))
  ));
}

// Case 2a: No filter
assert.strictEqual(filterNodes(mockNodes, null, '').length, 8);

// Case 2b: Filter by tool type only
const formulaNodes = filterNodes(mockNodes, 'Formula', '');
assert.strictEqual(formulaNodes.length, 3);
assert.ok(formulaNodes.every(n => n.tool_type === 'Formula'));

// Case 2c: Filter by tool type + search query matching one
const taxFormula = filterNodes(mockNodes, 'Formula', 'tax');
assert.strictEqual(taxFormula.length, 1);
assert.strictEqual(taxFormula[0].tool_name, 'Formula 1');

// Case 2d: Filter by tool type + search query matching none
const missingFormula = filterNodes(mockNodes, 'Formula', 'Customers');
assert.strictEqual(missingFormula.length, 0);

// Case 2e: Filter by search query across all tools
const joinSearch = filterNodes(mockNodes, null, 'Customers');
assert.strictEqual(joinSearch.length, 1);
assert.strictEqual(joinSearch[0].tool_type, 'Join');

console.log('✓ Test 2 Passed: Node filtering with tool selection and search composition operates correctly.');

// Test 3: Portfolio Workflow Filtering by Tool Type
const mockPortfolioWorkflows = [
  {
    workflow_id: 'wf1',
    filename: 'Claims_Processing.yxmd',
    business_area_tag: 'Claims & Risk',
    status: 'SUCCESS',
    tool_types: ['Input Data', 'Formula', 'Join', 'Output Data'],
  },
  {
    workflow_id: 'wf2',
    filename: 'Actuarial_Triangulation.yxmd',
    business_area_tag: 'Actuarial',
    status: 'SUCCESS',
    tool_types: ['Input Data', 'Summarize', 'Formula', 'Output Data'],
  },
  {
    workflow_id: 'wf3',
    filename: 'Legal_Matter_Aggregation.yxmd',
    business_area_tag: 'Legal',
    status: 'SUCCESS',
    tool_types: ['Input Data', 'Select', 'Output Data'],
  },
  {
    workflow_id: 'wf4',
    filename: 'Sales_Performance.yxmd',
    business_area_tag: 'Sales & Distribution',
    status: 'SUCCESS',
    tool_types: ['Input Data', 'Formula', 'Join', 'Summarize', 'Output Data'],
  },
];

function filterPortfolioWorkflows(workflows, businessArea, selectedToolType, searchQuery) {
  let result = workflows;

  if (businessArea) {
    result = result.filter(w => w.business_area_tag === businessArea);
  }

  if (selectedToolType) {
    result = result.filter(w =>
      (w.tool_types || []).some(t => t.toLowerCase() === selectedToolType.toLowerCase())
    );
  }

  if (searchQuery) {
    const q = searchQuery.toLowerCase();
    result = result.filter(w =>
      w.filename.toLowerCase().includes(q)
    );
  }

  return result;
}

// Case 3a: All workflows using 'Summarize'
const summarizeWfs = filterPortfolioWorkflows(mockPortfolioWorkflows, null, 'Summarize', '');
assert.strictEqual(summarizeWfs.length, 2);
assert.deepStrictEqual(summarizeWfs.map(w => w.workflow_id), ['wf2', 'wf4']);

// Case 3b: Workflows in 'Sales & Distribution' using 'Join'
const salesJoinWfs = filterPortfolioWorkflows(mockPortfolioWorkflows, 'Sales & Distribution', 'Join', '');
assert.strictEqual(salesJoinWfs.length, 1);
assert.strictEqual(salesJoinWfs[0].workflow_id, 'wf4');

// Case 3c: Workflows in 'Legal' using 'Formula' (should be empty)
const legalFormulaWfs = filterPortfolioWorkflows(mockPortfolioWorkflows, 'Legal', 'Formula', '');
assert.strictEqual(legalFormulaWfs.length, 0);

console.log('✓ Test 3 Passed: Portfolio workflow filtering by tool type and business domain functions correctly.');

// Test 4: Level 1 Area Counts with Tool Filter
function computeAreaCounts(workflows, selectedToolType) {
  const counts = {
    'Claims & Risk': 0,
    'Legal': 0,
    'Underwriting': 0,
    'Sales & Distribution': 0,
    'Actuarial': 0,
    'Other / Unclassified': 0,
  };

  const primaryKeys = new Set(['Claims & Risk', 'Legal', 'Underwriting', 'Sales & Distribution', 'Actuarial']);

  for (const w of workflows) {
    if (w.status === 'SUCCESS') {
      if (selectedToolType) {
        const hasTool = (w.tool_types || []).some(
          t => t.toLowerCase() === selectedToolType.toLowerCase()
        );
        if (!hasTool) continue;
      }
      const rawTag = w.business_area_tag;
      if (rawTag && primaryKeys.has(rawTag)) {
        counts[rawTag]++;
      } else {
        counts['Other / Unclassified']++;
      }
    }
  }

  return counts;
}

const unfilteredCounts = computeAreaCounts(mockPortfolioWorkflows, null);
assert.strictEqual(unfilteredCounts['Claims & Risk'], 1);
assert.strictEqual(unfilteredCounts['Actuarial'], 1);
assert.strictEqual(unfilteredCounts['Legal'], 1);
assert.strictEqual(unfilteredCounts['Sales & Distribution'], 1);

const formulaFilteredCounts = computeAreaCounts(mockPortfolioWorkflows, 'Formula');
assert.strictEqual(formulaFilteredCounts['Claims & Risk'], 1);
assert.strictEqual(formulaFilteredCounts['Actuarial'], 1);
assert.strictEqual(formulaFilteredCounts['Legal'], 0);
assert.strictEqual(formulaFilteredCounts['Sales & Distribution'], 1);

console.log('✓ Test 4 Passed: Level 1 business area counts reactively reflect active tool filter.');

console.log('\nAll Tool Usage Toolbar unit tests passed successfully!');
