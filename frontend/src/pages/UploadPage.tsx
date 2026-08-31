import React, { useState, useRef } from 'react';
import { Upload, AlertCircle, Sun, Moon, FolderUp, Files } from 'lucide-react';
import { api } from '../api/client';
import { AnalysisOverviewDTO } from '../types/workflow';
import { PortfolioOverviewDTO } from '../types/portfolio';
import { useTheme } from '../context/ThemeContext';
import { AnalysisLoadingScreen } from '../components/AnalysisLoadingScreen';

interface UploadPageProps {
  onUploadSuccess: (result: AnalysisOverviewDTO | PortfolioOverviewDTO) => void;
}

const SUPPORTED_EXTS = ['.yxmd', '.yxwz', '.xml', '.zip', '.yxzp'];

async function getFilesFromDataTransfer(dataTransfer: DataTransfer): Promise<{ file: File; path: string }[]> {
  const items = dataTransfer.items;
  if (!items || items.length === 0) {
    return Array.from(dataTransfer.files).map((f) => ({ file: f, path: f.name }));
  }

  const result: { file: File; path: string }[] = [];
  const queue: { entry: any; path: string }[] = [];

  for (let i = 0; i < items.length; i++) {
    const item = items[i];
    const entry = item.webkitGetAsEntry ? item.webkitGetAsEntry() : null;
    if (entry) {
      queue.push({ entry, path: entry.name });
    } else {
      const file = item.getAsFile();
      if (file) {
        result.push({ file, path: file.name });
      }
    }
  }

  while (queue.length > 0) {
    const { entry, path } = queue.shift()!;
    if (entry.isFile) {
      try {
        const file: File = await new Promise((resolve, reject) => entry.file(resolve, reject));
        result.push({ file, path });
      } catch (e) {
        console.warn('Could not read file entry', entry, e);
      }
    } else if (entry.isDirectory) {
      try {
        const reader = entry.createReader();
        const entries: any[] = await new Promise((resolve, reject) => reader.readEntries(resolve, reject));
        for (const child of entries) {
          queue.push({ entry: child, path: `${path}/${child.name}` });
        }
      } catch (e) {
        console.warn('Could not read directory entry', entry, e);
      }
    }
  }

  return result;
}

export const UploadPage: React.FC<UploadPageProps> = ({ onUploadSuccess }) => {
  const [isDragging, setIsDragging] = useState(false);
  const [loading, setLoading] = useState(false);
  const [analyzingFileName, setAnalyzingFileName] = useState<string | undefined>(undefined);
  const [error, setError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const folderInputRef = useRef<HTMLInputElement>(null);
  const { theme, toggleTheme } = useTheme();

  const handleFiles = async (fileEntries: { file: File; path: string }[]) => {
    setError(null);
    if (!fileEntries || fileEntries.length === 0) return;

    // Filter valid workflow candidates
    const valid = fileEntries.filter(({ file }) => {
      const ext = `.${file.name.split('.').pop()?.toLowerCase()}`;
      return SUPPORTED_EXTS.includes(ext);
    });

    if (valid.length === 0) {
      setError('No valid Alteryx workflow files (.yxmd, .yxwz, .xml, .zip) found in the selected files or folder.');
      return;
    }

    setLoading(true);

    try {
      if (valid.length === 1 && !valid[0].file.name.toLowerCase().endsWith('.zip')) {
        // Case A / D: Single YXMD workflow -> existing single-workflow analysis
        setAnalyzingFileName(valid[0].file.name);
        const overview = await api.uploadWorkflow(valid[0].file);
        onUploadSuccess(overview);
      } else {
        // Case B / C: Multiple workflows or ZIP package -> Portfolio mode
        setAnalyzingFileName(`Analyzing portfolio (${valid.length} workflow files)...`);
        const files = valid.map((v) => v.file);
        const paths = valid.map((v) => v.path);
        const result = await api.uploadPortfolio(files, paths);
        onUploadSuccess(result);
      }
    } catch (err: any) {
      setError(err.message || 'Analysis failed. Please check the workflow files and try again.');
    } finally {
      setLoading(false);
      setAnalyzingFileName(undefined);
    }
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    if (!loading) {
      setIsDragging(true);
    }
  };

  const handleDragLeave = () => {
    setIsDragging(false);
  };

  const handleDrop = async (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    if (loading) return;

    const fileEntries = await getFilesFromDataTransfer(e.dataTransfer);
    handleFiles(fileEntries);
  };

  const handleFileInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (loading) return;
    const files = e.target.files;
    if (files && files.length > 0) {
      const entries = Array.from(files).map((f) => ({ file: f, path: f.name }));
      handleFiles(entries);
    }
  };

  const handleFolderInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (loading) return;
    const files = e.target.files;
    if (files && files.length > 0) {
      const entries = Array.from(files).map((f) => ({
        file: f,
        path: (f as any).webkitRelativePath || f.name,
      }));
      handleFiles(entries);
    }
  };

  return (
    <div style={{
      minHeight: '100vh',
      display: 'flex',
      flexDirection: 'column',
      background: 'var(--color-bg)',
      position: 'relative',
    }}>
      {/* Full-page Dedicated Loading Screen */}
      {loading && <AnalysisLoadingScreen fileName={analyzingFileName} />}
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
            ETL Intelligence & Migration - Alteryx Workflows
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
            marginBottom: '4px',
          }}>
            ETL Intelligence & Migration
          </h1>
          <h2 style={{
            fontSize: '16px',
            fontWeight: '600',
            color: 'var(--color-text-secondary)',
            marginBottom: '10px',
          }}>
            Alteryx workflows
          </h2>
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
            accept=".yxmd,.yxwz,.xml,.zip,.yxzp"
            multiple
            style={{ display: 'none' }}
          />

          <input
            type="file"
            ref={folderInputRef}
            onChange={handleFolderInputChange}
            {...({ webkitdirectory: '', directory: '' } as any)}
            style={{ display: 'none' }}
          />

          <div style={{
            width: '48px',
            height: '48px',
            borderRadius: '50%',
            background: 'var(--color-surface-secondary)',
            border: '1px solid var(--color-border)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            color: 'var(--color-primary)',
          }}>
            <Upload size={22} />
          </div>

          <div>
            <div style={{ fontSize: '16px', fontWeight: '700', color: 'var(--color-text)', marginBottom: '4px' }}>
              Drop workflow file(s) or folder here
            </div>
            <div style={{ fontSize: '12px', color: 'var(--color-text-muted)', maxWidth: '420px', margin: '0 auto' }}>
              Select a single workflow file, multiple workflows, or an entire folder of workflows for portfolio rationalisation
            </div>
          </div>

          <div style={{ display: 'flex', gap: '12px', flexWrap: 'wrap', justifyContent: 'center' }}>
            <button
              type="button"
              className="btn-primary"
              onClick={(e) => {
                e.stopPropagation();
                fileInputRef.current?.click();
              }}
              style={{ padding: '8px 18px', fontSize: '13px', display: 'inline-flex', alignItems: 'center', gap: '6px' }}
            >
              <Files size={15} /> Choose File(s)
            </button>

            <button
              type="button"
              onClick={(e) => {
                e.stopPropagation();
                folderInputRef.current?.click();
              }}
              style={{
                padding: '8px 18px',
                fontSize: '13px',
                fontWeight: '600',
                borderRadius: 'var(--radius-sm)',
                border: '1px solid var(--color-border)',
                background: 'var(--color-surface-secondary)',
                color: 'var(--color-text)',
                cursor: 'pointer',
                display: 'inline-flex',
                alignItems: 'center',
                gap: '6px',
              }}
            >
              <FolderUp size={15} /> Choose Folder
            </button>
          </div>

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
            flexWrap: 'wrap',
          }}>
            <span style={{ fontSize: '11px', color: 'var(--color-text-muted)', fontWeight: '600', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
              Supported formats:
            </span>
            {['.yxmd', '.yxwz', '.xml', '.zip / folder'].map((fmt) => (
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
