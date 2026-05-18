import { test, expect } from '@playwright/test';

test.describe('Watchlist CRUD via API', () => {
  const ticker = 'PYPL';

  test('add and remove a ticker', async ({ request }) => {
    // Clean up any prior state from a previous run.
    await request.delete(`/api/watchlist/${ticker}`);

    // Add the ticker.
    const addRes = await request.post('/api/watchlist', {
      data: { ticker }
    });
    expect([200, 201]).toContain(addRes.status());

    // Verify it appears in the list.
    let list = await (await request.get('/api/watchlist')).json();
    let tickers = list.map((row: any) =>
      (row.ticker || row.symbol || '').toUpperCase()
    );
    expect(tickers).toContain(ticker);

    // Remove the ticker.
    const delRes = await request.delete(`/api/watchlist/${ticker}`);
    expect([200, 204]).toContain(delRes.status());

    // Verify it's gone.
    list = await (await request.get('/api/watchlist')).json();
    tickers = list.map((row: any) =>
      (row.ticker || row.symbol || '').toUpperCase()
    );
    expect(tickers).not.toContain(ticker);
  });

  test('adding a duplicate is handled gracefully', async ({ request }) => {
    const dup = 'PYPL';
    await request.post('/api/watchlist', { data: { ticker: dup } });
    const res = await request.post('/api/watchlist', { data: { ticker: dup } });
    // Acceptable behaviors: idempotent success (200/201) or conflict (409).
    expect([200, 201, 409]).toContain(res.status());
    // Cleanup.
    await request.delete(`/api/watchlist/${dup}`);
  });
});
