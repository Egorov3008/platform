// @ts-check
const { defineConfig, devices } = require('@playwright/test');

/**
 * Playwright конфигурация для VPN Web Frontend E2E тестов
 * @see https://playwright.dev/docs/test-configuration
 */
module.exports = defineConfig({
  testDir: './tests_e2e',
  
  // Полное параллельное выполнение тестов
  fullyParallel: true,
  
  // Запретить повторные запуски失败的 тестов в CI
  forbidOnly: !!process.env.CI,
  
  // Повторные попытки в CI
  retries: process.env.CI ? 2 : 0,
  
  // Оптимальное количество параллельных воркеров
  workers: process.env.CI ? 1 : undefined,
  
  reporter: [
    ['html', { outputFolder: 'playwright-report', open: 'never' }],
    ['list'],
    ['json', { outputFile: 'test-results/results.json' }]
  ],

  use: {
    // Базовый URL для навигации
    baseURL: process.env.BASE_URL || 'http://localhost:8000',
    
    // Собирать трейсы при падении тестов
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
    
    // Таймауты
    actionTimeout: 10000,
    navigationTimeout: 15000,
  },

  // Конфигурация для разных браузеров
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
    {
      name: 'firefox',
      use: { ...devices['Desktop Firefox'] },
    },
    {
      name: 'webkit',
      use: { ...devices['Desktop Safari'] },
    },
    // Мобильные устройства
    {
      name: 'Mobile Chrome',
      use: { ...devices['Pixel 5'] },
    },
    {
      name: 'Mobile Safari',
      use: { ...devices['iPhone 12'] },
    },
  ],

  // Запуск бэкенда перед тестами
  webServer: {
    command: 'docker-compose up -d && sleep 3',
    url: 'http://localhost:8000/health',
    reuseExistingServer: !process.env.CI,
    timeout: 60000,
  },

  outputDir: 'test-results/',
});
