import React, { useState } from 'react';
import { PythonOutputDTO } from '../types/workflow';
import { Copy, Check, Download, PackageCheck, Info } from 'lucide-react';

interface CodeViewerProps {
  pythonData: PythonOutputDTO;
  onDownload?: () => void;
}

export const CodeViewer: React.FC<CodeViewerProps> = ({ pythonData, onDownload }) => {
  const [copied, setCopied] = useState(false);
  const [highlightedToolId, setHighlightedToolId] = useState<number | null>(null);

  const handleCopy = () => {
    navigator.clipboard.writeText(pythonData.code);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const lines = pythonData.code.split('\n');

  // Find active line range if a tool is highlighted
  const activeEntry = highlightedToolId
    ? pythonData.trace_map.find((e) => e.tool_id === highlightedToolId)
    : null;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      {/* 1. Required Libraries Disclosure Card */}
      <div className="glass-card" style={{ padding: '16px 20px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '10px' }}>
          <PackageCheck size={16} color="#4ade80" />
          <span style={{ fontSize: '12px', fontWeight: '700', color: '#f8fafc', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
            Required Workflow Libraries
          </span>
        </div>
        <div style={{ fontSize: '12px', color: '#94a3b8', marginBottom: '12px' }}>
          Only dependencies imported by the generated script are listed. AWA internal dependencies (Lark, NetworkX, FastAPI) are excluded.
        </div>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
          {pythonData.required_libraries.map((lib) => (
            <span
              key={lib}
              style={{
                padding: '5px 12px',
                borderRadius: '6px',
                background: 'rgba(74, 222, 128, 0.12)',
                border: '1px solid rgba(74, 222, 128, 0.4)',
                color: '#4ade80',
                fontSize: '12px',
                fontFamily: 'monospace',
                fontWeight: '600',
              }}
            >
              {lib}
            </span>
          ))}
        </div>
      </div>

      {/* 2. Tool-to-Code Traceability Table */}
      <div className="glass-card" style={{ overflow: 'hidden' }}>
        <div style={{
          padding: '12px 18px',
          background: 'rgba(15, 23, 42, 0.9)',
          borderBottom: '1px solid rgba(51, 65, 85, 0.5)',
          display: 'flex',
          alignItems: 'center',
          gap: '8px',
        }}>
          <Info size={15} color="#38bdf8" />
          <span style={{ fontSize: '12px', fontWeight: '700', color: '#f8fafc', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
            Alteryx-to-Python Source Traceability & Explanations
          </span>
        </div>

        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '12px' }}>
            <thead>
              <tr style={{ background: 'rgba(15, 23, 42, 0.6)', borderBottom: '1px solid rgba(51, 65, 85, 0.4)', textAlign: 'left' }}>
                <th style={{ padding: '10px 16px', color: '#94a3b8', fontWeight: '600' }}>Tool</th>
                <th style={{ padding: '10px 16px', color: '#94a3b8', fontWeight: '600' }}>Type</th>
                <th style={{ padding: '10px 16px', color: '#94a3b8', fontWeight: '600' }}>Lines</th>
                <th style={{ padding: '10px 16px', color: '#94a3b8', fontWeight: '600' }}>Pandas Operation</th>
                <th style={{ padding: '10px 16px', color: '#94a3b8', fontWeight: '600' }}>Why Selected</th>
              </tr>
            </thead>
            <tbody>
              {pythonData.trace_map.map((entry) => {
                const isSelected = highlightedToolId === entry.tool_id;
                return (
                  <tr
                    key={entry.tool_id}
                    onClick={() => setHighlightedToolId(isSelected ? null : entry.tool_id)}
                    style={{
                      cursor: 'pointer',
                      borderBottom: '1px solid rgba(51, 65, 85, 0.2)',
                      background: isSelected ? 'rgba(56, 189, 248, 0.1)' : 'transparent',
                      transition: 'background 0.15s ease',
                    }}
                  >
                    <td style={{ padding: '10px 16px', fontWeight: '700', color: '#f8fafc' }}>
                      #{entry.tool_id}
                    </td>
                    <td style={{ padding: '10px 16px', color: '#38bdf8', fontWeight: '600' }}>
                      {entry.tool_type}
                    </td>
                    <td style={{ padding: '10px 16px', fontFamily: 'monospace', color: '#cbd5e1' }}>
                      {entry.start_line}–{entry.end_line}
                    </td>
                    <td style={{ padding: '10px 16px', color: '#cbd5e1' }}>
                      {entry.pandas_op}
                    </td>
                    <td style={{ padding: '10px 16px', color: '#94a3b8' }}>
                      {entry.reason}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      {/* 3. Code Editor / Viewer */}
      <div className="glass-card" style={{ overflow: 'hidden' }}>
        {/* Action Header */}
        <div style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '12px 18px',
          background: 'rgba(15, 23, 42, 0.9)',
          borderBottom: '1px solid rgba(51, 65, 85, 0.5)',
        }}>
          <div style={{ fontSize: '12px', fontFamily: 'monospace', color: '#94a3b8' }}>
            workflow.py — executable pandas pipeline ({pythonData.total_lines} lines)
          </div>

          <div style={{ display: 'flex', gap: '8px' }}>
            <button
              onClick={handleCopy}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
                padding: '6px 12px',
                borderRadius: '6px',
                background: 'rgba(30, 41, 59, 0.8)',
                border: '1px solid rgba(51, 65, 85, 0.8)',
                color: copied ? '#4ade80' : '#cbd5e1',
                fontSize: '12px',
                fontWeight: '500',
                cursor: 'pointer',
              }}
            >
              {copied ? <Check size={14} /> : <Copy size={14} />}
              <span>{copied ? 'Copied!' : 'Copy Code'}</span>
            </button>

            {onDownload && (
              <button
                onClick={onDownload}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px',
                  padding: '6px 12px',
                  borderRadius: '6px',
                  background: 'linear-gradient(135deg, #10b981 0%, #059669 100%)',
                  border: 'none',
                  color: '#ffffff',
                  fontSize: '12px',
                  fontWeight: '600',
                  cursor: 'pointer',
                }}
              >
                <Download size={14} />
                <span>Download .py</span>
              </button>
            )}
          </div>
        </div>

        {/* Code Lines with Line Numbers */}
        <div style={{
          padding: '20px 0',
          background: 'rgba(7, 11, 25, 0.95)',
          overflow: 'auto',
          maxHeight: '600px',
          fontFamily: "'JetBrains Mono', monospace",
          fontSize: '12px',
          lineHeight: '1.6',
        }}>
          {lines.map((lineContent, idx) => {
            const lineNum = idx + 1;
            const isHighlighted = activeEntry
              ? lineNum >= activeEntry.start_line && lineNum <= activeEntry.end_line
              : false;

            return (
              <div
                key={lineNum}
                style={{
                  display: 'flex',
                  padding: '0 20px',
                  background: isHighlighted ? 'rgba(56, 189, 248, 0.12)' : 'transparent',
                  borderLeft: isHighlighted ? '3px solid #38bdf8' : '3px solid transparent',
                }}
              >
                <span style={{
                  width: '45px',
                  minWidth: '45px',
                  color: '#475569',
                  userSelect: 'none',
                  textAlign: 'right',
                  marginRight: '20px',
                }}>
                  {lineNum}
                </span>
                <span style={{
                  color: lineContent.trim().startsWith('#')
                    ? '#64748b'
                    : lineContent.includes('import ')
                    ? '#a78bfa'
                    : '#e2e8f0',
                  whiteSpace: 'pre',
                }}>
                  {lineContent || ' '}
                </span>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
};
