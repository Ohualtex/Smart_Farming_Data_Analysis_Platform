# 🌾 SFDAP Dashboard

Static SPA dashboard served by FastAPI at `/dashboard`.

## 📐 Mevcut yapı (shiftFinal A3)

- Tek dosya `index.html` (inline CSS + inline JS, ~2970 satır).
- FastAPI `app/main.py` içinde `StaticFiles(directory="frontend", html=True)` ile
  `/dashboard` altına mount edilir.
- Chart.js (`4.4.0`) CDN'den yüklenir; Inter fontu Google Fonts'tan gelir.
- Vite build iskeleti (`vite.config.js` + `package.json`) hazırdır;
  şu an inline mimari korunduğu için derleme şart değil, ileride
  ES modüllerine bölme adımı bu iskelet üzerinden ilerleyecek.

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
