import React, { useState } from 'react';
import { Copy, Check, Download } from 'lucide-react';

interface JsonViewerProps {
  data: Record<string, any>;
  onDownload?: () => void;
}

export const JsonViewer: React.FC<JsonViewerProps> = ({ data, onDownload }) => {
  const [copied, setCopied] = useState(false);
  const jsonString = JSON.stringify(data, null, 2);

  const handleCopy = () => {
    navigator.clipboard.writeText(jsonString);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="glass-card" style={{ overflow: 'hidden' }}>
      {/* Top action bar */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: '12px 18px',
        background: 'rgba(15, 23, 42, 0.9)',
        borderBottom: '1px solid rgba(51, 65, 85, 0.5)',
      }}>
        <div style={{ fontSize: '12px', fontFamily: 'monospace', color: '#94a3b8' }}>
          workflow.json — canonical intermediate representation
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
            <span>{copied ? 'Copied!' : 'Copy JSON'}</span>
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
                background: 'linear-gradient(135deg, #0284c7 0%, #0369a1 100%)',
                border: 'none',
                color: '#ffffff',
                fontSize: '12px',
                fontWeight: '600',
                cursor: 'pointer',
              }}
            >
              <Download size={14} />
              <span>Download</span>
            </button>
          )}
        </div>
      </div>

      {/* Code Display Area */}
      <pre style={{
        margin: 0,
        padding: '20px 24px',
        fontSize: '12px',
        lineHeight: '1.6',
        color: '#38bdf8',
        background: 'rgba(7, 11, 25, 0.95)',
        overflow: 'auto',
        maxHeight: '650px',
        fontFamily: "'JetBrains Mono', monospace",
      }}>
        <code>{jsonString}</code>
      </pre>
    </div>
  );
};
