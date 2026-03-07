🌾 Akıllı Tarım Veri Analizi Platformu (SFDAP) - Detaylı Analiz Raporu
Hazırlayan: Emirhan (Fırat Üniversitesi Yazılım Mühendisliği)
Tarih: Mart 2026

1. Stratejik Amaç ve Vizyon
Bu projenin temel vizyonu, geleneksel tarım pratiklerini modern veri bilimi ve IoT (Nesnelerin İnterneti) ekosistemiyle birleştirerek "Hassas Tarım" (Precision Agriculture) devrimine katkı sağlamaktır.

Verimlilik: Birim alandan alınan mahsul miktarını veri odaklı kararlarla maksimize etmek.

Sürdürülebilirlik: Su ve gübre gibi kritik kaynakların israfını önleyerek çevresel etkiyi azaltmak.

Dijital Dönüşüm: Çiftçilerin teknolojik okuryazarlığını artıracak kullanıcı dostu araçlar sunmak.

2. Proje Kapsamı ve Modüler Yapı
Platform, birbirine entegre dört ana katmandan oluşmaktadır:

A. Veri Toplama Katmanı (Data Acquisition)
Toprak Sensörleri: Nem, sıcaklık ve pH değerlerinin gerçek zamanlı takibi.

Meteorolojik Veriler: Bölgesel hava durumu tahminleri ve anlık değişimlerin sisteme dahil edilmesi.

B. Analiz ve Tahminleme Katmanı (Intelligence)
Sulama Optimizasyonu: Evapotranspirasyon (buharlaşma) hesaplamalarıyla dinamik sulama takvimi.

Hastalık Teşhisi: Derin öğrenme (Deep Learning) modelleri ile yaprak fotoğraflarından otomatik patojen tespiti.

C. Kullanıcı Arayüzü ve Raporlama (Visualization)
Dashboard: Tarlanın genel sağlık durumunu gösteren ısı haritaları (Heatmaps).

Bildirim Sistemi: Kritik eşik değişimlerinde (don riski, aşırı kuraklık) anlık mobil/web uyarıları.

3. Veri Kaynakları ve Teknoloji Entegrasyonu
Projenin başarısı, kullanılan verilerin kalitesine ve çeşitliliğine dayanmaktadır:
Veri Kategorisi,Kaynak / Araç,Detay
Görüntü İşleme,PlantVillage Dataset,50.000+ hastalık etiketli bitki fotoğrafı.
Hava Durumu,OpenWeatherMap API,"Rüzgar hızı, nem ve 7 günlük tahmin verileri."
Analiz Kütüphaneleri,TensorFlow & Pandas,Model eğitimi ve veri manipülasyonu.
Depolama,SQL & Cloud (AWS/Azure),Ölçeklenebilir veri tabanı ve bulut bilişim altyapısı.

4. Beklenen Teknik Çıktılar (KPI - Key Performance Indicators)
Doğruluk Oranı: Hastalık teşhis modelinde minimum %85 başarı yüzdesi.

Kaynak Tasarrufu: Manuel sulamaya oranla %25 su tasarrufu öngörüsü.

Hızlı Yanıt: API uç noktalarının (endpoints) 200ms altında yanıt süresi ile çalışması.

5. Risk Analizi ve Çözüm Önerileri
Risk: Sensörlerin zorlu saha koşullarında bozulması.

Çözüm: Veri setinde "eksik veri" (missing data) durumları için ortalama değer atama algoritmaları geliştirilmesi.

Risk: İnternet erişimi kısıtlı bölgeler.

Çözüm: Platformun "Offline-first" prensibiyle çalışması ve veri senkronizasyonu yeteneği
