# 🖥️ Frontend (Kullanıcı Arayüzü) Kılavuzu

Bu doküman, kullanıcıların sistemle etkileşim kurduğu "Veri Görselleştirme Panosu" (Dashboard) hakkında teknik bilgi sağlar.

## 📁 Dizin Yapısı
Frontend kodları `frontend/` altında, **modüler vanilla-JS ESM** mimarisindedir (ES module split tamamlandı):
- `index.html` (~1 000 satır): yalnız markup — inline `<style>`/`<script>` yok; stiller `<link>`, JS `<script type="module">` ile yüklenir.
- `src/main.js`: SPA giriş noktası (264 satır); lib modüllerini import eder.
- `src/lib/*.js` (11 modül): `api`, `router`, `map`, `charts`, `render`, `skeleton`, `utils`, `ui_helpers`, `session`, `nav`, `filiz`.
- `src/styles/*.css` (10 modül): `main.css` import-hub ile `variables → base → layout → components → pages → welcome → filiz → theme-toggle → theme-light`.
- `package.json` + `vite.config.js`: Vite **yalnız** dev/build aracı (HMR + `/api` proxy); üretimde bundle servis edilmez.

## 🚀 Çalıştırma ve Test
1. **Üretim/demo:** FastAPI'yi başlatın (`make run`) → [http://localhost:8000/dashboard/](http://localhost:8000/dashboard/). `StaticFiles` `frontend/` kökünü mount eder; tarayıcı ham ES modüllerini ve Chart.js/Leaflet'i CDN'den yükler (build yok).
2. **Geliştirme (HMR):** `cd frontend && npm install && npm run dev` → :5173 (`/api`, `/metrics`, `/static` → :8000 proxy).
3. **Test:** `npm test` (Vitest + jsdom, 74 test) · `npm run a11y:axe` (axe-core, çalışan sunucu gerekir).

## 🔗 API İletişimi (Backend Entegrasyonu)
İstekler `src/lib/api.js` üzerinden asenkron `fetch()` ile yapılır:
- **Kimlik:** Tüm API çağrıları JWT **Bearer token** ile yapılır (`localStorage['sfdap_auth_token']`, `/api/auth/login`'den alınır); `apiAuth` 401'de logout, 403'te yetki uyarısı verir.
- **Legacy istisna:** `X-API-Key` yalnız `/api/model-performance` (2 route) için kalan eski koruma katmanıdır; son-kullanıcı akışı kullanmaz.
- Gelen JSON, `Chart.js` (çizgi/bar/doughnut vb.) ve `Leaflet` (harita) ile görselleştirilir.

## 🎨 Tasarım Sistemi (Aesthetics)
- **Tema:** Dark/Light (gün-gece) + glassmorphism; `localStorage['sfdap-theme']` + `<html data-theme>` ile yönetilir, tüm toggle'lar `.js-theme-toggle` paylaşır.
- **Kütüphaneler:**
  - Fontlar: Google Fonts (Inter)
  - Grafikler: Chart.js · Harita: Leaflet
  - İkonlar: emoji + inline SVG (FontAwesome kullanılmaz).
