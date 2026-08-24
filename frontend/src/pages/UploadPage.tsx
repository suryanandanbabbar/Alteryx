import React, { useState, useRef } from 'react';
import { Upload, AlertCircle, Loader2, Sun, Moon } from 'lucide-react';
import { api } from '../api/client';
import { AnalysisOverviewDTO } from '../types/workflow';
import { useTheme } from '../context/ThemeContext';

interface UploadPageProps {
  onUploadSuccess: (overview: AnalysisOverviewDTO) => void;
}

export const UploadPage: React.FC<UploadPageProps> = ({ onUploadSuccess }) => {
  const [isDragging, setIsDragging] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const { theme, toggleTheme } = useTheme();

  const handleFile = async (file: File) => {
    setError(null);
    setLoading(true);

    try {
      const overview = await api.uploadWorkflow(file);
      onUploadSuccess(overview);
    } catch (err: any) {
      setError(err.message || 'Workflow could not be analyzed. Please check the file and try again.');
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
      background: 'var(--color-bg)',
    }}>
      {/* Top Header Bar */}
      <header style={{
        height: '56px',
        borderBottom: '1px solid var(--color-border)',
        background: 'var(--color-surface)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: '0 32px',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <div style={{
            width: '28px',
            height: '28px',
            minWidth: '28px',
            borderRadius: 'var(--radius-sm)',
            background: 'var(--color-primary)',
            color: '#ffffff',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            fontWeight: '800',
            fontSize: '13px',
          }}>
            E
          </div>
          <span style={{ fontSize: '14px', fontWeight: '800', color: 'var(--color-text)' }}>
            ETL Intelligence & Migration - Alteryx Workflow
          </span>
        </div>

        <button
          onClick={toggleTheme}
          aria-label={`Switch to ${theme === 'light' ? 'dark' : 'light'} theme`}
          title={`Switch to ${theme === 'light' ? 'dark' : 'light'} theme`}
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            width: '32px',
            height: '32px',
            borderRadius: 'var(--radius-sm)',
            border: '1px solid var(--color-border)',
            background: 'var(--color-surface)',
            color: 'var(--color-text-secondary)',
            cursor: 'pointer',
            transition: 'all 0.15s ease',
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.backgroundColor = 'var(--color-surface-hover)';
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.backgroundColor = 'var(--color-surface)';
          }}
        >
          {theme === 'light' ? <Moon size={15} /> : <Sun size={15} />}
        </button>
      </header>

      {/* Main Container */}
      <main style={{
        flex: 1,
        maxWidth: '680px',
        width: '100%',
        margin: '0 auto',
        padding: '60px 24px',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
      }}>
        {/* Title & Introduction */}
        <div style={{ textAlign: 'center', marginBottom: '32px' }}>
          <h1 style={{
            fontSize: '28px',
            fontWeight: '800',
            letterSpacing: '-0.5px',
            color: 'var(--color-text)',
            marginBottom: '8px',
          }}>
            Analyze Alteryx Workflow
          </h1>
          <p style={{
            fontSize: '14px',
            color: 'var(--color-text-muted)',
            lineHeight: 1.5,
            maxWidth: '520px',
            margin: '0 auto',
          }}>
            Inspect workflow topology, tool configurations, data lineage, and generated Python transformations.
          </p>
        </div>

        {/* Upload Drop Zone Card */}
        <div
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          onClick={() => !loading && fileInputRef.current?.click()}
          className="app-card"
          style={{
            width: '100%',
            padding: '40px 24px',
            textAlign: 'center',
            cursor: loading ? 'not-allowed' : 'pointer',
            borderColor: isDragging ? 'var(--color-primary)' : 'var(--color-border)',
            background: isDragging ? 'var(--color-primary-subtle)' : 'var(--color-surface)',
            borderStyle: 'dashed',
            borderWidth: '2px',
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            gap: '16px',
            transition: 'all 0.15s ease',
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
            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '12px', padding: '16px 0' }}>
              <Loader2 size={32} color="var(--color-primary)" className="animate-spin" />
              <div style={{ fontSize: '14px', fontWeight: '600', color: 'var(--color-text)' }}>
                Analyzing workflow...
              </div>
              <div style={{ fontSize: '12px', color: 'var(--color-text-muted)' }}>
                Parsing graph topology and translating tool operations
              </div>
            </div>
          ) : (
            <>
              <div style={{
                width: '44px',
                height: '44px',
                borderRadius: '50%',
                background: 'var(--color-surface-secondary)',
                border: '1px solid var(--color-border)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: 'var(--color-primary)',
              }}>
                <Upload size={20} />
              </div>

              <div>
                <div style={{ fontSize: '15px', fontWeight: '700', color: 'var(--color-text)', marginBottom: '4px' }}>
                  Drop workflow file here, or choose file
                </div>
                <div style={{ fontSize: '12px', color: 'var(--color-text-muted)' }}>
                  Select a workflow file from your computer
                </div>
              </div>

              <button
                type="button"
                className="btn-primary"
                style={{ padding: '8px 20px', fontSize: '13px' }}
              >
                Choose file
              </button>

              {/* Supported Formats */}
              <div style={{
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                marginTop: '8px',
                paddingTop: '16px',
                borderTop: '1px solid var(--color-border-subtle)',
                width: '100%',
                justifyContent: 'center',
              }}>
                <span style={{ fontSize: '11px', color: 'var(--color-text-muted)', fontWeight: '600', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                  Supported formats:
                </span>
                {['.yxmd', '.yxwz', '.xml'].map((fmt) => (
                  <span
                    key={fmt}
                    style={{
                      fontFamily: 'var(--font-mono)',
                      fontSize: '11px',
                      fontWeight: '600',
                      color: 'var(--color-text-secondary)',
                      background: 'var(--color-surface-secondary)',
                      border: '1px solid var(--color-border)',
                      padding: '2px 6px',
                      borderRadius: 'var(--radius-sm)',
                    }}
                  >
                    {fmt}
                  </span>
                ))}
              </div>
            </>
          )}
        </div>

        {/* Error State */}
        {error && (
          <div style={{
            marginTop: '16px',
            width: '100%',
            padding: '12px 16px',
            borderRadius: 'var(--radius-sm)',
            background: 'var(--color-error-subtle)',
            border: '1px solid rgba(220, 38, 38, 0.3)',
            color: 'var(--color-error)',
            fontSize: '13px',
            display: 'flex',
            alignItems: 'center',
            gap: '10px',
          }}>
            <AlertCircle size={16} style={{ flexShrink: 0 }} />
            <div style={{ flex: 1 }}>{error}</div>
          </div>
        )}
      </main>
    </div>
  );
};
