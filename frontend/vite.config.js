import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    allowedHosts: true,
    proxy: {
      '/api/physical': {
        target: 'http://nginx',
        changeOrigin: true,
      },
      '/api/tactical': {
        target: 'http://nginx',
        changeOrigin: true,
      }
    }
  }
})
