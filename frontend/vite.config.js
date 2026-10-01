import react from '@vitejs/plugin-react'
import { defineConfig } from 'vitest/config'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    // api.js reads ../fixtures/*.json, which sits outside the Vite root.
    fs: { allow: ['..'] },
  },
  test: {
    environment: 'jsdom',
    setupFiles: './src/setupTests.js',
  },
})
