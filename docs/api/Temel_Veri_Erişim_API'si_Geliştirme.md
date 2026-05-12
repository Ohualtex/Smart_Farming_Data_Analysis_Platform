# 🌾 Akıllı Tarım Veri Analizi ve Karar Destek Platformu (S.F.D.A.P.)

> **Tarihsel doküman — proje ilk haftalarındaki API tasarım kararlarını belgeler.**
> Güncel API kullanımı için [`API_Kullanim_Kilavuzu.md`](./API_Kullanim_Kilavuzu.md) ve `/docs` Swagger UI.

**Departman:** Fırat Üniversitesi, Yazılım Mühendisliği Bölümü

---

## 📑 Proje Genel Bakış ve Problem Tanımı
Modern tarımda verimlilik, rastgele sulama veya gübreleme ile değil; veriye dayalı kararlar ile sağlanır. Bu platform, geleneksel çiftçilik yöntemlerini **IoT (Nesnelerin İnterneti)** ve **Yapay Zeka** ile birleştirerek tarımsal kaynakların optimum kullanılmasını sağlar.

**Hafta 4 Odak Noktası:** Toprak sensörlerinden ve meteorolojik istasyonlardan gelen heterojen verilerin, sistemin diğer bileşenleri (Mobil uygulama, Web Dashboard ve AI Modelleri) tarafından tüketilebilmesi için standartlaştırılmış bir **RESTful API** katmanının mimari kurulumu gerçekleştirilmiştir.

---

## 🚀 Teknik Stack ve Ekosistem

Sistemin kalbinde yer alan teknolojiler ve tercih nedenleri:

| Teknoloji | Kullanım Amacı | Avantajı |
| :--- | :--- | :--- |
| **Python 3.10+** | Ana Programlama Dili | Veri bilimi kütüphaneleriyle (Pandas/TensorFlow) tam uyum. |
| **FastAPI** | Web Framework | Pydantic sayesinde otomatik veri validasyonu ve yüksek performans. |
| **Uvicorn** | ASGI Server | Asenkron istekleri yöneterek sistemin çökmesini engeller. |
| **OpenAPI/Swagger** | Dokümantasyon | Geliştiriciler için interaktif test arayüzü sağlar. |
| **API Key Auth** | Güvenlik | Veri gizliliğini sağlamak adına yetkilendirme katmanı. |

---

## 🛠️ Mimari Katmanlar ve API Tasarımı

### 1. Veri Erişim Katmanı (Data Access Layer)
API, düşük seviyeli sensör verilerini alır ve bunları anlamlı JSON objelerine dönüştürür.

* **Toprak Analizi:** Nem (`moisture`), asidite (`pH`) ve besin değerleri (`nitrogen`) sensörlerden asenkron olarak okunur.
* **Meteorolojik Veri:** Lokasyon bazlı sıcaklık ve tahmin verileri standardize edilir.

### 2. Güvenlik Katmanı (Security Layer)
Üçüncü şahısların sensör verilerine erişimini engellemek adına `X-API-Key` mekanizması uygulanmıştır. Her istek, backend tarafında bir `Depends` (Bağımlılık Enjeksiyonu) filtresinden geçerek doğrulanır.

---

## 📊 API Endpoint (Uç Nokta) Spesifikasyonları

### [GET] `/api/v1/soil-data`
Tarladaki aktif IoT cihazlarından gelen verileri döndürür.
- **Header:** `X-API-Key: <secret_key>`
- **Response Format:** `application/json`
- **Örnek Veri Yapısı:**
  ```json
  {
    "sensor_id": "FIRAT-SENS-12",
    "moisture_level": 48.7,
    "ph_level": 6.4,
    "nitrogen_level": 45
  }
