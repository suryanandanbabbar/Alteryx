import React, { useState } from 'react';
import { PythonOutputDTO } from '../types/workflow';
import { Copy, Check, Download, Terminal, Layers, Info } from 'lucide-react';

interface CodeViewerProps {
  pythonData: PythonOutputDTO;
  onDownload?: () => void;
}

export const CodeViewer: React.FC<CodeViewerProps> = ({ pythonData, onDownload }) => {
  const [copied, setCopied] = useState(false);
  const [selectedToolId, setSelectedToolId] = useState<number | null>(
    pythonData.trace_map[0]?.tool_id || null
  );

  const lines = pythonData.code.split('\n');

  const handleCopy = () => {
    navigator.clipboard.writeText(pythonData.code);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const selectedTrace = pythonData.trace_map.find((t) => t.tool_id === selectedToolId);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      {/* Top Libraries & Actions Bar */}
      <div className="app-card" style={{ padding: '14px 20px', display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '12px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px', flexWrap: 'wrap' }}>
          <span style={{ fontSize: '12px', fontWeight: '700', color: 'var(--color-text-muted)', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
            Required Libraries:
          </span>
          {pythonData.required_libraries.map((lib) => (
            <span
              key={lib}
              style={{
                fontFamily: 'var(--font-mono)',
                fontSize: '12px',
                fontWeight: '600',
                color: 'var(--color-primary)',
                background: 'var(--color-primary-subtle)',
                border: '1px solid var(--color-primary-border)',
                padding: '2px 8px',
                borderRadius: 'var(--radius-sm)',
              }}
            >
              {lib}
            </span>
          ))}
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <button
            onClick={handleCopy}
            className="btn-secondary"
            style={{ padding: '6px 12px', fontSize: '12px' }}
          >
            {copied ? <Check size={13} color="var(--color-success)" /> : <Copy size={13} />}
            <span>{copied ? 'Copied' : 'Copy Script'}</span>
          </button>

          {onDownload && (
            <button
              onClick={onDownload}
              className="btn-secondary"
              style={{ padding: '6px 12px', fontSize: '12px' }}
            >
              <Download size={13} />
              <span>Download .py</span>
            </button>
          )}
        </div>
      </div>

      {/* Code Editor Surface */}
      <div className="app-card" style={{ overflow: 'hidden' }}>
        <div style={{
          padding: '10px 16px',
          borderBottom: '1px solid var(--color-border)',
          background: 'var(--color-surface-secondary)',
          display: 'flex',
          alignItems: 'center',
          gap: '8px',
        }}>
          <Terminal size={15} color="var(--color-primary)" />
          <span style={{ fontSize: '13px', fontWeight: '700', color: 'var(--color-text)' }}>
            workflow.py
          </span>
          <span style={{
            fontSize: '11px',
            color: 'var(--color-text-muted)',
            fontFamily: 'var(--font-mono)',
            padding: '2px 6px',
            background: 'var(--color-surface)',
            border: '1px solid var(--color-border)',
            borderRadius: 'var(--radius-sm)',
          }}>
            {pythonData.total_lines} lines
          </span>
        </div>

        <div style={{
          background: 'var(--color-bg)',
          overflow: 'auto',
          maxHeight: '480px',
          display: 'flex',
          fontSize: '12px',
          fontFamily: 'var(--font-mono)',
          lineHeight: 1.6,
        }}>
          {/* Line Numbers */}
          <div style={{
            padding: '16px 12px',
            textAlign: 'right',
            color: 'var(--color-text-subtle)',
            userSelect: 'none',
            borderRight: '1px solid var(--color-border)',
            background: 'var(--color-surface-secondary)',
            minWidth: '48px',
          }}>
            {lines.map((_, i) => (
              <div key={i}>{i + 1}</div>
            ))}
          </div>

          {/* Python Code */}
          <pre style={{
            padding: '16px 20px',
            margin: 0,
            color: 'var(--color-text)',
            whiteSpace: 'pre',
            overflowX: 'auto',
            flex: 1,
          }}>
            <code>{pythonData.code}</code>
          </pre>
        </div>
      </div>

      {/* Traceability & Tool Explanation Inspector (Section 16) */}
      <div className="app-card" style={{ padding: '20px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '16px' }}>
          <Layers size={16} color="var(--color-primary)" />
          <span style={{ fontSize: '13px', fontWeight: '700', color: 'var(--color-text)', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
            Tool-to-Code Traceability Map
          </span>
        </div>

        {/* Tool Select Pills */}
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px', marginBottom: '16px' }}>
          {pythonData.trace_map.map((entry) => {
            const isSelected = entry.tool_id === selectedToolId;
            return (
              <button
                key={entry.tool_id}
                onClick={() => setSelectedToolId(entry.tool_id)}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px',
                  padding: '6px 12px',
                  borderRadius: 'var(--radius-sm)',
                  border: isSelected ? '1px solid var(--color-primary)' : '1px solid var(--color-border)',
                  background: isSelected ? 'var(--color-primary-subtle)' : 'var(--color-surface-secondary)',
                  color: isSelected ? 'var(--color-primary)' : 'var(--color-text-secondary)',
                  fontSize: '12px',
                  fontWeight: isSelected ? '700' : '500',
                  cursor: 'pointer',
                  transition: 'all 0.12s ease',
                }}
              >
                <span style={{ fontFamily: 'var(--font-mono)' }}>#{entry.tool_id}</span>
                <span>{entry.tool_name || entry.tool_type}</span>
              </button>
            );
          })}
        </div>

        {/* Selected Tool Details Card */}
        {selectedTrace && (
          <div style={{
            background: 'var(--color-surface-secondary)',
            border: '1px solid var(--color-border)',
            borderRadius: 'var(--radius-sm)',
            padding: '16px',
            display: 'flex',
            flexDirection: 'column',
            gap: '12px',
          }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <div style={{ fontSize: '13px', fontWeight: '700', color: 'var(--color-text)' }}>
                Tool #{selectedTrace.tool_id} — {selectedTrace.tool_name} ({selectedTrace.tool_type})
              </div>
              <span style={{
                fontFamily: 'var(--font-mono)',
                fontSize: '11px',
                color: 'var(--color-text-muted)',
                background: 'var(--color-surface)',
                border: '1px solid var(--color-border)',
                padding: '2px 8px',
                borderRadius: 'var(--radius-sm)',
              }}>
                Lines {selectedTrace.start_line}–{selectedTrace.end_line}
              </span>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '12px', fontSize: '12px' }}>
              <div>
                <div style={{ fontWeight: '600', color: 'var(--color-text-muted)', marginBottom: '4px' }}>
                  Alteryx Operation
                </div>
                <div style={{ color: 'var(--color-text)', fontFamily: 'var(--font-mono)' }}>
                  {selectedTrace.description}
                </div>
              </div>

              <div>
                <div style={{ fontWeight: '600', color: 'var(--color-text-muted)', marginBottom: '4px' }}>
                  Python Translation
                </div>
                <div style={{ color: 'var(--color-text)', fontFamily: 'var(--font-mono)' }}>
                  {selectedTrace.pandas_op}
                </div>
              </div>
            </div>

            <div>
              <div style={{ fontWeight: '600', color: 'var(--color-text-muted)', marginBottom: '4px', display: 'flex', alignItems: 'center', gap: '4px' }}>
                <Info size={12} />
                <span>Translation Rationale</span>
              </div>
              <div style={{ color: 'var(--color-text-secondary)', fontSize: '12px' }}>
                {selectedTrace.reason}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
