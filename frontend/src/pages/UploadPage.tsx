import React, { useState, useRef } from 'react';
import { Upload, FileCode, FileText, Network, Terminal, AlertCircle, Loader2, Workflow } from 'lucide-react';
import { api } from '../api/client';
import { AnalysisOverviewDTO } from '../types/workflow';

interface UploadPageProps {
  onUploadSuccess: (overview: AnalysisOverviewDTO) => void;
}

export const UploadPage: React.FC<UploadPageProps> = ({ onUploadSuccess }) => {
  const [isDragging, setIsDragging] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFile = async (file: File) => {
    setError(null);
    setLoading(true);

    try {
      const overview = await api.uploadWorkflow(file);
      onUploadSuccess(overview);
    } catch (err: any) {
      setError(err.message || 'Failed to analyze workflow file.');
    } finally {
      setLoading(false);
    }
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = () => {
    setIsDragging(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    const file = e.dataTransfer.files[0];
    if (file) {
      handleFile(file);
    }
  };

  const handleFileInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      handleFile(file);
    }
  };

  return (
    <div style={{
      minHeight: '100vh',
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'space-between',
      padding: '40px 24px 32px 24px',
      boxSizing: 'border-box',
    }}>
      {/* Top Header Bar */}
      <header style={{
        width: '100%',
        maxWidth: '1000px',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <div style={{
            width: '36px',
            height: '36px',
            borderRadius: '10px',
            background: 'linear-gradient(135deg, #38bdf8 0%, #3b82f6 100%)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            color: '#0f172a',
          }}>
            <Workflow size={20} />
          </div>
          <span style={{ fontSize: '16px', fontWeight: '700', color: '#f8fafc' }}>
            Alteryx Converter
          </span>
        </div>

        <div style={{ display: 'flex', gap: '8px' }}>
          <span style={{
            padding: '4px 10px',
            borderRadius: '20px',
            background: 'rgba(56, 189, 248, 0.12)',
            border: '1px solid rgba(56, 189, 248, 0.4)',
            color: '#38bdf8',
            fontSize: '11px',
            fontWeight: '600',
            fontFamily: 'monospace',
          }}>
            FastAPI
          </span>
          <span style={{
            padding: '4px 10px',
            borderRadius: '20px',
            background: 'rgba(148, 163, 184, 0.12)',
            border: '1px solid rgba(148, 163, 184, 0.4)',
            color: '#cbd5e1',
            fontSize: '11px',
            fontWeight: '600',
            fontFamily: 'monospace',
          }}>
            v1.0
          </span>
        </div>
      </header>

      {/* Main Hero & Upload Card */}
      <main style={{
        width: '100%',
        maxWidth: '680px',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        textAlign: 'center',
        margin: 'auto 0',
      }}>
        <h1 style={{
          fontSize: '48px',
          fontWeight: '800',
          letterSpacing: '-1.5px',
          lineHeight: '1.1',
          marginBottom: '16px',
          background: 'linear-gradient(180deg, #ffffff 0%, #cbd5e1 100%)',
          WebkitBackgroundClip: 'text',
          WebkitTextFillColor: 'transparent',
        }}>
          From .yxmd<br />to Python
        </h1>

        <p style={{
          fontSize: '15px',
          color: '#94a3b8',
          lineHeight: '1.6',
          maxWidth: '520px',
          marginBottom: '36px',
        }}>
          Upload any Alteryx workflow and instantly get structured JSON, a full Word document, and an executable pandas pipeline.
        </p>

        {/* Drop Zone Box */}
        <div
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          onClick={() => !loading && fileInputRef.current?.click()}
          style={{
            width: '100%',
            padding: '48px 24px',
            borderRadius: '16px',
            border: isDragging ? '2px dashed #38bdf8' : '2px dashed rgba(51, 65, 85, 0.8)',
            background: isDragging ? 'rgba(56, 189, 248, 0.08)' : 'rgba(15, 23, 42, 0.6)',
            backdropFilter: 'blur(8px)',
            cursor: loading ? 'not-allowed' : 'pointer',
            transition: 'all 0.2s ease',
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            gap: '16px',
          }}
        >
          <input
            type="file"
            ref={fileInputRef}
            onChange={handleFileInputChange}
            accept=".yxmd,.yxwz,.xml"
            style={{ display: 'none' }}
          />

          {loading ? (
            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '12px' }}>
              <Loader2 size={36} color="#38bdf8" className="animate-spin" />
              <span style={{ fontSize: '14px', color: '#38bdf8', fontWeight: '600' }}>
                Analyzing workflow statically...
              </span>
            </div>
          ) : (
            <>
              <div style={{
                width: '48px',
                height: '48px',
                borderRadius: '50%',
                background: 'rgba(56, 189, 248, 0.12)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: '#38bdf8',
              }}>
                <Upload size={22} />
              </div>

              <div>
                <div style={{ fontSize: '16px', fontWeight: '700', color: '#f8fafc', marginBottom: '6px' }}>
                  Drop your workflow here
                </div>
                <div style={{ fontSize: '12px', color: '#64748b', fontFamily: 'monospace' }}>
                  .yxmd · .yxwz · .xml
                </div>
              </div>

              <button
                type="button"
                style={{
                  marginTop: '8px',
                  padding: '10px 24px',
                  borderRadius: '8px',
                  background: 'linear-gradient(135deg, #0284c7 0%, #2563eb 100%)',
                  border: 'none',
                  color: '#ffffff',
                  fontSize: '13px',
                  fontWeight: '600',
                  boxShadow: '0 4px 14px rgba(37, 99, 235, 0.4)',
                }}
              >
                Browse files
              </button>
            </>
          )}
        </div>

        {/* Error Alert */}
        {error && (
          <div style={{
            marginTop: '16px',
            width: '100%',
            padding: '12px 16px',
            borderRadius: '8px',
            background: 'rgba(239, 68, 68, 0.12)',
            border: '1px solid rgba(239, 68, 68, 0.4)',
            color: '#f87171',
            fontSize: '13px',
            display: 'flex',
            alignItems: 'center',
            gap: '10px',
            textAlign: 'left',
          }}>
            <AlertCircle size={16} style={{ flexShrink: 0 }} />
            <span>{error}</span>
          </div>
        )}
      </main>

      {/* Bottom Feature Pills */}
      <footer style={{
        width: '100%',
        maxWidth: '900px',
        display: 'flex',
        justifyContent: 'center',
        flexWrap: 'wrap',
        gap: '16px',
      }}>
        {[
          { label: 'DAG Diagram', icon: Network, color: '#38bdf8' },
          { label: 'Word Document', icon: FileText, color: '#a855f7' },
          { label: 'Python Pipeline', icon: Terminal, color: '#4ade80' },
          { label: 'Structured JSON', icon: FileCode, color: '#f59e0b' },
        ].map((pill, i) => {
          const Icon = pill.icon;
          return (
            <div
              key={i}
              className="glass-card"
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                padding: '8px 16px',
                fontSize: '12px',
                fontWeight: '600',
                color: '#cbd5e1',
              }}
            >
              <Icon size={15} color={pill.color} />
              <span>{pill.label}</span>
            </div>
          );
        })}
      </footer>
    </div>
  );
};
