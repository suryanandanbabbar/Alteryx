import React from 'react';
import { AnalysisOverviewDTO } from '../types/workflow';
import { 
  BarChart3, 
  Network, 
  FileCode2, 
  Terminal, 
  Download, 
  ArrowLeft, 
  FileText,
  Workflow
} from 'lucide-react';

interface SidebarProps {
  overview: AnalysisOverviewDTO;
  activeSection: string;
  onNavigate: (section: string) => void;
  onReset: () => void;
}

export const Sidebar: React.FC<SidebarProps> = ({
  overview,
  activeSection,
  onNavigate,
  onReset,
}) => {
  const navItems = [
    { id: 'overview', number: '01', label: 'Workflow Overview', icon: BarChart3 },
    { id: 'diagram', number: '02', label: 'Workflow Diagram', icon: Network },
    { id: 'json', number: '03', label: 'Structured JSON Output', icon: FileCode2 },
    { id: 'python', number: '04', label: 'Python Pipeline Output', icon: Terminal },
    { id: 'downloads', number: '05', label: 'Download All Files', icon: Download },
  ];

  return (
    <aside style={{
      width: '280px',
      minWidth: '280px',
      height: '100vh',
      position: 'sticky',
      top: 0,
      background: 'rgba(11, 17, 33, 0.95)',
      borderRight: '1px solid rgba(51, 65, 85, 0.5)',
      display: 'flex',
      flexDirection: 'column',
      padding: '24px 16px',
      boxSizing: 'border-box',
      zIndex: 10,
    }}>
      {/* Brand Header */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '28px', paddingLeft: '8px' }}>
        <div style={{
          width: '32px',
          height: '32px',
          borderRadius: '8px',
          background: 'linear-gradient(135deg, #38bdf8 0%, #3b82f6 100%)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          color: '#0f172a',
          fontWeight: 'bold',
        }}>
          <Workflow size={18} />
        </div>
        <div>
          <h2 style={{ fontSize: '15px', fontWeight: '700', color: '#f8fafc', letterSpacing: '-0.2px' }}>
            Alteryx Converter
          </h2>
          <div style={{ fontSize: '11px', color: '#38bdf8', fontFamily: 'monospace' }}>v1.0 · FastAPI</div>
        </div>
      </div>

      {/* ACTIVE FILE Section */}
      <div style={{
        background: 'rgba(15, 23, 42, 0.8)',
        border: '1px solid rgba(51, 65, 85, 0.6)',
        borderRadius: '10px',
        padding: '14px',
        marginBottom: '28px',
      }}>
        <div style={{
          fontSize: '10px',
          fontWeight: '700',
          letterSpacing: '1px',
          color: '#64748b',
          marginBottom: '8px',
          textTransform: 'uppercase',
        }}>
          Active File
        </div>
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: '8px',
          color: '#f8fafc',
          fontWeight: '600',
          fontSize: '13px',
          marginBottom: '6px',
          wordBreak: 'break-all',
        }}>
          <FileText size={15} color="#38bdf8" style={{ flexShrink: 0 }} />
          <span>{overview.source.original_filename}</span>
        </div>
        <div style={{ fontSize: '11px', color: '#94a3b8', display: 'flex', gap: '8px', alignItems: 'center' }}>
          <span>{overview.metadata.version ? `Alteryx ${overview.metadata.version}` : 'Alteryx Workflow'}</span>
          <span>·</span>
          <span>{overview.metrics.total_nodes} nodes</span>
        </div>
      </div>

      {/* NAVIGATION Section */}
      <div style={{
        fontSize: '10px',
        fontWeight: '700',
        letterSpacing: '1px',
        color: '#64748b',
        marginBottom: '12px',
        paddingLeft: '8px',
        textTransform: 'uppercase',
      }}>
        Navigation
      </div>

      <nav style={{ display: 'flex', flexDirection: 'column', gap: '4px', flex: 1 }}>
        {navItems.map((item) => {
          const isActive = activeSection === item.id;
          const Icon = item.icon;

          return (
            <button
              key={item.id}
              onClick={() => onNavigate(item.id)}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '12px',
                padding: '10px 12px',
                borderRadius: '8px',
                border: isActive ? '1px solid rgba(56, 189, 248, 0.4)' : '1px solid transparent',
                background: isActive ? 'rgba(56, 189, 248, 0.12)' : 'transparent',
                color: isActive ? '#38bdf8' : '#94a3b8',
                cursor: 'pointer',
                textAlign: 'left',
                width: '100%',
                transition: 'all 0.15s ease',
              }}
              onMouseEnter={(e) => {
                if (!isActive) {
                  e.currentTarget.style.background = 'rgba(30, 41, 59, 0.6)';
                  e.currentTarget.style.color = '#f8fafc';
                }
              }}
              onMouseLeave={(e) => {
                if (!isActive) {
                  e.currentTarget.style.background = 'transparent';
                  e.currentTarget.style.color = '#94a3b8';
                }
              }}
            >
              <span style={{
                fontFamily: 'monospace',
                fontSize: '11px',
                fontWeight: '600',
                color: isActive ? '#38bdf8' : '#64748b',
              }}>
                {item.number}
              </span>
              <Icon size={16} />
              <span style={{ fontSize: '13px', fontWeight: isActive ? '600' : '500' }}>
                {item.label}
              </span>
            </button>
          );
        })}
      </nav>

      {/* Convert Another File Button */}
      <button
        onClick={onReset}
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          gap: '8px',
          padding: '12px',
          borderRadius: '8px',
          background: 'rgba(15, 23, 42, 0.9)',
          border: '1px solid rgba(51, 65, 85, 0.8)',
          color: '#cbd5e1',
          fontSize: '12px',
          fontWeight: '600',
          cursor: 'pointer',
          marginTop: 'auto',
          transition: 'all 0.2s ease',
        }}
        onMouseEnter={(e) => {
          e.currentTarget.style.background = 'rgba(30, 41, 59, 1)';
          e.currentTarget.style.borderColor = 'rgba(56, 189, 248, 0.5)';
          e.currentTarget.style.color = '#38bdf8';
        }}
        onMouseLeave={(e) => {
          e.currentTarget.style.background = 'rgba(15, 23, 42, 0.9)';
          e.currentTarget.style.borderColor = 'rgba(51, 65, 85, 0.8)';
          e.currentTarget.style.color = '#cbd5e1';
        }}
      >
        <ArrowLeft size={14} />
        <span>Convert another file</span>
      </button>
    </aside>
  );
};
