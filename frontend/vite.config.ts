import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig(({ mode }) => {
  const pagesBuild = mode === 'pages';
  return {
    plugins: [react()],
    base: pagesBuild ? '/praesagus/seasonality/' : '/',
    build: pagesBuild ? { outDir: '../artifacts/seasonality', emptyOutDir: true } : undefined,
    server: {
      host: '0.0.0.0',
      port: 5173,
    },
  };
});
