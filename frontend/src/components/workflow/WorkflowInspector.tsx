import React, { useState } from 'react';
import {
  X,
  ArrowRight,
  ArrowLeft,
  Layers,
  ChevronRight,
  ChevronDown,
  Copy,
  Check,
} from 'lucide-react';
import { NodeDTO, ConnectionDTO } from '../../types/workflow';
import { getCategoryColor, getWorkflowRole } from '../../theme/palette';
import { resolveXmlToolName } from '../../utils/toolRegistry';

interface WorkflowInspectorProps {
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
}

export const WorkflowInspector: React.FC<WorkflowInspectorProps> = ({
  selectedNode,
  selectedConnection,
  upstreamNodes,
  downstreamNodes,
  isBusinessOutput,
  onSelectTool,
  onClose,
}) => {
  const [showTechDetails, setShowTechDetails] = useState(false);
  const [copiedXml, setCopiedXml] = useState(false);

  if (!selectedNode && !selectedConnection) {
    return null;
  }

  // If a connection edge is selected:
  if (selectedConnection) {
    const { connection, sourceNode, targetNode } = selectedConnection;
    return (
      <div
        style={{
          width: 'min(380px, 35vw)',
          minWidth: '320px',
          maxWidth: '420px',
          height: '100%',
          background: 'var(--color-surface)',
          borderLeft: '1px solid var(--color-border)',
          display: 'flex',
          flexDirection: 'column',
          boxShadow: '-2px 0 8px rgba(0, 0, 0, 0.08)',
          overflowY: 'auto',
          flexShrink: 0,
        }}
      >
        {/* Header */}
        <div
          style={{
            padding: '14px 16px',
            borderBottom: '1px solid var(--color-border)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            background: 'var(--color-surface-secondary)',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Layers size={16} color="var(--color-primary)" />
            <h3 style={{ fontSize: '13px', fontWeight: 700, margin: 0, color: 'var(--color-text)' }}>
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
            <X size={16} />
          </button>
        </div>

        <div style={{ padding: '16px', display: 'flex', flexDirection: 'column', gap: '16px' }}>
          {/* Source Tool */}
          <div>
            <div style={{ fontSize: '10px', fontWeight: 700, color: 'var(--color-text-muted)', textTransform: 'uppercase', marginBottom: '6px' }}>
              Origin (Source)
            </div>
            <div
              onClick={() => onSelectTool(connection.origin_tool_id)}
              style={{
                padding: '8px 10px',
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
                <span style={{ fontSize: '10px', color: 'var(--color-primary)', fontFamily: 'var(--font-mono)' }}>
                  Port: {connection.origin_anchor}
                </span>
              </div>
            </div>
          </div>

          <div style={{ display: 'flex', justifyContent: 'center' }}>
            <ArrowRight size={16} color="var(--color-text-muted)" />
          </div>

          {/* Destination Tool */}
          <div>
            <div style={{ fontSize: '10px', fontWeight: 700, color: 'var(--color-text-muted)', textTransform: 'uppercase', marginBottom: '6px' }}>
              Destination (Target)
            </div>
            <div
              onClick={() => onSelectTool(connection.destination_tool_id)}
              style={{
                padding: '8px 10px',
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
                <span style={{ fontSize: '10px', color: 'var(--color-primary)', fontFamily: 'var(--font-mono)' }}>
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
  const xmlToolName = resolveXmlToolName(node);

  // Technical Details values
  const containerIdDisplay = node.container_id != null ? `#${node.container_id}` : 'Not assigned';
  const rawNodeXml = node.raw_node_xml && node.raw_node_xml.trim().length > 0 ? node.raw_node_xml.trim() : 'Source Node unavailable';

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
        width: 'min(380px, 35vw)',
        minWidth: '320px',
        maxWidth: '420px',
        height: '100%',
        background: 'var(--color-surface)',
        borderLeft: '1px solid var(--color-border)',
        display: 'flex',
        flexDirection: 'column',
        boxShadow: '-2px 0 8px rgba(0, 0, 0, 0.08)',
        overflowY: 'auto',
        flexShrink: 0,
      }}
    >
      {/* 1. Header (Preserved Shell) */}
      <div
        style={{
          padding: '14px 16px',
          borderBottom: '1px solid var(--color-border)',
          display: 'flex',
          alignItems: 'flex-start',
          justifyContent: 'space-between',
          background: categoryColor.badgeBg || 'var(--color-surface-secondary)',
        }}
      >
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '2px' }}>
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
          </div>
          <h3 style={{ fontSize: '15px', fontWeight: 800, margin: '4px 0 0 0', color: 'var(--color-text)' }}>
            {node.name}
          </h3>
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
          <X size={16} />
        </button>
      </div>

      {/* Content body */}
      <div style={{ padding: '16px', display: 'flex', flexDirection: 'column', gap: '16px' }}>

        {/* 2. WHAT IT DOES */}
        <div>
          <div style={{ fontSize: '10px', fontWeight: 700, color: 'var(--color-text-muted)', textTransform: 'uppercase', letterSpacing: '0.5px', marginBottom: '6px' }}>
            What It Does
          </div>
          <div
            style={{
              padding: '10px 12px',
              background: 'var(--color-surface-secondary)',
              border: '1px solid var(--color-border)',
              borderRadius: 'var(--radius-sm, 4px)',
              fontSize: '12px',
              fontWeight: 500,
              color: 'var(--color-text)',
              lineHeight: '1.5',
              fontStyle: node.summary ? 'normal' : 'italic',
            }}
          >
            {node.summary || 'No functional description available.'}
          </div>
        </div>

        {/* 3. WORKFLOW ROLE */}
        <div>
          <div style={{ fontSize: '10px', fontWeight: 700, color: 'var(--color-text-muted)', textTransform: 'uppercase', letterSpacing: '0.5px', marginBottom: '6px' }}>
            Workflow Role
          </div>
          <div
            style={{
              padding: '8px 12px',
              background: 'var(--color-surface-secondary)',
              border: '1px solid var(--color-border)',
              borderRadius: 'var(--radius-sm, 4px)',
              fontSize: '12px',
              fontWeight: 700,
              color: 'var(--color-text)',
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
            }}
          >
            <span style={{ width: '8px', height: '8px', borderRadius: '50%', background: categoryColor.stroke || 'var(--color-primary)', flexShrink: 0 }} />
            <span>{workflowRole}</span>
          </div>
        </div>

        <div style={{ height: '1px', background: 'var(--color-border)' }} />

        {/* 4. DATA FLOW (Unified inputs/outputs with clickable focus navigation) */}
        <div>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px' }}>
            <span style={{ fontSize: '10px', fontWeight: 700, color: 'var(--color-text-muted)', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
              Data Flow
            </span>
            <span style={{ fontSize: '10px', color: 'var(--color-text-secondary)', fontFamily: 'var(--font-mono)', fontWeight: 600 }}>
              {upstreamNodes.length} upstream · {downstreamNodes.length} downstream
            </span>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
            {/* Upstream nodes */}
            {upstreamNodes.length === 0 ? (
              <div style={{ fontSize: '10.5px', color: 'var(--color-text-muted)', fontStyle: 'italic', padding: '4px 8px' }}>
                Source tool (no upstream inputs)
              </div>
            ) : (
              upstreamNodes.map((up) => (
                <div
                  key={up.tool_id}
                  onClick={() => onSelectTool(up.tool_id)}
                  style={{
                    padding: '6px 10px',
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
                    <ArrowLeft size={12} color="#0284c7" />
                    <span style={{ fontSize: '11.5px', fontWeight: 700, color: 'var(--color-text)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                      #{up.tool_id} {up.name}
                    </span>
                  </div>
                  <span style={{ fontSize: '10.5px', color: 'var(--color-text-secondary)', whiteSpace: 'nowrap', marginLeft: '6px' }}>
                    {up.tool_type}
                  </span>
                </div>
              ))
            )}

            {/* Current selected node indicator (Fully readable, high contrast) */}
            <div
              style={{
                padding: '7px 10px',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                background: 'var(--color-surface-secondary)',
                borderRadius: 'var(--radius-sm, 4px)',
                border: `1px solid ${categoryColor.stroke || 'var(--color-primary-border)'}`,
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px', overflow: 'hidden' }}>
                <span style={{ width: '8px', height: '8px', borderRadius: '50%', background: categoryColor.stroke || 'var(--color-primary)', flexShrink: 0 }} />
                <span style={{ fontSize: '11.5px', fontWeight: 700, color: 'var(--color-text)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                  #{node.tool_id} {node.name}
                </span>
              </div>
              <span
                style={{
                  fontSize: '9.5px',
                  fontWeight: 800,
                  color: categoryColor.text || 'var(--color-primary)',
                  background: categoryColor.badgeBg || 'var(--color-primary-subtle)',
                  border: '1px solid var(--color-border-subtle)',
                  padding: '1px 6px',
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
              <div style={{ fontSize: '10.5px', color: 'var(--color-text-muted)', fontStyle: 'italic', padding: '4px 8px' }}>
                Terminal tool (no downstream outputs)
              </div>
            ) : (
              downstreamNodes.map((down) => (
                <div
                  key={down.tool_id}
                  onClick={() => onSelectTool(down.tool_id)}
                  style={{
                    padding: '6px 10px',
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
                    <ArrowRight size={12} color="#16a34a" />
                    <span style={{ fontSize: '11.5px', fontWeight: 700, color: 'var(--color-text)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                      #{down.tool_id} {down.name}
                    </span>
                  </div>
                  <span style={{ fontSize: '10.5px', color: 'var(--color-text-secondary)', whiteSpace: 'nowrap', marginLeft: '6px' }}>
                    {down.tool_type}
                  </span>
                </div>
              ))
            )}
          </div>
        </div>

        <div style={{ height: '1px', background: 'var(--color-border)' }} />

        {/* 5. TECHNICAL DETAILS (Collapsible, collapsed by default) */}
        <div>
          <button
            onClick={() => setShowTechDetails((prev) => !prev)}
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              width: '100%',
              background: 'transparent',
              border: 'none',
              padding: '4px 0',
              cursor: 'pointer',
              color: 'var(--color-text-muted)',
              fontSize: '11px',
              fontWeight: 700,
              textTransform: 'uppercase',
              letterSpacing: '0.5px',
            }}
          >
            <span>Technical Details</span>
            {showTechDetails ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
          </button>

          {showTechDetails && (
            <div
              style={{
                marginTop: '8px',
                background: 'var(--color-surface-secondary)',
                borderRadius: 'var(--radius-sm, 4px)',
                border: '1px solid var(--color-border)',
                padding: '12px',
                display: 'flex',
                flexDirection: 'column',
                gap: '12px',
                fontSize: '11px',
              }}
            >
              {/* 1. CONTAINER ID */}
              <div>
                <div style={{ fontSize: '10px', color: 'var(--color-text-muted)', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.5px', marginBottom: '4px' }}>
                  Container ID
                </div>
                <div style={{ fontSize: '12px', fontWeight: 600, color: node.container_id != null ? 'var(--color-text)' : 'var(--color-text-muted)', fontStyle: node.container_id != null ? 'normal' : 'italic' }}>
                  {containerIdDisplay}
                </div>
              </div>

              {/* 2. XML TOOL NAME (Deterministic registry mapping) */}
              <div>
                <div style={{ fontSize: '10px', color: 'var(--color-text-muted)', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.5px', marginBottom: '4px' }}>
                  XML Tool Name
                </div>
                <div
                  style={{
                    fontSize: '11px',
                    fontWeight: 600,
                    fontFamily: 'var(--font-mono)',
                    color: xmlToolName !== 'Not available in tool registry' ? 'var(--color-text)' : 'var(--color-text-muted)',
                    fontStyle: xmlToolName !== 'Not available in tool registry' ? 'normal' : 'italic',
                    wordBreak: 'break-all',
                  }}
                >
                  {xmlToolName}
                </div>
              </div>

              {/* 3. WORKFLOW CONTEXT (Exact source <Node>...</Node> snippet) */}
              <div>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '6px' }}>
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
                    padding: '8px 10px',
                    maxHeight: '220px',
                    overflowX: 'auto',
                    overflowY: 'auto',
                    fontFamily: 'var(--font-mono)',
                    fontSize: '10px',
                    lineHeight: '1.45',
                    color: '#e2e8f0',
                    whiteSpace: 'pre',
                  }}
                >
                  <code>{rawNodeXml}</code>
                </div>
              </div>

            </div>
          )}
        </div>

      </div>
    </div>
  );
};
