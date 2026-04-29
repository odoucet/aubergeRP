import test from 'node:test';
import assert from 'node:assert/strict';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

import { chromium } from 'playwright';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const harnessUrl = pathToFileURL(path.join(__dirname, 'harness', 'mobile-scroll.html')).href;

async function withPage(fn, viewportOverride) {
  const browser = await chromium.launch({
    headless: true,
    args: ['--no-sandbox', '--disable-dev-shm-usage'],
  });
  const page = await browser.newPage();
  if (viewportOverride) await page.setViewportSize(viewportOverride);
  try {
    await page.goto(harnessUrl, { waitUntil: 'load' });
    await fn(page);
  } finally {
    await page.close();
    await browser.close();
  }
}

test('starts pinned to bottom', async () => {
  await withPage(async (page) => {
    const pinned = await page.evaluate(() => window.__scrollHarness.getPinned());
    assert.equal(pinned, true);
  });
});

test('streaming auto-scrolls to bottom when pinned', async () => {
  await withPage(async (page) => {
    await page.evaluate(() => {
      window.__scrollHarness.seed(20);
      window.__scrollHarness.scrollToBottom();
    });
    // Confirm pinned and at bottom
    const pinnedBefore = await page.evaluate(() => window.__scrollHarness.getPinned());
    assert.equal(pinnedBefore, true);

    // Start streaming and send tokens
    await page.evaluate(() => {
      window.__scrollHarness.startStreaming();
      window.__scrollHarness.sendToken('first token');
    });

    const isAtBottom = await page.evaluate(() => window.__scrollHarness.isAtBottom());
    assert.equal(isAtBottom, true, 'should stay at bottom while pinned');
  });
});

test('streaming does NOT force-scroll when user has scrolled up', async () => {
  await withPage(async (page) => {
    await page.evaluate(() => {
      window.__scrollHarness.seed(20);
      window.__scrollHarness.scrollToBottom();
    });

    // Simulate user scrolling up — also manually unpin since scroll event
    // fires asynchronously and the harness does not run initChat()
    await page.evaluate(() => {
      window.__scrollHarness.scrollToTop();
      window.__scrollHarness.setPinned(false);
    });

    const scrollTopBefore = await page.evaluate(() => window.__scrollHarness.getScrollTop());

    // Start streaming — should NOT scroll back to bottom
    await page.evaluate(() => {
      window.__scrollHarness.startStreaming();
      window.__scrollHarness.sendToken('token while user scrolled up');
    });

    const scrollTopAfter = await page.evaluate(() => window.__scrollHarness.getScrollTop());
    assert.equal(scrollTopAfter, scrollTopBefore, 'scroll position should not change when unpinned');
  });
});

test('pinning resumes when user scrolls back to bottom', async () => {
  await withPage(async (page) => {
    await page.evaluate(() => {
      window.__scrollHarness.seed(20);
      window.__scrollHarness.scrollToTop();
      window.__scrollHarness.setPinned(false);
    });

    const pinnedAfterScrollUp = await page.evaluate(() => window.__scrollHarness.getPinned());
    assert.equal(pinnedAfterScrollUp, false);

    // User scrolls back to bottom — re-pin manually (mirrors what the scroll
    // listener in initChat() does when the user scrolls within 80px of bottom)
    await page.evaluate(() => {
      window.__scrollHarness.scrollToBottom();
      window.__scrollHarness.setPinned(true);
    });

    const pinnedAfterScrollDown = await page.evaluate(() => window.__scrollHarness.getPinned());
    assert.equal(pinnedAfterScrollDown, true);

    // Now streaming should scroll again
    await page.evaluate(() => {
      window.__scrollHarness.startStreaming();
      window.__scrollHarness.sendToken('token after re-pin');
    });

    const isAtBottom = await page.evaluate(() => window.__scrollHarness.isAtBottom());
    assert.equal(isAtBottom, true, 'should auto-scroll again after re-pin');
  });
});

test('input area is visible within viewport on a mobile-sized screen', async () => {
  await withPage(async (page) => {
    await page.evaluate(() => window.__scrollHarness.seed(20));
    const inputBottom = await page.evaluate(() => window.__scrollHarness.getInputAreaBottom());
    const viewportHeight = await page.evaluate(() => window.__scrollHarness.getViewportHeight());
    assert.ok(
      inputBottom <= viewportHeight,
      `input area bottom (${inputBottom}) should be within viewport (${viewportHeight})`
    );
  }, { width: 390, height: 844 }); // iPhone 14 viewport
});
