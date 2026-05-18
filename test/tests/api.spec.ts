import { test, expect } from '@playwright/test';

test.describe('API health and portfolio', () => {
  test('GET /api/health returns ok', async ({ request }) => {
    const res = await request.get('/api/health');
    expect(res.ok()).toBeTruthy();
    expect((await res.json()).status).toBe('ok');
  });

  test('GET /api/watchlist returns 10+ tickers', async ({ request }) => {
    const res = await request.get('/api/watchlist');
    expect(res.ok()).toBeTruthy();
    const body = await res.json();
    expect(Array.isArray(body)).toBeTruthy();
    expect(body.length).toBeGreaterThanOrEqual(10);
  });

  test('GET /api/portfolio returns valid shape', async ({ request }) => {
    const res = await request.get('/api/portfolio');
    expect(res.ok()).toBeTruthy();
    const body = await res.json();
    expect(body).toHaveProperty('cash_balance');
    expect(body).toHaveProperty('positions');
    expect(body).toHaveProperty('total_value');
    expect(body.cash_balance).toBeGreaterThan(0);
  });

  test('POST /api/portfolio/trade - buy AAPL', async ({ request }) => {
    const portfolio = await (await request.get('/api/portfolio')).json();
    const initialCash = portfolio.cash_balance;

    const res = await request.post('/api/portfolio/trade', {
      data: { ticker: 'AAPL', quantity: 1, side: 'buy' }
    });
    expect(res.ok()).toBeTruthy();
    const updated = await res.json();
    expect(updated.cash_balance).toBeLessThan(initialCash);

    const aaplPos = updated.positions.find((p: any) => p.ticker === 'AAPL');
    expect(aaplPos).toBeDefined();
  });

  test('POST /api/portfolio/trade - invalid side returns 422', async ({ request }) => {
    const res = await request.post('/api/portfolio/trade', {
      data: { ticker: 'AAPL', quantity: 1, side: 'invalid' }
    });
    expect(res.status()).toBe(422);
  });

  test('POST /api/watchlist - add ticker', async ({ request }) => {
    const res = await request.post('/api/watchlist', {
      data: { ticker: 'PYPL' }
    });
    // 201 or 409 (if already exists from previous run)
    expect([201, 409]).toContain(res.status());
  });

  test('POST /api/chat returns message (mock mode)', async ({ request }) => {
    const res = await request.post('/api/chat', {
      data: { message: 'Hello, what can you do?' }
    });
    expect(res.ok()).toBeTruthy();
    const body = await res.json();
    expect(body).toHaveProperty('message');
    expect(typeof body.message).toBe('string');
    expect(body.message.length).toBeGreaterThan(0);
  });

  test('GET /api/portfolio/history returns array', async ({ request }) => {
    const res = await request.get('/api/portfolio/history');
    expect(res.ok()).toBeTruthy();
    expect(Array.isArray(await res.json())).toBeTruthy();
  });
});
