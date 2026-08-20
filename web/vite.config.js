import { defineConfig } from 'vite'
import { viteSingleFile } from 'vite-plugin-singlefile'
import react from '@vitejs/plugin-react'

// The backend runs no CORS middleware, so in dev we proxy rather than ask them
// to add one. Everything the app fetches is under /api, which is stripped here.
const BACKEND = process.env.BACKEND_URL || 'http://127.0.0.1:8000'

export default defineConfig({
  plugins: [react(), ...(process.env.SINGLE_FILE ? [viteSingleFile()] : [])],
  server: {
    proxy: {
      '/api': {
        target: BACKEND,
        changeOrigin: true,
        rewrite: (p) => p.replace(/^\/api/, ''),
      },
    },
  },
  build: process.env.SINGLE_FILE
    ? { assetsInlineLimit: 100_000_000, cssCodeSplit: false, outDir: 'dist-single' }
    : {},
})
