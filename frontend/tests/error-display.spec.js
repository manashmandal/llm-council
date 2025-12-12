// @ts-check
import { test, expect } from '@playwright/test';

test.describe('Error Display', () => {
  test('should display app and create conversation', async ({ page }) => {
    // Go to the app
    await page.goto('http://localhost:5173');

    // Check app loads
    await expect(page.locator('h1')).toContainText('LLM Council');

    // Click new conversation
    await page.click('.new-conversation-btn');

    // Wait for conversation to be created
    await expect(page.locator('.conversation-item')).toBeVisible({ timeout: 5000 });

    // Check empty state message
    await expect(page.locator('.empty-state')).toContainText('Start a conversation');
  });

  test('should display model responses including errors', async ({ page }) => {
    await page.goto('http://localhost:5173');

    // Create new conversation
    await page.click('.new-conversation-btn');
    await expect(page.locator('.conversation-item')).toBeVisible({ timeout: 5000 });

    // Type a message
    await page.fill('.message-input', 'What is 2+2?');

    // Send the message
    await page.click('.send-button');

    // Wait for Stage 1 to appear (may take time for CLI tools)
    await expect(page.locator('.stage1')).toBeVisible({ timeout: 120000 });

    // Check that tabs are visible (model responses)
    const tabs = page.locator('.stage1 .tab');
    await expect(tabs.first()).toBeVisible();

    // If any tab has error class, verify error content is displayed when clicked
    const errorTabs = page.locator('.stage1 .tab.error');
    const errorCount = await errorTabs.count();

    if (errorCount > 0) {
      // Click on error tab
      await errorTabs.first().click();

      // Check error text is displayed
      await expect(page.locator('.error-text')).toBeVisible();
      await expect(page.locator('.error-text')).toContainText('Error');
    }

    console.log(`Found ${errorCount} error tabs`);
  });
});
