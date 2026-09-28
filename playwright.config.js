// @ts-check
const { defineConfig, devices } = require('@playwright/test');

// 若本机需要通过代理访问外网，设置 HTTP_PROXY / HTTPS_PROXY 环境变量即可自动生效
const proxyServer =
  process.env.HTTPS_PROXY || process.env.HTTP_PROXY || process.env.https_proxy || process.env.http_proxy;

module.exports = defineConfig({
  testDir: './tests',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  reporter: 'list',

  use: {
    // 注意：baseURL 带路径，用例里请用 page.goto('./')，用 '/' 会解析到域名根目录
    baseURL: 'https://demo.playwright.dev/todomvc/',
    trace: 'on-first-retry',
    ...(proxyServer ? { proxy: { server: proxyServer } } : {}),
  },

  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],
});
