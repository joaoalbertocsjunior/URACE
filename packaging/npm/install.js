#!/usr/bin/env node
const { execSync } = require('child_process');
try {
  execSync('pip install urace --quiet', { stdio: 'inherit' });
  console.log('urace installed via pip. Run: urace --help');
} catch (e) {
  console.error('pip not found. Install Python 3.8+ and pip, then run: pip install urace');
  process.exit(1);
}
