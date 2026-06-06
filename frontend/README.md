# 🌾 SFDAP Dashboard

FastAPI tarafından `/dashboard` altında servis edilen **vanilla JS, ES-modül tabanlı** tek-sayfa dashboard. Build adımı olmadan (ham ESM + CDN) çalışır; Vite yalnızca yerel geliştirme ve test/build aracıdır.

## 📐 Yapı

```
frontend/
├── index.html              # Sadece markup (~1009 satır; inline <style>/<script> yok)
├── src/
│   ├── main.js             # SPA giriş noktası (~2154 satır) — lib modüllerini import eder
│   ├── lib/                # 8 ES modülü
│   │   ├── api.js          #   fetch sarmalayıcı + Bearer/X-API-Key auth
│   │   ├── router.js       #   hash-router + sayfa başlıkları
│   │   ├── map.js          #   Leaflet harita (7 bölge renk kodu)
│   │   ├── charts.js       #   Chart.js render yardımcıları
│   │   ├── render.js       #   saf HTML render (tarla detayı, bitki sonucu)
│   │   ├── skeleton.js     #   iskelet yükleyiciler + aria-busy
│   │   ├── ui_helpers.js   #   küçük UI yardımcıları
│   │   └── utils.js        #   format/toast/saat + durum etiketleri
│   └── styles/             # 10 CSS modülü (main.css import-hub ile sıralı)
│       │                   #   variables → base → layout → components → pages
│       └─                  #   → welcome → filiz → theme-toggle → theme-light
├── tests/                  # Vitest (jsdom) — 59 test: map(29) skeleton(14) ui_helpers(16)
├── package.json            # Vite + Vitest + @axe-core/cli devDependencies
└── vite.config.js          # dev :5173 + FastAPI proxy (/api, /metrics, /static)
```

- `index.html` yalnız markup içerir; stiller `<link rel="stylesheet" href="src/styles/main.css">`, JS `<script type="module" src="src/main.js">` ile yüklenir.
- FastAPI `app/main.py` içinde `StaticFiles(directory="frontend", html=True)` ile `/dashboard` altına mount edilir; tarayıcı ES modüllerini doğrudan yükler (bundle yok).
- **Chart.js 4.4.0** (cdn.jsdelivr.net) ve **Leaflet 1.9.4** (unpkg.com) CDN'den; Inter fontu Google Fonts'tan gelir.
- `vite.config.js`/`dist/` mevcuttur ama FastAPI mount'u `frontend/` köküne bakar — `dist/` `.gitignore`'dadır ve üretimde kullanılmaz.

## 🎨 Öne çıkan özellikler

- **Hoşgeldin ekranı** (`#welcome`, `welcome.css`): gün-gece temalı (sol-üst güneş / sağ-üst ay, bulut & yıldız geçişleri); toprağa gömülü **Filiz** tıklayınca çıkar.
- **Filiz maskotu**: SVG karakter, mood/göz/ağız animasyonları, rol-aware ipucu havuzları.
- **Tema**: `localStorage['sfdap-theme']` > sistem tercihi > dark default; `<html data-theme="light">`. Tüm toggle'lar `.js-theme-toggle` class'ını paylaşır.
- **Rol-aware nav**: `[data-role]` ile sidebar öğeleri (örn. `#users` yalnız admin) gizlenir/gösterilir.
- **Harita**: Leaflet + OpenStreetMap, 7 coğrafi bölge renk kodlu çiftlik dağılımı.

## 🚀 Geliştirici komutları

```bash
cd frontend && npm install          # Node 18+

npm run dev                         # Vite dev (:5173) — /api, /metrics, /static → :8000 proxy
npm test                            # Vitest (jsdom) — 59 test
npm run test:coverage               # coverage (src/lib/**)
npm run a11y:axe                    # axe-core (çalışan :8000 sunucu gerektirir)
npm run build                       # dist/ üretir (üretim mount'u kullanmaz; istenirse mount yolu frontend/dist yapılmalı)
```

## ♿ Erişilebilirlik

- Skip-to-content link (`<a href="#main-content">`) + `<main id="main-content">` landmark
- Sidebar `<nav aria-label="Ana menü">`, aktif öğede `aria-current="page"`
- Tablo başlıkları `<th scope="col">`
- Async render hedeflerinde `aria-busy` + `aria-live="polite"`
- Buton/ikonlarda `aria-label` (tema toggle, hamburger, maskot)
- CI'da `a11y.yml` ile axe-core (WCAG 2.0/2.1 A+AA) taranır

## 🦴 Skeleton loaders

Her async `loadXxx()` fetch ÖNCESİ `_skeletonCards()` / `_skeletonRows()` çağırır; veri geldiğinde gerçek HTML ile değiştirir (`src/lib/skeleton.js`).
