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
    args: ['--no-sandbox', '--disable-dev-shm-usage'],
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

test('shows a visible in-progress media status before assistant text arrives', async () => {
  await withPage(async (page) => {
    await page.evaluate(() => window.__chatHarness.startImage('a lantern-lit tavern interior'));

    await page.waitForSelector('.msg-media-status', { state: 'visible' });
    await page.waitForSelector('.img-placeholder', { state: 'visible' });

    const statusText = await page.textContent('.msg-media-status');
    const placeholderText = await page.textContent('.img-placeholder');
    const bubbleDisplay = await page.$eval('.msg-bubble', (el) => getComputedStyle(el).display);

    assert.ok(statusText.includes('Image generation in progress'));
    assert.ok(placeholderText.includes('Generating image'));
    assert.ok(placeholderText.includes('a lantern-lit tavern interior'));
    assert.equal(bubbleDisplay, 'none');
  });
});

test('updates progress and hides the pending status once the image completes', async () => {
  await withPage(async (page) => {
    await page.evaluate(() => {
      window.__chatHarness.startImage('storm over the keep');
      window.__chatHarness.progressImage(3, 5);
    });

    const labelText = await page.textContent('.img-progress-label');
    assert.ok(labelText.includes('3 / 5'));

    await page.evaluate(() => window.__chatHarness.completeImage('https://example.test/final-image.png'));
    await page.waitForSelector('.msg-image', { state: 'attached' });

    const statusVisible = await page.isVisible('.msg-media-status').catch(() => false);
    const imageSrc = await page.getAttribute('.msg-image', 'src');

    assert.equal(statusVisible, false);
    assert.equal(imageSrc, 'https://example.test/final-image.png');
  });
});

test('dispatchSSEEvent routes image progress events to the visible placeholder', async () => {
  await withPage(async (page) => {
    await page.evaluate(() => window.__chatHarness.dispatchProgressEvent());

    await page.waitForSelector('.msg-media-status', { state: 'visible' });
    const labelText = await page.textContent('.img-progress-label');
    const progressWidth = await page.$eval('.img-progress-bar', (el) => getComputedStyle(el).width);

    assert.ok(labelText.includes('1 / 4'));
    assert.notEqual(progressWidth, '0px');
  });
});
