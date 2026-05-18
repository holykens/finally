import { test, expect } from '@playwright/test';

test.describe('Portfolio state and history', () => {
  test('portfolio history records grow after a trade', async ({ request }) => {
    const before = await (await request.get('/api/portfolio/history')).json();
    expect(Array.isArray(before)).toBeTruthy();

    // Execute a small trade to generate a snapshot.
    const trade = await request.post('/api/portfolio/trade', {
      data: { ticker: 'MSFT', quantity: 1, side: 'buy' }
    });
    expect(trade.ok()).toBeTruthy();

    const after = await (await request.get('/api/portfolio/history')).json();
    expect(Array.isArray(after)).toBeTruthy();
    // History should be non-empty after at least one trade.
    expect(after.length).toBeGreaterThan(0);
    // It should be at least as long as before (snapshots are append-only).
    expect(after.length).toBeGreaterThanOrEqual(before.length);
  });

  test('portfolio total_value reflects cash plus positions', async ({ request }) => {
    const portfolio = await (await request.get('/api/portfolio')).json();
    expect(portfolio).toHaveProperty('total_value');
    expect(portfolio).toHaveProperty('cash_balance');
    expect(portfolio).toHaveProperty('positions');
    expect(typeof portfolio.total_value).toBe('number');
    // Sanity: total_value >= cash_balance (positions can't be negatively valued
    // in a long-only sim).
    expect(portfolio.total_value).toBeGreaterThanOrEqual(portfolio.cash_balance - 0.01);
  });
});

test.describe('Portfolio UI (browser)', () => {
  test('positions or portfolio area renders after a trade', async ({ page, request }) => {
    // Seed a position via API first so the UI has something to show.
    await request.post('/api/portfolio/trade', {
      data: { ticker: 'AAPL', quantity: 1, side: 'buy' }
    });

    await page.goto('/');
    // Look for the ticker we just bought somewhere on the page.
    await expect(page.getByText('AAPL').first()).toBeVisible({ timeout: 10000 });
  });
});
