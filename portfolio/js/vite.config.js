import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Vite's dev/preview server proxies /api to FastAPI so the browser always uses
// same-origin relative URLs -- works from any host (localhost, Tailscale, LAN IP)
// with zero config. In Docker, DOCKER_API_URL points at the compose service name.
const apiProxy = {
  '/api': {
    target: process.env.DOCKER_API_URL || 'http://127.0.0.1:8000',
    // Do NOT set changeOrigin: true — that replaces Host with the Docker-internal
    // hostname (api:8000), causing FastAPI redirects (e.g. missing trailing slash)
    // to emit Location: http://api:8000/... which the browser cannot reach.
    // Without changeOrigin, FastAPI sees the real browser Host and redirects correctly.
  },
}

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    host: '0.0.0.0',
    proxy: apiProxy,
  },
  preview: {
    host: '0.0.0.0',
    proxy: apiProxy,
  },
  test: {
    environment: 'jsdom',
    environmentOptions: { jsdom: { url: 'http://localhost/' } },
    setupFiles: ['./src/test/setup.ts'],
    include: ['src/**/*.test.{js,jsx,ts,tsx}'],
    // The shared host is often busy; the Trade Republic login test waits on a 2 s poll
    testTimeout: 15000,
  },
})
