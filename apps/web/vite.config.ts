import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import { resolve } from 'node:path';

// Relative base so the build works from any path, such as GitHub Pages.
export default defineConfig({
  base: './',
  plugins: [react()],
  // The Lance Ledger links to the walker viewer, so the build ships it beside the app.
  build: { rollupOptions: { input: { main: resolve(__dirname, 'index.html'), viewer: resolve(__dirname, 'viewer.html') } } },
  server: { fs: { allow: ['../..'] } },
});
