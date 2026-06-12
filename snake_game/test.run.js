// Runs every snake_game headless test file with plain `node` and tallies the
// PASS:/FAIL: assertion lines across all of them. Zero dependencies.
// Run: node snake_game/test.run.js

'use strict';

const { spawnSync } = require('child_process');
const path = require('path');

const files = [
  'test.headless.js', // original smoke tests
  'test.powerups.js',
  'test.collisions.js',
  'test.scoring.js',
  'test.statemachine.js',
];

let pass = 0;
let fail = 0;
const failedFiles = [];

for (const f of files) {
  const res = spawnSync(process.execPath, [path.join(__dirname, f)], { encoding: 'utf8' });
  const out = (res.stdout || '') + (res.stderr || '');
  process.stdout.write(`\n=== ${f} ===\n${out}`);
  pass += (out.match(/^PASS:/gm) || []).length;
  fail += (out.match(/^FAIL:/gm) || []).length;
  if (res.status !== 0) failedFiles.push(f);
}

console.log(`\n${'='.repeat(60)}`);
console.log(`Total: ${pass} passed, ${fail} failed across ${files.length} files.`);
if (failedFiles.length > 0) {
  console.error('Failing files:', failedFiles.join(', '));
  process.exit(1);
}
console.log('All snake_game headless tests passed.');
