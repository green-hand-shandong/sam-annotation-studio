import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

export default defineConfig({
  plugins: [react()],
  resolve: { alias: { '@': path.resolve(__dirname, './src') } },
  server: {
    proxy: { '/api': 'http://localhost:8100' },  // 开发模式转发后端
  },
  build: { outDir: path.resolve(__dirname, '../frontend-dist'), emptyOutDir: true },
})
