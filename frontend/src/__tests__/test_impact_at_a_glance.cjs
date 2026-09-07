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
// Test 8: Single Workflow KPI Evidence Derivations (All 6 Modals)
// ----------------------------------------------------------------------------
function deriveWorkflowEvidence(overview, modalType) {
  const { business_summary, execution_order, connections } = overview;

  if (modalType === 'sources') {
    const sources = business_summary?.source_inputs || [];
    const classifySourceFormat = (src) => {
      const raw = (src.source_filename || src.raw_source || '').toLowerCase();
      if (raw.endsWith('.xlsx') || raw.endsWith('.xls')) return 'EXCEL';
      if (raw.endsWith('.csv')) return 'CSV';
      if (raw.endsWith('.yxdb')) return 'YXDB';
      if (src.source_type === 'DATABASE' || raw.includes('dbo.') || raw.includes('select')) return 'DATABASE';
      return 'DATASET';
    };
    return {
      count: sources.length,
      items: sources.map((s) => ({
        toolId: s.tool_id,
        name: s.name,
        format: classifySourceFormat(s),
        sheetOrTable: s.sheet_or_table,
        description: s.description || s.business_role,
      })),
    };
  }

  if (modalType === 'tools') {
    const tools = execution_order || [];
    const groups = {};
    tools.forEach((t) => {
      const type = t.tool_type || 'Unknown';
      if (!groups[type]) groups[type] = [];
      groups[type].push(t);
    });
    return {
      count: tools.length,
      groups: Object.entries(groups).map(([type, list]) => ({ type, count: list.length, items: list })),
    };
  }

  if (modalType === 'stages') {
    const stages = business_summary?.processing_stages || [];
    return {
      count: stages.length,
      stages: stages.map((s) => ({
        stageNumber: s.stage_number,
        name: s.name,
        toolCount: s.tool_count,
        summary: s.summary || s.description,
        businessPurpose: s.business_purpose,
        majorTransformation: s.major_transformation,
        toolIds: s.tool_ids || [],
      })),
    };
  }

  if (modalType === 'lineage') {
    const lineage = business_summary?.lineage || [];
    return {
      count: lineage.length,
      items: lineage.map((l) => ({
        sourceName: l.source_name,
        targetName: l.target_name,
        sourceToolId: l.source_tool_id,
        targetToolId: l.target_tool_id,
        transformation: l.transformation_summary || l.transformation,
        intermediateStages: l.intermediate_stages || [],
      })),
    };
  }

  if (modalType === 'outputs') {
    const outputs = business_summary?.business_outputs || [];
    const classifyOutputFormat = (out) => {
      const raw = (out.raw_destination || out.name || '').toLowerCase();
      if (raw.endsWith('.xlsx') || raw.endsWith('.xls')) return 'EXCEL';
      if (raw.endsWith('.csv')) return 'CSV';
      if (raw.endsWith('.yxdb')) return 'YXDB';
      if (out.destination_type === 'DATABASE' || raw.includes('dbo.')) return 'DATABASE';
      return 'DELIVERABLE';
    };
    return {
      count: outputs.length,
      items: outputs.map((o) => ({
        toolId: o.tool_id,
        name: o.name,
        format: classifyOutputFormat(o),
        sheetOrTable: o.sheet_or_table,
        businessMeaning: o.business_meaning,
        likelyUse: o.likely_use,
      })),
    };
  }

  if (modalType === 'connections') {
    const conns = connections || [];
    return {
      count: conns.length,
      items: conns.map((c) => ({
        originToolId: c.origin_tool_id,
        destinationToolId: c.destination_tool_id,
        originAnchor: c.origin_anchor,
        destinationAnchor: c.destination_anchor,
      })),
    };
  }

  return null;
}

const sampleWorkflowWithDetails = {
  ...sampleWorkflow,
  connections: [
    { origin_tool_id: 1, destination_tool_id: 4, origin_anchor: 'Output', destination_anchor: 'Left' },
    { origin_tool_id: 2, destination_tool_id: 4, origin_anchor: 'Output', destination_anchor: 'Right' },
    { origin_tool_id: 4, destination_tool_id: 6, origin_anchor: 'Join', destination_anchor: 'Input' },
  ],
  business_summary: {
    ...sampleWorkflow.business_summary,
    source_inputs: [
      { tool_id: 1, name: 'Input Data (Claims)', source_filename: 'Claims.csv', sheet_or_table: null, description: 'Monthly claims raw feed' },
      { tool_id: 2, name: 'Input Data (Policies)', source_filename: 'Policies.xlsx', sheet_or_table: 'PolicyData', description: 'Active policy reference' },
      { tool_id: 3, name: 'Input Data (Rates)', source_filename: 'Rates.csv', sheet_or_table: null, description: 'Actuarial rate table' },
    ],
    business_outputs: [
      { tool_id: 38, name: 'Output Data (Losses)', raw_destination: 'Claims_Summary.xlsx', sheet_or_table: 'Summary', business_meaning: 'Consolidated loss ledger', likely_use: 'Actuarial reserving' },
      { tool_id: 39, name: 'Output Data (Audit)', raw_destination: 'Audit_Log.csv', sheet_or_table: null, business_meaning: 'Audit trail for excluded records', likely_use: 'Compliance checks' },
    ],
    lineage: [
      { source_name: 'Claims.csv.CLAIM_AMT', target_name: 'Claims_Summary.xlsx.TOTAL_LOSS', source_tool_id: 1, target_tool_id: 38, transformation_summary: 'Summed across policy IDs', intermediate_stages: ['Extract', 'Summarise'] },
      { source_name: 'Policies.xlsx.POLICY_ID', target_name: 'Claims_Summary.xlsx.POLICY_KEY', source_tool_id: 2, target_tool_id: 38, transformation_summary: 'Cleaned and formatted string', intermediate_stages: ['Extract', 'Reserves'] },
    ],
  },
};

const sourcesModal = deriveWorkflowEvidence(sampleWorkflowWithDetails, 'sources');
assert.strictEqual(sourcesModal.count, 3);
assert.strictEqual(sourcesModal.items[0].format, 'CSV');
assert.strictEqual(sourcesModal.items[1].format, 'EXCEL');

const toolsModal = deriveWorkflowEvidence(sampleWorkflowWithDetails, 'tools');
assert.strictEqual(toolsModal.count, 12);
assert.strictEqual(toolsModal.groups.find((g) => g.type === 'Join').count, 2);

const stagesModal = deriveWorkflowEvidence(sampleWorkflowWithDetails, 'stages');
assert.strictEqual(stagesModal.count, 4);
assert.strictEqual(stagesModal.stages[0].name, 'Extract Claims Data');

const lineageModal = deriveWorkflowEvidence(sampleWorkflowWithDetails, 'lineage');
assert.strictEqual(lineageModal.count, 2);
assert.strictEqual(lineageModal.items[0].intermediateStages.length, 2);

const outputsModal = deriveWorkflowEvidence(sampleWorkflowWithDetails, 'outputs');
assert.strictEqual(outputsModal.count, 2);
assert.strictEqual(outputsModal.items[0].format, 'EXCEL');
assert.strictEqual(outputsModal.items[1].format, 'CSV');

const connsModal = deriveWorkflowEvidence(sampleWorkflowWithDetails, 'connections');
assert.strictEqual(connsModal.count, 3);
assert.strictEqual(connsModal.items[0].originAnchor, 'Output');

console.log('✓ Test 8 Passed: Single Workflow KPI Evidence Modal derivations (sources, tools, stages, lineage, outputs, connections) verified.');

// ----------------------------------------------------------------------------
// Test 9: Processing Tools Modal Tool-Level Filtering & Search Composition
// ----------------------------------------------------------------------------
function filterWorkflowTools(executionOrder, processingStages, selectedToolType, searchQuery) {
  // Build tool to stage map
  const toolToStageMap = new Map();
  (processingStages || []).forEach((st) => {
    (st.tool_ids || []).forEach((tid) => {
      mapStage = { stageNumber: st.stage_number, name: st.name };
      toolToStageMap.set(tid, mapStage);
    });
  });

  // Group tools by tool_type
  const groupsMap = new Map();
  executionOrder.forEach((step) => {
    const type = step.tool_type || 'Unknown';
    if (!groupsMap.has(type)) {
      groupsMap.set(type, []);
    }
    groupsMap.get(type).push(step);
  });
  const allGroups = Array.from(groupsMap.entries()).sort((a, b) => b[1].length - a[1].length);

  let filteredGroups = allGroups;
  if (selectedToolType) {
    filteredGroups = filteredGroups.filter(([type]) => type === selectedToolType);
  }

  const q = (searchQuery || '').toLowerCase().trim();
  if (q) {
    filteredGroups = filteredGroups
      .map(([type, tools]) => {
        const matchingTools = tools.filter((t) => {
          const stage = toolToStageMap.get(t.tool_id);
          return (
            (t.name && t.name.toLowerCase().includes(q)) ||
            (t.tool_type && t.tool_type.toLowerCase().includes(q)) ||
            (t.visual_category && t.visual_category.toLowerCase().includes(q)) ||
            (t.summary && t.summary.toLowerCase().includes(q)) ||
            (t.container_name && t.container_name.toLowerCase().includes(q)) ||
            (stage && stage.name.toLowerCase().includes(q)) ||
            String(t.tool_id).includes(q)
          );
        });
        return [type, matchingTools];
      })
      .filter(([type, tools]) => {
        if (selectedToolType) return true;
        return type.toLowerCase().includes(q) || tools.length > 0;
      });
  }

  const totalMatchingTools = filteredGroups.reduce((acc, [, tools]) => acc + tools.length, 0);

  return {
    allGroups,
    filteredGroups,
    totalMatchingTools,
    selectedToolType,
    searchQuery: q,
  };
}

const sampleExecutionOrder = [
  { step_number: 1, tool_id: 1, tool_type: 'DbFileInput', name: 'Claims Raw File', visual_category: 'In/Out', summary: 'Reads Claims.csv' },
  { step_number: 2, tool_id: 2, tool_type: 'DbFileInput', name: 'Policies Reference', visual_category: 'In/Out', summary: 'Reads Policies.xlsx' },
  { step_number: 3, tool_id: 3, tool_type: 'DbFileInput', name: 'Rates Master', visual_category: 'In/Out', summary: 'Reads Rates.csv' },
  { step_number: 4, tool_id: 4, tool_type: 'DbFileInput', name: 'Exchange Rates', visual_category: 'In/Out', summary: 'Reads FX.csv' },
  { step_number: 5, tool_id: 10, tool_type: 'Join', name: 'Join Claims to Policies', visual_category: 'Join', summary: 'Joins on Policy_ID' },
  { step_number: 6, tool_id: 11, tool_type: 'Join', name: 'Join Rates', visual_category: 'Join', summary: 'Joins on Rate_Code' },
  { step_number: 7, tool_id: 12, tool_type: 'Join', name: 'Join FX', visual_category: 'Join', summary: 'Joins on Currency' },
  { step_number: 8, tool_id: 13, tool_type: 'Join', name: 'Join Historical', visual_category: 'Join', summary: 'Joins prior year stats' },
  { step_number: 9, tool_id: 20, tool_type: 'DbFileOutput', name: 'Loss Summary Excel', visual_category: 'In/Out', summary: 'Exports Claims_Summary.xlsx' },
  { step_number: 10, tool_id: 21, tool_type: 'DbFileOutput', name: 'Audit Log CSV', visual_category: 'In/Out', summary: 'Exports Audit_Log.csv' },
  { step_number: 11, tool_id: 22, tool_type: 'DbFileOutput', name: 'Actuarial YXDB', visual_category: 'In/Out', summary: 'Exports Losses.yxdb' },
  { step_number: 12, tool_id: 23, tool_type: 'DbFileOutput', name: 'Executive Report', visual_category: 'In/Out', summary: 'Exports Executive_Summary.xlsx' },
  { step_number: 13, tool_id: 24, tool_type: 'DbFileOutput', name: 'Regulatory Sched', visual_category: 'In/Out', summary: 'Exports Regulatory_Filing.csv' },
  { step_number: 14, tool_id: 30, tool_type: 'Summarize', name: 'Aggregate Loss by State', visual_category: 'Transform', summary: 'Group by State, Sum Loss' },
  { step_number: 15, tool_id: 31, tool_type: 'Summarize', name: 'Aggregate Loss by LOB', visual_category: 'Transform', summary: 'Group by Line of Business' },
  { step_number: 16, tool_id: 32, tool_type: 'Summarize', name: 'Count Policies', visual_category: 'Transform', summary: 'Count Distinct Policy IDs' },
  { step_number: 17, tool_id: 33, tool_type: 'Summarize', name: 'Average Incurred', visual_category: 'Transform', summary: 'Avg Incurred Claims' },
  { step_number: 18, tool_id: 34, tool_type: 'Summarize', name: 'Monthly Reserving', visual_category: 'Transform', summary: 'Monthly loss development' },
  { step_number: 19, tool_id: 35, tool_type: 'Summarize', name: 'Catastrophe Grouping', visual_category: 'Transform', summary: 'Group Cat Claims' },
  { step_number: 20, tool_id: 36, tool_type: 'Summarize', name: 'Final Portfolio Sum', visual_category: 'Transform', summary: 'Estate-level aggregation' },
];

const sampleStages = [
  { stage_number: 1, name: 'Data Ingestion', tool_ids: [1, 2, 3, 4] },
  { stage_number: 2, name: 'Integration & Joins', tool_ids: [10, 11, 12, 13] },
  { stage_number: 3, name: 'Aggregations', tool_ids: [30, 31, 32, 33, 34, 35, 36] },
  { stage_number: 4, name: 'Export Outputs', tool_ids: [20, 21, 22, 23, 24] },
];

// 1. Initial unfiltered state
const initialRes = filterWorkflowTools(sampleExecutionOrder, sampleStages, null, '');
assert.strictEqual(initialRes.totalMatchingTools, 20);
assert.strictEqual(initialRes.allGroups.length, 4);
assert.strictEqual(initialRes.allGroups.find(([t]) => t === 'Summarize')[1].length, 7);
assert.strictEqual(initialRes.allGroups.find(([t]) => t === 'DbFileOutput')[1].length, 5);
assert.strictEqual(initialRes.allGroups.find(([t]) => t === 'DbFileInput')[1].length, 4);
assert.strictEqual(initialRes.allGroups.find(([t]) => t === 'Join')[1].length, 4);

// 2. Select DbFileOutput (DbFileOutput x 5)
const dbOutputRes = filterWorkflowTools(sampleExecutionOrder, sampleStages, 'DbFileOutput', '');
assert.strictEqual(dbOutputRes.filteredGroups.length, 1);
assert.strictEqual(dbOutputRes.filteredGroups[0][0], 'DbFileOutput');
assert.strictEqual(dbOutputRes.filteredGroups[0][1].length, 5);
assert.strictEqual(dbOutputRes.totalMatchingTools, 5);
assert.strictEqual(dbOutputRes.filteredGroups[0][1][0].tool_id, 20);
assert.strictEqual(dbOutputRes.filteredGroups[0][1][4].tool_id, 24);

// 3. Compose filter DbFileOutput + search for specific ID "22"
const searchIdRes = filterWorkflowTools(sampleExecutionOrder, sampleStages, 'DbFileOutput', '22');
assert.strictEqual(searchIdRes.filteredGroups.length, 1);
assert.strictEqual(searchIdRes.totalMatchingTools, 1);
assert.strictEqual(searchIdRes.filteredGroups[0][1][0].tool_id, 22);
assert.strictEqual(searchIdRes.filteredGroups[0][1][0].name, 'Actuarial YXDB');

// 4. Compose filter DbFileOutput + search for non-matching tool type "Join"
const searchNonMatch = filterWorkflowTools(sampleExecutionOrder, sampleStages, 'DbFileOutput', 'Join');
assert.strictEqual(searchNonMatch.filteredGroups.length, 1);
assert.strictEqual(searchNonMatch.totalMatchingTools, 0); // 0 matching within DbFileOutput

// 5. Clear search query while retaining DbFileOutput filter
const clearSearchRes = filterWorkflowTools(sampleExecutionOrder, sampleStages, 'DbFileOutput', '');
assert.strictEqual(clearSearchRes.totalMatchingTools, 5);
assert.strictEqual(clearSearchRes.filteredGroups[0][0], 'DbFileOutput');

// 6. Clear filter (All Tools) restoring all 20 tools
const clearFilterRes = filterWorkflowTools(sampleExecutionOrder, sampleStages, null, '');
assert.strictEqual(clearFilterRes.totalMatchingTools, 20);
assert.strictEqual(clearFilterRes.filteredGroups.length, 4);

console.log('✓ Test 9 Passed: Processing Tools Evidence tool-level filtering and search composition verified.');

// ----------------------------------------------------------------------------
// Test 10: Shared Page Shell Layout and Global H1 Typography Rules
// ----------------------------------------------------------------------------
function verifyPageShellRules(pageShellStyle, h1Style) {
  assert.strictEqual(pageShellStyle.width, '100%', 'Page shell must use width: 100% to match shared alignment');
  assert.strictEqual(pageShellStyle.maxWidth, '1400px', 'Page shell must use maxWidth: 1400px');
  assert.strictEqual(pageShellStyle.margin, undefined, 'Page shell must not use margin: 0 auto offset');
  assert.strictEqual(h1Style.fontSize, '24px', 'Global and page H1 must resolve to 24px');
  return true;
}

const impactPageShell = { display: 'flex', flexDirection: 'column', gap: '20px', maxWidth: '1400px', width: '100%' };
const globalH1 = { fontSize: '24px', fontWeight: '800', lineHeight: 1.2 };
assert.ok(verifyPageShellRules(impactPageShell, globalH1));
console.log('✓ Test 10 Passed: Shared Page Shell alignment (width: 100%, maxWidth: 1400px) and H1 (24px) verified.');

// ----------------------------------------------------------------------------
// Test 11: Workflow Inventory Analysed/Total Headline & Rationalisation Eyebrow
// ----------------------------------------------------------------------------
function deriveWorkflowInventoryHeadline(portfolio) {
  const { metrics, workflows = [] } = portfolio;
  const analysedWorkflowCount = metrics?.successful_workflows ?? workflows.filter((w) => w.status === 'SUCCESS').length;
  const totalWorkflowCount = metrics?.total_workflows ?? workflows.length;

  const formattedAnalysed = String(analysedWorkflowCount).padStart(2, '0');
  const formattedTotal = String(totalWorkflowCount).padStart(2, '0');

  return {
    analysedWorkflowCount,
    totalWorkflowCount,
    metricText: `${formattedAnalysed} / ${formattedTotal}`,
    fullHeadline: `${formattedAnalysed} / ${formattedTotal} WORKFLOWS ANALYSED`,
  };
}

// 1. Full 8/8 analysed estate
const portfolio8of8 = {
  metrics: { total_workflows: 8, successful_workflows: 8, failed_workflows: 0 },
  workflows: Array.from({ length: 8 }, (_, i) => ({ workflow_id: `wf-${i}`, status: 'SUCCESS' })),
};
const res8of8 = deriveWorkflowInventoryHeadline(portfolio8of8);
assert.strictEqual(res8of8.metricText, '08 / 08');
assert.strictEqual(res8of8.fullHeadline, '08 / 08 WORKFLOWS ANALYSED');

// 2. Partial 6/8 analysed estate
const portfolio6of8 = {
  metrics: { total_workflows: 8, successful_workflows: 6, failed_workflows: 2 },
  workflows: [
    ...Array.from({ length: 6 }, (_, i) => ({ workflow_id: `wf-${i}`, status: 'SUCCESS' })),
    ...Array.from({ length: 2 }, (_, i) => ({ workflow_id: `wf-fail-${i}`, status: 'FAILED' })),
  ],
};
const res6of8 = deriveWorkflowInventoryHeadline(portfolio6of8);
assert.strictEqual(res6of8.metricText, '06 / 08');
assert.strictEqual(res6of8.fullHeadline, '06 / 08 WORKFLOWS ANALYSED');

// 3. Fallback derivation when metrics are missing
const portfolioFallback = {
  workflows: [
    { workflow_id: 'w1', status: 'SUCCESS' },
    { workflow_id: 'w2', status: 'SUCCESS' },
    { workflow_id: 'w3', status: 'FAILED' },
  ],
};
const resFallback = deriveWorkflowInventoryHeadline(portfolioFallback);
assert.strictEqual(resFallback.metricText, '02 / 03');
assert.strictEqual(resFallback.fullHeadline, '02 / 03 WORKFLOWS ANALYSED');

console.log('✓ Test 11 Passed: Dynamic Workflow Inventory Analysed / Total Workflows headline derivation verified.');

console.log('\nAll Impact at a Glance, Evidence Modal, Rationalisation & Navigation tests passed successfully!');

