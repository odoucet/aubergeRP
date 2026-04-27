#!/usr/bin/env node
/**
 * autotest.js — aubergeRP iterative UI autotest robot.
 *
 * Reads the test dialogue from dialogue.md, executes each scenario with
 * Playwright, collects UI bugs (assertion failures + screenshots), then
 * opens a GitHub Issue for every bug via the `gh` CLI and assigns it to
 * Copilot for automatic remediation.
 *
 * Usage:
 *   node autotest.js [--base-url <url>] [--no-issues] [--headless <bool>]
 *
 * Environment variables (override CLI flags):
 *   BASE_URL          Base URL of the running aubergeRP server (default: http://localhost:8123)
 *   CREATE_ISSUES     Set to "false" to skip GitHub issue creation
 *   HEADLESS          Set to "false" to show the browser window
 *   GH_REPO          GitHub repo slug (owner/repo) for issue creation; auto-detected if omitted
 */

'use strict';

const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');
const { spawnSync } = require('child_process');

// ── Configuration ─────────────────────────────────────────────────────────────

function parseArgs() {
  const args = process.argv.slice(2);
  const opts = {
    baseUrl: process.env.BASE_URL || 'http://localhost:8123',
    createIssues: process.env.CREATE_ISSUES !== 'false',
    headless: process.env.HEADLESS !== 'false',
    ghRepo: process.env.GH_REPO || null,
  };

  for (let i = 0; i < args.length; i++) {
    if (args[i] === '--base-url' && args[i + 1]) opts.baseUrl = args[++i];
    else if (args[i] === '--no-issues') opts.createIssues = false;
    else if (args[i] === '--headless' && args[i + 1]) opts.headless = args[++i] !== 'false';
    else if (args[i] === '--repo' && args[i + 1]) opts.ghRepo = args[++i];
  }

  // Normalise: strip trailing slash
  opts.baseUrl = opts.baseUrl.replace(/\/$/, '');
  return opts;
}

// ── Dialogue parser ───────────────────────────────────────────────────────────

/**
 * Parse dialogue.md into an array of scenario objects.
 * Each scenario: { name: string, steps: Array<{ action, args }> }
 */
function parseDialogue(mdPath) {
  const content = fs.readFileSync(mdPath, 'utf-8');
  const lines = content.split('\n');
  const scenarios = [];
  let current = null;

  for (const raw of lines) {
    const line = raw.trimEnd();

    if (line.startsWith('## Scenario:')) {
      if (current) scenarios.push(current);
      current = {
        name: line.slice('## Scenario:'.length).trim(),
        steps: [],
      };
      continue;
    }

    if (!current) continue;

    // Step lines: "- ACTION: args"
    const stepMatch = line.match(/^[-*]\s+([A-Z_]+):\s*(.*)/);
    if (stepMatch) {
      current.steps.push({
        action: stepMatch[1],
        args: stepMatch[2].trim(),
      });
    }
  }

  if (current) scenarios.push(current);
  return scenarios;
}

// ── Step executor ─────────────────────────────────────────────────────────────

const TIMEOUT = 8123; // ms for waits

/**
 * Execute a single step against the Playwright page.
 * Throws on failure so the caller can record a bug.
 */
async function executeStep(page, step, config, screenshotDir) {
  const { action, args } = step;
  const resolveUrl = (u) => (u.startsWith('http') ? u : config.baseUrl + u);

  switch (action) {
    case 'NAVIGATE':
      await page.goto(resolveUrl(args), { waitUntil: 'domcontentloaded', timeout: 15000 });
      break;

    case 'EXPECT_TITLE': {
      const title = await page.title();
      if (!title.includes(args)) {
        throw new Error(`Page title is "${title}" — expected to contain "${args}"`);
      }
      break;
    }

    case 'EXPECT_VISIBLE':
      try {
        await page.waitForSelector(args, { state: 'visible', timeout: TIMEOUT });
      } catch (_) {
        throw new Error(`Element "${args}" is not visible`);
      }
      break;

    case 'EXPECT_NOT_VISIBLE': {
      // Passes if the element is absent or hidden
      const el = await page.$(args);
      if (el) {
        const visible = await el.isVisible();
        if (visible) {
          throw new Error(`Element "${args}" should not be visible but is`);
        }
      }
      break;
    }

    case 'EXPECT_TEXT': {
      const pipeIdx = args.indexOf('|');
      if (pipeIdx < 0) throw new Error(`EXPECT_TEXT requires "selector | text" format`);
      const selector = args.slice(0, pipeIdx).trim();
      const expected = args.slice(pipeIdx + 1).trim();
      try {
        await page.waitForSelector(selector, { timeout: TIMEOUT });
      } catch (_) {
        throw new Error(`Element "${selector}" not found`);
      }
      const text = await page.textContent(selector);
      if (!text || !text.includes(expected)) {
        throw new Error(`Element "${selector}" has text "${(text || '').slice(0, 200)}" — expected to contain "${expected}"`);
      }
      break;
    }

    case 'EXPECT_ATTR': {
      const parts = args.split('|').map((s) => s.trim());
      if (parts.length < 3) throw new Error(`EXPECT_ATTR requires "selector | attr | value" format`);
      const [attrSel, attr, expectedVal] = parts;
      const actual = await page.getAttribute(attrSel, attr);
      if (actual !== expectedVal) {
        throw new Error(`Element "${attrSel}" attr "${attr}" is "${actual}" — expected "${expectedVal}"`);
      }
      break;
    }

    case 'CLICK':
      try {
        await page.waitForSelector(args, { state: 'visible', timeout: TIMEOUT });
        await page.click(args);
      } catch (err) {
        throw new Error(`Failed to click "${args}": ${err.message}`);
      }
      break;

    case 'FILL': {
      const pipeIdx = args.indexOf('|');
      if (pipeIdx < 0) throw new Error(`FILL requires "selector | text" format`);
      const fillSel = args.slice(0, pipeIdx).trim();
      const fillText = args.slice(pipeIdx + 1).trim();
      try {
        await page.waitForSelector(fillSel, { state: 'visible', timeout: TIMEOUT });
        await page.fill(fillSel, fillText);
      } catch (err) {
        throw new Error(`Failed to fill "${fillSel}": ${err.message}`);
      }
      break;
    }

    case 'PRESS': {
      const pipeIdx = args.indexOf('|');
      if (pipeIdx < 0) throw new Error(`PRESS requires "selector | key" format`);
      const pressSel = args.slice(0, pipeIdx).trim();
      const key = args.slice(pipeIdx + 1).trim();
      await page.press(pressSel, key);
      break;
    }

    case 'WAIT_FOR':
      try {
        await page.waitForSelector(args, { timeout: TIMEOUT });
      } catch (_) {
        throw new Error(`Element "${args}" never appeared within ${TIMEOUT}ms`);
      }
      break;

    case 'WAIT_MS':
      await page.waitForTimeout(parseInt(args, 10));
      break;

    case 'SET_VIEWPORT': {
      // "WIDTHxHEIGHT" e.g. "375x812"
      const [w, h] = args.split('x').map((n) => parseInt(n, 10));
      if (!w || !h) throw new Error(`SET_VIEWPORT requires "WIDTHxHEIGHT" format, got "${args}"`);
      await page.setViewportSize({ width: w, height: h });
      break;
    }

    case 'SCREENSHOT': {
      const filename = `${args.replace(/[^a-zA-Z0-9_-]/g, '_')}.png`;
      await page.screenshot({ path: path.join(screenshotDir, filename), fullPage: true });
      break;
    }

    default:
      console.warn(`  ⚠  Unknown action "${action}" — skipping`);
  }
}

// ── Scenario runner ───────────────────────────────────────────────────────────

async function runScenario(browser, scenario, config, screenshotDir) {
  const bugs = [];
  const page = await browser.newPage();

  // Capture JS console errors to surface as potential bugs
  const consoleErrors = [];
  page.on('console', (msg) => {
    if (msg.type() === 'error') consoleErrors.push(msg.text());
  });
  page.on('pageerror', (err) => consoleErrors.push(err.message));

  console.log(`\n▶  ${scenario.name}`);

  for (const step of scenario.steps) {
    const label = `${step.action}: ${step.args}`;
    try {
      await executeStep(page, step, config, screenshotDir);
      if (step.action !== 'SCREENSHOT' && step.action !== 'WAIT_MS') {
        console.log(`   ✓  ${label}`);
      }
    } catch (err) {
      console.error(`   ✗  ${label}`);
      console.error(`      ${err.message}`);

      // Capture failure screenshot
      const safeName = `${scenario.name}_${step.action}`.replace(/[^a-zA-Z0-9_-]/g, '_').slice(0, 80);
      const screenshotPath = path.join(screenshotDir, `BUG_${safeName}.png`);
      try {
        await page.screenshot({ path: screenshotPath, fullPage: true });
      } catch (_) {
        // ignore screenshot errors
      }

      bugs.push({
        scenario: scenario.name,
        step: label,
        error: err.message,
        screenshot: screenshotPath,
        url: page.url(),
        consoleErrors: [...consoleErrors],
      });

      // Continue with remaining steps (do not abort scenario on single failure)
    }
  }

  await page.close();
  return bugs;
}

// ── GitHub issue creation ─────────────────────────────────────────────────────

function detectGhRepo() {
  const result = spawnSync('gh', ['repo', 'view', '--json', 'nameWithOwner', '-q', '.nameWithOwner'], {
    encoding: 'utf-8',
  });
  if (result.status === 0) return result.stdout.trim();
  return null;
}

function ghAvailable() {
  const result = spawnSync('gh', ['auth', 'status'], { encoding: 'utf-8' });
  return result.status === 0;
}

function createGithubIssue(bug, ghRepo) {
  const screenshotBasename = path.basename(bug.screenshot);
  const consoleSection =
    bug.consoleErrors.length > 0
      ? `\n### JavaScript Console Errors\n\`\`\`\n${bug.consoleErrors.slice(0, 10).join('\n')}\n\`\`\``
      : '';

  const body = `## 🐛 UI Bug Report — Automated Autotest

**Scenario**: \`${bug.scenario}\`
**Failing step**: \`${bug.step}\`
**Error**: ${bug.error}
**Page URL at failure**: ${bug.url}
${consoleSection}

### Screenshot

A screenshot was captured at failure time: \`${screenshotBasename}\`
_(Screenshots are saved in \`tests/e2e/screenshots/\` during the test run.)_

### How to Reproduce

1. Start the aubergeRP server: \`make run\`
2. Run the autotest robot:
   \`\`\`bash
   cd tests/e2e
   npm ci
   npx playwright install chromium
   node autotest.js
   \`\`\`

---
*Reported automatically by the [aubergeRP UI autotest robot](tests/e2e/autotest.js).*
*Test dialogue: [tests/e2e/dialogue.md](tests/e2e/dialogue.md)*`;

  const repoArgs = ghRepo ? ['--repo', ghRepo] : [];
  const result = spawnSync(
    'gh',
    [
      'issue', 'create',
      '--title', `🐛 UI Bug: [${bug.scenario}] ${bug.step}`,
      '--body', body,
      '--label', 'bug',
      '--assignee', 'copilot',
      ...repoArgs,
    ],
    { encoding: 'utf-8' },
  );

  if (result.error) {
    // gh binary error (not found, etc.)
    console.error(`   gh spawn error: ${result.error.message}`);
    return null;
  }
  if (result.status !== 0) {
    // gh returned non-zero — possibly "copilot" assignee not available; retry without it
    const result2 = spawnSync(
      'gh',
      [
        'issue', 'create',
        '--title', `🐛 UI Bug: [${bug.scenario}] ${bug.step}`,
        '--body', body + '\n\n> **Note**: Please assign this issue to Copilot for automated remediation.',
        '--label', 'bug',
        ...repoArgs,
      ],
      { encoding: 'utf-8' },
    );
    if (result2.status !== 0) {
      console.error(`   gh issue create failed: ${result2.stderr}`);
      return null;
    }
    const url = result2.stdout.trim();
    console.log(`   Issue created (without Copilot assignee): ${url}`);
    return url;
  }

  const url = result.stdout.trim();
  console.log(`   Issue created: ${url}`);
  return url;
}

// ── Main ──────────────────────────────────────────────────────────────────────

async function main() {
  const config = parseArgs();
  const dialoguePath = path.join(__dirname, 'dialogue.md');
  const screenshotDir = path.join(__dirname, 'screenshots');

  // Validate preconditions
  if (!fs.existsSync(dialoguePath)) {
    console.error(`dialogue.md not found at ${dialoguePath}`);
    process.exit(1);
  }
  fs.mkdirSync(screenshotDir, { recursive: true });

  // Detect GitHub repo for issue creation
  let ghRepo = config.ghRepo;
  if (config.createIssues && !ghRepo) {
    ghRepo = detectGhRepo();
    if (!ghRepo) {
      console.warn('⚠  Could not detect GitHub repo. Issues will not be created.');
      config.createIssues = false;
    }
  }
  if (config.createIssues && !ghAvailable()) {
    console.warn('⚠  gh CLI not authenticated. Run `gh auth login`. Issues will not be created.');
    config.createIssues = false;
  }

  // Parse dialogue
  const scenarios = parseDialogue(dialoguePath);
  console.log(`\naubergeRP UI Autotest Robot`);
  console.log(`${'═'.repeat(50)}`);
  console.log(`Base URL  : ${config.baseUrl}`);
  console.log(`Scenarios : ${scenarios.length}`);
  console.log(`Issues    : ${config.createIssues ? `enabled → ${ghRepo}` : 'disabled (--no-issues)'}`);
  console.log(`Headless  : ${config.headless}`);
  console.log(`${'═'.repeat(50)}`);

  // Launch browser (--no-sandbox is required in container / CI environments)
  const browser = await chromium.launch({
    headless: config.headless,
    args: ['--no-sandbox', '--disable-dev-shm-usage'],
  });
  const allBugs = [];

  for (const scenario of scenarios) {
    const bugs = await runScenario(browser, scenario, config, screenshotDir);
    allBugs.push(...bugs);
  }

  await browser.close();

  // Summary
  console.log(`\n${'═'.repeat(50)}`);
  const passed = scenarios.length - new Set(allBugs.map((b) => b.scenario)).size;
  console.log(`Scenarios : ${scenarios.length} total | ${passed} clean | ${allBugs.length} bug(s)`);

  if (allBugs.length === 0) {
    console.log('✅  No bugs found — all scenarios passed!');
    process.exit(0);
  }

  console.log(`\nBugs found:`);
  allBugs.forEach((b, i) => {
    console.log(`  ${i + 1}. [${b.scenario}] ${b.step}`);
    console.log(`     ${b.error}`);
  });

  // Open GitHub issues
  if (config.createIssues) {
    console.log(`\nCreating ${allBugs.length} GitHub issue(s)...`);
    for (const bug of allBugs) {
      createGithubIssue(bug, ghRepo);
    }
  }

  process.exit(allBugs.length > 0 ? 1 : 0);
}

main().catch((err) => {
  console.error('\nFatal error in autotest robot:', err);
  process.exit(2);
});
