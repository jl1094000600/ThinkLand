import { resolve } from 'node:path'
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

const rootDir = process.cwd()
const localModules = resolve(rootDir, 'node_modules')

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': resolve(rootDir, 'src'),
      vue: resolve(localModules, 'vue/dist/vue.runtime.esm-bundler.js'),
      'vue-router': resolve(localModules, 'vue-router/dist/vue-router.mjs')
    }
  },
  server: {
    port: 3100,
    proxy: {
      '/api': {
        target: 'http://localhost:8080',
        changeOrigin: true
      }
    }
  }
})
