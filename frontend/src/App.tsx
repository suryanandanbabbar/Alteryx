import React, { useState } from 'react';
import { AnalysisOverviewDTO } from './types/workflow';
import { Sidebar } from './components/Sidebar';
import { UploadPage } from './pages/UploadPage';
import { OverviewPage } from './pages/OverviewPage';
import { DiagramPage } from './pages/DiagramPage';
import { JsonPage } from './pages/JsonPage';
import { PythonPage } from './pages/PythonPage';
import { DownloadPage } from './pages/DownloadPage';

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

  // If no active analysis, show upload page
  if (!overview) {
    return <UploadPage onUploadSuccess={handleUploadSuccess} />;
  }

  // Otherwise render full app shell with sidebar and active page view
  return (
    <div style={{ display: 'flex', minHeight: '100vh', background: 'var(--bg-dark)' }}>
      {/* Persistent Left Sidebar */}
      <Sidebar
        overview={overview}
        activeSection={activeSection}
        onNavigate={(section) => setActiveSection(section)}
        onReset={handleReset}
      />

      {/* Main Content Area */}
      <main style={{
        flex: 1,
        padding: '36px 48px',
        overflowY: 'auto',
        maxHeight: '100vh',
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
  );
};
