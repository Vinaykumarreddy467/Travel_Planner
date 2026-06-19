import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Vite config — tells the dev server where the React app lives
// and proxies /api requests to our FastAPI backend (port 8000)
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/chat': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
})
