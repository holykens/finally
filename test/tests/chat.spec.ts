import { test, expect } from '@playwright/test';

test.describe('AI Chat (mock mode)', () => {
  test('chat endpoint responds with message', async ({ request }) => {
    const res = await request.post('/api/chat', {
      data: { message: 'Show me my portfolio' }
    });
    expect(res.ok()).toBeTruthy();
    const body = await res.json();
    expect(body.message).toBeTruthy();
    expect(Array.isArray(body.trades)).toBeTruthy();
    expect(Array.isArray(body.watchlist_changes)).toBeTruthy();
  });
});
