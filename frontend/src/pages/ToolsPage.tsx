import React, { useEffect, useState, useMemo } from 'react';
import { api } from '../api/client';
import { DiagramDTO } from '../types/workflow';
import { PortfolioOverviewDTO } from '../types/portfolio';
import { NodeDetails } from '../components/NodeDetails';
import { DocumentGenerationModal, ReportType } from '../components/DocumentGenerationModal';
import { Loader2, AlertCircle, Search, X, Download, ArrowRight, Wrench } from 'lucide-react';

interface ToolsPageProps {
  analysisId: string;
  selectedToolId?: number | null;
  portfolio?: PortfolioOverviewDTO | null;
  selectedToolType?: string | null;
  onSelectToolType?: (toolType: string | null) => void;
  onNavigateToPortfolio?: () => void;
}

export const ToolsPage: React.FC<ToolsPageProps> = ({
  analysisId,
  selectedToolId,
  portfolio,
  selectedToolType: selectedToolTypeProp,
  onSelectToolType,
  onNavigateToPortfolio,
}) => {
  const [diagramData, setDiagramData] = useState<DiagramDTO | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [localSelectedToolType, setLocalSelectedToolType] = useState<string | null>(null);
  const [generatingReport, setGeneratingReport] = useState<ReportType | null>(null);
  const [downloadError, setDownloadError] = useState<string | null>(null);

  // Controlled or local tool type filter
  const activeToolType = selectedToolTypeProp !== undefined ? selectedToolTypeProp : localSelectedToolType;

  useEffect(() => {
    let mounted = true;
    api.getDiagram(analysisId)
      .then((data) => {
        if (mounted) {
          setDiagramData(data);
          setLoading(false);
        }
      })
      .catch((err) => {
        if (mounted) {
          setError(err.message || 'Failed to load tool configurations.');
          setLoading(false);
        }
      });

    return () => {
      mounted = false;
    };
  }, [analysisId]);

  const handleDownloadToolSpecifications = async () => {
    if (generatingReport) return;
    setDownloadError(null);
    setGeneratingReport('tool-specifications');

    try {
      await api.downloadFile(analysisId, 'tool-specifications');
    } catch (err: any) {
      setDownloadError(err.message || 'Failed to download tool specifications. Please try again.');
    } finally {
      setGeneratingReport(null);
    }
  };

  // Group tool nodes by tool_type and compute deterministic occurrence counts
  const toolUsageStats = useMemo(() => {
    if (!diagramData?.nodes) return [];
    const counts: Record<string, number> = {};
    diagramData.nodes.forEach((n) => {
      const type = n.tool_type || 'Unknown';
      counts[type] = (counts[type] || 0) + 1;
    });
    return Object.entries(counts)
      .map(([toolType, count]) => ({ toolType, count }))
      .sort((a, b) => b.count - a.count || a.toolType.localeCompare(b.toolType));
  }, [diagramData?.nodes]);

  // Handle selecting or toggling a tool type
  const handleSelectToolType = (toolType: string | null) => {
    const nextType = (!toolType || toolType === 'ALL' || toolType === activeToolType) ? null : toolType;
    setLocalSelectedToolType(nextType);
    if (onSelectToolType) {
      onSelectToolType(nextType);
    }
  };

  // Filter nodes client-side by activeToolType and search query
  const filteredNodes = useMemo(() => {
    if (!diagramData?.nodes) return [];
    const q = searchQuery.trim().toLowerCase();
    const activeTypeLower = activeToolType && activeToolType !== 'ALL' ? activeToolType.toLowerCase() : null;

    return diagramData.nodes.filter((node) => {
      // 1. Tool Type filter
      if (activeTypeLower && (node.tool_type || '').toLowerCase() !== activeTypeLower) {
        return false;
      }

      // 2. Search query filter
      if (!q) return true;

      const nameMatch = node.name?.toLowerCase().includes(q);
      const typeMatch = node.tool_type?.toLowerCase().includes(q);
      const summaryMatch = node.summary?.toLowerCase().includes(q);
      const annotationMatch = node.annotation?.toLowerCase().includes(q);
      const containerMatch = node.container_name?.toLowerCase().includes(q);
      const idMatch = `#${node.tool_id}`.includes(q) || String(node.tool_id) === q;

      return nameMatch || typeMatch || summaryMatch || annotationMatch || containerMatch || idMatch;
    });
  }, [diagramData?.nodes, searchQuery, activeToolType]);

  const totalCount = diagramData?.nodes?.length ?? 0;
  const filteredCount = filteredNodes.length;
  const isFiltering = searchQuery.trim() !== '' || (activeToolType !== null && activeToolType !== 'ALL');

  // Count matching workflows across the portfolio if portfolio context is present
  const matchingPortfolioWorkflowsCount = useMemo(() => {
    if (!portfolio || !activeToolType || activeToolType === 'ALL') return 0;
    const target = activeToolType.toLowerCase();
    return portfolio.workflows.filter((w) =>
      w.tool_types && w.tool_types.some((t) => t.toLowerCase() === target)
    ).length;
  }, [portfolio, activeToolType]);

  if (loading) {
    return (
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', minHeight: '300px', gap: '12px' }}>
        <Loader2 size={24} color="var(--color-primary)" className="animate-spin" />
        <span style={{ color: 'var(--color-text-muted)', fontSize: '13px' }}>Loading tool specifications...</span>
      </div>
    );
  }

  if (error || !diagramData) {
    return (
      <div style={{
        padding: '16px',
        borderRadius: 'var(--radius-sm)',
        background: 'var(--color-error-subtle)',
        border: '1px solid rgba(220, 38, 38, 0.3)',
        color: 'var(--color-error)',
        fontSize: '13px',
        display: 'flex',
        alignItems: 'center',
        gap: '10px',
      }}>
        <AlertCircle size={16} />
        <span>Failed to load tools: {error}</span>
      </div>
    );
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px', maxWidth: '1400px', width: '100%', position: 'relative' }}>
      {/* Document Generation Loading Modal */}
      {generatingReport && <DocumentGenerationModal type={generatingReport} />}

      {/* Error Alert */}
      {downloadError && (
        <div style={{
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
          <div style={{ flex: 1 }}>{downloadError}</div>
        </div>
      )}

      {/* Page Header with Prominent Metric Treatment */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        flexWrap: 'wrap',
        gap: '16px',
        paddingBottom: '4px',
      }}>
        <div>
          <div style={{
            fontSize: '11px',
            fontWeight: '700',
            letterSpacing: '1px',
            color: 'var(--color-primary)',
            textTransform: 'uppercase',
            marginBottom: '4px',
          }}>
            Tools &amp; Configuration
          </div>
          <h2 style={{
            fontSize: '22px',
            fontWeight: '800',
            color: 'var(--color-text)',
            letterSpacing: '-0.3px',
            margin: 0,
          }}>
            Tool Specifications &amp; Configuration
          </h2>
        </div>

        {/* Header Right: Prominent Tool Count Metric + Download Button */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '14px', flexWrap: 'wrap' }}>
          {/* Prominent Metric Display */}
          <div style={{
            display: 'flex',
            alignItems: 'center',
            gap: '12px',
            background: 'var(--color-surface)',
            border: isFiltering ? '1px solid #38bdf8' : '1px solid var(--color-border)',
            boxShadow: isFiltering ? '0 0 14px rgba(56, 189, 248, 0.15)' : '0 2px 6px rgba(0, 0, 0, 0.1)',
            borderRadius: '8px',
            padding: '8px 16px',
            transition: 'all 0.2s ease',
          }}>
            <div style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              width: '32px',
              height: '32px',
              borderRadius: '6px',
              background: isFiltering ? 'rgba(56, 189, 248, 0.15)' : 'var(--color-surface-secondary)',
              color: isFiltering ? '#38bdf8' : 'var(--color-text-muted)',
            }}>
              <Wrench size={16} />
            </div>

            <div style={{ display: 'flex', flexDirection: 'column' }}>
              <div style={{ display: 'flex', alignItems: 'baseline', gap: '5px' }}>
                <span style={{
                  fontSize: '24px',
                  fontWeight: '800',
                  color: isFiltering ? '#38bdf8' : 'var(--color-text)',
                  fontFamily: 'var(--font-mono, monospace)',
                  lineHeight: '1',
                  fontFeatureSettings: '"tnum"',
                }}>
                  {isFiltering ? filteredCount : totalCount}
                </span>
                {isFiltering && (
                  <span style={{
                    fontSize: '12px',
                    fontWeight: '600',
                    color: 'var(--color-text-muted)',
                    fontFamily: 'var(--font-mono, monospace)',
                  }}>
                    / {totalCount}
                  </span>
                )}
              </div>
              <span style={{
                fontSize: '10px',
                fontWeight: '700',
                letterSpacing: '0.08em',
                color: isFiltering ? '#38bdf8' : 'var(--color-text-muted)',
                textTransform: 'uppercase',
                marginTop: '2px',
              }}>
                {isFiltering ? 'VISIBLE TOOLS' : 'TOOLS USED'}
              </span>
            </div>

            <div style={{ width: '1px', height: '26px', background: 'var(--color-border)', margin: '0 2px' }} />

            <div style={{ display: 'flex', flexDirection: 'column' }}>
              <span style={{
                fontSize: '15px',
                fontWeight: '700',
                color: 'var(--color-text)',
                fontFamily: 'var(--font-mono, monospace)',
                lineHeight: '1',
              }}>
                {toolUsageStats.length}
              </span>
              <span style={{
                fontSize: '9.5px',
                fontWeight: '700',
                letterSpacing: '0.06em',
                color: 'var(--color-text-muted)',
                textTransform: 'uppercase',
                marginTop: '2px',
              }}>
                DISTINCT TYPES
              </span>
            </div>
          </div>

          <button
            onClick={handleDownloadToolSpecifications}
            disabled={generatingReport !== null}
            className="btn btn-secondary"
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '8px',
              padding: '10px 16px',
              fontSize: '12.5px',
              fontWeight: '600',
              cursor: generatingReport ? 'not-allowed' : 'pointer',
              opacity: generatingReport ? 0.7 : 1,
            }}
            title="Download complete tool-by-tool specifications spreadsheet (.xlsx)"
          >
            <Download size={14} />
            <span>Download Tool Specifications</span>
            <span style={{
              fontFamily: 'var(--font-mono)',
              fontSize: '10px',
              fontWeight: '700',
              padding: '2px 6px',
              borderRadius: 'var(--radius-xs)',
              background: 'var(--color-surface)',
              border: '1px solid var(--color-border)',
              color: 'var(--color-text-muted)',
              textTransform: 'uppercase',
            }}>
              .xlsx
            </span>
          </button>
        </div>
      </div>

      {/* Tool Usage Toolbar (Interactive Pills with Occurrence Counts) */}
      <div
        role="toolbar"
        aria-label="Tool Usage Toolbar"
        style={{
          display: 'flex',
          flexDirection: 'column',
          gap: '10px',
          background: 'var(--color-surface-secondary)',
          padding: '14px 18px',
          borderRadius: 'var(--radius-md)',
          border: '1px solid var(--color-border)',
        }}
      >
        <div style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          flexWrap: 'wrap',
          gap: '8px',
        }}>
          <div style={{
            fontSize: '11px',
            fontWeight: '700',
            letterSpacing: '0.08em',
            color: 'var(--color-text-muted)',
            textTransform: 'uppercase',
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
          }}>
            <span>Tool Usage Breakdown</span>
            <span style={{ color: 'var(--color-text-subtle)' }}>•</span>
            <span style={{ fontWeight: '500', textTransform: 'none', letterSpacing: 'normal' }}>
              Click any tool to filter workflow &amp; portfolio
            </span>
          </div>

          {activeToolType && activeToolType !== 'ALL' && (
            <button
              onClick={() => handleSelectToolType('ALL')}
              style={{
                background: 'transparent',
                border: 'none',
                color: 'var(--color-primary)',
                fontSize: '12px',
                fontWeight: '600',
                cursor: 'pointer',
                padding: '2px 6px',
                display: 'inline-flex',
                alignItems: 'center',
                gap: '4px',
                transition: 'opacity 0.15s ease',
              }}
              title="Clear active tool filter"
            >
              <span>Clear Tool Filter</span>
              <X size={13} />
            </button>
          )}
        </div>

        {/* Toolbar Filter Pills */}
        <div style={{
          display: 'flex',
          flexWrap: 'wrap',
          gap: '8px',
          alignItems: 'center',
        }}>
          {/* "ALL TOOLS" Pill */}
          <button
            type="button"
            aria-pressed={!activeToolType || activeToolType === 'ALL'}
            onClick={() => handleSelectToolType('ALL')}
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '8px',
              padding: '6px 14px',
              borderRadius: '20px',
              fontSize: '12.5px',
              fontWeight: '700',
              cursor: 'pointer',
              transition: 'all 0.15s ease',
              background: (!activeToolType || activeToolType === 'ALL')
                ? 'var(--color-primary)'
                : 'var(--color-surface)',
              color: (!activeToolType || activeToolType === 'ALL')
                ? '#ffffff'
                : 'var(--color-text)',
              border: (!activeToolType || activeToolType === 'ALL')
                ? '1px solid var(--color-primary)'
                : '1px solid var(--color-border)',
              boxShadow: (!activeToolType || activeToolType === 'ALL')
                ? '0 0 10px rgba(249, 115, 22, 0.25)'
                : 'none',
            }}
          >
            <span>All Tools</span>
            <span style={{
              fontSize: '11px',
              fontWeight: '800',
              padding: '1px 6px',
              borderRadius: '10px',
              background: (!activeToolType || activeToolType === 'ALL')
                ? 'rgba(255, 255, 255, 0.25)'
                : 'var(--color-surface-secondary)',
              color: (!activeToolType || activeToolType === 'ALL')
                ? '#ffffff'
                : 'var(--color-text-muted)',
              fontFamily: 'var(--font-mono, monospace)',
            }}>
              {totalCount}
            </span>
          </button>

          {/* Individual Tool Pills with Occurrence Count */}
          {toolUsageStats.map(({ toolType, count }) => {
            const isSelected = activeToolType?.toLowerCase() === toolType.toLowerCase();
            return (
              <button
                key={toolType}
                type="button"
                aria-pressed={isSelected}
                onClick={() => handleSelectToolType(toolType)}
                style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '8px',
                  padding: '6px 12px',
                  borderRadius: '20px',
                  fontSize: '12.5px',
                  fontWeight: isSelected ? '700' : '600',
                  cursor: 'pointer',
                  transition: 'all 0.15s ease',
                  background: isSelected
                    ? 'rgba(56, 189, 248, 0.15)'
                    : 'var(--color-surface)',
                  color: isSelected
                    ? '#38bdf8'
                    : 'var(--color-text)',
                  border: isSelected
                    ? '1.5px solid #38bdf8'
                    : '1px solid var(--color-border)',
                  boxShadow: isSelected
                    ? '0 0 12px rgba(56, 189, 248, 0.25)'
                    : 'none',
                }}
              >
                <span>{toolType}</span>
                <span style={{
                  fontSize: '11px',
                  fontWeight: '800',
                  padding: '1px 6px',
                  borderRadius: '10px',
                  background: isSelected
                    ? 'rgba(56, 189, 248, 0.3)'
                    : 'var(--color-surface-secondary)',
                  color: isSelected
                    ? '#ffffff'
                    : 'var(--color-text-muted)',
                  fontFamily: 'var(--font-mono, monospace)',
                }}>
                  {count}
                </span>
              </button>
            );
          })}
        </div>

        {/* Portfolio Context Link (When viewing a single workflow within an active portfolio) */}
        {portfolio && activeToolType && activeToolType !== 'ALL' && (
          <div style={{
            marginTop: '4px',
            paddingTop: '10px',
            borderTop: '1px solid var(--color-border-subtle, rgba(255, 255, 255, 0.06))',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            flexWrap: 'wrap',
            gap: '8px',
            fontSize: '12px',
            color: 'var(--color-text-secondary)',
          }}>
            <span>
              Active Filter: <strong>{activeToolType}</strong> is used across <strong>{matchingPortfolioWorkflowsCount}</strong> {matchingPortfolioWorkflowsCount === 1 ? 'workflow' : 'workflows'} in this portfolio.
            </span>
            {onNavigateToPortfolio && (
              <button
                onClick={onNavigateToPortfolio}
                style={{
                  background: 'transparent',
                  border: 'none',
                  color: '#38bdf8',
                  fontSize: '12px',
                  fontWeight: '700',
                  cursor: 'pointer',
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '5px',
                  padding: 0,
                }}
              >
                <span>View matching workflows in Portfolio</span>
                <ArrowRight size={13} />
              </button>
            )}
          </div>
        )}
      </div>

      {/* Free-Text Search Toolbar */}
      <div style={{
        display: 'flex',
        gap: '12px',
        alignItems: 'center',
        flexWrap: 'wrap',
        background: 'var(--color-surface-secondary)',
        padding: '12px 16px',
        borderRadius: 'var(--radius-md)',
        border: '1px solid var(--color-border)',
      }}>
        {/* Search Input Box */}
        <div style={{
          flex: 1,
          minWidth: '240px',
          position: 'relative',
          display: 'flex',
          alignItems: 'center',
        }}>
          <Search
            size={16}
            color="var(--color-text-muted)"
            style={{ position: 'absolute', left: '12px', pointerEvents: 'none' }}
          />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search tools by name, type, function, annotation, id..."
            aria-label="Search tools"
            style={{
              width: '100%',
              padding: '8px 36px 8px 36px',
              fontSize: '13px',
              borderRadius: 'var(--radius-sm)',
              border: '1px solid var(--color-border)',
              background: 'var(--color-surface)',
              color: 'var(--color-text)',
              outline: 'none',
              transition: 'border-color 0.15s ease',
            }}
            onFocus={(e) => {
              e.currentTarget.style.borderColor = 'var(--color-primary)';
            }}
            onBlur={(e) => {
              e.currentTarget.style.borderColor = 'var(--color-border)';
            }}
          />
          {searchQuery && (
            <button
              onClick={() => setSearchQuery('')}
              aria-label="Clear search"
              title="Clear search"
              style={{
                position: 'absolute',
                right: '10px',
                background: 'transparent',
                border: 'none',
                color: 'var(--color-text-muted)',
                cursor: 'pointer',
                padding: '2px',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
              }}
            >
              <X size={15} />
            </button>
          )}
        </div>

        {/* Status Count and Reset */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <span style={{ fontSize: '12.5px', color: 'var(--color-text-muted)', fontWeight: '500' }}>
            Showing {filteredCount} of {totalCount} tools
          </span>

          {isFiltering && (
            <button
              onClick={() => {
                setSearchQuery('');
                handleSelectToolType('ALL');
              }}
              className="btn-secondary"
              style={{ padding: '6px 12px', fontSize: '12px', fontWeight: '600' }}
            >
              Reset Filters
            </button>
          )}
        </div>
      </div>

      {/* Results / Empty State */}
      {filteredCount === 0 ? (
        <div
          className="app-card"
          style={{
            padding: '48px 24px',
            textAlign: 'center',
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            gap: '8px',
          }}
        >
          <Search size={32} color="var(--color-text-muted)" />
          <div style={{ fontSize: '15px', fontWeight: '700', color: 'var(--color-text)', marginTop: '4px' }}>
            No tools found
          </div>
          <div style={{ fontSize: '13px', color: 'var(--color-text-muted)', maxWidth: '440px', lineHeight: 1.4 }}>
            {searchQuery && activeToolType ? (
              <>No tools match &ldquo;<strong>{searchQuery}</strong>&rdquo; with type <strong>{activeToolType}</strong>. Try clearing search or selecting All Tools.</>
            ) : searchQuery ? (
              <>No tools match &ldquo;<strong>{searchQuery}</strong>&rdquo;. Try searching by tool name, configuration, or formula.</>
            ) : (
              <>No tools found for type <strong>{activeToolType}</strong>.</>
            )}
          </div>
          <button
            onClick={() => {
              setSearchQuery('');
              handleSelectToolType('ALL');
            }}
            className="btn-secondary"
            style={{ marginTop: '12px', padding: '6px 14px', fontSize: '12px' }}
          >
            Clear search &amp; filters
          </button>
        </div>
      ) : (
        <NodeDetails
          nodes={filteredNodes}
          selectedToolId={selectedToolId}
          hideHeader={true}
        />
      )}
    </div>
  );
};

