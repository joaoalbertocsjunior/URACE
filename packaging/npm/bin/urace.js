#!/usr/bin/env node
const { spawn } = require('child_process');
const proc = spawn('urace', process.argv.slice(2), { stdio: 'inherit', shell: false });
proc.on('exit', (code) => process.exit(code || 0));
