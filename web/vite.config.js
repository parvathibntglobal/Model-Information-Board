import { fileURLToPath } from 'node:url'
import { defineConfig, loadEnv } from 'vite'
import { viteSingleFile } from 'vite-plugin-singlefile'
import react from '@vitejs/plugin-react'

// The backend runs no CORS middleware, so in dev we proxy rather than ask them
// to add one. Everything the app fetches is under /api, which is stripped here.
const BACKEND = process.env.BACKEND_URL || 'http://127.0.0.1:8000'

/** The repo root, where the ONE .env lives. */
const REPO_ROOT = fileURLToPath(new URL('..', import.meta.url))

export default defineConfig(({ mode }) => {
  // ONE .env FOR THE WHOLE PROJECT, at the repo root.
  //
  // Vite would normally read `web/.env`, which meant the API token had to be
  // written twice — once as API_TOKEN for the backend and once as
  // VITE_API_TOKEN here. Two copies of one secret is two things to rotate and
  // one to forget, so this reads the root file instead.
  //
  // The empty prefix is what makes that possible: `loadEnv(mode, dir, '')`
  // returns EVERY variable, not just VITE_-prefixed ones, so `API_TOKEN` is
  // visible. That is also why exactly one value is injected below and the
  // object is never spread — `env` here holds DATABASE_URL and
  // OPENROUTER_API_KEY too, and `define` puts whatever it is given into the
  // browser bundle in clear text.
  const env = loadEnv(mode, REPO_ROOT, '')
  const token = env.API_TOKEN || process.env.API_TOKEN || ''

  return {
    plugins: [react(), ...(process.env.SINGLE_FILE ? [viteSingleFile()] : [])],

    // NOT A SECRET ONCE IT IS HERE. Anything `define` injects is readable by
    // anyone who loads the page — view-source, devtools, the built bundle. This
    // is a development convenience so the dev server can reach a token-gated
    // API; a deployed build must get its credential from a session the server
    // issues, never from a value compiled into the client.
    define: {
      'import.meta.env.VITE_API_TOKEN': JSON.stringify(token),
    },

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
  }
})
