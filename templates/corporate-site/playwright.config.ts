import { defineConfig } from '@playwright/test';
export default defineConfig({
  testDir: './tests/browser', workers: 1, retries: 0,
  use: { baseURL: 'http://127.0.0.1:3183', browserName: 'chromium' },
  webServer: { command: 'npm start -- --port 3183', url: 'http://127.0.0.1:3183', reuseExistingServer: false },
});
