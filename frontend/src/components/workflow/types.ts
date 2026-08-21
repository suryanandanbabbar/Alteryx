import { Node, Edge } from '@xyflow/react';
import { NodeDTO, DiagnosticDTO } from '../../types/workflow';

export interface WorkflowNodeData extends Record<string, unknown> {
  toolId: number;
  toolType: string;
  name: string;
  plugin: string;
  visualCategory: string;
  summary?: string;
  annotation: string;
  containerId?: number | null;
  containerName?: string | null;
  inputCount: number;
  outputCount: number;
  isBusinessOutput: boolean;
  diagnostics: DiagnosticDTO[];
  nodeDto: NodeDTO;
  // Visual states
  isSelected?: boolean;
  isHighlighted?: boolean;
  isDimmed?: boolean;
  isSearchMatch?: boolean;
  isActiveSearchMatch?: boolean;
  isUpstream?: boolean;
  isDownstream?: boolean;
}

export type WorkflowNodeType = Node<WorkflowNodeData, 'workflowNode'>;

export interface WorkflowEdgeData extends Record<string, unknown> {
  originToolId: number;
  originAnchor: string;
  destinationToolId: number;
  destinationAnchor: string;
  isHighlighted?: boolean;
  isDimmed?: boolean;
}

export type WorkflowEdgeType = Edge<WorkflowEdgeData>;

export interface LineageState {
  selectedToolId: number | null;
  upstreamToolIds: Set<number>;
  downstreamToolIds: Set<number>;
  connectedEdgeIds: Set<string>;
}
