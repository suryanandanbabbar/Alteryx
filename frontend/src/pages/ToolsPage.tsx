import React, { useEffect, useState, useMemo } from 'react';
import { api } from '../api/client';
import { DiagramDTO } from '../types/workflow';
import { NodeDetails } from '../components/NodeDetails';
import { Loader2, AlertCircle, Search, X, Filter } from 'lucide-react';

interface ToolsPageProps {
  analysisId: string;
  selectedToolId?: number | null;
}

export const ToolsPage: React.FC<ToolsPageProps> = ({ analysisId, selectedToolId }) => {
  const [diagramData, setDiagramData] = useState<DiagramDTO | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedType, setSelectedType] = useState('ALL');

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

  // Extract unique tool types sorted alphabetically
  const toolTypes = useMemo(() => {
    if (!diagramData?.nodes) return [];
    const types = new Set<string>();
    diagramData.nodes.forEach((n) => {
      if (n.tool_type) types.add(n.tool_type);
    });
    return Array.from(types).sort();
  }, [diagramData?.nodes]);

  // Filter nodes client-side
  const filteredNodes = useMemo(() => {
    if (!diagramData?.nodes) return [];
    const q = searchQuery.trim().toLowerCase();

    return diagramData.nodes.filter((node) => {
      // 1. Tool Type filter
      if (selectedType !== 'ALL' && node.tool_type !== selectedType) {
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
  }, [diagramData?.nodes, searchQuery, selectedType]);

  const isFiltering = searchQuery.trim() !== '' || selectedType !== 'ALL';
  const totalCount = diagramData?.nodes?.length ?? 0;
  const filteredCount = filteredNodes.length;

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
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px', maxWidth: '1000px', width: '100%' }}>
      {/* Page Header */}
      <div>
        <div style={{
          fontSize: '11px',
          fontWeight: '700',
          letterSpacing: '1px',
          color: 'var(--color-primary)',
          textTransform: 'uppercase',
          marginBottom: '4px',
        }}>
          03 Tools &amp; Configuration
        </div>
        <div style={{ display: 'flex', alignItems: 'baseline', justifyContent: 'space-between', flexWrap: 'wrap', gap: '8px' }}>
          <h2 style={{ fontSize: '20px', fontWeight: '800', color: 'var(--color-text)', letterSpacing: '-0.3px', margin: 0 }}>
            Tool Specifications &amp; Configuration
          </h2>
          <span style={{ fontSize: '12.5px', color: 'var(--color-text-muted)', fontWeight: '500' }}>
            {isFiltering ? `Showing ${filteredCount} of ${totalCount} tools` : `${totalCount} tools`}
          </span>
        </div>
      </div>

      {/* Search & Filter Toolbar */}
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
            placeholder="Search tools by name, type, function, annotation..."
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

        {/* Tool Type Filter Dropdown */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Filter size={15} color="var(--color-text-muted)" />
          <select
            value={selectedType}
            onChange={(e) => setSelectedType(e.target.value)}
            aria-label="Filter by tool type"
            style={{
              padding: '8px 12px',
              fontSize: '13px',
              borderRadius: 'var(--radius-sm)',
              border: '1px solid var(--color-border)',
              background: 'var(--color-surface)',
              color: 'var(--color-text)',
              cursor: 'pointer',
              outline: 'none',
              fontWeight: '500',
            }}
          >
            <option value="ALL">All Tool Types ({toolTypes.length})</option>
            {toolTypes.map((type) => (
              <option key={type} value={type}>
                {type}
              </option>
            ))}
          </select>
        </div>

        {/* Clear All Filters Button */}
        {isFiltering && (
          <button
            onClick={() => {
              setSearchQuery('');
              setSelectedType('ALL');
            }}
            className="btn-secondary"
            style={{ padding: '7px 12px', fontSize: '12px' }}
          >
            Reset
          </button>
        )}
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
          <div style={{ fontSize: '13px', color: 'var(--color-text-muted)', maxWidth: '420px', lineHeight: 1.4 }}>
            {searchQuery ? (
              <>No tools match &ldquo;<strong>{searchQuery}</strong>&rdquo;{selectedType !== 'ALL' ? ` with type "${selectedType}"` : ''}. Try searching by tool name, type, or function.</>
            ) : (
              <>No tools found for type &ldquo;<strong>{selectedType}</strong>&rdquo;.</>
            )}
          </div>
          <button
            onClick={() => {
              setSearchQuery('');
              setSelectedType('ALL');
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
