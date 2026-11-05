import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [
    react(),
    tailwindcss(),
  ],
  server: {
    host: true,
    port: 9000,
    proxy: {
      '/backend': {
        target: process.env.CODEX_API_PROXY_TARGET || 'http://127.0.0.1:8000',
        rewrite: path => path.replace(/^\/backend/, ''),
      },
    },
    watch: {
      usePolling: true,
    },
  }
})
