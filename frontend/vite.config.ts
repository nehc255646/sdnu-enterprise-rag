import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/ingest-api': {
        target: 'http://127.0.0.1:8001',
        changeOrigin: true,
        rewrite: (p) => p.replace(/^\/ingest-api/, ''),
      },
      '/chat-api': {
        target: 'http://127.0.0.1:8002',
        changeOrigin: true,
        rewrite: (p) => p.replace(/^\/chat-api/, ''),
      },
    },
  },
})
