import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/web': { target: 'http://localhost:8000', changeOrigin: true },
      '/sandbox': { target: 'http://localhost:8000', changeOrigin: true, ws: true },
    },
  },
})
