const assert = require('assert');

// ----------------------------------------------------------------------------
// Test 1: Single Workflow Metric Extraction and Aggregation
// ----------------------------------------------------------------------------
function deriveWorkflowImpactMetrics(overview) {
  const { metrics, business_summary, execution_order } = overview;
  const toolSupport = metrics.support_summary || {};
  const fullySupported = toolSupport['FULL'] || 0;
  const passThrough = toolSupport['PASS_THROUGH'] || 0;
  const totalTools = metrics.total_nodes || 0;
  const totalConnections = metrics.total_connections || 0;
  const inputCount = metrics.input_count || business_summary?.source_inputs?.length || 0;
  const outputCount = metrics.business_output_count || metrics.output_count || business_summary?.business_outputs?.length || 0;
  const stageCount = business_summary?.processing_stages?.length || metrics.container_count || 1;
  const lineageCount = business_summary?.lineage?.length || 0;
  const transformationCount = business_summary?.transformations?.length || 0;
  const businessRuleCount = business_summary?.business_rules?.length || 0;

  const toolTypeCounts = {};
  (execution_order || []).forEach((step) => {
    const type = step.tool_type || 'Unknown';
    toolTypeCounts[type] = (toolTypeCounts[type] || 0) + 1;
  });

  const joinsCount = (toolTypeCounts['Join'] || 0) + (toolTypeCounts['Union'] || 0) + (toolTypeCounts['FindReplace'] || 0);
  const transformsCount = (toolTypeCounts['Formula'] || 0) + (toolTypeCounts['Select'] || 0) + (toolTypeCounts['Filter'] || 0) + (toolTypeCounts['DataCleansing'] || 0);
  const analyticsCount = (toolTypeCounts['Summarize'] || 0) + (toolTypeCounts['Sort'] || 0) + (toolTypeCounts['CrossTab'] || 0) + (toolTypeCounts['Transpose'] || 0);

  const narrative = `From ${totalTools} extracted processing tools across ${inputCount} data inputs, the platform automatically derived ${totalConnections} data-flow dependencies, ${stageCount} logical process stages, ${lineageCount} column-level lineage mappings, and ${outputCount} final business deliverables with full AI-assisted semantic documentation.`;

  return {
    fullySupported,
    passThrough,
    totalTools,
    totalConnections,
    inputCount,
    outputCount,
    stageCount,
    lineageCount,
    transformationCount,
    businessRuleCount,
    joinsCount,
    transformsCount,
    analyticsCount,
    narrative,
  };
}

const sampleWorkflow = {
  analysis_id: 'wf-123',
  source: { original_filename: 'Monthly_Claims_Aggregation.yxmd' },
  metrics: {
    total_nodes: 39,
    total_connections: 44,
    input_count: 3,
    output_count: 2,
    business_output_count: 2,
    container_count: 4,
    support_summary: { FULL: 36, PASS_THROUGH: 3 },
  },
  business_summary: {
    one_line_purpose: 'Aggregates monthly claims across regional sources and calculates loss reserves.',
    source_inputs: [{ tool_id: 1 }, { tool_id: 2 }, { tool_id: 3 }],
    processing_stages: [
      { stage_number: 1, name: 'Extract Claims Data', tool_count: 2 },
      { stage_number: 2, name: 'Create Summarizations', tool_count: 12 },
      { stage_number: 3, name: 'Apply Reserves Logic', tool_count: 6 },
      { stage_number: 4, name: 'Final Output', tool_count: 4 },
    ],
    transformations: [{ category: 'Calculation' }, { category: 'Filter' }, { category: 'Join' }],
    business_rules: [{ rule_name: 'Reserve Calculation' }, { rule_name: 'Exclude Void Claims' }],
    lineage: [
      { source_name: 'Claims.csv', target_name: 'Claims_Summary.xlsx' },
      { source_name: 'Policies.csv', target_name: 'Claims_Summary.xlsx' },
    ],
    business_outputs: [{ tool_id: 38 }, { tool_id: 39 }],
  },
  execution_order: [
    { tool_id: 1, tool_type: 'Input Data' },
    { tool_id: 2, tool_type: 'Input Data' },
    { tool_id: 3, tool_type: 'Input Data' },
    { tool_id: 4, tool_type: 'Join' },
    { tool_id: 5, tool_type: 'Join' },
    { tool_id: 6, tool_type: 'Formula' },
    { tool_id: 7, tool_type: 'Formula' },
    { tool_id: 8, tool_type: 'Filter' },
    { tool_id: 9, tool_type: 'Summarize' },
    { tool_id: 10, tool_type: 'Sort' },
    { tool_id: 38, tool_type: 'Output Data' },
    { tool_id: 39, tool_type: 'Output Data' },
  ],
};

const wfImpact = deriveWorkflowImpactMetrics(sampleWorkflow);
assert.strictEqual(wfImpact.totalTools, 39);
assert.strictEqual(wfImpact.totalConnections, 44);
assert.strictEqual(wfImpact.inputCount, 3);
assert.strictEqual(wfImpact.outputCount, 2);
assert.strictEqual(wfImpact.stageCount, 4);
assert.strictEqual(wfImpact.lineageCount, 2);
assert.strictEqual(wfImpact.joinsCount, 2);
assert.strictEqual(wfImpact.transformsCount, 3);
assert.strictEqual(wfImpact.analyticsCount, 2);
assert.strictEqual(
  wfImpact.narrative,
  'From 39 extracted processing tools across 3 data inputs, the platform automatically derived 44 data-flow dependencies, 4 logical process stages, 2 column-level lineage mappings, and 2 final business deliverables with full AI-assisted semantic documentation.'
);
console.log('✓ Test 1 Passed: Single Workflow Impact metrics and narrative derived accurately.');

// ----------------------------------------------------------------------------
// Test 2: Portfolio Impact Metric Aggregation and Process Stages
// ----------------------------------------------------------------------------
function derivePortfolioImpactMetrics(portfolio) {
  const { metrics, workflows = [], rationalisation_candidates = [], shared_sources = [], shared_targets = [] } = portfolio;
  const totalWorkflows = metrics?.total_workflows ?? workflows.length;
  const successfulWorkflows = metrics?.successful_workflows ?? workflows.filter((w) => w.status === 'SUCCESS').length;
  const totalTools = metrics?.total_tools ?? workflows.reduce((acc, w) => acc + (w.node_count || 0), 0);
  const totalConnections = workflows.reduce((acc, w) => acc + (w.connection_count || 0), 0);
  const totalSources = metrics?.total_sources ?? workflows.reduce((acc, w) => acc + (w.source_count || 0), 0);
  const uniqueSources = metrics?.unique_sources ?? totalSources;
  const totalTargets = metrics?.total_targets ?? workflows.reduce((acc, w) => acc + (w.target_count || 0), 0);
  const uniqueTargets = metrics?.unique_targets ?? totalTargets;
  const rationalisationCount = rationalisation_candidates.length;
  const totalSttmMappings = workflows.reduce((acc, w) => acc + (w.sttm_mappings_count || 0), 0);

  const totalProcessStages = workflows.reduce((acc, w) => {
    const stageCount = w.processing_stages && w.processing_stages.length > 0 ? w.processing_stages.length : (w.node_count > 0 ? 1 : 0);
    return acc + stageCount;
  }, 0);

  // Migration asset counts
  const pythonAssetCount = successfulWorkflows;
  const jsonAssetCount = successfulWorkflows;
  const sttmAssetCount = workflows.filter((w) => (w.sttm_mappings_count || 0) > 0 || w.status === 'SUCCESS').length;
  const businessReportCount = successfulWorkflows;
  const toolSpecCount = successfulWorkflows;
  const completePackagesCount = successfulWorkflows;
  const totalArtifactsCount = pythonAssetCount + jsonAssetCount + sttmAssetCount + businessReportCount + toolSpecCount;

  const businessAreas = new Set(workflows.map((w) => w.business_area_tag || w.business_area?.business_area || 'Other')).size;

  const strongestCandidate = [...rationalisation_candidates].sort((a, b) => {
    if (a.recommendation_type === 'CONSOLIDATE' && b.recommendation_type !== 'CONSOLIDATE') return -1;
    if (b.recommendation_type === 'CONSOLIDATE' && a.recommendation_type !== 'CONSOLIDATE') return 1;
    return (b.opportunity_score || 0) - (a.opportunity_score || 0);
  })[0];

  return {
    totalWorkflows,
    successfulWorkflows,
    totalTools,
    totalConnections,
    totalSources,
    uniqueSources,
    totalTargets,
    uniqueTargets,
    totalProcessStages,
    rationalisationCount,
    totalSttmMappings,
    pythonAssetCount,
    jsonAssetCount,
    sttmAssetCount,
    businessReportCount,
    toolSpecCount,
    completePackagesCount,
    totalArtifactsCount,
    businessAreas,
    strongestCandidate,
  };
}

const samplePortfolio = {
  portfolio_id: 'port-456',
  portfolio_name: 'Insurance Enterprise Estate',
  metrics: {
    total_workflows: 3,
    successful_workflows: 3,
    failed_workflows: 0,
    total_tools: 55,
    total_sources: 8,
    unique_sources: 6,
    total_targets: 5,
    unique_targets: 4,
    shared_sources_count: 2,
    shared_targets_count: 1,
    tool_distribution: {
      Formula: 15,
      Join: 10,
      Filter: 8,
      Summarize: 12,
      Select: 10,
    },
  },
  workflows: [
    {
      workflow_id: 'w1',
      filename: 'Monthly_Claims_A.yxmd',
      node_count: 20,
      connection_count: 22,
      source_count: 3,
      target_count: 2,
      sources: ['Claims.csv', 'PolicyRef.xlsx', 'Rates.csv'],
      targets: ['LossReport.xlsx', 'Summary.csv'],
      tool_types: ['Formula', 'Join', 'Summarize', 'Filter'],
      sttm_mappings_count: 8,
      business_area_tag: 'Claims & Risk',
      status: 'SUCCESS',
      processing_stages: [
        { stage_number: 1, name: 'Extract Claims Data', tool_count: 2 },
        { stage_number: 2, name: 'Create Summarizations', tool_count: 12 },
        { stage_number: 3, name: 'Final Output', tool_count: 4 },
      ],
    },
    {
      workflow_id: 'w2',
      filename: 'Monthly_Claims_B.yxmd',
      node_count: 20,
      connection_count: 22,
      source_count: 3,
      target_count: 2,
      sources: ['Claims.csv', 'RegionalClaims.xlsx', 'Rates.csv'],
      targets: ['LossReport.xlsx'],
      tool_types: ['Formula', 'Join', 'Summarize'],
      sttm_mappings_count: 8,
      business_area_tag: 'Claims & Risk',
      status: 'SUCCESS',
      processing_stages: [
        { stage_number: 1, name: 'Ingest Regional Data', tool_count: 3 },
        { stage_number: 2, name: 'Consolidate Losses', tool_count: 10 },
      ],
    },
    {
      workflow_id: 'w3',
      filename: 'Underwriting_Policy_Issuance.yxmd',
      node_count: 15,
      connection_count: 16,
      source_count: 2,
      target_count: 1,
      sources: ['PolicyApps.xlsx', 'RiskRating.csv'],
      targets: ['IssuedPolicies.xlsx'],
      tool_types: ['Select', 'Filter', 'Formula'],
      sttm_mappings_count: 5,
      business_area_tag: 'Underwriting',
      status: 'SUCCESS',
      processing_stages: [
        { stage_number: 1, name: 'Policy Eligibility Scoring', tool_count: 5 },
        { stage_number: 2, name: 'Premium Calculation', tool_count: 6 },
        { stage_number: 3, name: 'Publish Deliverables', tool_count: 4 },
      ],
    },
  ],
  rationalisation_candidates: [
    {
      candidate_id: 'cand-1',
      workflow_names: ['Monthly_Claims_A.yxmd', 'Monthly_Claims_B.yxmd'],
      recommendation_type: 'CONSOLIDATE',
      opportunity_score: 98,
      proposed_strategy: 'Merge identical claim consolidation pipelines.',
    },
  ],
};

const portImpact = derivePortfolioImpactMetrics(samplePortfolio);
assert.strictEqual(portImpact.totalWorkflows, 3);
assert.strictEqual(portImpact.successfulWorkflows, 3);
assert.strictEqual(portImpact.totalTools, 55);
assert.strictEqual(portImpact.totalSources, 8);
assert.strictEqual(portImpact.uniqueSources, 6);
assert.strictEqual(portImpact.totalProcessStages, 8); // 3 + 2 + 3 = 8 stages
assert.strictEqual(portImpact.rationalisationCount, 1);
assert.strictEqual(portImpact.pythonAssetCount, 3);
assert.strictEqual(portImpact.jsonAssetCount, 3);
assert.strictEqual(portImpact.sttmAssetCount, 3);
assert.strictEqual(portImpact.businessReportCount, 3);
assert.strictEqual(portImpact.toolSpecCount, 3);
assert.strictEqual(portImpact.completePackagesCount, 3);
assert.strictEqual(portImpact.totalArtifactsCount, 15);
assert.strictEqual(portImpact.strongestCandidate.candidate_id, 'cand-1');
console.log('✓ Test 2 Passed: Portfolio Impact metrics, process stage aggregation, and asset quantities derived accurately.');

// ----------------------------------------------------------------------------
// Test 3: Sidebar ETL Workflow Inventory Dynamic Business Areas
// ----------------------------------------------------------------------------
function deriveSidebarBusinessAreas(portfolio) {
  if (portfolio.business_areas && portfolio.business_areas.length > 0) {
    return portfolio.business_areas
      .filter((ba) => ba.workflow_count > 0 || (ba.workflows && ba.workflows.length > 0))
      .map((ba) => ({ name: ba.business_area, count: ba.workflow_count || ba.workflows?.length || 0 }));
  }
  const counts = new Map();
  (portfolio.workflows || []).forEach((w) => {
    const tag = w.business_area_tag || w.business_area?.business_area || 'Other / Unclassified';
    counts.set(tag, (counts.get(tag) || 0) + 1);
  });
  return Array.from(counts.entries()).map(([name, count]) => ({ name, count }));
}

const areas = deriveSidebarBusinessAreas(samplePortfolio);
assert.strictEqual(areas.length, 2);
assert.strictEqual(areas.find((a) => a.name === 'Claims & Risk').count, 2);
assert.strictEqual(areas.find((a) => a.name === 'Underwriting').count, 1);
console.log('✓ Test 3 Passed: Sidebar ETL Workflow Inventory business areas dynamically extracted with accurate counts.');

// ----------------------------------------------------------------------------
// Test 4: Workflows Analysed Evidence Modal Data Mapping
// ----------------------------------------------------------------------------
function deriveWorkflowsEvidence(portfolio) {
  const { workflows = [], metrics } = portfolio;
  const totalWorkflows = metrics?.total_workflows ?? workflows.length;
  const successfulWorkflows = metrics?.successful_workflows ?? workflows.filter((w) => w.status === 'SUCCESS').length;

  const mappedWorkflows = workflows.map((wf) => {
    const stagesCount = wf.processing_stages && wf.processing_stages.length > 0 ? wf.processing_stages.length : (wf.node_count > 0 ? 1 : 0);
    return {
      id: wf.workflow_id,
      name: wf.filename,
      businessArea: wf.business_area_tag || 'Other',
      status: wf.status || 'SUCCESS',
      toolCount: wf.node_count || 0,
      sourceCount: wf.source_count || (wf.sources ? wf.sources.length : 0),
      targetCount: wf.target_count || (wf.targets ? wf.targets.length : 0),
      stageCount: stagesCount,
    };
  });

  return {
    totalWorkflows,
    successfulWorkflows,
    headline: `${successfulWorkflows} of ${totalWorkflows} Workflows Successfully Analysed`,
    workflows: mappedWorkflows,
  };
}

const wfEvidence = deriveWorkflowsEvidence(samplePortfolio);
assert.strictEqual(wfEvidence.totalWorkflows, 3);
assert.strictEqual(wfEvidence.successfulWorkflows, 3);
assert.strictEqual(wfEvidence.headline, '3 of 3 Workflows Successfully Analysed');
assert.strictEqual(wfEvidence.workflows.length, 3);
assert.strictEqual(wfEvidence.workflows[0].stageCount, 3);
assert.strictEqual(wfEvidence.workflows[1].stageCount, 2);
assert.strictEqual(wfEvidence.workflows[2].stageCount, 3);
console.log('✓ Test 4 Passed: Workflows Analysed modal evidence mapping verified.');

// ----------------------------------------------------------------------------
// Test 5: Output Targets Evidence Modal Data Mapping & Format Badges
// ----------------------------------------------------------------------------
function deriveTargetsEvidence(portfolio) {
  const { workflows = [], metrics } = portfolio;
  const totalTargets = metrics?.total_targets ?? workflows.reduce((acc, w) => acc + (w.target_count || (w.targets ? w.targets.length : 0)), 0);
  const uniqueTargets = metrics?.unique_targets ?? totalTargets;

  const classifyFormat = (tgt) => {
    if (tgt.endsWith('.xlsx') || tgt.endsWith('.xls')) return 'EXCEL';
    if (tgt.endsWith('.csv')) return 'CSV';
    if (tgt.endsWith('.yxdb')) return 'YXDB';
    if (tgt.includes('dbo.') || tgt.includes('INSERT') || tgt.includes('UPDATE')) return 'DATABASE';
    return 'DELIVERABLE';
  };

  const targetsByWorkflow = workflows.map((wf) => ({
    workflowId: wf.workflow_id,
    filename: wf.filename,
    businessArea: wf.business_area_tag,
    targets: (wf.targets || []).map((t) => ({
      name: t,
      format: classifyFormat(t),
    })),
  }));

  return {
    totalTargets,
    uniqueTargets,
    headline: `${totalTargets} Output Targets across ${workflows.length} Workflows / ${uniqueTargets} Unique Outputs`,
    targetsByWorkflow,
  };
}

const targetsEvidence = deriveTargetsEvidence(samplePortfolio);
assert.strictEqual(targetsEvidence.totalTargets, 5);
assert.strictEqual(targetsEvidence.uniqueTargets, 4);
assert.strictEqual(targetsEvidence.headline, '5 Output Targets across 3 Workflows / 4 Unique Outputs');
assert.strictEqual(targetsEvidence.targetsByWorkflow[0].targets[0].format, 'EXCEL');
assert.strictEqual(targetsEvidence.targetsByWorkflow[0].targets[1].format, 'CSV');
assert.strictEqual(targetsEvidence.targetsByWorkflow[2].targets[0].format, 'EXCEL');
console.log('✓ Test 5 Passed: Output Targets modal evidence mapping and format classification verified.');

// ----------------------------------------------------------------------------
// Test 6: Configurable Sidebar Navigation Items and Captions
// ----------------------------------------------------------------------------
function resolveSidebarCaptions(items) {
  return items.map((item) => ({
    id: item.id,
    label: item.label,
    caption: item.caption || item.label,
  }));
}

const defaultWorkflowNav = [
  { id: 'overview', label: 'Workflow Overview' },
  { id: 'impact', label: 'Impact at a Glance', caption: 'Custom Impact Subtext' },
];
const resolvedNav = resolveSidebarCaptions(defaultWorkflowNav);
assert.strictEqual(resolvedNav[0].caption, 'Workflow Overview');
assert.strictEqual(resolvedNav[1].caption, 'Custom Impact Subtext');
console.log('✓ Test 6 Passed: Configurable sidebar captions fallback to label and support custom captions.');

// ----------------------------------------------------------------------------
// Test 7: Tool Type Normalization (Ensuring Numeric/Invalid Strings are Filtered)
// ----------------------------------------------------------------------------
function normalizeToolType(toolType) {
  if (!toolType || typeof toolType !== 'string' || toolType.trim() === '' || /^\d+$/.test(toolType.trim())) {
    return 'Unknown';
  }
  return toolType.trim();
}

assert.strictEqual(normalizeToolType('1'), 'Unknown');
assert.strictEqual(normalizeToolType('42'), 'Unknown');
assert.strictEqual(normalizeToolType(''), 'Unknown');
assert.strictEqual(normalizeToolType(null), 'Unknown');
assert.strictEqual(normalizeToolType('Formula'), 'Formula');
assert.strictEqual(normalizeToolType('AlteryxBasePluginsGui.DbFileInput.DbFileInput'), 'AlteryxBasePluginsGui.DbFileInput.DbFileInput');
console.log('✓ Test 7 Passed: Tool type normalization filters invalid numeric identifiers.');

console.log('\nAll Impact at a Glance, Evidence Modal & Navigation tests passed successfully!');

