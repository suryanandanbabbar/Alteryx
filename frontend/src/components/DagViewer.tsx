import React, { useState, useRef, useEffect, useCallback } from 'react';
import { ZoomIn, ZoomOut, RotateCcw, Download, Maximize2 } from 'lucide-react';

interface DagViewerProps {
  svgContent: string;
  onDownloadSvg?: () => void;
  onSelectNode?: (toolId: number) => void;
  selectedToolId?: number | null;
}

export const DagViewer: React.FC<DagViewerProps> = ({
  svgContent,
  onDownloadSvg,
  onSelectNode,
  selectedToolId,
}) => {
  const viewportRef = useRef<HTMLDivElement>(null);
  const [zoom, setZoom] = useState(1);
  const [pan, setPan] = useState({ x: 0, y: 0 });
  const [isDragging, setIsDragging] = useState(false);
  const dragStartRef = useRef({ x: 0, y: 0, panX: 0, panY: 0, hasMoved: false });
  const [svgDimensions, setSvgDimensions] = useState({ width: 1200, height: 600 });

  // 1. Parse SVG natural viewBox dimensions from svgContent
  useEffect(() => {
    if (!svgContent) return;

    let width = 1200;
    let height = 600;

    const viewBoxMatch = svgContent.match(/viewBox=["']\s*0\s+0\s+(\d+(?:\.\d+)?)\s+(\d+(?:\.\d+)?)\s*["']/i);
    if (viewBoxMatch) {
      width = parseFloat(viewBoxMatch[1]) || 1200;
      height = parseFloat(viewBoxMatch[2]) || 600;
    } else {
      const wMatch = svgContent.match(/width=["'](\d+(?:\.\d+)?)/i);
      const hMatch = svgContent.match(/height=["'](\d+(?:\.\d+)?)/i);
      if (wMatch && parseFloat(wMatch[1])) width = parseFloat(wMatch[1]);
      if (hMatch && parseFloat(hMatch[1])) height = parseFloat(hMatch[1]);
    }

    setSvgDimensions({ width, height });
  }, [svgContent]);

  // 2. Fit to View calculation
  const fitToView = useCallback(() => {
    if (!viewportRef.current) return;
    const viewportWidth = viewportRef.current.clientWidth;
    const viewportHeight = viewportRef.current.clientHeight;

    if (viewportWidth <= 0 || viewportHeight <= 0) return;

    const paddingX = 40;
    const paddingY = 40;

    const availableWidth = Math.max(viewportWidth - paddingX * 2, 100);
    const availableHeight = Math.max(viewportHeight - paddingY * 2, 100);

    const scaleX = availableWidth / svgDimensions.width;
    const scaleY = availableHeight / svgDimensions.height;

    // Use best fitting scale
    const fitScale = Math.max(0.1, Math.min(scaleX, scaleY, 1.8));

    const fitPanX = (viewportWidth - svgDimensions.width * fitScale) / 2;
    const fitPanY = (viewportHeight - svgDimensions.height * fitScale) / 2;

    setZoom(fitScale);
    setPan({ x: fitPanX, y: fitPanY });
  }, [svgDimensions]);

  // Initial fit on mount or dimensions change
  useEffect(() => {
    fitToView();
  }, [fitToView]);

  // Responsive resize observer
  useEffect(() => {
    if (!viewportRef.current) return;
    const observer = new ResizeObserver(() => {
      fitToView();
    });
    observer.observe(viewportRef.current);
    return () => observer.disconnect();
  }, [fitToView]);

  // 3. Wheel / Pinch Zoom (centered on cursor)
  useEffect(() => {
    const viewport = viewportRef.current;
    if (!viewport) return;

    const handleWheel = (e: WheelEvent) => {
      e.preventDefault();

      const rect = viewport.getBoundingClientRect();
      const cursorX = e.clientX - rect.left;
      const cursorY = e.clientY - rect.top;

      const delta = -e.deltaY;
      const zoomFactor = delta > 0 ? 1.12 : 0.89;

      setZoom((currentZoom) => {
        const newZoom = Math.max(0.1, Math.min(currentZoom * zoomFactor, 3.5));
        const ratio = newZoom / currentZoom;

        setPan((currentPan) => ({
          x: cursorX - (cursorX - currentPan.x) * ratio,
          y: cursorY - (cursorY - currentPan.y) * ratio,
        }));

        return newZoom;
      });
    };

    viewport.addEventListener('wheel', handleWheel, { passive: false });
    return () => {
      viewport.removeEventListener('wheel', handleWheel);
    };
  }, []);

  // 4. Pan / Drag handling
  const handleMouseDown = (e: React.MouseEvent) => {
    if (e.button !== 0) return;

    dragStartRef.current = {
      x: e.clientX,
      y: e.clientY,
      panX: pan.x,
      panY: pan.y,
      hasMoved: false,
    };
    setIsDragging(true);
  };

  const handleMouseMove = (e: React.MouseEvent) => {
    if (!isDragging) return;

    const dx = e.clientX - dragStartRef.current.x;
    const dy = e.clientY - dragStartRef.current.y;

    if (Math.abs(dx) > 3 || Math.abs(dy) > 3) {
      dragStartRef.current.hasMoved = true;
    }

    setPan({
      x: dragStartRef.current.panX + dx,
      y: dragStartRef.current.panY + dy,
    });
  };

  const handleMouseUp = (e: React.MouseEvent) => {
    if (!isDragging) return;
    setIsDragging(false);

    if (!dragStartRef.current.hasMoved && onSelectNode) {
      const target = e.target as HTMLElement | SVGElement;
      const nodeEl = target.closest('[id^="node-"]');
      if (nodeEl) {
        const toolIdMatch = nodeEl.id.match(/^node-(\d+)$/);
        if (toolIdMatch) {
          const toolId = parseInt(toolIdMatch[1], 10);
          onSelectNode(toolId);
        }
      }
    }
  };

  // 5. Button Zoom Controls (centered on viewport center)
  const zoomAtCenter = (factor: number) => {
    if (!viewportRef.current) return;
    const centerX = viewportRef.current.clientWidth / 2;
    const centerY = viewportRef.current.clientHeight / 2;

    setZoom((currentZoom) => {
      const newZoom = Math.max(0.1, Math.min(currentZoom * factor, 3.5));
      const ratio = newZoom / currentZoom;

      setPan((currentPan) => ({
        x: centerX - (centerX - currentPan.x) * ratio,
        y: centerY - (centerY - currentPan.y) * ratio,
      }));

      return newZoom;
    });
  };

  const handleZoomIn = () => zoomAtCenter(1.2);
  const handleZoomOut = () => zoomAtCenter(0.83);

  return (
    <div className="app-card" style={{ overflow: 'hidden', width: '100%' }}>
      {/* Dynamic Node Highlight CSS */}
      {selectedToolId && (
        <style>
          {`
            #node-${selectedToolId} rect:first-of-type {
              stroke: #ea580c !important;
              stroke-width: 2.5px !important;
              filter: drop-shadow(0 0 10px rgba(234, 88, 12, 0.7));
            }
          `}
        </style>
      )}

      {/* Viewer Header / Toolbar */}
      <div style={{
        padding: '12px 18px',
        borderBottom: '1px solid var(--color-border)',
        background: 'var(--color-surface-secondary)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        flexWrap: 'wrap',
        gap: '12px',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <span style={{ fontSize: '13px', fontWeight: '700', color: 'var(--color-text)' }}>
            Workflow Graph (DAG)
          </span>
          <span style={{
            fontSize: '11px',
            color: 'var(--color-text-muted)',
            fontFamily: 'var(--font-mono)',
            padding: '2px 8px',
            background: 'var(--color-surface)',
            border: '1px solid var(--color-border)',
            borderRadius: 'var(--radius-sm)',
          }}>
            Interactive Canvas
          </span>
        </div>

        {/* Action Controls */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          {/* Zoom Controls */}
          <div style={{
            display: 'flex',
            alignItems: 'center',
            background: 'var(--color-surface)',
            border: '1px solid var(--color-border)',
            borderRadius: 'var(--radius-sm)',
          }}>
            <button
              onClick={handleZoomOut}
              aria-label="Zoom out"
              title="Zoom Out"
              style={{
                padding: '6px 9px',
                border: 'none',
                background: 'transparent',
                color: 'var(--color-text-secondary)',
                cursor: 'pointer',
                borderRight: '1px solid var(--color-border)',
                display: 'flex',
                alignItems: 'center',
              }}
            >
              <ZoomOut size={14} />
            </button>
            <span style={{
              padding: '4px 10px',
              fontSize: '11.5px',
              fontFamily: 'var(--font-mono)',
              color: 'var(--color-text)',
              fontWeight: '600',
              minWidth: '48px',
              textAlign: 'center',
            }}>
              {Math.round(zoom * 100)}%
            </span>
            <button
              onClick={handleZoomIn}
              aria-label="Zoom in"
              title="Zoom In"
              style={{
                padding: '6px 9px',
                border: 'none',
                background: 'transparent',
                color: 'var(--color-text-secondary)',
                cursor: 'pointer',
                borderLeft: '1px solid var(--color-border)',
                display: 'flex',
                alignItems: 'center',
              }}
            >
              <ZoomIn size={14} />
            </button>
          </div>

          <button
            onClick={fitToView}
            className="btn-secondary"
            style={{ padding: '6px 12px', fontSize: '12px', gap: '6px' }}
            title="Fit to View"
          >
            <Maximize2 size={13} />
            <span>Fit to View</span>
          </button>

          <button
            onClick={fitToView}
            className="btn-secondary"
            style={{ padding: '6px 10px', fontSize: '12px' }}
            title="Reset Transform"
          >
            <RotateCcw size={13} />
            <span>Reset</span>
          </button>

          {onDownloadSvg && (
            <button
              onClick={onDownloadSvg}
              className="btn-secondary"
              style={{ padding: '6px 12px', fontSize: '12px', gap: '6px' }}
              title="Download standalone SVG"
            >
              <Download size={13} />
              <span>Download SVG</span>
            </button>
          )}
        </div>
      </div>

      {/* Interactive Graph Canvas Area */}
      <div
        ref={viewportRef}
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        onMouseLeave={handleMouseUp}
        style={{
          height: '560px',
          width: '100%',
          position: 'relative',
          overflow: 'hidden',
          cursor: isDragging ? 'grabbing' : 'grab',
          userSelect: 'none',
          backgroundColor: '#0a0f1d',
          backgroundImage: 'radial-gradient(rgba(255, 255, 255, 0.08) 1px, transparent 1px)',
          backgroundSize: '24px 24px',
        }}
      >
        {/* Transformable Canvas Content */}
        <div
          style={{
            position: 'absolute',
            top: 0,
            left: 0,
            width: `${svgDimensions.width}px`,
            height: `${svgDimensions.height}px`,
            transform: `translate(${pan.x}px, ${pan.y}px) scale(${zoom})`,
            transformOrigin: '0 0',
            pointerEvents: isDragging ? 'none' : 'auto',
          }}
          dangerouslySetInnerHTML={{ __html: svgContent }}
        />

        {/* Viewport Navigation Hint */}
        <div style={{
          position: 'absolute',
          bottom: '12px',
          left: '14px',
          fontSize: '11px',
          color: 'rgba(148, 163, 184, 0.65)',
          background: 'rgba(15, 23, 42, 0.75)',
          backdropFilter: 'blur(4px)',
          padding: '4px 10px',
          borderRadius: 'var(--radius-sm)',
          border: '1px solid rgba(51, 65, 85, 0.5)',
          pointerEvents: 'none',
        }}>
          Drag empty space to pan · Scroll / pinch to zoom · Click node to inspect
        </div>
      </div>
    </div>
  );
};
