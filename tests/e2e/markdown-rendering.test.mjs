/**
 * markdown-rendering.test.mjs
 *
 * Playwright unit tests for Markdown-formatted roleplay dialog rendering.
 * Verifies that:
 *   - *[stage direction]* renders as <em>[...]</em> (not rp-hint span)
 *   - **CharName** renders as <strong> with accent colour
 *   - Plain dialogue text is not wrapped in <em> or <strong>
 *   - User-typed [action] hints still get the rp-hint pill style
 */
import test from 'node:test';
import assert from 'node:assert/strict';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

import { chromium } from 'playwright';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const harnessUrl = pathToFileURL(path.join(__dirname, 'harness', 'markdown-rendering.html')).href;

async function withPage(fn) {
  const browser = await chromium.launch({
    headless: true,
    args: ['--no-sandbox', '--disable-dev-shm-usage', '--allow-file-access-from-files'],
  });
  const page = await browser.newPage();
  try {
    await page.goto(harnessUrl, { waitUntil: 'load' });
    await fn(page);
  } finally {
    await page.close();
    await browser.close();
  }
}

test('stage direction *[text]* renders as <em> element inside assistant bubble', async () => {
  await withPage(async (page) => {
    await page.evaluate(() => {
      window.__markdownHarness.renderAssistantMessage('**Aria** *[Her voice trembles]* I never wanted this.');
    });

    const emCount = await page.$$eval('.msg.assistant .msg-bubble em', (els) => els.length);
    assert.ok(emCount >= 1, 'Expected at least one <em> element for stage direction');

    const emText = await page.$eval('.msg.assistant .msg-bubble em', (el) => el.textContent);
    assert.ok(emText.includes('[Her voice trembles]'), `Expected stage direction text, got: ${emText}`);
  });
});

test('stage direction inside <em> is NOT double-wrapped with rp-hint span', async () => {
  await withPage(async (page) => {
    await page.evaluate(() => {
      window.__markdownHarness.renderAssistantMessage('**Aria** *[She looks away]* Fine.');
    });

    // The text "[She looks away]" should be inside <em>, not inside .rp-hint
    const rpHintInsideEm = await page.$$eval(
      '.msg.assistant .msg-bubble em .rp-hint',
      (els) => els.length,
    );
    assert.equal(rpHintInsideEm, 0, '<em> stage directions must not be wrapped in .rp-hint');
  });
});

test('character name **bold** renders as <strong> element', async () => {
  await withPage(async (page) => {
    await page.evaluate(() => {
      window.__markdownHarness.renderAssistantMessage('**Aria** *[smiles]* Hello there.');
    });

    const strongCount = await page.$$eval('.msg.assistant .msg-bubble strong', (els) => els.length);
    assert.ok(strongCount >= 1, 'Expected at least one <strong> element for character name');

    const strongText = await page.$eval('.msg.assistant .msg-bubble strong', (el) => el.textContent);
    assert.equal(strongText, 'Aria', `Expected character name, got: ${strongText}`);
  });
});

test('plain dialogue text is not wrapped in <em> or <strong>', async () => {
  await withPage(async (page) => {
    await page.evaluate(() => {
      window.__markdownHarness.renderAssistantMessage('I step forward and open the door.');
    });

    const emCount = await page.$$eval('.msg.assistant .msg-bubble em', (els) => els.length);
    const strongCount = await page.$$eval('.msg.assistant .msg-bubble strong', (els) => els.length);
    assert.equal(emCount, 0, 'Plain dialogue must not have <em> elements');
    assert.equal(strongCount, 0, 'Plain dialogue must not have <strong> elements');
  });
});

test('user-typed [action] hints still receive rp-hint pill styling', async () => {
  await withPage(async (page) => {
    await page.evaluate(() => {
      window.__markdownHarness.renderUserMessage('I step closer. [whispers] Hello.');
    });

    const rpHintCount = await page.$$eval('.msg.user .msg-bubble .rp-hint', (els) => els.length);
    assert.ok(rpHintCount >= 1, 'User [action] hints must be styled with rp-hint');

    const rpHintText = await page.$eval('.msg.user .msg-bubble .rp-hint', (el) => el.textContent);
    assert.ok(rpHintText.includes('[whispers]'), `Expected whispers hint, got: ${rpHintText}`);
  });
});

test('<em> stage directions in assistant bubble have muted colour (CSS)', async () => {
  await withPage(async (page) => {
    await page.evaluate(() => {
      window.__markdownHarness.renderAssistantMessage('**Aria** *[quietly]* I see.');
    });

    const emColor = await page.$eval(
      '.msg.assistant .msg-bubble em',
      (el) => getComputedStyle(el).color,
    );
    // The computed color should differ from the default text colour (i.e., muted)
    const defaultColor = await page.$eval(
      '.msg.assistant .msg-bubble',
      (el) => getComputedStyle(el).color,
    );
    assert.notEqual(emColor, defaultColor, '<em> stage direction should use muted colour, not default text colour');
  });
});
