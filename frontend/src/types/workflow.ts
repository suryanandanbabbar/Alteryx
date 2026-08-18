/**
 * TypeScript contracts corresponding exactly to FastAPI Pydantic DTOs.
 */

export interface PackageMetadataDTO {
  primary_workflow: string;
  contained_files: string[];
  total_size_bytes: number;
}

export interface SourceInfoDTO {
  source_format: 'yxmd' | 'yxwz' | 'xml' | string;
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
  support_level: string;
  annotation: string;
  output_fields: FieldDTO[];
  engine_settings?: Record<string, string>;
  visual_category: string;
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
  path_points: { x: number; y: number }[];
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

export interface AnalysisOverviewDTO {
  analysis_id: string;
  source: SourceInfoDTO;
  metadata: WorkflowMetadataDTO;
  metrics: WorkflowMetricsDTO;
  execution_order: ExecutionStepDTO[];
  connections: ConnectionDTO[];
  diagnostics: DiagnosticDTO[];
}
