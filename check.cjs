'use strict';

const { execFileSync } = require('node:child_process');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');

function checkPaths(files) {
  const firstByKey = new Map();
  const conflicts = new Map();
  for (const file of files) {
    const components = file.split('/');
    let prefix = '';
    let key = '';
    for (const [index, part] of components.entries()) {
      prefix += (prefix ? '/' : '') + part;
      key += (key ? '/' : '') + part.normalize('NFC').toLowerCase();
      const kind = index === components.length - 1 ? 'file' : 'directory';
      const first = firstByKey.get(key);
      if (!first) {
        firstByKey.set(key, { path: prefix, kind });
      } else if (first.path !== prefix || first.kind !== kind) {
        const pair = [first.path, prefix];
        conflicts.set(JSON.stringify(pair), { paths: pair, reason: first.kind === kind ? 'name collision' : 'file/directory collision' });
      }
    }
  }
  return { files: files.length, count: conflicts.size, collisions: [...conflicts.values()] };
}

function run() {
  const fail = (process.env.INPUT_FAIL_ON_COLLISION || 'true').toLowerCase();
  if (!['true', 'false'].includes(fail)) throw new Error('fail_on_collision must be true or false.');
  const raw = execFileSync('git', ['ls-files', '--cached', '--full-name', '-z'], {
    cwd: process.env.GITHUB_WORKSPACE || process.cwd(), maxBuffer: 64 * 1024 * 1024
  });
  const files = new TextDecoder('utf-8', { fatal: true, ignoreBOM: true }).decode(raw).split('\0').filter(Boolean);
  const report = checkPaths(files);
  const folder = fs.mkdtempSync(path.join(process.env.RUNNER_TEMP || os.tmpdir(), 'release-path-'));
  const output = path.join(folder, 'report.json');
  fs.writeFileSync(output, JSON.stringify(report, null, 2) + '\n');
  if (process.env.GITHUB_OUTPUT) fs.appendFileSync(process.env.GITHUB_OUTPUT, 'collisions=' + report.count + '\nreport=' + output + '\n');
  console.log('Checked ' + report.files + ' tracked files. Found ' + report.count + ' path collisions.');
  console.log('Report: ' + output);
  if (report.count && fail === 'true') process.exitCode = 1;
}

if (require.main === module) {
  try { run(); } catch (error) { console.error(error.message); process.exitCode = 2; }
}

module.exports = { checkPaths };
