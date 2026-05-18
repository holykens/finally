import { test, expect } from '@playwright/test';

test.describe('Trading via API', () => {
  test('full buy-sell cycle', async ({ request }) => {
    const before = await (await request.get('/api/portfolio')).json();

    // Buy
    const buyRes = await request.post('/api/portfolio/trade', {
      data: { ticker: 'NVDA', quantity: 2, side: 'buy' }
    });
    expect(buyRes.ok()).toBeTruthy();
    const afterBuy = await buyRes.json();
    expect(afterBuy.cash_balance).toBeLessThan(before.cash_balance);

    const nvdaPos = afterBuy.positions.find((p: any) => p.ticker === 'NVDA');
    expect(nvdaPos?.quantity).toBeGreaterThanOrEqual(2);

    // Sell 1 share
    const sellRes = await request.post('/api/portfolio/trade', {
      data: { ticker: 'NVDA', quantity: 1, side: 'sell' }
    });
    expect(sellRes.ok()).toBeTruthy();
    const afterSell = await sellRes.json();
    expect(afterSell.cash_balance).toBeGreaterThan(afterBuy.cash_balance);
  });

  test('cannot sell more than owned', async ({ request }) => {
    const res = await request.post('/api/portfolio/trade', {
      data: { ticker: 'GOOGL', quantity: 99999, side: 'sell' }
    });
    expect(res.status()).toBe(400);
  });

  test('cannot buy with insufficient cash', async ({ request }) => {
    const res = await request.post('/api/portfolio/trade', {
      data: { ticker: 'AAPL', quantity: 999999, side: 'buy' }
    });
    expect(res.status()).toBe(400);
  });
});
