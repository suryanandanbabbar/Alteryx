import React, { useState, useEffect } from 'react';
import { Sun, Moon, ArrowRight, AlertCircle, Terminal, FileCode, Loader2 } from 'lucide-react';
import { api } from '../api/client';
import { useTheme } from '../context/ThemeContext';

export interface ApplicationChooserPageProps {
  onSelectAlteryx: () => void;
}

export const ApplicationChooserPage: React.FC<ApplicationChooserPageProps> = ({ onSelectAlteryx }) => {
  const { theme, toggleTheme } = useTheme();
  const [hoveredCard, setHoveredCard] = useState<'code' | 'alteryx' | null>(null);
  const [codeBasedUrl, setCodeBasedUrl] = useState<string | null>(null);
  const [configLoading, setConfigLoading] = useState<boolean>(true);
  const [configError, setConfigError] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);

  useEffect(() => {
    let isMounted = true;
    api.getConfig()
      .then((cfg) => {
        if (isMounted) {
          setCodeBasedUrl(cfg.code_based_workflows_url || null);
          setConfigLoading(false);
        }
      })
      .catch((err) => {
        if (isMounted) {
          console.warn('Failed to load application configuration:', err);
          setConfigError('Unable to load application configuration.');
          setConfigLoading(false);
        }
      });

    return () => {
      isMounted = false;
    };
  }, []);

  const handleCodeBasedStart = () => {
    setActionError(null);
    if (configLoading) return;

    if (!codeBasedUrl) {
      setActionError('Code-based workflow application is not configured.');
      return;
    }

    try {
      const parsed = new URL(codeBasedUrl);
      if (parsed.protocol !== 'http:' && parsed.protocol !== 'https:') {
        setActionError('Code-based workflow application is not configured with a valid URL.');
        return;
      }
      window.location.assign(parsed.href);
    } catch {
      setActionError('Code-based workflow application is not configured with a valid URL.');
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
            ETL Discovery, Intelligence, Rationalisation &amp; Migration
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
            e.currentTarget.style.color = 'var(--color-text)';
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.backgroundColor = 'var(--color-surface)';
            e.currentTarget.style.color = 'var(--color-text-secondary)';
          }}
        >
          {theme === 'light' ? <Moon size={15} /> : <Sun size={15} />}
        </button>
      </header>

      {/* Main Container */}
      <main style={{
        flex: 1,
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '48px 24px',
        maxWidth: '880px',
        margin: '0 auto',
        width: '100%',
        boxSizing: 'border-box',
      }}>
        {/* Header Block */}
        <div style={{ textAlign: 'center', marginBottom: '36px' }}>
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
            Powered By EXL
          </div>

          <h1 style={{
            fontSize: '24px',
            fontWeight: '800',
            color: 'var(--color-text)',
            letterSpacing: '-0.5px',
            marginBottom: '12px',
            lineHeight: 1.2,
          }}>
            ETL Discovery, Intelligence, Rationalisation &amp; Migration
          </h1>

          <h2 style={{
            fontSize: '18px',
            fontWeight: '700',
            color: 'var(--color-text)',
            marginBottom: '8px',
          }}>
            Choose your workflow application
          </h2>

          <p style={{
            fontSize: '14px',
            color: 'var(--color-text-muted)',
            lineHeight: 1.5,
            maxWidth: '560px',
            margin: '0 auto',
          }}>
            Select the environment you want to work with.
          </p>
        </div>

        {/* Side-by-Side Equal Application Cards */}
        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))',
          gap: '24px',
          width: '100%',
          boxSizing: 'border-box',
        }}>
          {/* Card 1: Alteryx Workflows */}
          <div
            className="app-card"
            onMouseEnter={() => setHoveredCard('alteryx')}
            onMouseLeave={() => setHoveredCard(null)}
            style={{
              padding: '32px 28px',
              display: 'flex',
              flexDirection: 'column',
              justifyContent: 'space-between',
              background: 'var(--color-surface)',
              borderColor: hoveredCard === 'alteryx' ? 'var(--color-primary-border)' : 'var(--color-border)',
              borderRadius: 'var(--radius-lg)',
              transition: 'border-color 0.15s ease, box-shadow 0.15s ease',
              boxShadow: hoveredCard === 'alteryx' ? '0 4px 16px rgba(0, 0, 0, 0.12)' : '0 1px 3px rgba(0, 0, 0, 0.05)',
            }}
          >
            <div>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '16px' }}>
                <div style={{
                  width: '40px',
                  height: '40px',
                  borderRadius: 'var(--radius-md)',
                  background: 'var(--color-surface-secondary)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  color: 'var(--color-primary)',
                }}>
                  <FileCode size={20} />
                </div>
                <span style={{
                  fontSize: '11px',
                  fontWeight: '700',
                  textTransform: 'uppercase',
                  letterSpacing: '0.06em',
                  color: 'var(--color-text-muted)',
                  background: 'var(--color-surface-secondary)',
                  padding: '4px 8px',
                  borderRadius: 'var(--radius-sm)',
                  border: '1px solid var(--color-border)',
                }}>
                  .yxmd / .yxwz / .xml
                </span>
              </div>

              <h3 style={{
                fontSize: '18px',
                fontWeight: '700',
                color: 'var(--color-text)',
                marginBottom: '10px',
                letterSpacing: '-0.3px',
              }}>
                Alteryx Workflows
              </h3>

              <p style={{
                fontSize: '13px',
                color: 'var(--color-text-muted)',
                lineHeight: 1.5,
                marginBottom: '24px',
              }}>
                Analyse Alteryx workflows for intelligence, rationalisation &amp; migration. Inspect tool configurations, data lineage, business logic, and export generated Python transformations.
              </p>
            </div>

            <div>
              <button
                type="button"
                onClick={onSelectAlteryx}
                className="btn-primary"
                style={{
                  width: '100%',
                  padding: '10px 16px',
                  fontSize: '14px',
                  fontWeight: '600',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  gap: '8px',
                  cursor: 'pointer',
                }}
              >
                <span>Start</span>
                <ArrowRight size={16} />
              </button>
            </div>
          </div>

          {/* Card 2: Code-Based Workflows (Python) */}
          <div
            className="app-card"
            onMouseEnter={() => setHoveredCard('code')}
            onMouseLeave={() => setHoveredCard(null)}
            style={{
              padding: '32px 28px',
              display: 'flex',
              flexDirection: 'column',
              justifyContent: 'space-between',
              background: 'var(--color-surface)',
              borderColor: hoveredCard === 'code' ? 'var(--color-primary-border)' : 'var(--color-border)',
              borderRadius: 'var(--radius-lg)',
              transition: 'border-color 0.15s ease, box-shadow 0.15s ease',
              boxShadow: hoveredCard === 'code' ? '0 4px 16px rgba(0, 0, 0, 0.12)' : '0 1px 3px rgba(0, 0, 0, 0.05)',
            }}
          >
            <div>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '16px' }}>
                <div style={{
                  width: '40px',
                  height: '40px',
                  borderRadius: 'var(--radius-md)',
                  background: 'var(--color-surface-secondary)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  color: 'var(--color-primary)',
                }}>
                  <Terminal size={20} />
                </div>
                <span style={{
                  fontSize: '11px',
                  fontWeight: '700',
                  textTransform: 'uppercase',
                  letterSpacing: '0.06em',
                  color: 'var(--color-primary)',
                  background: 'var(--color-primary-subtle)',
                  padding: '4px 8px',
                  borderRadius: 'var(--radius-sm)',
                  border: '1px solid var(--color-primary-border)',
                }}>
                  Python
                </span>
              </div>

              <h3 style={{
                fontSize: '18px',
                fontWeight: '700',
                color: 'var(--color-text)',
                marginBottom: '10px',
                letterSpacing: '-0.3px',
              }}>
                Code-Based Workflows (Python)
              </h3>

              <div style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '6px',
                padding: '4px 10px',
                borderRadius: '6px',
                background: 'var(--color-surface-secondary)',
                border: '1px solid var(--color-border)',
                color: 'var(--color-text-secondary)',
                fontSize: '12px',
                fontWeight: '600',
                marginBottom: '14px',
              }}>
                PolicyCentre &amp; ClaimCentre as sources
              </div>

              <p style={{
                fontSize: '13px',
                color: 'var(--color-text-muted)',
                lineHeight: 1.5,
                marginBottom: '24px',
              }}>
                Open the separate code-based workflow application to inspect and process Python ETL pipelines and data transformations.
              </p>
            </div>

            <div>
              {(actionError || (configError && !codeBasedUrl)) && (
                <div
                  role="alert"
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '6px',
                    color: 'var(--color-error)',
                    fontSize: '12px',
                    marginBottom: '12px',
                    fontWeight: '500',
                  }}
                >
                  <AlertCircle size={14} />
                  <span>{actionError || configError}</span>
                </div>
              )}

              <button
                type="button"
                onClick={handleCodeBasedStart}
                disabled={configLoading}
                className="btn-primary"
                style={{
                  width: '100%',
                  padding: '10px 16px',
                  fontSize: '14px',
                  fontWeight: '600',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  gap: '8px',
                  cursor: configLoading ? 'not-allowed' : 'pointer',
                  opacity: configLoading ? 0.7 : 1,
                }}
              >
                {configLoading ? (
                  <>
                    <Loader2 size={16} className="animate-spin" />
                    <span>Loading...</span>
                  </>
                ) : (
                  <>
                    <span>Start</span>
                    <ArrowRight size={16} />
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
};
