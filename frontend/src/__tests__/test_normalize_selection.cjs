// Node.js test script for normalizeSelection logic
const assert = require('assert');

const SUPPORTED_EXTENSIONS = ['.yxmd', '.yxwz', '.xml'];

function normalizeSelection(entries) {
  const seenPaths = new Set();
  const validWorkflows = [];
  let ignoredCount = 0;

  for (const entry of entries) {
    const fname = entry.file.name;
    // Skip macOS metadata and hidden files
    if (fname.startsWith('.') || entry.path.includes('__MACOSX')) {
      ignoredCount++;
      continue;
    }

    const ext = '.' + (fname.split('.').pop() || '').toLowerCase();
    if (SUPPORTED_EXTENSIONS.includes(ext)) {
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

// 1. Single valid file
{
  const res = normalizeSelection([{ file: { name: 'Claims.yxmd' }, path: 'Claims.yxmd' }]);
  assert.strictEqual(res.validWorkflows.length, 1);
  assert.strictEqual(res.ignoredCount, 0);
  console.log('✓ 1. Single valid file passed');
}

// 2. Case-insensitive extensions (.YXMD, .YXWZ, .XML)
{
  const res = normalizeSelection([
    { file: { name: 'Claims.YXMD' }, path: 'Claims.YXMD' },
    { file: { name: 'Customer.Yxwz' }, path: 'Customer.Yxwz' },
    { file: { name: 'Finance.XML' }, path: 'Finance.XML' },
  ]);
  assert.strictEqual(res.validWorkflows.length, 3);
  assert.strictEqual(res.ignoredCount, 0);
  console.log('✓ 2. Case-insensitive extensions passed');
}

// 3. Folder with 1 workflow and unsupported files (.md, .txt, .png, .xlsx)
{
  const res = normalizeSelection([
    { file: { name: 'Claims.yxmd' }, path: 'ETL/Claims.yxmd' },
    { file: { name: 'README.md' }, path: 'ETL/README.md' },
    { file: { name: 'notes.txt' }, path: 'ETL/notes.txt' },
    { file: { name: 'screenshot.png' }, path: 'ETL/screenshot.png' },
    { file: { name: 'report.xlsx' }, path: 'ETL/report.xlsx' },
  ]);
  assert.strictEqual(res.validWorkflows.length, 1);
  assert.strictEqual(res.validWorkflows[0].file.name, 'Claims.yxmd');
  assert.strictEqual(res.ignoredCount, 4);
  console.log('✓ 3. Folder with 1 workflow and unsupported files passed');
}

// 4. Nested folders preserving relative path and distinguishing identical filenames
{
  const res = normalizeSelection([
    { file: { name: 'A.yxmd' }, path: 'Sales/A.yxmd' },
    { file: { name: 'A.yxmd' }, path: 'Finance/A.yxmd' },
  ]);
  assert.strictEqual(res.validWorkflows.length, 2);
  assert.strictEqual(res.validWorkflows[0].path, 'Sales/A.yxmd');
  assert.strictEqual(res.validWorkflows[1].path, 'Finance/A.yxmd');
  console.log('✓ 4. Nested folders with identical filenames passed');
}

// 5. Empty folder (0 valid workflows)
{
  const res = normalizeSelection([
    { file: { name: 'README.md' }, path: 'ETL/README.md' },
    { file: { name: 'notes.txt' }, path: 'ETL/notes.txt' },
  ]);
  assert.strictEqual(res.validWorkflows.length, 0);
  assert.strictEqual(res.ignoredCount, 2);
  console.log('✓ 5. Empty folder passed');
}

// 6. Deduplication of identical file entries
{
  const res = normalizeSelection([
    { file: { name: 'A.yxmd' }, path: 'A.yxmd' },
    { file: { name: 'A.yxmd' }, path: 'A.yxmd' },
  ]);
  assert.strictEqual(res.validWorkflows.length, 1);
  console.log('✓ 6. Deduplication passed');
}

console.log('\nALL NORMALIZESELECTION TESTS PASSED SUCCESSFULLY!');
