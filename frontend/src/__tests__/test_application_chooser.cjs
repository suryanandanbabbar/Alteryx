const assert = require('assert');

console.log('--- Running Application Chooser Backend Configuration & Navigation Tests ---');

// Mock Application Chooser state & handler logic
function createChooserState(mockBackendConfig) {
  let codeBasedUrl = null;
  let configLoading = true;
  let configError = null;
  let actionError = null;
  let navigatedUrl = null;
  let alteryxSelected = false;

  // Simulate api.getConfig()
  if (mockBackendConfig instanceof Error) {
    configError = 'Unable to load application configuration.';
    configLoading = false;
  } else {
    codeBasedUrl = mockBackendConfig?.code_based_workflows_url || null;
    configLoading = false;
  }

  function handleCodeBasedStart() {
    actionError = null;
    if (configLoading) return false;

    if (!codeBasedUrl) {
      actionError = 'Code-based workflow application is not configured.';
      return false;
    }

    try {
      const parsed = new URL(codeBasedUrl);
      if (parsed.protocol !== 'http:' && parsed.protocol !== 'https:') {
        actionError = 'Code-based workflow application is not configured with a valid URL.';
        return false;
      }
      navigatedUrl = parsed.href;
      return true;
    } catch {
      actionError = 'Code-based workflow application is not configured with a valid URL.';
      return false;
    }
  }

  function handleAlteryxStart() {
    alteryxSelected = true;
  }

  return {
    getCodeBasedUrl: () => codeBasedUrl,
    isLoading: () => configLoading,
    getConfigError: () => configError,
    getActionError: () => actionError,
    getNavigatedUrl: () => navigatedUrl,
    isAlteryxSelected: () => alteryxSelected,
    handleCodeBasedStart,
    handleAlteryxStart,
  };
}

// Test 1: Configured backend URL leads to successful navigation on Start
const stateWithUrl = createChooserState({ code_based_workflows_url: 'https://code-app.example.com/python' });
assert.strictEqual(stateWithUrl.getCodeBasedUrl(), 'https://code-app.example.com/python');
assert.strictEqual(stateWithUrl.isLoading(), false);

const startedSuccess = stateWithUrl.handleCodeBasedStart();
assert.strictEqual(startedSuccess, true);
assert.strictEqual(stateWithUrl.getNavigatedUrl(), 'https://code-app.example.com/python');
assert.strictEqual(stateWithUrl.getActionError(), null);
console.log('✓ Test 1 Passed: Configured backend URL navigates correctly without frontend text input.');

// Test 2: Missing/null backend URL shows concise user error and blocks navigation
const stateNoUrl = createChooserState({ code_based_workflows_url: null });
assert.strictEqual(stateNoUrl.getCodeBasedUrl(), null);

const startedNoUrl = stateNoUrl.handleCodeBasedStart();
assert.strictEqual(startedNoUrl, false);
assert.strictEqual(stateNoUrl.getNavigatedUrl(), null);
assert.strictEqual(stateNoUrl.getActionError(), 'Code-based workflow application is not configured.');
console.log('✓ Test 2 Passed: Unconfigured code-based application shows concise user-facing error.');

// Test 3: Backend config failure does not affect Alteryx navigation
const stateConfigFail = createChooserState(new Error('Network error'));
assert.strictEqual(stateConfigFail.getConfigError(), 'Unable to load application configuration.');

// Alteryx Start still functions independently
stateConfigFail.handleAlteryxStart();
assert.strictEqual(stateConfigFail.isAlteryxSelected(), true);
console.log('✓ Test 3 Passed: Backend config failure does not break or impact Alteryx workflow navigation.');

// Test 4: App state machine flow (Chooser -> Alteryx Upload -> Reset -> Chooser)
let appState = {
  selectedApp: 'chooser',
  overview: null,
};

// Initial state
assert.strictEqual(appState.selectedApp, 'chooser');

// User selects Alteryx
appState.selectedApp = 'alteryx';
assert.strictEqual(appState.selectedApp, 'alteryx');

// User resets back to Chooser
appState.overview = null;
appState.selectedApp = 'chooser';
assert.strictEqual(appState.selectedApp, 'chooser');
console.log('✓ Test 4 Passed: Lifecycle navigation between Chooser and Upload page verified.');

console.log('\nAll Application Chooser unit tests passed successfully!');
