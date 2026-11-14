#!/usr/bin/env node
const { execSync } = require('child_process');
const pkg = require('./package.json');
const version = pkg.version;
// Always upgrade to the exact version matching this npm package.
// Using `pip install urace` without --upgrade would silently skip the update
// if any older version is already installed.
try {
  execSync(`pip install --upgrade "urace==${version}" --quiet`, { stdio: 'inherit' });
  console.log(`urace ${version} installed via pip. Run: urace --help`);
} catch (e) {
  console.error(`pip not found. Install Python 3.11+ and pip, then run: pip install "urace==${version}"`);
  process.exit(1);
}
