import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api': {
        target: 'http://nginx',  // Point vers nginx qui route vers les backends
        changeOrigin: true,
      }
    }
  }
})
