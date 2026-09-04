import React, { useState } from 'react';
import { AnalysisOverviewDTO } from './types/workflow';
import { PortfolioOverviewDTO } from './types/portfolio';
import { Sidebar } from './components/Sidebar';
import { Header } from './components/Header';
import { SplashScreen } from './components/SplashScreen';
import { UploadPage } from './pages/UploadPage';
import { OverviewPage } from './pages/OverviewPage';
import { DiagramPage } from './pages/DiagramPage';
import { ToolsPage } from './pages/ToolsPage';
import { JsonPage } from './pages/JsonPage';
import { PythonPage } from './pages/PythonPage';
import { DownloadPage } from './pages/DownloadPage';
import { PortfolioPage } from './pages/PortfolioPage';
import { DocumentGenerationModal } from './components/DocumentGenerationModal';
import { api, isPortfolioResponse } from './api/client';

const SECTION_TITLES: Record<string, string> = {
  overview: 'Overview',
  diagram: 'Workflow Diagram',
  tools: 'Tools & Configuration',
  json: 'JSON',
  python: 'Python',
  downloads: 'Download',
};

export const App: React.FC = () => {
  const [overview, setOverview] = useState<AnalysisOverviewDTO | null>(null);
  const [portfolio, setPortfolio] = useState<PortfolioOverviewDTO | null>(null);
  const [selectedBusinessArea, setSelectedBusinessArea] = useState<string | null>(null);
  const [activeSection, setActiveSection] = useState<string>('overview');
  const [selectedToolId, setSelectedToolId] = useState<number | null>(null);
  const [selectedToolTypeFilter, setSelectedToolTypeFilter] = useState<string | null>(null);

  const [showRationalisation, setShowRationalisation] = useState<boolean>(false);
  const [downloadingXlsx, setDownloadingXlsx] = useState<boolean>(false);

  const handleDownloadPortfolioXlsx = async () => {
    if (!portfolio || downloadingXlsx) return;
    setDownloadingXlsx(true);
    try {
      await api.downloadPortfolioXlsx(portfolio.portfolio_id, portfolio.portfolio_name);
    } catch (err) {
      console.error('Failed to download portfolio XLSX:', err);
    } finally {
      setDownloadingXlsx(false);
    }
  };

  const handleUploadSuccess = (result: AnalysisOverviewDTO | PortfolioOverviewDTO) => {
    if (isPortfolioResponse(result)) {
      setPortfolio(result);
      setOverview(null);
      setSelectedBusinessArea(null);
    } else {
      setOverview(result);
      setPortfolio(null);
      setSelectedBusinessArea(null);
    }
    setActiveSection('overview');
    setSelectedToolId(null);
    setSelectedToolTypeFilter(null);
    setShowRationalisation(false);
  };

  const handleReset = () => {
    setOverview(null);
    setPortfolio(null);
    setSelectedBusinessArea(null);
    setActiveSection('overview');
    setSelectedToolId(null);
    setSelectedToolTypeFilter(null);
    setShowRationalisation(false);
  };

  const handleSelectTool = (toolId: number) => {
    setSelectedToolId(toolId);
    setActiveSection('tools');
  };

  // If no active analysis and no active portfolio, render upload view
  if (!overview && !portfolio) {
    return (
      <>
        <SplashScreen />
        <UploadPage onUploadSuccess={handleUploadSuccess} />
      </>
    );
  }

  // If active portfolio and no individual workflow selected, render portfolio overview with Left Sidebar
  if (portfolio && !overview) {
    return (
      <div style={{ display: 'flex', minHeight: '100vh', background: 'var(--color-bg)' }}>
        <SplashScreen />
        {downloadingXlsx && <DocumentGenerationModal type="portfolio-xlsx" />}
        {/* Persistent Left Sidebar in Portfolio View */}
        <Sidebar
          portfolio={portfolio}
          onReset={handleReset}
          onOpenRationalisation={() => setShowRationalisation(true)}
          onDownloadPortfolioXlsx={handleDownloadPortfolioXlsx}
          isDownloadingXlsx={downloadingXlsx}
        />

        {/* Main Content Area */}
        <div style={{
          flex: 1,
          display: 'flex',
          flexDirection: 'column',
          minWidth: 0,
          height: '100vh',
        }}>
          <main style={{
            flex: 1,
            padding: '32px 40px',
            overflowY: 'auto',
            boxSizing: 'border-box',
          }}>
            <PortfolioPage
              portfolio={portfolio}
              selectedBusinessArea={selectedBusinessArea}
              onSelectBusinessArea={(area) => setSelectedBusinessArea(area)}
              selectedToolType={selectedToolTypeFilter}
              onSelectToolType={setSelectedToolTypeFilter}
              onSelectWorkflow={async (workflowId, businessArea) => {
                try {
                  if (businessArea) {
                    setSelectedBusinessArea(businessArea);
                  }
                  const wfOverview = await api.getOverview(workflowId);
                  setOverview(wfOverview);
                  setActiveSection('overview');
                } catch (err) {
                  console.error('Failed to load workflow overview:', err);
                  throw err;
                }
              }}
              onReset={handleReset}
              showRationalisation={showRationalisation}
              setShowRationalisation={setShowRationalisation}
            />
          </main>
        </div>
      </div>
    );
  }

  if (!overview) {
    return null;
  }

  const sectionTitle = SECTION_TITLES[activeSection] || 'Workflow Analysis';

  return (
    <div style={{ display: 'flex', minHeight: '100vh', background: 'var(--color-bg)' }}>
      <SplashScreen />
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
          onBackToPortfolio={portfolio ? () => setOverview(null) : undefined}
          backLabel={selectedBusinessArea ? `← Back to ${selectedBusinessArea}` : '← All Workflows'}
        />

        {/* Scrollable Page Body */}
        <main style={{
          flex: 1,
          padding: '32px 40px',
          overflowY: 'auto',
          boxSizing: 'border-box',
        }}>
          {activeSection === 'overview' && (
            <OverviewPage
              overview={overview}
              onSelectTool={handleSelectTool}
              onNavigateToDiagram={() => setActiveSection('diagram')}
            />
          )}
          {activeSection === 'diagram' && (
            <DiagramPage
              analysisId={overview.analysis_id}
              selectedToolId={selectedToolId}
            />
          )}
          {activeSection === 'tools' && (
            <ToolsPage
              analysisId={overview.analysis_id}
              selectedToolId={selectedToolId}
              portfolio={portfolio}
              selectedToolType={selectedToolTypeFilter}
              onSelectToolType={setSelectedToolTypeFilter}
              onNavigateToPortfolio={portfolio ? () => setOverview(null) : undefined}
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
