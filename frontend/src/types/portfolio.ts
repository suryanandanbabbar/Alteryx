/**
 * TypeScript definitions for Multi-Workflow Portfolio Analysis and ETL Rationalisation.
 */

import { BusinessStageDTO } from './workflow';

export interface BusinessAreaClassificationDTO {
  business_area: string;
  confidence: string;
  evidence: string[];
  classification_source: string;
  secondary_business_areas: string[];
  classification_conflict?: boolean;
  business_area_taxonomy_version?: string;
}

export interface PortfolioWorkflowSummaryDTO {
  workflow_id: string;
  analysis_id?: string;
  filename: string;
  relative_path: string;
  status: 'SUCCESS' | 'FAILED';
  error_message?: string | null;
  node_count: number;
  connection_count: number;
  source_count: number;
  target_count: number;
  sources: string[];
  targets: string[];
  inspection_sinks: string[];
  sink_classifications: Record<string, string>;
  tool_types: string[];
  business_purpose: string;
  business_function?: string;
  sttm_mappings_count: number;
  business_area?: BusinessAreaClassificationDTO;
  business_area_tag?: string;
  business_area_tag_source?: string;
  business_area_taxonomy_version?: string;
  complexity_score?: number;
  complexity_level?: 'HIGH' | 'MEDIUM' | 'LOW';
  complexity_factors?: string[];
  criticality_score?: number;
  criticality_level?: 'HIGH' | 'MEDIUM' | 'LOW';
  criticality_factors?: string[];
  criticality_justification?: string;
  business_consequence?: string;
  dependency_impact?: string;
  affected_scope?: string;
  migration_implication?: string;
  criticality_confidence?: 'HIGH' | 'MEDIUM' | 'LOW';
  criticality_source?: string;
  factor_assessments?: Record<string, FactorAssessmentDTO>;
  last_run?: string;
  frequency?: string;
  processing_stages?: BusinessStageDTO[];
  rationalisation_status?: string;
}

export interface FactorAssessmentDTO {
  name?: string;
  category?: string;
  raw_value?: number | string;
  display_value?: string;
  weight_pct?: number;
  raw_evidence?: string;
  factor_score?: number;
  weighted_contribution_pct?: number;
  dimension?: string;
  assessment?: 'HIGH' | 'MEDIUM' | 'LOW' | 'NOT_ESTABLISHED';
  evidence?: string;
  rationale?: string;
}

export interface DeterministicSignalsDTO {
  shared_sources: string[];
  shared_targets: string[];
  tool_sequence_similarity: number;
  graph_topology_similarity: number;
  transformation_overlap: number;
  field_overlap: number;
  lineage_overlap: number;
  composite_score: number;
}

export interface WorkflowRelationshipDTO {
  workflow_a_id: string;
  workflow_a_name: string;
  workflow_b_id: string;
  workflow_b_name: string;
  relationship_type:
    | 'STRUCTURAL_SIMILARITY'
    | 'SEMANTIC_SIMILARITY'
    | 'SHARED_SOURCE'
    | 'SHARED_TARGET'
    | 'SHARED_LOGIC'
    | 'OVERLAPPING_PIPELINE'
    | 'DUPLICATE_CANDIDATE';
  deterministic_signals: DeterministicSignalsDTO;
  llm_reasoning: string;
  confidence: 'HIGH' | 'MEDIUM' | 'LOW';
  evidence: string[];
}

export interface DeterministicMetricsDTO {
  source_overlap: number;
  target_overlap: number;
  transformation_similarity: number;
  schema_similarity: number;
  grain_similarity: number;
  dag_similarity: number;
  frequency_overlap: number;
}

export interface RiskContextDTO {
  complexity_by_workflow: Record<string, string>;
  criticality_by_workflow: Record<string, string>;
  risk_level: 'HIGH' | 'MEDIUM' | 'LOW';
  risk_notes: string[];
}

export interface OutputEvidenceDTO {
  production_targets: Record<string, string[]>;
  inspection_sinks: Record<string, string[]>;
  output_schemas: Record<string, string[]>;
  output_grains: Record<string, string[]>;
  is_equivalent_target: boolean;
  is_equivalent_schema: boolean;
  is_equivalent_grain: boolean;
}

export interface DependencyEvidenceDTO {
  downstream_consumers: Record<string, string[]>;
  upstream_producers: Record<string, string[]>;
  shared_sources: string[];
  shared_source_fields?: string[];
  shared_targets: string[];
  dependency_status: string;
  dependency_notes: string;
}

export interface ColumnEvidenceDTO {
  original_name: string;
  normalized_name: string;
  source_dataset: string;
  source_tool_id?: string;
  source_tool_type?: string;
  provenance: string;
  sample_values?: string[];
  is_required: boolean;
}

export interface DataSubsumptionEvidenceDTO {
  source_workflow_id: string;
  source_workflow_name: string;
  target_workflow_id: string;
  target_workflow_name: string;
  data_coverage_pct: number;
  missing_fields_count: number;
  missing_fields: string[];
  shared_required_fields: string[];
  additional_fields_in_target: string[];
  field_provenance_map: Record<string, ColumnEvidenceDTO>;
  sample_data_matches: Array<{
    field?: string;
    source_workflow?: string;
    source_samples?: string[];
    row_count?: number;
    status?: string;
  }>;
  processing_substitutability_matrix: Array<{
    source_tool_id?: string;
    source_tool_type?: string;
    source_operation?: string;
    target_equivalent?: string;
    target_tool_id?: string;
    status?: string;
    notes?: string;
  }>;
  processing_compatibility: 'SUPPORTED' | 'PARTIALLY_SUPPORTED' | 'UNSUPPORTED';
  output_compatibility: 'COMPATIBLE' | 'INSPECTION_SINK_ONLY' | 'IDENTICAL' | 'INCOMPATIBLE';
  has_unresolved_unique_functionality: boolean;
  unresolved_unique_details: string[];
  direction_statement: string;
  recommendation_summary: string;
}

export interface ConsolidationDecisionDTO {
  recommendation: 'MERGE' | 'DO NOT MERGE';
  matched_rule: string;
  reason: string;
  evidence: string[];
  source_overlap_pct: number;
  is_source_100_pct: boolean;
  output_relationship: string;
  complexity_a: string;
  complexity_b: string;
  frequency_a: string;
  frequency_b: string;
  is_same_frequency: boolean;
  logic_preservable: boolean;
  merge_direction?: string | null;
  data_subsumption_evidence?: DataSubsumptionEvidenceDTO | null;
}

export interface RationalisationCandidateDTO {
  candidate_id: string;
  workflow_ids: string[];
  workflow_names: string[];
  recommendation_type: 'CONSOLIDATE' | 'RETIRE' | 'RETIRE_CANDIDATE' | 'SHARED_LOGIC' | 'REVIEW' | 'KEEP' | 'NO_ACTION';
  confidence: 'HIGH' | 'MEDIUM' | 'LOW';
  opportunity_score: number;
  reasoning: string;
  evidence: string[];
  shared_logic: string[];
  unique_functionality: Record<string, string[]>;
  proposed_strategy: string;
  validation_requirements: string[];
  deterministic_metrics: DeterministicMetricsDTO;
  output_evidence: OutputEvidenceDTO;
  dependency_evidence: DependencyEvidenceDTO;
  risk_context: RiskContextDTO;
  admissible_recommendations: string[];
  llm_enrichment_status: string;
  consolidation_decision?: ConsolidationDecisionDTO | null;
  data_subsumption_evidence?: DataSubsumptionEvidenceDTO | null;
  sources_by_workflow?: Record<string, string[]>;
  source_fields_by_workflow?: Record<string, Record<string, string[]>>;
  targets_by_workflow?: Record<string, string[]>;
  target_fields_by_workflow?: Record<string, Record<string, string[]>>;
  transformations_by_workflow?: Record<string, string[]>;
  frequencies_by_workflow?: Record<string, string>;
  original_recommendation_type?: string;
}

export interface RationalisationAnalysisDTO {
  portfolio_id: string;
  candidates: RationalisationCandidateDTO[];
  total_opportunities: number;
  recommendation_counts: Record<string, number>;
  workflow_classifications?: Record<string, string>;
  workflow_counts?: Record<string, number>;
  analysed_workflow_count: number;
}

export interface SharedDatasetDTO {
  dataset_name: string;
  dataset_type: 'SOURCE' | 'TARGET';
  workflow_ids: string[];
  workflow_names: string[];
}

export interface PortfolioAggregateMetricsDTO {
  total_workflows: number;
  successful_workflows: number;
  failed_workflows: number;
  total_tools: number;
  total_sources: number;
  unique_sources: number;
  total_targets: number;
  unique_targets: number;
  shared_sources_count: number;
  shared_targets_count: number;
  inspection_sinks_count: number;
  tool_distribution: Record<string, number>;
}

export interface BusinessAreaGroupDTO {
  business_area: string;
  workflow_count: number;
  workflows: PortfolioWorkflowSummaryDTO[];
  description: string;
}

export interface PortfolioOverviewDTO {
  portfolio_id: string;
  portfolio_name: string;
  workflow_count: number;
  workflows: PortfolioWorkflowSummaryDTO[];
  metrics: PortfolioAggregateMetricsDTO;
  shared_sources: SharedDatasetDTO[];
  shared_targets: SharedDatasetDTO[];
  relationships: WorkflowRelationshipDTO[];
  rationalisation_candidates: RationalisationCandidateDTO[];
  business_area_counts?: Record<string, number>;
  business_area_descriptions?: Record<string, string>;
  business_areas?: BusinessAreaGroupDTO[];
  created_at: number;
}

export interface EvaluationFactorDTO {
  id: string;
  name: string;
  weight_pct: number;
  category?: string | null;
  description?: string;
}

export interface EvaluationModelDTO {
  model_name: string;
  description?: string;
  total_weight_pct: number;
  technical_weight_pct?: number | null;
  operational_weight_pct?: number | null;
  factors: EvaluationFactorDTO[];
}

export interface EvaluationModelsDTO {
  complexity: EvaluationModelDTO;
  criticality: EvaluationModelDTO;
}


