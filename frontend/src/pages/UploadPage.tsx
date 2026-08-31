import React, { useState, useRef, useEffect } from 'react';
import { Upload, AlertCircle, Sun, Moon, ChevronDown, FileCode, FolderUp } from 'lucide-react';
import { api } from '../api/client';
import { AnalysisOverviewDTO } from '../types/workflow';
import { PortfolioOverviewDTO } from '../types/portfolio';
import { useTheme } from '../context/ThemeContext';
import { AnalysisLoadingScreen } from '../components/AnalysisLoadingScreen';

interface UploadPageProps {
  onUploadSuccess: (result: AnalysisOverviewDTO | PortfolioOverviewDTO) => void;
}

export const SUPPORTED_EXTENSIONS = ['.yxmd', '.yxwz', '.xml'] as const;

export interface NormalizedEntry {
  file: File;
  path: string;
}

export interface NormalizationResult {
  validWorkflows: NormalizedEntry[];
  ignoredCount: number;
  totalFiles: number;
}

/**
 * Normalise and filter user selection to supported workflow files (.yxmd, .yxwz, .xml).
 * Extension matching is case-insensitive.
 * Relative paths are preserved.
 */
export function normalizeSelection(entries: NormalizedEntry[]): NormalizationResult {
  const seenPaths = new Set<string>();
  const validWorkflows: NormalizedEntry[] = [];
  let ignoredCount = 0;

  for (const entry of entries) {
    const fname = entry.file.name;
    // Skip macOS metadata and hidden files
    if (fname.startsWith('.') || entry.path.includes('__MACOSX')) {
      ignoredCount++;
      continue;
    }

    const ext = `.${fname.split('.').pop()?.toLowerCase()}`;
    if (SUPPORTED_EXTENSIONS.includes(ext as any)) {
      const key = entry.path || fname;
      if (!seenPaths.has(key)) {
        seenPaths.add(key);
        validWorkflows.push(entry);
      }
    } else {
      ignoredCount++;
    }
  }

  return {
    validWorkflows,
    ignoredCount,
    totalFiles: entries.length,
  };
}

/**
 * Recursively discover files and relative paths from DataTransferItemList (drag and drop).
 */
async function getFilesFromDataTransfer(dataTransfer: DataTransfer): Promise<NormalizedEntry[]> {
  const items = dataTransfer.items;
  if (!items || items.length === 0) {
    return Array.from(dataTransfer.files).map((f) => ({ file: f, path: f.name }));
  }

  const result: NormalizedEntry[] = [];
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

/**
 * Recursively scan a FileSystemDirectoryHandle using the File System Access API.
 */
async function scanDirectoryHandle(handle: any, currentPath: string): Promise<NormalizedEntry[]> {
  const entries: NormalizedEntry[] = [];
  for await (const item of handle.values()) {
    if (item.kind === 'file') {
      try {
        const file: File = await item.getFile();
        entries.push({
          file,
          path: currentPath ? `${currentPath}/${file.name}` : file.name,
        });
      } catch (err) {
        console.warn('Could not read file from directory handle', item.name, err);
      }
    } else if (item.kind === 'directory') {
      const subPath = currentPath ? `${currentPath}/${item.name}` : item.name;
      const subEntries = await scanDirectoryHandle(item, subPath);
      entries.push(...subEntries);
    }
  }
  return entries;
}

export const UploadPage: React.FC<UploadPageProps> = ({ onUploadSuccess }) => {
  const [isDragging, setIsDragging] = useState(false);
  const [loading, setLoading] = useState(false);
  const [analyzingFileName, setAnalyzingFileName] = useState<string | undefined>(undefined);
  const [error, setError] = useState<string | null>(null);
  const [menuOpen, setMenuOpen] = useState(false);

  const fileInputRef = useRef<HTMLInputElement>(null);
  const folderInputRef = useRef<HTMLInputElement>(null);
  const menuRef = useRef<HTMLDivElement>(null);
  const { theme, toggleTheme } = useTheme();

  // Close dropdown on click outside
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setMenuOpen(false);
      }
    };
    if (menuOpen) {
      document.addEventListener('mousedown', handleClickOutside);
    }
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [menuOpen]);

  // Ensure webkitdirectory is attached to DOM node for directory input
  useEffect(() => {
    if (folderInputRef.current) {
      folderInputRef.current.setAttribute('webkitdirectory', '');
      folderInputRef.current.setAttribute('directory', '');
      (folderInputRef.current as any).webkitdirectory = true;
    }
  }, []);

  /**
   * Unified ingestion pipeline for all selection and drop interactions.
   */
  const processEntries = async (entries: NormalizedEntry[]) => {
    setError(null);
    if (!entries || entries.length === 0) return;

    const { validWorkflows } = normalizeSelection(entries);

    // Rule 10: Empty folder / zero valid workflows
    if (validWorkflows.length === 0) {
      setError('No supported Alteryx workflow files were found in this folder. Supported formats: .yxmd, .yxwz, .xml');
      return;
    }

    setLoading(true);

    try {
      if (validWorkflows.length === 1) {
        // Rule 5 & 6: Single workflow (file or 1-workflow folder) -> existing single-workflow pipeline
        setAnalyzingFileName(validWorkflows[0].file.name);
        const overview = await api.uploadWorkflow(validWorkflows[0].file);
        onUploadSuccess(overview);
      } else {
        // Rule 7 & 8: Multiple workflows -> portfolio pipeline
        setAnalyzingFileName(`Analyzing portfolio (${validWorkflows.length} workflows)...`);
        const files = validWorkflows.map((v) => v.file);
        const paths = validWorkflows.map((v) => v.path);
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

  /**
   * Trigger folder selection using File System Access API (when supported) or webkitdirectory fallback.
   */
  const handleSelectFolder = async () => {
    setMenuOpen(false);
    if ('showDirectoryPicker' in window) {
      try {
        const dirHandle = await (window as any).showDirectoryPicker();
        const entries = await scanDirectoryHandle(dirHandle, dirHandle.name);
        await processEntries(entries);
        return;
      } catch (err: any) {
        if (err.name === 'AbortError') {
          return; // User cancelled picker
        }
        console.warn('showDirectoryPicker failed, falling back to input:', err);
      }
    }

    // Fallback: trigger hidden directory input
    if (folderInputRef.current) {
      folderInputRef.current.value = '';
      folderInputRef.current.click();
    }
  };

  /**
   * Trigger file selection using native file input.
   */
  const handleSelectFiles = () => {
    setMenuOpen(false);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
      fileInputRef.current.click();
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
    processEntries(fileEntries);
  };

  const handleFileInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (loading) return;
    const files = e.target.files;
    if (files && files.length > 0) {
      const entries = Array.from(files).map((f) => ({ file: f, path: f.name }));
      processEntries(entries);
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
      processEntries(entries);
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

      {/* Top Brand Header */}
      <header style={{
        height: '56px',
        borderBottom: '1px solid var(--color-border)',
        background: 'var(--color-surface)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: '0 32px',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span style={{
            fontSize: '12px',
            fontWeight: '600',
            color: 'var(--color-text-muted)',
            letterSpacing: '0.3px',
          }}>
            ETL Intelligence & Migration
          </span>
        </div>

        <button
          onClick={toggleTheme}
          style={{
            background: 'none',
            border: 'none',
            color: 'var(--color-text-secondary)',
            cursor: 'pointer',
            padding: '6px',
            borderRadius: 'var(--radius-sm)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            transition: 'color 0.15s ease',
          }}
          title={theme === 'dark' ? 'Switch to Light Mode' : 'Switch to Dark Mode'}
        >
          {theme === 'dark' ? <Sun size={16} /> : <Moon size={16} />}
        </button>
      </header>

      {/* Main Container */}
      <main style={{
        flex: 1,
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '40px 24px',
        maxWidth: '680px',
        margin: '0 auto',
        width: '100%',
        boxSizing: 'border-box',
      }}>
        {/* Header Block */}
        <div style={{ textAlign: 'center', marginBottom: '32px' }}>
          <div style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: '6px',
            padding: '4px 10px',
            borderRadius: '12px',
            background: 'var(--color-primary-subtle)',
            color: 'var(--color-primary)',
            fontSize: '12px',
            fontWeight: '600',
            marginBottom: '16px',
          }}>
            ETL Rationalisation
          </div>
          <h1 style={{
            fontSize: '32px',
            fontWeight: '800',
            color: 'var(--color-text)',
            letterSpacing: '-0.5px',
            marginBottom: '8px',
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
          onClick={() => {
            if (!loading && !menuOpen) {
              setMenuOpen(true);
            }
          }}
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
            position: 'relative',
          }}
        >
          {/* Hidden file input for single/multi-file picking */}
          <input
            type="file"
            ref={fileInputRef}
            onChange={handleFileInputChange}
            accept=".yxmd,.yxwz,.xml,.YXMD,.YXWZ,.XML"
            multiple
            style={{ display: 'none' }}
          />

          {/* Hidden directory input with guaranteed webkitdirectory attribute */}
          <input
            type="file"
            ref={folderInputRef}
            onChange={handleFolderInputChange}
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
              Drop workflow file(s) or folder here, or click Choose
            </div>
            <div style={{ fontSize: '12px', color: 'var(--color-text-muted)', maxWidth: '420px', margin: '0 auto' }}>
              Select a workflow file (.yxmd, .yxwz, .xml) or an entire folder of workflows
            </div>
          </div>

          {/* Single Primary "Choose" Button with Unified Selection */}
          <div style={{ position: 'relative', display: 'inline-block' }}>
            <button
              type="button"
              className="btn-primary"
              onClick={(e) => {
                e.stopPropagation();
                setMenuOpen((prev) => !prev);
              }}
              style={{
                padding: '9px 24px',
                fontSize: '14px',
                fontWeight: '600',
                display: 'inline-flex',
                alignItems: 'center',
                gap: '8px',
                cursor: 'pointer',
              }}
            >
              Choose <ChevronDown size={14} style={{ transform: menuOpen ? 'rotate(180deg)' : 'none', transition: 'transform 0.15s ease' }} />
            </button>

            {menuOpen && (
              <div
                ref={menuRef}
                style={{
                  position: 'absolute',
                  top: 'calc(100% + 8px)',
                  left: '50%',
                  transform: 'translateX(-50%)',
                  background: 'var(--color-surface)',
                  border: '1px solid var(--color-border)',
                  borderRadius: 'var(--radius-sm)',
                  boxShadow: '0 8px 24px rgba(0,0,0,0.15)',
                  minWidth: '220px',
                  padding: '6px',
                  zIndex: 50,
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '2px',
                }}
                onClick={(e) => e.stopPropagation()}
              >
                <button
                  type="button"
                  onClick={handleSelectFiles}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '10px',
                    padding: '8px 12px',
                    borderRadius: '4px',
                    border: 'none',
                    background: 'transparent',
                    color: 'var(--color-text)',
                    fontSize: '13px',
                    fontWeight: '500',
                    cursor: 'pointer',
                    textAlign: 'left',
                    width: '100%',
                  }}
                  onMouseEnter={(e) => (e.currentTarget.style.background = 'var(--color-surface-secondary)')}
                  onMouseLeave={(e) => (e.currentTarget.style.background = 'transparent')}
                >
                  <FileCode size={16} color="var(--color-primary)" />
                  <div>
                    <div style={{ fontWeight: '600' }}>Workflow File(s)</div>
                    <div style={{ fontSize: '11px', color: 'var(--color-text-muted)' }}>.yxmd, .yxwz, or .xml</div>
                  </div>
                </button>

                <button
                  type="button"
                  onClick={handleSelectFolder}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '10px',
                    padding: '8px 12px',
                    borderRadius: '4px',
                    border: 'none',
                    background: 'transparent',
                    color: 'var(--color-text)',
                    fontSize: '13px',
                    fontWeight: '500',
                    cursor: 'pointer',
                    textAlign: 'left',
                    width: '100%',
                  }}
                  onMouseEnter={(e) => (e.currentTarget.style.background = 'var(--color-surface-secondary)')}
                  onMouseLeave={(e) => (e.currentTarget.style.background = 'transparent')}
                >
                  <FolderUp size={16} color="var(--color-primary)" />
                  <div>
                    <div style={{ fontWeight: '600' }}>Workflow Folder</div>
                    <div style={{ fontSize: '11px', color: 'var(--color-text-muted)' }}>Scan folder for workflows</div>
                  </div>
                </button>
              </div>
            )}
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
            {SUPPORTED_EXTENSIONS.map((fmt) => (
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
