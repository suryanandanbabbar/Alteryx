import React, { useState, useEffect, useCallback, useMemo, useRef } from 'react';
import {
  ReactFlow,
  ReactFlowProvider,
  Background,
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
import { getLayoutedElements, getWorkflowBounds, NODE_WIDTH, NODE_HEIGHT } from './layout';
import { WorkflowNodeType, WorkflowEdgeType, WorkflowEdgeData } from './types';

const nodeTypes: NodeTypes = {
  workflowNode: WorkflowNode as any,
};

const edgeTypes: EdgeTypes = {
  workflowEdge: WorkflowEdge as any,
};

const SEARCH_ZOOM = 1.25;

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
  const reactFlowWrapperRef = useRef<HTMLDivElement>(null);

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

  // Deterministic search matches calculation
  const matchedToolIds = useMemo(() => {
    if (!searchQuery.trim()) return [];
    const q = searchQuery.toLowerCase().trim();
    return diagramData.nodes
      .filter((n) => {
        const idMatch = String(n.tool_id) === q || `#${n.tool_id}` === q || String(n.tool_id).includes(q);
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
          isActiveSearchMatch: false,
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

  // Helper to frame the viewport tightly around the actual workflow bounding rectangle
  const fitWorkflowBounds = useCallback(
    (targetNodes: WorkflowNodeType[], customPadding = 24, duration = 300) => {
      if (targetNodes.length === 0) return;
      const bounds = getWorkflowBounds(targetNodes);
      reactFlow.fitBounds(
        {
          x: bounds.minX - customPadding,
          y: bounds.minY - customPadding,
          width: bounds.width + customPadding * 2,
          height: bounds.height + customPadding * 2,
        },
        { duration }
      );
    },
    [reactFlow]
  );

  // Initial tight framing on load
  const isInitialFitRef = useRef(false);
  useEffect(() => {
    if (!isInitialFitRef.current && nodes.length > 0) {
      setTimeout(() => {
        fitWorkflowBounds(nodes, 24, 250);
        isInitialFitRef.current = true;
      }, 50);
    }
  }, [nodes, fitWorkflowBounds]);

  // Update dynamic visual highlighting without moving node positions or resetting zoom/pan
  useEffect(() => {
    const activeMatchToolId = matchedToolIds.length > 0 ? matchedToolIds[activeMatchIndex] : null;

    setNodes((prevNodes) =>
      prevNodes.map((node) => {
        const toolId = Number(node.id);
        const isSelected = selectedToolId === toolId;
        const isUpstream = lineage.upstreamToolIds.has(toolId);
        const isDownstream = lineage.downstreamToolIds.has(toolId);
        const isHighlighted = isSelected || isUpstream || isDownstream;
        const isSearchMatch = matchedToolIds.includes(toolId);
        const isActiveSearchMatch = activeMatchToolId === toolId;
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
          currentData.isActiveSearchMatch === isActiveSearchMatch &&
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
            isActiveSearchMatch,
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
  }, [selectedToolId, selectedEdgeId, lineage, matchedToolIds, activeMatchIndex, setNodes, setEdges]);

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

  // Navigate & zoom specifically to a search match node
  const navigateToSearchMatch = useCallback(
    (targetToolId: number) => {
      const node = nodes.find((n) => n.id === String(targetToolId));
      if (node) {
        reactFlow.setCenter(node.position.x + NODE_WIDTH / 2, node.position.y + NODE_HEIGHT / 2, {
          zoom: SEARCH_ZOOM,
          duration: 350,
        });
      }
    },
    [nodes, reactFlow]
  );

  // When user types a search query and matches change, automatically navigate to the 1st match
  const lastNavigatedQueryRef = useRef('');
  useEffect(() => {
    const trimmed = searchQuery.trim();
    if (trimmed && matchedToolIds.length > 0) {
      if (lastNavigatedQueryRef.current !== trimmed) {
        lastNavigatedQueryRef.current = trimmed;
        setActiveMatchIndex(0);
        navigateToSearchMatch(matchedToolIds[0]);
      }
    } else {
      lastNavigatedQueryRef.current = '';
    }
  }, [searchQuery, matchedToolIds, navigateToSearchMatch]);

  // Search Prev/Next Navigation
  const handleNextMatch = useCallback(() => {
    if (matchedToolIds.length === 0) return;
    const nextIdx = (activeMatchIndex + 1) % matchedToolIds.length;
    setActiveMatchIndex(nextIdx);
    const targetId = matchedToolIds[nextIdx];
    navigateToSearchMatch(targetId);
  }, [matchedToolIds, activeMatchIndex, navigateToSearchMatch]);

  const handlePrevMatch = useCallback(() => {
    if (matchedToolIds.length === 0) return;
    const prevIdx = (activeMatchIndex - 1 + matchedToolIds.length) % matchedToolIds.length;
    setActiveMatchIndex(prevIdx);
    const targetId = matchedToolIds[prevIdx];
    navigateToSearchMatch(targetId);
  }, [matchedToolIds, activeMatchIndex, navigateToSearchMatch]);

  // Handle search text changes
  const handleSearchChange = (q: string) => {
    setSearchQuery(q);
    setActiveMatchIndex(0);
  };

  // Clear search preserves the user's current viewport
  const handleClearSearch = () => {
    setSearchQuery('');
    setActiveMatchIndex(0);
  };

  // Zoom and Fit handlers
  const handleFitView = () => {
    fitWorkflowBounds(nodes, 24, 300);
  };

  const handleResetLayout = () => {
    const layouted = getLayoutedElements(nodes, edges, { direction });
    setNodes(layouted.nodes);
    setEdges(layouted.edges);
    setTimeout(() => {
      fitWorkflowBounds(layouted.nodes, 24, 300);
    }, 50);
  };

  const handleToggleDirection = () => {
    const newDir = direction === 'LR' ? 'TB' : 'LR';
    setDirection(newDir);
    const layouted = getLayoutedElements(nodes, edges, { direction: newDir });
    setNodes(layouted.nodes);
    setEdges(layouted.edges);
    setTimeout(() => {
      fitWorkflowBounds(layouted.nodes, 24, 300);
    }, 50);
  };

  const handleZoomIn = () => {
    reactFlow.zoomIn({ duration: 200 });
  };

  const handleZoomOut = () => {
    reactFlow.zoomOut({ duration: 200 });
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
        height: 'min(640px, 72vh)',
        minHeight: '480px',
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
        <div ref={reactFlowWrapperRef} style={{ flex: 1, height: '100%', position: 'relative' }}>
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

