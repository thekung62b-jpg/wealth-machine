/*
 * Playwright loopback smoke test - Little Homie tooling
 * Audited 2026-08-17, see ops/TOOL_AUDIT_2026-08-17.md item 1.
 *
 * SAFETY: binds to 127.0.0.1 on an ephemeral port and drives a headless
 * browser against that local page ONLY. It contacts no external host, reads
 * no credential, and touches no repository file. Safe to re-run any time.
 *
 * REQUIRES: the pinned `playwright` package (1.56.1) resolvable by node, plus
 * its matching browser build. This repo does NOT vendor it - point NODE_PATH
 * at the existing install rather than adding a new one:
 *   node ops/tooling/playwright_smoke.js
 *   NODE_PATH=<path-to>/node_modules node ops/tooling/playwright_smoke.js
 * A "Cannot find module 'playwright'" error means the pinned install is not
 * on this host - that is a setup gap, not a smoke-test failure.
 *
 * Run:  node ops/tooling/playwright_smoke.js
 * PASS = exit code 0 and "SMOKE RESULT: PASS" on the last line.
 *
 * Verified 2026-08-17 on the audit host: PASS, exit 0, Chromium 141.0.7390.37.
 */

const { chromium } = require('playwright');
const http = require('http');
const fs = require('fs');
const os = require('os');
const path = require('path');

const PAGE = `<!doctype html><html><body>
<h1 id="t">CODEX SMOKE TEST</h1>
<button id="b" onclick="document.getElementById('t').textContent='CLICK-OK'">go</button>
</body></html>`;

const shotPath = path.join(os.tmpdir(), 'pw_smoke_shot.png');

const server = http.createServer((req, res) => {
  res.writeHead(200, { 'Content-Type': 'text/html' });
  res.end(PAGE);
});

server.listen(0, '127.0.0.1', async () => {
  const url = `http://127.0.0.1:${server.address().port}/`;
  console.log('LOOPBACK URL:', url);

  let browser;
  try {
    browser = await chromium.launch({ headless: true });
    console.log('BROWSER:', browser.version());

    const page = await browser.newPage();
    await page.goto(url);

    const before = await page.textContent('#t');
    console.log('TITLE-BEFORE:', before);

    await page.click('#b');
    const after = await page.textContent('#t');
    console.log('TITLE-AFTER :', after);

    await page.screenshot({ path: shotPath });
    const bytes = fs.statSync(shotPath).size;
    console.log('SCREENSHOT BYTES:', bytes);

    // Assert rather than assume - a run that renders nothing must not pass.
    if (before !== 'CODEX SMOKE TEST') throw new Error('initial DOM text wrong');
    if (after !== 'CLICK-OK') throw new Error('click did not mutate the DOM');
    if (!bytes) throw new Error('screenshot was empty');

    console.log('SMOKE RESULT: PASS');
  } catch (err) {
    console.error('SMOKE RESULT: FAIL -', err.message);
    process.exitCode = 1;
  } finally {
    if (browser) await browser.close();
    server.close();
    fs.rmSync(shotPath, { force: true });
  }
});
