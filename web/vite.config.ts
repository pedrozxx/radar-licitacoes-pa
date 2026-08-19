import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  // O GitHub Pages serve em /radar-licitacoes-pa/, não na raiz. Sem isto o
  // HTML pediria /assets/... e receberia 404 — a página abriria em branco.
  // Em desenvolvimento fica '/', para o servidor do Vite continuar simples.
  base: process.env.BASE_PATH ?? '/',
  server: {
    // Em desenvolvimento o front fala com o FastAPI local. Em produção o
    // site lê o snapshot estático e só chama a API no "atualizar agora".
    proxy: { '/api': 'http://127.0.0.1:8778' },
  },
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: ['./src/setupTests.ts'],
  },
})
