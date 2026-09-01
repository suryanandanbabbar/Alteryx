/**
 * TypeScript definitions for Multi-Workflow Portfolio Analysis and ETL Rationalisation.
 */

export interface BusinessAreaClassificationDTO {
  business_area: string;
  confidence: string;
  evidence: string[];
  classification_source: string;
  secondary_business_areas: string[];
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
  sttm_mappings_count: number;
  business_area?: BusinessAreaClassificationDTO;
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

export interface RationalisationCandidateDTO {
  workflow_ids: string[];
  workflow_names: string[];
  recommendation_type: 'CONSOLIDATE' | 'RETIRE_CANDIDATE' | 'SHARED_LOGIC' | 'REVIEW';
  reasoning: string;
  evidence: string[];
  confidence: 'HIGH' | 'MEDIUM' | 'LOW';
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
  created_at: number;
}
