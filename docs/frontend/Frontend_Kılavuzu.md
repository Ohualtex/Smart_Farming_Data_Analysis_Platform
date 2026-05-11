# 🖥️ Frontend (Kullanıcı Arayüzü) Kılavuzu

Bu doküman, Ecenur Üner tarafından geliştirilen ve kullanıcıların sistemle etkileşim kurduğu "Veri Görselleştirme Panosu" (Dashboard) hakkında teknik bilgiler içerir.

## 📁 Dizin Yapısı
Frontend kodları projenin kök dizinindeki `frontend/` klasörü altında bulunur ve şu an **tek dosyalı SPA** mimarisindedir:
- `index.html` (≈2 873 satır): Tüm uygulama — HTML iskelet, CSS (inline `<style>`, dark/light tema, glassmorphism), JavaScript (vanilla, asenkron `fetch`, Chart.js render, Filiz mascot logic).

> **shiftFinal planı:** Bu tek dosya Vite/esbuild ile `css/`, `js/` çıktılarına ayrılacak (HMR + minify + cache busting). Bkz. `projeakisi.md` → shiftFinal → Ecenur "Frontend Build Pipeline".

## 🚀 Çalıştırma ve Test
Frontend dosyaları doğrudan tarayıcıda açılabilir veya FastAPI üzerinden sunulur:
1. FastAPI'yi başlatın (`make run`).
2. Tarayıcıdan [http://localhost:8000/dashboard](http://localhost:8000/dashboard) adresine gidin.
3. FastAPI'nin `StaticFiles` modülü sayesinde `frontend/` dizini otomatik olarak serve edilir.

## 🔗 API İletişimi (Backend Entegrasyonu)
Frontend tarafı, backend ile konuşurken global olarak tanımlanmış bir yapı kullanır:
- İstekler asenkron `fetch()` fonksiyonu ile yapılır.
- Korunan (Protected) endpoint'lere veri gönderilirken `Headers` kısmında `"X-API-Key": "dev-api-key"` bilgisi iletilir.
- Gelen JSON verisi `Chart.js` kütüphanesi aracılığıyla (Doughnut, Bar, Polar Area ve Radar grafikleri olarak) görselleştirilir.

## 🎨 Tasarım Sistemi (Aesthetics)
- **Tema:** Dark Mode ve Glassmorphism (Bulanık arka plan) kombinasyonu.
- **Kütüphaneler:**
  - Fontlar: Google Fonts (Inter)
  - Grafikler: Chart.js
  - İkonlar: FontAwesome (Gelecek cycle'larda eklenecek).
