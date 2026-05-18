# 🌾 SFDAP Dashboard

Static SPA dashboard served by FastAPI at `/dashboard`.

## 📐 Mevcut yapı

```
frontend/
├── index.html              # Markup-only (~629 satır)
├── src/
│   ├── styles/main.css     # Extracted stylesheet (~1239 satır)
│   └── main.js             # Extracted JavaScript (~1253 satır)
├── package.json            # Vite + @axe-core/cli devDependencies
├── vite.config.js          # Vite build scaffold (dev :5173 + FastAPI proxy)
└── README.md               # bu dosya
```

- `index.html` sadece markup içerir; CSS `<link>`, JS `<script src>` ile yüklenir.
- FastAPI `app/main.py` içinde `StaticFiles(directory="frontend", html=True)` ile
  `/dashboard` altına mount edilir; alt dizinler otomatik servis edilir.
- Chart.js (`4.4.0`) CDN'den yüklenir; Inter fontu Google Fonts'tan gelir.
- Vite build iskeleti hazır; `npm run build` ile minified `dist/` üretilebilir.

## 🚀 Geliştirici komutları

```bash
# Bağımlılıklar (sadece Vite scaffold — Node 18+)
cd frontend && npm install

# Dev sunucusu (Vite, :5173) — FastAPI :8000'e proxy'ler /api, /metrics, /static
npm run dev

# Production build (dist/ üretir; FastAPI mount'u şu an `frontend/` köküne bakar,
# build çıktısı kullanılmak istenirse mount yolu `frontend/dist` olarak güncellenmeli)
npm run build
```

## ♿ Erişilebilirlik (shiftFinal A3)

- Skip-to-content link (`<a href="#main-content">`)
- `<main id="main-content">` landmark
- Sidebar `<nav aria-label="Ana menü">`, aktif öğeye `aria-current="page"`
- Tablo başlıkları `<th scope="col">`
- Tüm async render hedefleri (`#dashboardCards`, `#sensorsTable`, vb.) için
  `aria-busy` + `aria-live="polite"` durumları
- Mevcut buton/ikonlar için `aria-label` (theme toggle, hamburger, maskot)

## 🦴 Skeleton loaders (shiftFinal A3)

Her async `loadXxx()` fonksiyonu fetch BEFORE'da `_skeletonCards()` /
`_skeletonRows()` çağırır; veri geldiğinde gerçek HTML ile değiştirir.
Sınıf adı `.skeleton` zaten CSS'te mevcuttu (Cycle 5 Ecenur).
