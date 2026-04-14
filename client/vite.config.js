import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    proxy: {
      '/api': {
        target: process.env.VITE_API_HOST || 'http://localhost:3001',
        changeOrigin: true,
      },
      '/socket.io': {
        target: process.env.VITE_API_HOST || 'http://localhost:3001',
        ws: true,
      },
    },
  },
})
