// SFDAP Dashboard — Vite Build Configuration
// shiftFinal A3 — Ecenur Üner: bundling scaffold
//
// EN: Vite scaffold for the static SPA dashboard. Today the dashboard is
//     a single `index.html` with inline CSS + inline JS. The scaffold is
//     ready so future PRs can split styles/scripts into ES modules without
//     touching FastAPI's StaticFiles mount.
//
// ---
//
// TR: Statik dashboard SPA'si icin Vite iskeleti. Su an dashboard tek
//     bir `index.html` (inline CSS + inline JS). Ileride stilleri ve
//     script'leri ES modullerine bolmek istedigimizde FastAPI'nin
//     StaticFiles mount'una dokunmadan calisir hale gelsin diye iskelet
//     hazirlandi.

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
