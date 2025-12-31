import { test, expect } from '@playwright/test';

test.describe('Terminal Create Session', () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to the app
    await page.goto('http://127.0.0.1:5000/');
  });

  test('should display the app header', async ({ page }) => {
    // Check header is present
    await expect(page.locator('.app-header h1')).toContainText('Copilot Terminal Carousel');
  });

  test('should show connection status', async ({ page }) => {
    // Wait for connection
    await page.waitForSelector('.connection-status');
    const status = page.locator('.connection-status');
    
    // Should show connected or disconnected
    await expect(status).toBeVisible();
  });

  test('should have new session button', async ({ page }) => {
    const newSessionBtn = page.locator('.new-session-btn');
    await expect(newSessionBtn).toBeVisible();
    await expect(newSessionBtn).toContainText('New Session');
  });

  test('should show no session message initially', async ({ page }) => {
    const noSession = page.locator('.no-session');
    await expect(noSession).toContainText('No session selected');
  });

  test('should create session when clicking new session button', async ({ page }) => {
    // Wait for connection to be established
    await page.waitForSelector('.connection-status.connected', { timeout: 5000 });
    
    // Click new session button
    await page.click('.new-session-btn');
    
    // Wait for session to be created and terminal to appear
    await page.waitForSelector('.terminal-pane', { timeout: 5000 });
    
    // Verify terminal pane is visible
    const terminalPane = page.locator('.terminal-pane');
    await expect(terminalPane).toBeVisible();
    
    // Verify session appears in the list
    const sessionList = page.locator('.session-list');
    const sessionItems = sessionList.locator('.session-item');
    await expect(sessionItems).toHaveCount(1);
  });

  test('should show session as running after creation', async ({ page }) => {
    // Wait for connection
    await page.waitForSelector('.connection-status.connected', { timeout: 5000 });
    
    // Create a session
    await page.click('.new-session-btn');
    
    // Wait for session item
    await page.waitForSelector('.session-item', { timeout: 5000 });
    
    // Check status shows running
    const sessionStatus = page.locator('.session-status');
    await expect(sessionStatus).toContainText('running');
  });

  test('should highlight selected session', async ({ page }) => {
    // Wait for connection
    await page.waitForSelector('.connection-status.connected', { timeout: 5000 });
    
    // Create a session
    await page.click('.new-session-btn');
    
    // Wait for session item
    await page.waitForSelector('.session-item', { timeout: 5000 });
    
    // Check session is selected (has .selected class)
    const sessionItem = page.locator('.session-item');
    await expect(sessionItem).toHaveClass(/selected/);
  });

  test('should terminate session when clicking terminate button', async ({ page }) => {
    // Wait for connection
    await page.waitForSelector('.connection-status.connected', { timeout: 5000 });
    
    // Create a session
    await page.click('.new-session-btn');
    
    // Wait for session item
    await page.waitForSelector('.session-item', { timeout: 5000 });
    
    // Hover over session to show terminate button
    await page.hover('.session-item');
    
    // Click terminate button
    await page.click('.terminate-btn');
    
    // Wait for status to change to exited
    await page.waitForSelector('.session-status.exited', { timeout: 5000 });
    
    const sessionStatus = page.locator('.session-status');
    await expect(sessionStatus).toContainText('exited');
  });
});

test.describe('Terminal UI Rendering', () => {
  test('terminal container renders with xterm', async ({ page }) => {
    await page.goto('http://127.0.0.1:5000/');
    
    // Wait for connection
    await page.waitForSelector('.connection-status.connected', { timeout: 5000 });
    
    // Create a session
    await page.click('.new-session-btn');
    
    // Wait for xterm terminal to initialize
    await page.waitForSelector('.xterm', { timeout: 5000 });
    
    // Verify xterm elements are present
    const xtermScreen = page.locator('.xterm-screen');
    await expect(xtermScreen).toBeVisible();
  });
});
