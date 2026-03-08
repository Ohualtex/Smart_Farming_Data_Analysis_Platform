
 1. Veri Kaynakları ve Profili
Proje kapsamında üç ana veri akışı işlenecektir:

Toprak Sensörü Verileri :     
Nem, sıcaklık, pH seviyesi ve NPK (Azot, Fosfor, Potasyum) değerleri (Zaman serisi / Tabular).

Hava Durumu API Verileri: Saatlik/Günlük sıcaklık, yağış miktarı, rüzgar hızı ve güneşlenme süresi (Zaman serisi / Tabular).

Bitki Sağlığı Görüntüleri: İHA (Drone) veya sabit kameralardan alınan, hastalık tespiti için kullanılacak RGB/Multispektral görüntüler (Görüntü verisi).

2. Eksik Veri Tamamlama (Imputation)
Sensör arızaları veya ağ kesintileri nedeniyle oluşabilecek eksik veriler (NaN/Null) aşağıdaki stratejilerle yönetilecektir:

Zaman Serisi Verileri: Kısa süreli kesintiler (< 3 saat) için İleri/Geri Doldurma veya Doğrusal İnterpolasyon; uzun süreli kesintiler için hareketli ortalama kullanılacaktır.

Kategorik Veriler: Eksik değerler mod değeri ile doldurulacak veya "Bilinmiyor" olarak etiketlenecektir.

Görüntü Verileri: Bozuk veya metadata eksikliği olan dosyalar pipeline'dan tamamen çıkarılacaktır.

3. Aykırı Değer Tespiti (Outlier Detection)
Sensörlerin yanlış kalibrasyonu veya anlık hatalı okumaları sonucu ortaya çıkan aykırı değerlerin tespiti için hibrit bir yaklaşım benimsenecektir:

İstatistiksel Yöntemler: Tabular verilerde Z-Skoru (Z > 3) veya IQR yöntemleri ile aykırılıklar tespit edilecektir.

Alan Bilgisi Filtreleme: Mantıksal sınırların (Örn: pH 0-14 dışı, nem %100 üstü) dışındaki değerler "Eksik Veri" olarak işaretlenip tamamlama yöntemlerine tabi tutulacaktır.

4. Veri Dönüşümü ve Normalizasyon
Modellerin daha hızlı ve kararlı öğrenebilmesi için veri setleri standart formatlara dönüştürülecektir:

Ölçeklendirme: Farklı birimlerdeki veriler MinMaxScaler veya StandardScaler ile normalize edilecektir.

Feature Engineering: Datetime sütunlarından Ay, Gün ve Mevsim gibi anlamlı özellikler çıkarılacaktır.

Görüntü Ön İşleme: Görüntüler 224x224 boyutuna getirilecek, piksel değerleri 0-1 arasına çekilecek ve Data Augmentation (döndürme, zoom vb.) uygulanacaktır.

5. Kullanılacak Teknolojiler ve Kütüphaneler
Veri Manipülasyonu: Pandas, NumPy

Makine Öğrenimi Hazırlığı: Scikit-learn

Görüntü İşleme: OpenCV, TensorFlow/Keras

Veritabanı: SQL tabanlı ham veri sorgulama ve temizlenmiş verilerin bulut sistemlerine (AWS/GCP/Azure) aktarımı.

Hazırlayan: Mehmet Sait Taysi

Görev: Veri Seti İncelemesi ve Ön İşleme Adımları

Tarih: 08.03.2026
