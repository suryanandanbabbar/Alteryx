import React, { useState, useEffect, useCallback, useMemo, useRef } from 'react';
import {
  ReactFlow,
  ReactFlowProvider,
  Background,
  MiniMap,
  useNodesState,
  useEdgesState,
  useReactFlow,
  MarkerType,
  NodeTypes,
  EdgeTypes,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';

import { DiagramDTO, NodeDTO, ConnectionDTO, DiagnosticDTO } from '../../types/workflow';
import { WorkflowNode } from './WorkflowNode';
import { WorkflowEdge } from './WorkflowEdge';
import { WorkflowToolbar } from './WorkflowToolbar';
import { WorkflowInspector } from './WorkflowInspector';
import { getLayoutedElements, NODE_WIDTH, NODE_HEIGHT } from './layout';
import { WorkflowNodeType, WorkflowEdgeType, WorkflowNodeData, WorkflowEdgeData } from './types';
import { getCategoryColor } from '../../theme/palette';

const nodeTypes: NodeTypes = {
  workflowNode: WorkflowNode as any,
};

const edgeTypes: EdgeTypes = {
  workflowEdge: WorkflowEdge as any,
};

interface WorkflowCanvasInternalProps {
  diagramData: DiagramDTO;
  selectedToolId?: number | null;
  onSelectTool?: (toolId: number | null) => void;
  onDownloadSvg?: () => void;
}

const WorkflowCanvasInternal: React.FC<WorkflowCanvasInternalProps> = ({
  diagramData,
  selectedToolId: externalSelectedToolId,
  onSelectTool: externalOnSelectTool,
  onDownloadSvg,
}) => {
  const reactFlow = useReactFlow();

  const [direction, setDirection] = useState<'LR' | 'TB'>('LR');
  const [selectedToolId, setSelectedToolId] = useState<number | null>(externalSelectedToolId ?? null);
  const [selectedEdgeId, setSelectedEdgeId] = useState<string | null>(null);

  const [searchQuery, setSearchQuery] = useState('');
  const [activeMatchIndex, setActiveMatchIndex] = useState(0);
  const [zoomLevel, setZoomLevel] = useState(1);

  // Sync external selected tool ID
  useEffect(() => {
    if (externalSelectedToolId !== undefined) {
      setSelectedToolId(externalSelectedToolId);
    }
  }, [externalSelectedToolId]);

  // Extract connections and diagnostics
  const connections: ConnectionDTO[] = useMemo(() => {
    if (diagramData.connections && diagramData.connections.length > 0) {
      return diagramData.connections;
    }
    if (diagramData.dag_layout?.edges) {
      return diagramData.dag_layout.edges.map((e) => ({
        origin_tool_id: e.source_id,
        origin_anchor: e.source_anchor,
        destination_tool_id: e.target_id,
        destination_anchor: e.target_anchor,
      }));
    }
    return [];
  }, [diagramData]);

  const diagnostics: DiagnosticDTO[] = useMemo(() => {
    return diagramData.diagnostics || [];
  }, [diagramData]);

  const businessOutputIds: Set<number> = useMemo(() => {
    if (diagramData.metrics?.business_output_node_ids) {
      return new Set(diagramData.metrics.business_output_node_ids);
    }
    // Fallback classification
    const previewTypes = new Set(['Browse', 'BrowseV2', 'Message', 'Test']);
    const nonBusinessIds = new Set<number>();
    diagramData.nodes.forEach((n) => {
      if (previewTypes.has(n.tool_type)) {
        nonBusinessIds.add(n.tool_id);
      }
    });
    const terminalIds = new Set(
      diagramData.nodes
        .filter((n) => !connections.some((c) => c.origin_tool_id === n.tool_id))
        .map((n) => n.tool_id)
    );
    const outputs = new Set<number>();
    terminalIds.forEach((id) => {
      if (!nonBusinessIds.has(id)) {
        outputs.add(id);
      }
    });
    return outputs;
  }, [diagramData, connections]);

  // Input and output counts per tool ID
  const portCounts = useMemo(() => {
    const inputMap = new Map<number, number>();
    const outputMap = new Map<number, number>();

    connections.forEach((c) => {
      outputMap.set(c.origin_tool_id, (outputMap.get(c.origin_tool_id) || 0) + 1);
      inputMap.set(c.destination_tool_id, (inputMap.get(c.destination_tool_id) || 0) + 1);
    });

    return { inputMap, outputMap };
  }, [connections]);

  // Node Map by tool ID
  const nodeMap = useMemo(() => {
    const map = new Map<number, NodeDTO>();
    diagramData.nodes.forEach((n) => map.set(n.tool_id, n));
    return map;
  }, [diagramData.nodes]);

  // Lineage calculation for active selection
  const lineage = useMemo(() => {
    if (selectedToolId === null) {
      return {
        upstreamToolIds: new Set<number>(),
        downstreamToolIds: new Set<number>(),
        connectedEdgeIds: new Set<string>(),
      };
    }

    const upstream = new Set<number>();
    const downstream = new Set<number>();
    const connectedEdges = new Set<string>();

    connections.forEach((c) => {
      const edgeId = `e-${c.origin_tool_id}-${c.origin_anchor}-${c.destination_tool_id}-${c.destination_anchor}`;
      if (c.destination_tool_id === selectedToolId) {
        upstream.add(c.origin_tool_id);
        connectedEdges.add(edgeId);
      }
      if (c.origin_tool_id === selectedToolId) {
        downstream.add(c.destination_tool_id);
        connectedEdges.add(edgeId);
      }
    });

    return {
      upstreamToolIds: upstream,
      downstreamToolIds: downstream,
      connectedEdgeIds: connectedEdges,
    };
  }, [selectedToolId, connections]);

  // Search matches
  const matchedToolIds = useMemo(() => {
    if (!searchQuery.trim()) return [];
    const q = searchQuery.toLowerCase().trim();
    return diagramData.nodes
      .filter((n) => {
        const idMatch = String(n.tool_id).includes(q) || `#${n.tool_id}`.includes(q);
        const nameMatch = (n.name || '').toLowerCase().includes(q);
        const typeMatch = (n.tool_type || '').toLowerCase().includes(q);
        const annotMatch = (n.annotation || '').toLowerCase().includes(q);
        const summaryMatch = (n.summary || '').toLowerCase().includes(q);
        return idMatch || nameMatch || typeMatch || annotMatch || summaryMatch;
      })
      .map((n) => n.tool_id);
  }, [searchQuery, diagramData.nodes]);

  // Initial build of Base Layouted Elements
  const baseLayout = useMemo(() => {
    const rawNodes: WorkflowNodeType[] = diagramData.nodes.map((node) => {
      const toolDiags = diagnostics.filter((d) => d.tool_id === node.tool_id);
      return {
        id: String(node.tool_id),
        type: 'workflowNode',
        position: { x: 0, y: 0 },
        data: {
          toolId: node.tool_id,
          toolType: node.tool_type,
          name: node.name,
          plugin: node.plugin,
          visualCategory: node.visual_category,
          summary: node.summary,
          annotation: node.annotation,
          containerId: node.container_id,
          containerName: node.container_name,
          inputCount: portCounts.inputMap.get(node.tool_id) || 0,
          outputCount: portCounts.outputMap.get(node.tool_id) || 0,
          isBusinessOutput: businessOutputIds.has(node.tool_id),
          diagnostics: toolDiags,
          nodeDto: node,
          isSelected: false,
          isHighlighted: false,
          isDimmed: false,
          isSearchMatch: false,
          isUpstream: false,
          isDownstream: false,
        },
      };
    });

    const rawEdges: WorkflowEdgeType[] = connections.map((conn) => {
      const edgeId = `e-${conn.origin_tool_id}-${conn.origin_anchor}-${conn.destination_tool_id}-${conn.destination_anchor}`;
      return {
        id: edgeId,
        source: String(conn.origin_tool_id),
        target: String(conn.destination_tool_id),
        type: 'workflowEdge',
        markerEnd: {
          type: MarkerType.ArrowClosed,
          width: 14,
          height: 14,
          color: 'var(--color-border)',
        },
        data: {
          originToolId: conn.origin_tool_id,
          originAnchor: conn.origin_anchor,
          destinationToolId: conn.destination_tool_id,
          destinationAnchor: conn.destination_anchor,
          isHighlighted: false,
          isDimmed: false,
        },
      };
    });

    return getLayoutedElements(rawNodes, rawEdges, { direction });
  }, [diagramData, connections, diagnostics, portCounts, businessOutputIds, direction]);

  const [nodes, setNodes, onNodesChange] = useNodesState(baseLayout.nodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(baseLayout.edges);

  // Sync state whenever baseLayout updates (e.g. initial load or direction toggle)
  useEffect(() => {
    setNodes(baseLayout.nodes);
    setEdges(baseLayout.edges);
  }, [baseLayout, setNodes, setEdges]);

  // Update dynamic visual highlighting without moving node positions or resetting zoom/pan
  useEffect(() => {
    setNodes((prevNodes) =>
      prevNodes.map((node) => {
        const toolId = Number(node.id);
        const isSelected = selectedToolId === toolId;
        const isUpstream = lineage.upstreamToolIds.has(toolId);
        const isDownstream = lineage.downstreamToolIds.has(toolId);
        const isHighlighted = isSelected || isUpstream || isDownstream;
        const isSearchMatch = matchedToolIds.includes(toolId);
        const hasActiveSelection = selectedToolId !== null;
        const isDimmed =
          (hasActiveSelection && !isHighlighted) ||
          (matchedToolIds.length > 0 && !isSearchMatch && !isHighlighted);

        const currentData = node.data;
        if (
          currentData.isSelected === isSelected &&
          currentData.isHighlighted === isHighlighted &&
          currentData.isDimmed === isDimmed &&
          currentData.isSearchMatch === isSearchMatch &&
          currentData.isUpstream === isUpstream &&
          currentData.isDownstream === isDownstream
        ) {
          return node;
        }

        return {
          ...node,
          data: {
            ...currentData,
            isSelected,
            isHighlighted,
            isDimmed,
            isSearchMatch,
            isUpstream,
            isDownstream,
          },
        };
      })
    );

    setEdges((prevEdges) =>
      prevEdges.map((edge) => {
        const isHighlighted = lineage.connectedEdgeIds.has(edge.id) || selectedEdgeId === edge.id;
        const hasActiveSelection = selectedToolId !== null || selectedEdgeId !== null;
        const isDimmed = hasActiveSelection && !isHighlighted;

        const currentData = edge.data as WorkflowEdgeData;
        if (currentData?.isHighlighted === isHighlighted && currentData?.isDimmed === isDimmed) {
          return edge;
        }

        return {
          ...edge,
          markerEnd: {
            type: MarkerType.ArrowClosed,
            width: 14,
            height: 14,
            color: isHighlighted ? 'var(--color-primary)' : 'var(--color-border)',
          },
          data: {
            originToolId: currentData.originToolId,
            originAnchor: currentData.originAnchor,
            destinationToolId: currentData.destinationToolId,
            destinationAnchor: currentData.destinationAnchor,
            isHighlighted,
            isDimmed,
          },
        };
      })
    );
  }, [selectedToolId, selectedEdgeId, lineage, matchedToolIds, setNodes, setEdges]);

  // Initial fit view on load
  const isInitialFitRef = useRef(false);
  useEffect(() => {
    if (!isInitialFitRef.current && nodes.length > 0) {
      setTimeout(() => {
        reactFlow.fitView({ padding: 0.15, duration: 250 });
        isInitialFitRef.current = true;
      }, 50);
    }
  }, [nodes, reactFlow]);

  // Handle node selection
  const handleSelectNode = useCallback(
    (toolId: number | null) => {
      setSelectedToolId(toolId);
      setSelectedEdgeId(null);
      if (externalOnSelectTool) {
        externalOnSelectTool(toolId);
      }
    },
    [externalOnSelectTool]
  );

  // Center on a specific tool node preserving current zoom level
  const centerOnNode = useCallback(
    (toolId: number) => {
      const node = nodes.find((n) => n.id === String(toolId));
      if (node) {
        const currentZoom = reactFlow.getViewport().zoom;
        reactFlow.setCenter(node.position.x + NODE_WIDTH / 2, node.position.y + NODE_HEIGHT / 2, {
          zoom: currentZoom,
          duration: 350,
        });
      }
    },
    [nodes, reactFlow]
  );

  // Search Navigation
  const handleNextMatch = useCallback(() => {
    if (matchedToolIds.length === 0) return;
    const nextIdx = (activeMatchIndex + 1) % matchedToolIds.length;
    setActiveMatchIndex(nextIdx);
    const targetId = matchedToolIds[nextIdx];
    handleSelectNode(targetId);
    centerOnNode(targetId);
  }, [matchedToolIds, activeMatchIndex, handleSelectNode, centerOnNode]);

  const handlePrevMatch = useCallback(() => {
    if (matchedToolIds.length === 0) return;
    const prevIdx = (activeMatchIndex - 1 + matchedToolIds.length) % matchedToolIds.length;
    setActiveMatchIndex(prevIdx);
    const targetId = matchedToolIds[prevIdx];
    handleSelectNode(targetId);
    centerOnNode(targetId);
  }, [matchedToolIds, activeMatchIndex, handleSelectNode, centerOnNode]);

  // Handle search text changes
  const handleSearchChange = (q: string) => {
    setSearchQuery(q);
    setActiveMatchIndex(0);
    if (q.trim()) {
      const qLower = q.toLowerCase().trim();
      const firstMatch = diagramData.nodes.find(
        (n) =>
          String(n.tool_id).includes(qLower) ||
          `#${n.tool_id}`.includes(qLower) ||
          (n.name || '').toLowerCase().includes(qLower) ||
          (n.tool_type || '').toLowerCase().includes(qLower)
      );
      if (firstMatch) {
        centerOnNode(firstMatch.tool_id);
      }
    }
  };

  const handleClearSearch = () => {
    setSearchQuery('');
    setActiveMatchIndex(0);
  };

  // Zoom and Fit handlers
  const handleFitView = () => {
    reactFlow.fitView({ padding: 0.15, duration: 300 });
  };

  const handleResetLayout = () => {
    const layouted = getLayoutedElements(nodes, edges, { direction });
    setNodes(layouted.nodes);
    setEdges(layouted.edges);
    setTimeout(() => {
      reactFlow.fitView({ padding: 0.15, duration: 300 });
    }, 50);
  };

  const handleToggleDirection = () => {
    const newDir = direction === 'LR' ? 'TB' : 'LR';
    setDirection(newDir);
    const layouted = getLayoutedElements(nodes, edges, { direction: newDir });
    setNodes(layouted.nodes);
    setEdges(layouted.edges);
    setTimeout(() => {
      reactFlow.fitView({ padding: 0.15, duration: 300 });
    }, 50);
  };

  const handleZoomIn = () => {
    reactFlow.zoomIn({ duration: 200 });
  };

  const handleZoomOut = () => {
    reactFlow.zoomOut({ duration: 200 });
  };

  const handleDownloadJson = () => {
    const jsonStr = JSON.stringify(diagramData, null, 2);
    const blob = new Blob([jsonStr], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'workflow_diagram.json';
    a.click();
    URL.revokeObjectURL(url);
  };

  // Data for Inspector
  const selectedNodeDto = selectedToolId !== null ? nodeMap.get(selectedToolId) || null : null;
  const upstreamNodes = useMemo(() => {
    return Array.from(lineage.upstreamToolIds)
      .map((id) => nodeMap.get(id))
      .filter((n): n is NodeDTO => !!n);
  }, [lineage.upstreamToolIds, nodeMap]);

  const downstreamNodes = useMemo(() => {
    return Array.from(lineage.downstreamToolIds)
      .map((id) => nodeMap.get(id))
      .filter((n): n is NodeDTO => !!n);
  }, [lineage.downstreamToolIds, nodeMap]);

  const selectedConnectionObj = useMemo(() => {
    if (!selectedEdgeId) return null;
    const conn = connections.find(
      (c) => `e-${c.origin_tool_id}-${c.origin_anchor}-${c.destination_tool_id}-${c.destination_anchor}` === selectedEdgeId
    );
    if (!conn) return null;
    return {
      connection: conn,
      sourceNode: nodeMap.get(conn.origin_tool_id),
      targetNode: nodeMap.get(conn.destination_tool_id),
    };
  }, [selectedEdgeId, connections, nodeMap]);

  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        gap: '10px',
        width: '100%',
        height: '740px',
        position: 'relative',
      }}
    >
      {/* Top Controls Toolbar */}
      <WorkflowToolbar
        searchQuery={searchQuery}
        onSearchChange={handleSearchChange}
        onClearSearch={handleClearSearch}
        matchCount={matchedToolIds.length}
        activeMatchIndex={activeMatchIndex}
        onNextMatch={handleNextMatch}
        onPrevMatch={handlePrevMatch}
        onFitView={handleFitView}
        onResetLayout={handleResetLayout}
        onZoomIn={handleZoomIn}
        onZoomOut={handleZoomOut}
        zoomLevel={zoomLevel}
        direction={direction}
        onToggleDirection={handleToggleDirection}
        onDownloadSvg={onDownloadSvg}
        onDownloadJson={handleDownloadJson}
      />

      {/* Main Canvas & Inspector Split View */}
      <div
        style={{
          flex: 1,
          display: 'flex',
          background: 'var(--color-surface)',
          border: '1px solid var(--color-border)',
          borderRadius: 'var(--radius-md, 6px)',
          overflow: 'hidden',
          position: 'relative',
        }}
      >
        {/* React Flow Graph Area */}
        <div style={{ flex: 1, height: '100%', position: 'relative' }}>
          <ReactFlow
            nodes={nodes}
            edges={edges}
            nodeTypes={nodeTypes}
            edgeTypes={edgeTypes}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            onNodeClick={(_, node) => handleSelectNode(Number(node.id))}
            onEdgeClick={(_, edge) => {
              setSelectedEdgeId(edge.id);
              setSelectedToolId(null);
            }}
            onPaneClick={() => {
              setSelectedToolId(null);
              setSelectedEdgeId(null);
            }}
            onMove={(_, viewport) => {
              setZoomLevel(viewport.zoom);
            }}
            minZoom={0.15}
            maxZoom={2.5}
            fitView
            proOptions={{ hideAttribution: true }}
          >
            <Background gap={18} size={1} color="var(--color-border)" />
            <MiniMap
              nodeColor={(node) => {
                const nd = node.data as WorkflowNodeData;
                const color = getCategoryColor(nd.visualCategory || nd.toolType.toLowerCase());
                return color.stroke || '#94a3b8';
              }}
              nodeStrokeWidth={2}
              style={{
                background: 'var(--color-surface)',
                border: '1px solid var(--color-border)',
                borderRadius: 'var(--radius-sm, 4px)',
                width: 140,
                height: 90,
              }}
            />
          </ReactFlow>
        </div>

        {/* Right Inspector Panel */}
        {(selectedNodeDto || selectedConnectionObj) && (
          <WorkflowInspector
            selectedNode={selectedNodeDto}
            selectedConnection={selectedConnectionObj}
            upstreamNodes={upstreamNodes}
            downstreamNodes={downstreamNodes}
            isBusinessOutput={selectedToolId ? businessOutputIds.has(selectedToolId) : false}
            onSelectTool={(id) => {
              handleSelectNode(id);
            }}
            onClose={() => {
              setSelectedToolId(null);
              setSelectedEdgeId(null);
            }}
          />
        )}
      </div>
    </div>
  );
};

export const WorkflowCanvas: React.FC<WorkflowCanvasInternalProps> = (props) => {
  return (
    <ReactFlowProvider>
      <WorkflowCanvasInternal {...props} />
    </ReactFlowProvider>
  );
};

