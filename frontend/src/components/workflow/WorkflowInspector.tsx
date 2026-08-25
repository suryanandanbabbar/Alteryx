import React, { useState, useEffect } from 'react';
import {
  X,
  ArrowRight,
  ArrowLeft,
  Layers,
  Copy,
  Check,
} from 'lucide-react';
import { api } from '../../api/client';
import { NodeDTO, ConnectionDTO } from '../../types/workflow';
import { getCategoryColor, getWorkflowRole, getWorkflowRoleColor } from '../../theme/palette';
import { resolveXmlToolName } from '../../utils/toolRegistry';
import { formatXmlForDisplay } from '../../utils/xmlFormatter';

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
                transition: 'border-color 0.15s ease',
              }}
              className="app-card-hover"
            >
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <span style={{ fontSize: '12px', fontWeight: 700, color: 'var(--color-text)' }}>
                  #{connection.origin_tool_id} {sourceNode?.name || sourceNode?.tool_type || 'Source Tool'}
                </span>
                <span style={{ fontSize: '10.5px', color: 'var(--color-primary)', fontFamily: 'var(--font-mono)' }}>
                  Port: {connection.origin_anchor}
                </span>
              </div>
            </div>
          </div>

          <div style={{ display: 'flex', justifyContent: 'center' }}>
            <ArrowRight size={20} color="var(--color-text-muted)" />
          </div>

          {/* Destination Tool */}
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
                transition: 'border-color 0.15s ease',
              }}
              className="app-card-hover"
            >
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
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

  return (
    <div
      style={{
        width: '100%',
        height: '240px',
        maxHeight: '34vh',
        minHeight: '200px',
        background: 'var(--color-surface)',
        borderTop: '1px solid var(--color-border)',
        display: 'flex',
        flexDirection: 'column',
        boxShadow: '0 -2px 10px rgba(0, 0, 0, 0.12)',
        flexShrink: 0,
        zIndex: 10,
      }}
    >
      {/* 1. Header (Compact Horizontal Banner) */}
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

      {/* 2. Content Body: 3 Responsive Columns */}
      <div
        style={{
          flex: 1,
          display: 'grid',
          gridTemplateColumns: 'minmax(0, 1fr) minmax(0, 1.15fr) minmax(0, 1.25fr)',
          minHeight: 0,
          overflow: 'hidden',
        }}
      >
        {/* ======================================================== */}
        {/* COLUMN 1: WHAT IT DOES + WORKFLOW ROLE                    */}
        {/* ======================================================== */}
        <div
          style={{
            padding: '12px 16px',
            borderRight: '1px solid var(--color-border)',
            display: 'flex',
            flexDirection: 'column',
            gap: '12px',
            overflowY: 'auto',
          }}
        >
          {/* What It Does */}
          <div>
            <div style={{
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              marginBottom: '6px',
            }}>
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

        {/* ======================================================== */}
        {/* COLUMN 2: DATA FLOW                                      */}
        {/* ======================================================== */}
        <div
          style={{
            padding: '12px 16px',
            borderRight: '1px solid var(--color-border)',
            display: 'flex',
            flexDirection: 'column',
            gap: '8px',
            overflowY: 'auto',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <span style={{ fontSize: '10px', fontWeight: 700, color: 'var(--color-text-muted)', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
              Data Flow
            </span>
            <span style={{ fontSize: '10px', color: 'var(--color-text-secondary)', fontFamily: 'var(--font-mono)', fontWeight: 600 }}>
              {upstreamNodes.length} upstream · {downstreamNodes.length} downstream
            </span>
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

        {/* ======================================================== */}
        {/* COLUMN 3: TECHNICAL DETAILS                              */}
        {/* ======================================================== */}
        <div
          style={{
            padding: '12px 16px',
            display: 'flex',
            flexDirection: 'column',
            gap: '10px',
            overflowY: 'auto',
          }}
        >
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
                height: '100px',
                maxHeight: '120px',
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

      </div>
    </div>
  );
};
