import { test, expect } from '@playwright/test';

test.describe('Frontend loads correctly', () => {
  test('page loads without errors', async ({ page }) => {
    await page.goto('/');
    // Check no fatal errors
    await expect(page).not.toHaveURL(/error/);
    // Page should have some content
    await expect(page.locator('body')).not.toBeEmpty();
  });

  test('default tickers visible', async ({ page }) => {
    await page.goto('/');
    for (const ticker of ['AAPL', 'MSFT', 'TSLA']) {
      await expect(page.getByText(ticker).first()).toBeVisible({ timeout: 10000 });
    }
  });

  test('shows portfolio value', async ({ page }) => {
    await page.goto('/');
    // Look for dollar amounts
    await expect(page.locator('text=/\\$[0-9,]+/')).toBeVisible({ timeout: 10000 });
  });
});
