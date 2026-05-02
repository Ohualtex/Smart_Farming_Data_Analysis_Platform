# 🖥️ Frontend (Kullanıcı Arayüzü) Kılavuzu

Bu doküman, Ecenur Üner tarafından geliştirilen ve kullanıcıların sistemle etkileşim kurduğu "Veri Görselleştirme Panosu" (Dashboard) hakkında teknik bilgiler içerir.

## 📁 Dizin Yapısı
Frontend kodları projenin kök dizinindeki `frontend/` klasörü altında bulunur:
- `index.html`: Uygulamanın ana iskeleti ve tek sayfalık yapısı (Single Page Application - SPA).
- `css/`: Ortak tasarım token'larını (renkler, fontlar, glassmorphism efektleri) içeren stil dosyaları.
- `js/`: API'den verileri `fetch` ederek grafikleri render eden asenkron iş mantığı dosyaları.

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
