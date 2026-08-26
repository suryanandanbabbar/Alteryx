export interface PackageMetadataDTO {
  primary_workflow: string;
  contained_files: string[];
  total_size_bytes: number;
}

export interface SourceInfoDTO {
  source_format: string;
  original_filename: string;
  package_metadata?: PackageMetadataDTO | null;
}

export interface WorkflowMetadataDTO {
  name: string;
  version: string;
  author?: string | null;
  description?: string | null;
}

export interface WorkflowMetricsDTO {
  total_nodes: number;
  total_connections: number;
  input_count: number;
  output_count: number;
  terminal_node_count?: number;
  terminal_node_ids?: number[];
  business_output_count?: number;
  business_output_node_ids?: number[];
  container_count?: number;
  annotation_count?: number;
  input_node_ids: number[];
  output_node_ids: number[];
  support_summary: Record<string, number>;
}

export interface PositionDTO {
  x: number;
  y: number;
}

export interface FieldDTO {
  name: string;
  type: string;
  size?: number | null;
  scale?: number | null;
}

export interface DiagnosticDTO {
  level: 'info' | 'warning' | 'error';
  category: string;
  tool_id?: number | null;
  tool_type?: string | null;
  message: string;
  detail?: string | null;
}

export interface NodeDTO {
  tool_id: number;
  tool_type: string;
  name: string;
  plugin: string;
  position?: PositionDTO | null;
  configuration: Record<string, any>;
  summary?: string;
  annotation: string;
  output_fields: FieldDTO[];
  engine_settings?: Record<string, string>;
  visual_category: string;
  container_id?: number | null;
  container_name?: string | null;
  raw_node_xml?: string | null;
  xml_tool_name?: string | null;
}

export interface ConnectionDTO {
  origin_tool_id: number;
  origin_anchor: string;
  destination_tool_id: number;
  destination_anchor: string;
}

export interface ExecutionStepDTO {
  step_number: number;
  tool_id: number;
  tool_type: string;
  name: string;
  visual_category: string;
  summary?: string;
  container_id?: number | null;
  container_name?: string | null;
}

export interface DagNodeLayoutDTO {
  tool_id: number;
  x: number;
  y: number;
  width: number;
  height: number;
  label: string;
  tool_type: string;
  execution_index: number;
  visual_category: string;
}

export interface DagEdgeLayoutDTO {
  source_id: number;
  target_id: number;
  source_anchor: string;
  target_anchor: string;
  path_points?: Array<{ x: number; y: number }>;
}

export interface DagLayoutDTO {
  nodes: DagNodeLayoutDTO[];
  edges: DagEdgeLayoutDTO[];
  width: number;
  height: number;
  title: string;
}

export interface DiagramDTO {
  svg: string;
  nodes: NodeDTO[];
  dag_layout: DagLayoutDTO;
  connections?: ConnectionDTO[];
  diagnostics?: DiagnosticDTO[];
  metrics?: WorkflowMetricsDTO | null;
}

export interface PythonTraceDTO {
  tool_id: number;
  tool_type: string;
  tool_name: string;
  start_line: number;
  end_line: number;
  description: string;
  pandas_op: string;
  reason: string;
  libraries: string[];
}

export interface PythonOutputDTO {
  code: string;
  required_libraries: string[];
  trace_map: PythonTraceDTO[];
  total_lines: number;
}

export interface BusinessInputDTO {
  tool_id: number;
  name: string;
  raw_source: string;
  source_type: string;
  source_filename?: string | null;
  sheet_or_table?: string | null;
  container_name?: string | null;
  business_role?: string;
  description?: string;
}

export interface BusinessOutputDTO {
  tool_id: number;
  name: string;
  raw_destination: string;
  destination_type: string;
  sheet_or_table?: string | null;
  business_meaning?: string;
  likely_use?: string;
  business_purpose?: string;
  container_name?: string | null;
  upstream_sources?: string[];
}

export interface BusinessStageDTO {
  stage_number: number;
  name: string;
  short_title?: string;
  summary?: string;
  description: string;
  business_purpose?: string;
  major_transformation?: string;
  tool_ids: number[];
  input_ids?: number[];
  output_ids?: number[];
  tool_count: number;
  container_name?: string | null;
  annotations?: string[];
  transformations?: string[];
}

export interface BusinessTransformationDTO {
  category: string;
  description: string;
  affected_fields?: string[];
  tool_ids?: number[];
}

export interface BusinessRuleDTO {
  rule_name: string;
  category: string;
  description: string;
  tool_ids: number[];
  evidence?: string;
}

export interface BusinessLineageDTO {
  source_name: string;
  transformation?: string;
  target_name: string;
  intermediate_stages: string[];
  transformation_summary: string;
  source_tool_id: number;
  target_tool_id: number;
}

export interface BusinessAssessmentDTO {
  complexity: string;
  complexity_reason: string;
  complexity_factors: string[];
  platform?: string;
  business_owner: string;
  schedule: string;
  criticality: string;
  documentation_quality: string;
  assessment_status?: string;
  key_observations: string[];
  key_activities: string[];
  key_findings?: string[];
  role_and_value?: string[];
  assessment_gaps?: Array<{ dimension: string; status: string; action: string }>;
  preliminary_disposition?: string;
  disposition_rationale?: string;
  validation_checklist?: string[];
  why_it_matters: string;
}

export interface WorkflowBusinessSummaryDTO {
  business_purpose: string;
  one_line_purpose?: string;
  why_it_matters?: string;
  source_inputs: BusinessInputDTO[];
  processing_stages: BusinessStageDTO[];
  transformations: BusinessTransformationDTO[];
  business_rules?: BusinessRuleDTO[];
  lineage: BusinessLineageDTO[];
  business_outputs: BusinessOutputDTO[];
  assessment?: BusinessAssessmentDTO;
  process_overview: string;
  information_flow: string[];
  overall_interpretation?: string;
  confidence_level?: string;
}

export interface AnalysisOverviewDTO {
  analysis_id: string;
  source: SourceInfoDTO;
  metadata: WorkflowMetadataDTO;
  metrics: WorkflowMetricsDTO;
  execution_order: ExecutionStepDTO[];
  connections: ConnectionDTO[];
  diagnostics: DiagnosticDTO[];
  business_summary?: WorkflowBusinessSummaryDTO | null;
}
