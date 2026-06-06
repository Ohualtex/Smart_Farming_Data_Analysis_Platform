// SFDAP Dashboard — Vite Build Configuration
// shiftFinal A3 — Ecenur Üner: bundling scaffold
//
// EN: Vite dev/build tooling for the SPA dashboard. The ES-module split is
//     done: markup-only `index.html` + `src/main.js` + `src/lib/*.js` (8) +
//     `src/styles/*.css` (10). Production serves raw ESM + CDN via FastAPI's
//     StaticFiles mount; Vite is only the dev server (HMR + /api proxy) and
//     test/build runner — its bundle is not served.
//
// ---
//
// TR: SPA dashboard icin Vite dev/build araci. ES-modul ayrimi tamamlandi:
//     markup-only `index.html` + `src/main.js` + `src/lib/*.js` (8) +
//     `src/styles/*.css` (10). Uretimde FastAPI ham ESM + CDN servis eder;
//     Vite yalnizca dev sunucusu (HMR + /api proxy) ve test/build aracidir.

import { defineConfig } from "vite";

export default defineConfig({
  root: ".",
  // EN: build output goes to `dist/`; ignored in .gitignore.
  // TR: build cikti dizini `dist/` — .gitignore'a eklendi.
  build: {
    outDir: "dist",
    emptyOutDir: true,
    // EN: keep filenames stable — FastAPI does not yet hash-bust.
    // TR: dosya adlarini sabit tut — FastAPI henuz hash-bust kullanmiyor.
    rollupOptions: {
      output: {
        entryFileNames: "assets/[name].js",
        chunkFileNames: "assets/[name].js",
        assetFileNames: "assets/[name].[ext]",
      },
    },
  },
  // EN: dev server proxies API calls to FastAPI on :8000 so the dashboard
  //     can be developed standalone with hot reload.
  // TR: dev sunucusu API isteklerini FastAPI :8000'e proxy'ler — boylece
  //     dashboard'u canli yeniden yukleme ile standalone gelistirebiliriz.
  server: {
    port: 5173,
    proxy: {
      "/api": "http://127.0.0.1:8000",
      "/metrics": "http://127.0.0.1:8000",
      "/static": "http://127.0.0.1:8000",
    },
  },
});
