import test from 'node:test';
import assert from 'node:assert/strict';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

import { chromium } from 'playwright';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const harnessUrl = pathToFileURL(path.join(__dirname, 'harness', 'chat-streaming.html')).href;

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

test('generate-image button is hidden by default', async () => {
  await withPage(async (page) => {
    const display = await page.$eval('#generate-image-btn', (el) => el.style.display);
    assert.equal(display, 'none');
  });
});

test('generate-image button becomes visible when image connector is set', async () => {
  await withPage(async (page) => {
    await page.evaluate(() => window.__chatHarness.setImageConnector(true));
    const display = await page.$eval('#generate-image-btn', (el) => getComputedStyle(el).display);
    assert.notEqual(display, 'none');
  });
});

test('generate-image button is hidden when image connector is removed', async () => {
  await withPage(async (page) => {
    await page.evaluate(() => {
      window.__chatHarness.setImageConnector(true);
      window.__chatHarness.setImageConnector(false);
    });
    const display = await page.$eval('#generate-image-btn', (el) => el.style.display);
    assert.equal(display, 'none');
  });
});

test('updateImageConnectorStatus tracks connector presence in state', async () => {
  await withPage(async (page) => {
    const before = await page.evaluate(() => window.__chatHarness.getHasImageConnector());
    assert.equal(before, false);

    await page.evaluate(() => window.__chatHarness.setImageConnector(true));
    const after = await page.evaluate(() => window.__chatHarness.getHasImageConnector());
    assert.equal(after, true);
  });
});

test('generate-image button has a distinctive label', async () => {
  await withPage(async (page) => {
    const label = await page.$eval('#generate-image-btn', (el) => el.getAttribute('aria-label'));
    assert.ok(label && label.length > 0, 'aria-label should be non-empty');
    // Should describe image generation in some way
    const text = (await page.$eval('#generate-image-btn', (el) => el.textContent)).trim();
    assert.ok(text.length > 0, 'button should have visible content (icon)');
  });
});

test('generate-image button is still present after toggling connector status multiple times', async () => {
  await withPage(async (page) => {
    for (let i = 0; i < 3; i++) {
      await page.evaluate(() => window.__chatHarness.setImageConnector(true));
      await page.evaluate(() => window.__chatHarness.setImageConnector(false));
    }
    const btn = await page.$('#generate-image-btn');
    assert.ok(btn !== null, 'button element must still exist in the DOM');
    const display = await page.$eval('#generate-image-btn', (el) => el.style.display);
    assert.equal(display, 'none');
  });
});
