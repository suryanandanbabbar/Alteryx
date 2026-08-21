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
