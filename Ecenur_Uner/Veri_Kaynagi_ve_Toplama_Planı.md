# 2.Hafta: Veri Kaynaklarının Belirlenmesi ve Veri Toplama Planının Oluşturulması

## 1. Veri Kaynakları (Data Sources)
Projemizde kullanılacak temel veri kaynakları şunlardır:
* **Hava Durumu Verileri:** OpenWeatherMap API (sıcaklık, nem ve yağış tahminleri için).
* **Toprak Verileri:** IoT simülasyon araçları (Toprak nemi, pH değeri ve mineral seviyeleri).
* **Piyasa Verileri:** Tarım ve Orman Bakanlığı web servisleri (Ürün fiyat endeksleri).

## 2. Veri Toplama Yöntemi (Data Collection Method)
* **API Entegrasyonu:** Hava durumu ve piyasa değerleri için REST API üzerinden JSON formatında veri çekilecektir.
* **Web Scraping:** API desteği olmayan ikincil kaynaklar için Python (BeautifulSoup) kullanılarak veri kazıma yapılacaktır.

## 3. Toplama Sıklığı (Update Frequency)
* **Hava Durumu:** Her 3 saatte bir güncellenecek.
* **Toprak Sensörleri:** Gerçek zamanlıya yakın (Her 15 dakikada bir).
* **Piyasa Fiyatları:** Günlük olarak bir kez çekilecek.

## 4. Veri Formatı ve Tahmini Hacim
* **Format:** Tüm veriler işlenmek üzere **JSON** ve **CSV** formatında saklanacaktır.
* **Hacim:** Başlangıç aşamasında günlük yaklaşık 10-15 MB veri birikmesi öngörülmektedir.