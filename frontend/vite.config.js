import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

const API_PATHS = [
  '/auth',
  '/interactions',
  '/chat',
  '/doctors',
  '/doctor',
  '/metrics',
  '/followups',
  '/job',
  '/log-interaction',
  '/log-structured-interaction',
  '/edit-interaction',
  '/format-notes',
  '/summarize-async',
]

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: Object.fromEntries(
      API_PATHS.map(path => [path, { target: 'http://13.233.132.223:8000', changeOrigin: true }])
    ),
  },
})
