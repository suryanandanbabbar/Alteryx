import dagre from '@dagrejs/dagre';
import { WorkflowNodeType, WorkflowEdgeType } from './types';

export const NODE_WIDTH = 220;
export const NODE_HEIGHT = 86;

export interface LayoutOptions {
  direction?: 'LR' | 'TB';
  nodeWidth?: number;
  nodeHeight?: number;
  rankSep?: number;
  nodeSep?: number;
}

/**
 * Calculates a hierarchical DAG layout using dagre.
 * Guarantees that upstream nodes are rendered to the left (or top) of downstream nodes.
 */
export function getLayoutedElements(
  nodes: WorkflowNodeType[],
  edges: WorkflowEdgeType[],
  options: LayoutOptions = {}
): { nodes: WorkflowNodeType[]; edges: WorkflowEdgeType[] } {
  const {
    direction = 'LR',
    nodeWidth = NODE_WIDTH,
    nodeHeight = NODE_HEIGHT,
    rankSep = 80,
    nodeSep = 45,
  } = options;

  const dagreGraph = new dagre.graphlib.Graph();
  dagreGraph.setDefaultEdgeLabel(() => ({}));

  const isHorizontal = direction === 'LR';
  dagreGraph.setGraph({
    rankdir: direction,
    ranksep: rankSep,
    nodesep: nodeSep,
    marginx: 40,
    marginy: 40,
  });

  nodes.forEach((node) => {
    dagreGraph.setNode(node.id, { width: nodeWidth, height: nodeHeight });
  });

  edges.forEach((edge) => {
    dagreGraph.setEdge(edge.source, edge.target);
  });

  dagre.layout(dagreGraph);

  const layoutedNodes = nodes.map((node) => {
    const nodeWithPosition = dagreGraph.node(node.id);
    return {
      ...node,
      targetPosition: isHorizontal ? 'left' : 'top',
      sourcePosition: isHorizontal ? 'right' : 'bottom',
      position: {
        x: nodeWithPosition.x - nodeWidth / 2,
        y: nodeWithPosition.y - nodeHeight / 2,
      },
    } as WorkflowNodeType;
  });

  return { nodes: layoutedNodes, edges };
}

export interface WorkflowBounds {
  x: number;
  y: number;
  width: number;
  height: number;
  minX: number;
  minY: number;
  maxX: number;
  maxY: number;
}

/**
 * Calculates the bounding rectangle across all workflow nodes.
 */
export function getWorkflowBounds(
  nodes: WorkflowNodeType[],
  nodeWidth = NODE_WIDTH,
  nodeHeight = NODE_HEIGHT
): WorkflowBounds {
  if (nodes.length === 0) {
    return { x: 0, y: 0, width: 800, height: 600, minX: 0, minY: 0, maxX: 800, maxY: 600 };
  }

  let minX = Infinity;
  let minY = Infinity;
  let maxX = -Infinity;
  let maxY = -Infinity;

  for (const node of nodes) {
    const x = node.position.x;
    const y = node.position.y;
    const w = node.measured?.width || nodeWidth;
    const h = node.measured?.height || nodeHeight;
    if (x < minX) minX = x;
    if (y < minY) minY = y;
    if (x + w > maxX) maxX = x + w;
    if (y + h > maxY) maxY = y + h;
  }

  return {
    x: minX,
    y: minY,
    width: Math.max(1, maxX - minX),
    height: Math.max(1, maxY - minY),
    minX,
    minY,
    maxX,
    maxY,
  };
}
