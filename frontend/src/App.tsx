import React, { useState } from 'react';
import { AnalysisOverviewDTO } from './types/workflow';
import { Sidebar } from './components/Sidebar';
import { Header } from './components/Header';
import { UploadPage } from './pages/UploadPage';
import { OverviewPage } from './pages/OverviewPage';
import { DiagramPage } from './pages/DiagramPage';
import { JsonPage } from './pages/JsonPage';
import { PythonPage } from './pages/PythonPage';
import { DownloadPage } from './pages/DownloadPage';

const SECTION_TITLES: Record<string, string> = {
  overview: '01 Overview',
  diagram: '02 Workflow Diagram',
  json: '03 JSON',
  python: '04 Python',
  downloads: '05 Download',
};

export const App: React.FC = () => {
  const [overview, setOverview] = useState<AnalysisOverviewDTO | null>(null);
  const [activeSection, setActiveSection] = useState<string>('overview');
  const [selectedToolId, setSelectedToolId] = useState<number | null>(null);

  const handleUploadSuccess = (newOverview: AnalysisOverviewDTO) => {
    setOverview(newOverview);
    setActiveSection('overview');
    setSelectedToolId(null);
  };

  const handleReset = () => {
    setOverview(null);
    setActiveSection('overview');
    setSelectedToolId(null);
  };

  const handleSelectTool = (toolId: number) => {
    setSelectedToolId(toolId);
    setActiveSection('diagram');
  };

  // If no active analysis, render upload view
  if (!overview) {
    return <UploadPage onUploadSuccess={handleUploadSuccess} />;
  }

  const sectionTitle = SECTION_TITLES[activeSection] || 'Workflow Analysis';

  return (
    <div style={{ display: 'flex', minHeight: '100vh', background: 'var(--color-bg)' }}>
      {/* Persistent Left Sidebar */}
      <Sidebar
        overview={overview}
        activeSection={activeSection}
        onNavigate={(section) => setActiveSection(section)}
        onReset={handleReset}
      />

      {/* Main Content Area */}
      <div style={{
        flex: 1,
        display: 'flex',
        flexDirection: 'column',
        minWidth: 0,
        height: '100vh',
      }}>
        {/* Top Header */}
        <Header
          sectionTitle={sectionTitle}
          workflowName={overview.source.original_filename}
        />

        {/* Scrollable Page Body */}
        <main style={{
          flex: 1,
          padding: '32px 40px',
          overflowY: 'auto',
          boxSizing: 'border-box',
        }}>
          {activeSection === 'overview' && (
            <OverviewPage overview={overview} onSelectTool={handleSelectTool} />
          )}
          {activeSection === 'diagram' && (
            <DiagramPage
              analysisId={overview.analysis_id}
              selectedToolId={selectedToolId}
            />
          )}
          {activeSection === 'json' && (
            <JsonPage analysisId={overview.analysis_id} />
          )}
          {activeSection === 'python' && (
            <PythonPage analysisId={overview.analysis_id} />
          )}
          {activeSection === 'downloads' && (
            <DownloadPage analysisId={overview.analysis_id} />
          )}
        </main>
      </div>
    </div>
  );
};
