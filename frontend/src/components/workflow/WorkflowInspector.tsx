import React, { useState, useEffect, useRef } from 'react';
import {
  X,
  ArrowRight,
  ArrowLeft,
  Layers,
  Copy,
  Check,
  ExternalLink,
  ArrowDownLeft,
  RotateCcw,
} from 'lucide-react';
import { api } from '../../api/client';
import { NodeDTO, ConnectionDTO } from '../../types/workflow';
import { getCategoryColor, getWorkflowRole, getWorkflowRoleColor } from '../../theme/palette';
import { resolveXmlToolName } from '../../utils/toolRegistry';
import { formatXmlForDisplay } from '../../utils/xmlFormatter';

export type ColumnId = 'WHAT_IT_DOES' | 'DATA_FLOW' | 'TECHNICAL_DETAILS';

interface FloatingPanelState {
  x: number;
  y: number;
  width: number;
  height: number;
  zIndex: number;
}

interface WorkflowInspectorProps {
  analysisId?: string;
  selectedNode: NodeDTO | null;
  selectedConnection: {
    connection: ConnectionDTO;
    sourceNode?: NodeDTO;
    targetNode?: NodeDTO;
  } | null;
  upstreamNodes: NodeDTO[];
  downstreamNodes: NodeDTO[];
  isBusinessOutput?: boolean;
  onSelectTool: (toolId: number) => void;
  onClose: () => void;
  onUpdateNodeSummary?: (toolId: number, summary: string) => void;
}

const DEFAULT_PANE_HEIGHT = 240;
const MIN_PANE_HEIGHT = 120;

export const WorkflowInspector: React.FC<WorkflowInspectorProps> = ({
  analysisId,
  selectedNode,
  selectedConnection,
  upstreamNodes,
  downstreamNodes,
  isBusinessOutput,
  onSelectTool,
  onClose,
  onUpdateNodeSummary,
}) => {
  const [copiedXml, setCopiedXml] = useState(false);
  const [llmSummary, setLlmSummary] = useState<string | null>(null);
  const [loadingSummary, setLoadingSummary] = useState(false);

  // Pane layout state (session-only, resets on workflow switch)
  const [paneHeight, setPaneHeight] = useState<number>(DEFAULT_PANE_HEIGHT);
  const [detachedColumns, setDetachedColumns] = useState<Set<ColumnId>>(new Set());
  const [floatingPanels, setFloatingPanels] = useState<Record<ColumnId, FloatingPanelState>>({
    WHAT_IT_DOES: { x: 40, y: 40, width: 340, height: 260, zIndex: 100 },
    DATA_FLOW: { x: 80, y: 80, width: 360, height: 280, zIndex: 100 },
    TECHNICAL_DETAILS: { x: 120, y: 120, width: 400, height: 300, zIndex: 100 },
  });
  const [highestZIndex, setHighestZIndex] = useState<number>(100);

  // Resizing bottom pane state
  const isResizingRef = useRef(false);
  const startYRef = useRef(0);
  const startHeightRef = useRef(0);

  // Dragging floating panel state
  const isDraggingPanelRef = useRef<ColumnId | null>(null);
  const dragOffsetRef = useRef<{ x: number; y: number }>({ x: 0, y: 0 });

  // Reset pane layout on workflow change
  useEffect(() => {
    setPaneHeight(DEFAULT_PANE_HEIGHT);
    setDetachedColumns(new Set());
    setFloatingPanels({
      WHAT_IT_DOES: { x: 40, y: 40, width: 340, height: 260, zIndex: 100 },
      DATA_FLOW: { x: 80, y: 80, width: 360, height: 280, zIndex: 100 },
      TECHNICAL_DETAILS: { x: 120, y: 120, width: 400, height: 300, zIndex: 100 },
    });
    setHighestZIndex(100);
  }, [analysisId]);

  // Global mouse handlers for bottom pane resize and floating panel drag
  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      // 1. Bottom pane vertical resize
      if (isResizingRef.current) {
        const deltaY = startYRef.current - e.clientY;
        const maxH = Math.max(window.innerHeight * 0.75, 300);
        const newHeight = Math.min(Math.max(startHeightRef.current + deltaY, MIN_PANE_HEIGHT), maxH);
        setPaneHeight(newHeight);
      }

      // 2. Floating panel dragging
      if (isDraggingPanelRef.current) {
        const colId = isDraggingPanelRef.current;
        const newX = Math.max(0, Math.min(window.innerWidth - 100, e.clientX - dragOffsetRef.current.x));
        const newY = Math.max(0, Math.min(window.innerHeight - 50, e.clientY - dragOffsetRef.current.y));

        setFloatingPanels((prev) => ({
          ...prev,
          [colId]: {
            ...prev[colId],
            x: newX,
            y: newY,
          },
        }));
      }
    };

    const handleMouseUp = () => {
      if (isResizingRef.current) {
        isResizingRef.current = false;
        document.body.style.cursor = '';
        document.body.style.userSelect = '';
      }
      if (isDraggingPanelRef.current) {
        isDraggingPanelRef.current = null;
        document.body.style.cursor = '';
        document.body.style.userSelect = '';
      }
    };

    window.addEventListener('mousemove', handleMouseMove);
    window.addEventListener('mouseup', handleMouseUp);

    return () => {
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('mouseup', handleMouseUp);
    };
  }, []);

  const handleStartResize = (e: React.MouseEvent) => {
    e.preventDefault();
    isResizingRef.current = true;
    startYRef.current = e.clientY;
    startHeightRef.current = paneHeight;
    document.body.style.cursor = 'ns-resize';
    document.body.style.userSelect = 'none';
  };

  const handleDetachColumn = (colId: ColumnId) => {
    setDetachedColumns((prev) => {
      const next = new Set(prev);
      next.add(colId);
      return next;
    });

    const nextZ = highestZIndex + 1;
    setHighestZIndex(nextZ);
    setFloatingPanels((prev) => {
      // Cascade initial floating positions neatly
      const cascadeOffset = colId === 'WHAT_IT_DOES' ? 30 : colId === 'DATA_FLOW' ? 80 : 130;
      return {
        ...prev,
        [colId]: {
          ...prev[colId],
          x: Math.min(window.innerWidth - 440, Math.max(40, cascadeOffset + 40)),
          y: Math.min(window.innerHeight - 360, Math.max(60, cascadeOffset + 30)),
          zIndex: nextZ,
        },
      };
    });
  };

  const handleDockColumn = (colId: ColumnId) => {
    setDetachedColumns((prev) => {
      const next = new Set(prev);
      next.delete(colId);
      return next;
    });
  };

  const handleResetPaneLayout = () => {
    setPaneHeight(DEFAULT_PANE_HEIGHT);
    setDetachedColumns(new Set());
    setHighestZIndex(100);
  };

  const handleBringToFront = (colId: ColumnId) => {
    const nextZ = highestZIndex + 1;
    setHighestZIndex(nextZ);
    setFloatingPanels((prev) => ({
      ...prev,
      [colId]: {
        ...prev[colId],
        zIndex: nextZ,
      },
    }));
  };

  const handleStartPanelDrag = (colId: ColumnId, e: React.MouseEvent) => {
    // Only allow dragging from header element, ignore close/dock buttons
    if ((e.target as HTMLElement).closest('button')) {
      return;
    }
    e.preventDefault();
    handleBringToFront(colId);
    isDraggingPanelRef.current = colId;
    dragOffsetRef.current = {
      x: e.clientX - floatingPanels[colId].x,
      y: e.clientY - floatingPanels[colId].y,
    };
    document.body.style.cursor = 'grabbing';
    document.body.style.userSelect = 'none';
  };

  // Demand-driven fetch for selected tool's workflow-specific narrative
  useEffect(() => {
    if (!selectedNode || !analysisId) {
      setLlmSummary(null);
      return;
    }

    let isMounted = true;
    setLoadingSummary(true);

    api.getToolSummary(analysisId, selectedNode.tool_id)
      .then((res) => {
        if (isMounted && res.summary) {
          setLlmSummary(res.summary);
          if (onUpdateNodeSummary) {
            onUpdateNodeSummary(selectedNode.tool_id, res.summary);
          }
        }
      })
      .catch(() => {
        // If on-demand fetch fails, keep existing node.summary fallback
      })
      .finally(() => {
        if (isMounted) {
          setLoadingSummary(false);
        }
      });

    return () => {
      isMounted = false;
    };
  }, [selectedNode?.tool_id, analysisId]);

  if (!selectedNode && !selectedConnection) {
    return null;
  }

  // If a connection edge is selected:
  if (selectedConnection) {
    const { connection, sourceNode, targetNode } = selectedConnection;
    return (
      <div
        style={{
          width: '100%',
          height: '220px',
          maxHeight: '30vh',
          minHeight: '180px',
          background: 'var(--color-surface)',
          borderTop: '1px solid var(--color-border)',
          display: 'flex',
          flexDirection: 'column',
          boxShadow: '0 -2px 10px rgba(0, 0, 0, 0.12)',
          flexShrink: 0,
          zIndex: 10,
        }}
      >
        {/* Header */}
        <div
          style={{
            padding: '8px 16px',
            borderBottom: '1px solid var(--color-border)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            background: 'var(--color-surface-secondary)',
            height: '38px',
            boxSizing: 'border-box',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Layers size={15} color="var(--color-primary)" />
            <h3 style={{ fontSize: '12.5px', fontWeight: 700, margin: 0, color: 'var(--color-text)' }}>
              Connection Details
            </h3>
          </div>
          <button
            onClick={onClose}
            aria-label="Close connection inspector"
            style={{
              background: 'transparent',
              border: 'none',
              cursor: 'pointer',
              color: 'var(--color-text-muted)',
              padding: '4px',
              display: 'flex',
              alignItems: 'center',
            }}
          >
            <X size={15} />
          </button>
        </div>

        <div
          style={{
            flex: 1,
            padding: '16px 20px',
            display: 'grid',
            gridTemplateColumns: '1fr auto 1fr',
            alignItems: 'center',
            gap: '24px',
            overflowY: 'auto',
          }}
        >
          {/* Source Tool */}
          <div>
            <div style={{ fontSize: '10px', fontWeight: 700, color: 'var(--color-text-muted)', textTransform: 'uppercase', marginBottom: '6px' }}>
              Origin (Source)
            </div>
            <div
              onClick={() => onSelectTool(connection.origin_tool_id)}
              style={{
                padding: '10px 12px',
                background: 'var(--color-surface-secondary)',
                border: '1px solid var(--color-border)',
                borderRadius: 'var(--radius-sm, 4px)',
                cursor: 'pointer',
                display: 'flex',
                flexDirection: 'column',
                gap: '4px',
              }}
              className="app-card-hover"
            >
              <span style={{ fontSize: '12px', fontWeight: 700, color: 'var(--color-text)' }}>
                #{connection.origin_tool_id} {sourceNode?.name || sourceNode?.tool_type || 'Source Tool'}
              </span>
              <span style={{ fontSize: '10.5px', color: 'var(--color-text-secondary)', fontFamily: 'var(--font-mono)' }}>
                Port: {connection.origin_anchor}
              </span>
            </div>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <ArrowRight size={20} color="var(--color-text-muted)" />
          </div>

          {/* Target Tool */}
          <div>
            <div style={{ fontSize: '10px', fontWeight: 700, color: 'var(--color-text-muted)', textTransform: 'uppercase', marginBottom: '6px' }}>
              Destination (Target)
            </div>
            <div
              onClick={() => onSelectTool(connection.destination_tool_id)}
              style={{
                padding: '10px 12px',
                background: 'var(--color-surface-secondary)',
                border: '1px solid var(--color-border)',
                borderRadius: 'var(--radius-sm, 4px)',
                cursor: 'pointer',
                display: 'flex',
                flexDirection: 'column',
                gap: '4px',
              }}
              className="app-card-hover"
            >
              <span style={{ fontSize: '12px', fontWeight: 700, color: 'var(--color-text)' }}>
                #{connection.destination_tool_id} {targetNode?.name || targetNode?.tool_type || 'Target Tool'}
              </span>
              <span style={{ fontSize: '10.5px', color: 'var(--color-primary)', fontFamily: 'var(--font-mono)' }}>
                Port: {connection.destination_anchor}
              </span>
            </div>
          </div>
        </div>
      </div>
    );
  }

  // Node details inspector
  const node = selectedNode!;
  const categoryColor = getCategoryColor(node.visual_category || node.tool_type.toLowerCase());
  const workflowRole = getWorkflowRole(node.tool_type, node.visual_category, isBusinessOutput);
  const roleColor = getWorkflowRoleColor(workflowRole);
  const xmlToolName = resolveXmlToolName(node);

  // Technical Details values
  const containerIdDisplay = node.container_id != null ? `#${node.container_id}` : 'Not assigned';
  const rawNodeXml = node.raw_node_xml && node.raw_node_xml.trim().length > 0 ? node.raw_node_xml.trim() : 'Source Node unavailable';
  const formattedNodeXml = React.useMemo(() => {
    return formatXmlForDisplay(rawNodeXml);
  }, [rawNodeXml]);

  const handleCopyXml = () => {
    if (rawNodeXml && rawNodeXml !== 'Source Node unavailable') {
      navigator.clipboard.writeText(rawNodeXml);
      setCopiedXml(true);
      setTimeout(() => setCopiedXml(false), 2000);
    }
  };

  // -------------------------------------------------------------
  // Column Renderers (Shared between Docked & Floating modes)
  // -------------------------------------------------------------

  const renderWhatItDoesContent = (isFloating: boolean) => (
    <div
      style={{
        padding: '12px 16px',
        display: 'flex',
        flexDirection: 'column',
        gap: '12px',
        overflowY: 'auto',
        flex: 1,
        borderRight: !isFloating ? '1px solid var(--color-border)' : 'none',
      }}
    >
      {/* What It Does */}
      <div>
        <div style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          marginBottom: '6px',
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span style={{
              fontSize: '10px',
              fontWeight: 700,
              color: 'var(--color-text-muted)',
              textTransform: 'uppercase',
              letterSpacing: '0.5px',
            }}>
              What It Does
            </span>
            <span style={{
              fontSize: '9.5px',
              fontWeight: '600',
              padding: '1px 6px',
              borderRadius: 'var(--radius-sm, 4px)',
              background: 'var(--color-primary-subtle)',
              color: 'var(--color-primary)',
              border: '1px solid var(--color-primary-border)',
              letterSpacing: '0.3px',
              textTransform: 'none',
              lineHeight: '1.4',
              display: 'inline-flex',
              alignItems: 'center',
            }}>
              AI Generated
            </span>
          </div>

          {!isFloating && (
            <button
              onClick={() => handleDetachColumn('WHAT_IT_DOES')}
              title="Pop out What It Does / Workflow Role as floating panel"
              aria-label="Detach What It Does"
              style={{
                background: 'transparent',
                border: 'none',
                cursor: 'pointer',
                color: 'var(--color-text-muted)',
                padding: '2px 4px',
                display: 'inline-flex',
                alignItems: 'center',
                gap: '3px',
                fontSize: '10px',
                fontWeight: 600,
                borderRadius: '3px',
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.color = 'var(--color-primary)';
                e.currentTarget.style.backgroundColor = 'var(--color-surface-hover)';
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.color = 'var(--color-text-muted)';
                e.currentTarget.style.backgroundColor = 'transparent';
              }}
            >
              <ExternalLink size={12} />
            </button>
          )}
        </div>
        <div
          style={{
            padding: '8px 10px',
            background: 'var(--color-surface-secondary)',
            border: '1px solid var(--color-border)',
            borderRadius: 'var(--radius-sm, 4px)',
            fontSize: '11.5px',
            fontWeight: 500,
            color: 'var(--color-text)',
            lineHeight: '1.45',
            fontStyle: (llmSummary || node.summary) ? 'normal' : 'italic',
            opacity: loadingSummary ? 0.7 : 1,
            transition: 'opacity 0.2s ease',
          }}
        >
          {llmSummary || node.summary || 'No functional description available.'}
        </div>
      </div>

      {/* Workflow Role */}
      <div>
        <div style={{ fontSize: '10px', fontWeight: 700, color: 'var(--color-text-muted)', textTransform: 'uppercase', letterSpacing: '0.5px', marginBottom: '5px' }}>
          Workflow Role
        </div>
        <div
          style={{
            padding: '7px 10px',
            background: 'var(--color-surface-secondary)',
            border: '1px solid var(--color-border)',
            borderRadius: 'var(--radius-sm, 4px)',
            fontSize: '11.5px',
            fontWeight: 700,
            color: 'var(--color-text)',
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
          }}
        >
          <span style={{ width: '8px', height: '8px', borderRadius: '50%', background: roleColor, flexShrink: 0 }} />
          <span>{workflowRole}</span>
        </div>
      </div>
    </div>
  );

  const renderDataFlowContent = (isFloating: boolean) => (
    <div
      style={{
        padding: '12px 16px',
        display: 'flex',
        flexDirection: 'column',
        gap: '8px',
        overflowY: 'auto',
        flex: 1,
        borderRight: !isFloating ? '1px solid var(--color-border)' : 'none',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <span style={{ fontSize: '10px', fontWeight: 700, color: 'var(--color-text-muted)', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
          Data Flow
        </span>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span style={{ fontSize: '10px', color: 'var(--color-text-secondary)', fontFamily: 'var(--font-mono)', fontWeight: 600 }}>
            {upstreamNodes.length} upstream · {downstreamNodes.length} downstream
          </span>
          {!isFloating && (
            <button
              onClick={() => handleDetachColumn('DATA_FLOW')}
              title="Pop out Data Flow as floating panel"
              aria-label="Detach Data Flow"
              style={{
                background: 'transparent',
                border: 'none',
                cursor: 'pointer',
                color: 'var(--color-text-muted)',
                padding: '2px 4px',
                display: 'inline-flex',
                alignItems: 'center',
                gap: '3px',
                fontSize: '10px',
                fontWeight: 600,
                borderRadius: '3px',
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.color = 'var(--color-primary)';
                e.currentTarget.style.backgroundColor = 'var(--color-surface-hover)';
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.color = 'var(--color-text-muted)';
                e.currentTarget.style.backgroundColor = 'transparent';
              }}
            >
              <ExternalLink size={12} />
            </button>
          )}
        </div>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: '5px' }}>
        {/* Upstream nodes */}
        {upstreamNodes.length === 0 ? (
          <div style={{ fontSize: '10.5px', color: 'var(--color-text-muted)', fontStyle: 'italic', padding: '3px 6px' }}>
            Source tool (no upstream inputs)
          </div>
        ) : (
          upstreamNodes.map((up) => (
            <div
              key={up.tool_id}
              onClick={() => onSelectTool(up.tool_id)}
              style={{
                padding: '5px 8px',
                background: 'var(--color-surface-secondary)',
                border: '1px solid var(--color-border)',
                borderRadius: 'var(--radius-sm, 4px)',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
              }}
              className="app-card-hover"
              title={`Focus upstream tool #${up.tool_id}`}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px', overflow: 'hidden' }}>
                <ArrowLeft size={11} color="#0284c7" />
                <span style={{ fontSize: '11px', fontWeight: 700, color: 'var(--color-text)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                  #{up.tool_id} {up.name}
                </span>
              </div>
              <span style={{ fontSize: '10px', color: 'var(--color-text-secondary)', whiteSpace: 'nowrap', marginLeft: '6px' }}>
                {up.tool_type}
              </span>
            </div>
          ))
        )}

        {/* Current selected node indicator */}
        <div
          style={{
            padding: '6px 8px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            background: 'var(--color-surface-secondary)',
            borderRadius: 'var(--radius-sm, 4px)',
            border: `1px solid ${categoryColor.stroke || 'var(--color-primary-border)'}`,
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px', overflow: 'hidden' }}>
            <span style={{ width: '7px', height: '7px', borderRadius: '50%', background: roleColor, flexShrink: 0 }} />
            <span style={{ fontSize: '11px', fontWeight: 700, color: 'var(--color-text)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
              #{node.tool_id} {node.name}
            </span>
          </div>
          <span
            style={{
              fontSize: '9px',
              fontWeight: 800,
              color: categoryColor.text || 'var(--color-primary)',
              background: categoryColor.badgeBg || 'var(--color-primary-subtle)',
              border: '1px solid var(--color-border-subtle)',
              padding: '1px 5px',
              borderRadius: '3px',
              letterSpacing: '0.5px',
              textTransform: 'uppercase',
            }}
          >
            CURRENT
          </span>
        </div>

        {/* Downstream nodes */}
        {downstreamNodes.length === 0 ? (
          <div style={{ fontSize: '10.5px', color: 'var(--color-text-muted)', fontStyle: 'italic', padding: '3px 6px' }}>
            Terminal tool (no downstream outputs)
          </div>
        ) : (
          downstreamNodes.map((down) => (
            <div
              key={down.tool_id}
              onClick={() => onSelectTool(down.tool_id)}
              style={{
                padding: '5px 8px',
                background: 'var(--color-surface-secondary)',
                border: '1px solid var(--color-border)',
                borderRadius: 'var(--radius-sm, 4px)',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
              }}
              className="app-card-hover"
              title={`Focus downstream tool #${down.tool_id}`}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px', overflow: 'hidden' }}>
                <ArrowRight size={11} color="#16a34a" />
                <span style={{ fontSize: '11px', fontWeight: 700, color: 'var(--color-text)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                  #{down.tool_id} {down.name}
                </span>
              </div>
              <span style={{ fontSize: '10px', color: 'var(--color-text-secondary)', whiteSpace: 'nowrap', marginLeft: '6px' }}>
                {down.tool_type}
              </span>
            </div>
          ))
        )}
      </div>
    </div>
  );

  const renderTechnicalDetailsContent = (isFloating: boolean) => (
    <div
      style={{
        padding: '12px 16px',
        display: 'flex',
        flexDirection: 'column',
        gap: '10px',
        overflowY: 'auto',
        flex: 1,
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <span style={{ fontSize: '10px', fontWeight: 700, color: 'var(--color-text-muted)', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
          Technical Details
        </span>
        {!isFloating && (
          <button
            onClick={() => handleDetachColumn('TECHNICAL_DETAILS')}
            title="Pop out Technical Details as floating panel"
            aria-label="Detach Technical Details"
            style={{
              background: 'transparent',
              border: 'none',
              cursor: 'pointer',
              color: 'var(--color-text-muted)',
              padding: '2px 4px',
              display: 'inline-flex',
              alignItems: 'center',
              gap: '3px',
              fontSize: '10px',
              fontWeight: 600,
              borderRadius: '3px',
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.color = 'var(--color-primary)';
              e.currentTarget.style.backgroundColor = 'var(--color-surface-hover)';
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.color = 'var(--color-text-muted)';
              e.currentTarget.style.backgroundColor = 'transparent';
            }}
          >
            <ExternalLink size={12} />
          </button>
        )}
      </div>

      {/* Container ID & XML Tool Name Metadata Row */}
      <div style={{ display: 'grid', gridTemplateColumns: 'auto 1fr', gap: '14px', alignItems: 'flex-start' }}>
        <div>
          <div style={{ fontSize: '10px', color: 'var(--color-text-muted)', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.5px', marginBottom: '2px' }}>
            Container ID
          </div>
          <div style={{ fontSize: '11px', fontWeight: 600, color: node.container_id != null ? 'var(--color-text)' : 'var(--color-text-muted)', fontStyle: node.container_id != null ? 'normal' : 'italic' }}>
            {containerIdDisplay}
          </div>
        </div>

        <div style={{ overflow: 'hidden' }}>
          <div style={{ fontSize: '10px', color: 'var(--color-text-muted)', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.5px', marginBottom: '2px' }}>
            XML Tool Name
          </div>
          <div
            style={{
              fontSize: '11px',
              fontWeight: 600,
              fontFamily: 'var(--font-mono)',
              color: xmlToolName !== 'Not available in tool registry' ? 'var(--color-text)' : 'var(--color-text-muted)',
              fontStyle: xmlToolName !== 'Not available in tool registry' ? 'normal' : 'italic',
              whiteSpace: 'nowrap',
              overflow: 'hidden',
              textOverflow: 'ellipsis',
            }}
            title={xmlToolName}
          >
            {xmlToolName}
          </div>
        </div>
      </div>

      {/* Workflow Context (Formatted XML Code Viewer) */}
      <div style={{ display: 'flex', flexDirection: 'column', flex: 1, minHeight: 0 }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '4px' }}>
          <div style={{ fontSize: '10px', color: 'var(--color-text-muted)', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.5px' }}>
            Workflow Context
          </div>
          {rawNodeXml !== 'Source Node unavailable' && (
            <button
              onClick={handleCopyXml}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '4px',
                background: 'transparent',
                border: '1px solid var(--color-border)',
                borderRadius: '3px',
                padding: '2px 6px',
                fontSize: '9.5px',
                color: copiedXml ? 'var(--color-success)' : 'var(--color-text-muted)',
                cursor: 'pointer',
                transition: 'all 0.15s ease',
              }}
              title="Copy exact Node XML to clipboard"
            >
              {copiedXml ? <Check size={11} color="var(--color-success)" /> : <Copy size={11} />}
              <span>{copiedXml ? 'Copied' : 'Copy XML'}</span>
            </button>
          )}
        </div>
        <div
          style={{
            background: '#090d16',
            border: '1px solid var(--color-border)',
            borderRadius: '4px',
            padding: '6px 8px',
            height: isFloating ? '140px' : '100px',
            maxHeight: isFloating ? '220px' : '120px',
            overflowX: 'auto',
            overflowY: 'auto',
            fontFamily: 'var(--font-mono)',
            fontSize: '10px',
            lineHeight: '1.4',
            color: '#e2e8f0',
            whiteSpace: 'pre',
          }}
        >
          <code>{formattedNodeXml}</code>
        </div>
      </div>
    </div>
  );

  // Active docked columns
  const isCol1Docked = !detachedColumns.has('WHAT_IT_DOES');
  const isCol2Docked = !detachedColumns.has('DATA_FLOW');
  const isCol3Docked = !detachedColumns.has('TECHNICAL_DETAILS');
  const dockedCount = (isCol1Docked ? 1 : 0) + (isCol2Docked ? 1 : 0) + (isCol3Docked ? 1 : 0);

  // Dynamic grid template for remaining docked columns
  const getGridTemplateColumns = () => {
    if (dockedCount === 3) return 'minmax(0, 1fr) minmax(0, 1.15fr) minmax(0, 1.25fr)';
    if (dockedCount === 2) return 'minmax(0, 1fr) minmax(0, 1fr)';
    return 'minmax(0, 1fr)';
  };

  const hasDetachedPanels = detachedColumns.size > 0;
  const isCustomHeight = paneHeight !== DEFAULT_PANE_HEIGHT;
  const showResetButton = hasDetachedPanels || isCustomHeight;

  return (
    <>
      {/* ------------------------------------------------------------- */}
      {/* 1. FLOATING DETACHED PANELS (Rendered as Viewport Overlays)   */}
      {/* ------------------------------------------------------------- */}
      {Array.from(detachedColumns).map((colId) => {
        const panelState = floatingPanels[colId];
        const title =
          colId === 'WHAT_IT_DOES'
            ? 'What It Does & Role'
            : colId === 'DATA_FLOW'
            ? 'Data Flow'
            : 'Technical Details';

        return (
          <div
            key={colId}
            onMouseDown={() => handleBringToFront(colId)}
            style={{
              position: 'fixed',
              left: `${panelState.x}px`,
              top: `${panelState.y}px`,
              width: `${panelState.width}px`,
              maxHeight: '70vh',
              background: 'var(--color-surface)',
              border: '1px solid var(--color-border)',
              borderRadius: 'var(--radius-md, 6px)',
              boxShadow: '0 8px 24px rgba(0, 0, 0, 0.22), 0 2px 6px rgba(0, 0, 0, 0.1)',
              zIndex: panelState.zIndex,
              display: 'flex',
              flexDirection: 'column',
              overflow: 'hidden',
            }}
          >
            {/* Draggable Header */}
            <div
              onMouseDown={(e) => handleStartPanelDrag(colId, e)}
              style={{
                padding: '6px 12px',
                borderBottom: '1px solid var(--color-border)',
                background: 'var(--color-surface-secondary)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                cursor: 'grab',
                userSelect: 'none',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px', overflow: 'hidden' }}>
                <span
                  style={{
                    fontSize: '10.5px',
                    fontWeight: 800,
                    fontFamily: 'var(--font-mono)',
                    color: 'var(--color-text)',
                    background: 'var(--color-surface)',
                    border: '1px solid var(--color-border)',
                    padding: '1px 4px',
                    borderRadius: '3px',
                  }}
                >
                  #{node.tool_id}
                </span>
                <span style={{ fontSize: '11px', fontWeight: 700, color: 'var(--color-text)', whiteSpace: 'nowrap' }}>
                  {title}
                </span>
              </div>

              <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                {/* Dock Button */}
                <button
                  onClick={() => handleDockColumn(colId)}
                  title="Dock back to bottom pane"
                  aria-label="Dock column"
                  style={{
                    background: 'transparent',
                    border: '1px solid var(--color-border)',
                    borderRadius: '3px',
                    cursor: 'pointer',
                    color: 'var(--color-text-secondary)',
                    padding: '2px 5px',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '3px',
                    fontSize: '10px',
                    fontWeight: 600,
                  }}
                  onMouseEnter={(e) => {
                    e.currentTarget.style.backgroundColor = 'var(--color-surface-hover)';
                    e.currentTarget.style.color = 'var(--color-primary)';
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.backgroundColor = 'transparent';
                    e.currentTarget.style.color = 'var(--color-text-secondary)';
                  }}
                >
                  <ArrowDownLeft size={11} />
                  <span>Dock</span>
                </button>
              </div>
            </div>

            {/* Panel Content Body */}
            <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflowY: 'auto' }}>
              {colId === 'WHAT_IT_DOES' && renderWhatItDoesContent(true)}
              {colId === 'DATA_FLOW' && renderDataFlowContent(true)}
              {colId === 'TECHNICAL_DETAILS' && renderTechnicalDetailsContent(true)}
            </div>
          </div>
        );
      })}

      {/* ------------------------------------------------------------- */}
      {/* 2. DOCKED BOTTOM PANE (Only rendered if at least 1 docked)     */}
      {/* ------------------------------------------------------------- */}
      {dockedCount > 0 && (
        <div
          style={{
            width: '100%',
            height: `${paneHeight}px`,
            background: 'var(--color-surface)',
            borderTop: '1px solid var(--color-border)',
            display: 'flex',
            flexDirection: 'column',
            boxShadow: '0 -2px 10px rgba(0, 0, 0, 0.12)',
            flexShrink: 0,
            position: 'relative',
            zIndex: 10,
          }}
        >
          {/* Draggable Horizontal Resize Handle at the Top Edge */}
          <div
            onMouseDown={handleStartResize}
            title="Drag to resize inspector height"
            style={{
              position: 'absolute',
              top: '-4px',
              left: 0,
              width: '100%',
              height: '8px',
              cursor: 'ns-resize',
              zIndex: 30,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}
          >
            <div
              style={{
                width: '36px',
                height: '3px',
                borderRadius: '2px',
                background: 'var(--color-border)',
                transition: 'background 0.15s ease',
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.background = 'var(--color-primary)';
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.background = 'var(--color-border)';
              }}
            />
          </div>

          {/* 1. Header Banner */}
          <div
            style={{
              padding: '6px 16px',
              borderBottom: '1px solid var(--color-border)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              background: categoryColor.badgeBg || 'var(--color-surface-secondary)',
              height: '36px',
              boxSizing: 'border-box',
              flexShrink: 0,
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', overflow: 'hidden' }}>
              <span
                style={{
                  fontSize: '11px',
                  fontWeight: 800,
                  fontFamily: 'var(--font-mono)',
                  color: 'var(--color-text)',
                  background: 'var(--color-surface)',
                  border: '1px solid var(--color-border)',
                  padding: '1px 5px',
                  borderRadius: '3px',
                }}
              >
                #{node.tool_id}
              </span>
              <span
                style={{
                  fontSize: '11px',
                  fontWeight: 800,
                  color: categoryColor.text || 'var(--color-text)',
                  textTransform: 'uppercase',
                  letterSpacing: '0.4px',
                }}
              >
                {node.tool_type}
              </span>
              {isBusinessOutput && (
                <span
                  style={{
                    fontSize: '9px',
                    fontWeight: 800,
                    padding: '1px 5px',
                    borderRadius: '3px',
                    background: 'rgba(147, 51, 234, 0.2)',
                    color: '#9333ea',
                    textTransform: 'uppercase',
                    border: '1px solid rgba(147, 51, 234, 0.4)',
                  }}
                >
                  Output Deliverable
                </span>
              )}
              <span style={{ fontSize: '13px', fontWeight: 800, color: 'var(--color-text)', marginLeft: '4px', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                {node.name}
              </span>
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              {/* Reset Layout Button (Restores all detached panels and default height) */}
              {showResetButton && (
                <button
                  onClick={handleResetPaneLayout}
                  title="Reset pane layout & dock all panels"
                  aria-label="Reset pane layout"
                  style={{
                    background: 'var(--color-surface)',
                    border: '1px solid var(--color-border)',
                    borderRadius: 'var(--radius-sm, 4px)',
                    cursor: 'pointer',
                    color: 'var(--color-text-secondary)',
                    padding: '2px 8px',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '4px',
                    fontSize: '11px',
                    fontWeight: 600,
                    transition: 'all 0.15s ease',
                  }}
                  onMouseEnter={(e) => {
                    e.currentTarget.style.backgroundColor = 'var(--color-surface-hover)';
                    e.currentTarget.style.borderColor = 'var(--color-primary-border)';
                    e.currentTarget.style.color = 'var(--color-primary)';
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.backgroundColor = 'var(--color-surface)';
                    e.currentTarget.style.borderColor = 'var(--color-border)';
                    e.currentTarget.style.color = 'var(--color-text-secondary)';
                  }}
                >
                  <RotateCcw size={11} />
                  <span>Reset Layout</span>
                </button>
              )}

              <button
                onClick={onClose}
                aria-label="Close tool inspector"
                style={{
                  background: 'transparent',
                  border: 'none',
                  cursor: 'pointer',
                  color: 'var(--color-text-muted)',
                  padding: '4px',
                  display: 'flex',
                  alignItems: 'center',
                }}
                title="Close Inspector (Esc)"
              >
                <X size={15} />
              </button>
            </div>
          </div>

          {/* 2. Content Body: Docked Columns */}
          <div
            style={{
              flex: 1,
              display: 'grid',
              gridTemplateColumns: getGridTemplateColumns(),
              minHeight: 0,
              overflow: 'hidden',
            }}
          >
            {isCol1Docked && renderWhatItDoesContent(false)}
            {isCol2Docked && renderDataFlowContent(false)}
            {isCol3Docked && renderTechnicalDetailsContent(false)}
          </div>
        </div>
      )}
    </>
  );
};
