import React, { useState } from 'react';
import { Copy, Check, Download, FileCode } from 'lucide-react';

interface JsonViewerProps {
  data: Record<string, any>;
  onDownload?: () => void;
}

export const JsonViewer: React.FC<JsonViewerProps> = ({ data, onDownload }) => {
  const [copied, setCopied] = useState(false);
  const jsonString = JSON.stringify(data, null, 2);
  const lines = jsonString.split('\n');

  const handleCopy = () => {
    navigator.clipboard.writeText(jsonString);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="app-card" style={{ overflow: 'hidden' }}>
      {/* Editor Toolbar */}
      <div style={{
        padding: '10px 16px',
        borderBottom: '1px solid var(--color-border)',
        background: 'var(--color-surface-secondary)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <FileCode size={15} color="var(--color-primary)" />
          <span style={{ fontSize: '13px', fontWeight: '700', color: 'var(--color-text)' }}>
            workflow.json
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
            {lines.length} lines · {(jsonString.length / 1024).toFixed(1)} KB
          </span>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <button
            onClick={handleCopy}
            className="btn-secondary"
            style={{ padding: '6px 12px', fontSize: '12px' }}
          >
            {copied ? <Check size={13} color="var(--color-success)" /> : <Copy size={13} />}
            <span>{copied ? 'Copied' : 'Copy JSON'}</span>
          </button>

          {onDownload && (
            <button
              onClick={onDownload}
              className="btn-secondary"
              style={{ padding: '6px 12px', fontSize: '12px' }}
            >
              <Download size={13} />
              <span>Download</span>
            </button>
          )}
        </div>
      </div>

      {/* Editor Body with Line Numbers */}
      <div style={{
        background: 'var(--color-bg)',
        overflow: 'auto',
        maxHeight: '650px',
        display: 'flex',
        alignItems: 'flex-start',
        fontSize: '12px',
        fontFamily: 'var(--font-mono)',
        lineHeight: 1.6,
      }}>
        {/* Line Numbers Gutter */}
        <div style={{
          padding: '16px 12px',
          textAlign: 'right',
          color: 'var(--color-text-subtle)',
          userSelect: 'none',
          borderRight: '1px solid var(--color-border)',
          background: 'var(--color-surface-secondary)',
          minWidth: '48px',
          flexShrink: 0,
          boxSizing: 'border-box',
        }}>
          {lines.map((_, i) => (
            <div key={i} style={{ height: '1.6em', lineHeight: '1.6em' }}>{i + 1}</div>
          ))}
        </div>

        {/* Code Content */}
        <pre style={{
          padding: '16px 20px',
          margin: 0,
          color: 'var(--color-text)',
          whiteSpace: 'pre',
          overflowX: 'auto',
          flex: 1,
          fontFamily: 'inherit',
          fontSize: 'inherit',
          lineHeight: '1.6',
        }}>
          <code>
            {lines.map((line, i) => (
              <div key={i} style={{ height: '1.6em', lineHeight: '1.6em' }}>
                {line || ' '}
              </div>
            ))}
          </code>
        </pre>
      </div>
    </div>
  );
};
