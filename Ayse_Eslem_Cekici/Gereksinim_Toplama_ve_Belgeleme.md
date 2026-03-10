# 🚀 Akıllı Tarım Veri Analizi Platformu: Detaylı Gereksinim Analizi

---

## 1. İşlevsel Gereksinimler (Functional Requirements)
* **Hiper-Yerel Hava Durumu Entegrasyonu:** Tarla koordinatlarına özel, genel veriden bağımsız yağış ve don tahmini.
* **Otonom Sulama Karar Mekanizması:** Toprak nemi ve beklenen yağış verisini karşılaştırarak otomatik vana kontrolü.
* **Bitki Sağlığı Analizi (CNN):** Görüntü işleme ile yaprak fotoğrafları üzerinden hastalık ve zararlı tespiti.
* **Dinamik Gübreleme Reçetesi:** Toprak pH ve NPK değerlerine göre her parsel için özelleştirilmiş gübreleme önerisi.
* **Hasat Zamanı Projeksiyonu:** Bitki büyüme evrelerini takip ederek en kârlı hasat tarihini önerme.

## 2. İşlevsel Olmayan Gereksinimler (Non-Functional Requirements)
* **Uç Birim İşleme (Edge Computing):** İnternet kesilse dahi kritik sulama kararlarının tarladaki yerel cihazda verilmesi.
* **Veri Güvenliği:** Çiftlik verilerinin ve konum bilgilerinin uçtan uca şifrelenmesi.
* **Düşük Güç Tüketimi:** Sensörlerin güneş paneli veya uzun ömürlü pillerle en az 1 yıl kesintisiz çalışması.
* **Hata Toleransı:** Bir sensör arızalandığında çevredeki verilerle tahminleme yaparak sistemin durmaması.

## 3. Veri Gereksinimleri (Data Requirements)
* **Zaman Serisi Verileri:** Nem, sıcaklık ve ışık şiddeti gibi değerlerin tarihsel logları.
* **Görüntü Veri Seti:** ML modelleri için etiketlenmiş, hastalıklı ve sağlıklı bitki fotoğraf kümesi.
* **API Entegrasyon Katmanı:** Meteoroloji ve tarım borsası verilerinin JSON formatında çekilmesi.

## 4. Kullanıcı Gereksinimleri (User Requirements)
* **Bilişsel Yükü Azaltılmış Arayüz:** Karmaşık grafikler yerine doğrudan aksiyon öneren (Evet/Hayır) sade dashboard.
* **Sesli Uyarı Sistemi:** Don riski gibi kritik durumlarda traktör başındaki çiftçiye sesli mobil bildirim.
* **Rol Tabanlı Erişim:** Çiftçi, Ziraat Mühendisi ve Sistem Yöneticisi için farklı yetki seviyeleri.

---
### 💡 Yenilikçi Yaklaşımlar (Özgün Fikirler):
* **Su Ayak İzi Takibi:** Yapılan su tasarrufunun finansal ve çevresel raporunun sunulması.
* **Piyasa Entegrasyonu:** Gübre fiyatlarını takip ederek en uygun maliyetli satın alma zamanını bildirme.