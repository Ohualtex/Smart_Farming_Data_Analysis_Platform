HAFTA 1: Veri Seti İncelemesi ve Ön İşleme Raporu
Hazırlayan: MEHMET SAİT TAYSİ

Görev: Veri Analizi ve Ön İşleme

Tarih: 08.03.2026

1. Veri Kaynaklarının Analizi
Platformun temelini oluşturacak üç ana veri kategorisi belirlenmiştir:

Zaman Serisi Verileri: Toprak nemi, sıcaklık, pH ve ışık şiddeti logları.

Görsel Veri Setleri: Bitki sağlığı analizi (CNN) için etiketlenmiş yaprak fotoğrafları.

Dış Kaynaklı Veriler: Meteoroloji servislerinden (JSON formatında) alınan hava tahmin verileri.

2. Veri Ön İşleme (Preprocessing) Adımları
Ham verilerin model eğitimine uygun hale getirilmesi için aşağıdaki teknik süreçler uygulanacaktır:

Eksik Veri Tamamlama (Handling Missing Values)

İnterpolasyon: Kısa süreli veri kayıpları doğrusal tamamlama ile giderilecektir.

Medyan Atama: Uzun süreli eksikliklerde tarihsel ortalamalar kullanılacaktır.

Aykırı Değer Tespiti (Outlier Detection)

Z-Score ve IQR Analizi: İstatistiksel sınırların dışındaki hatalı ölçümler temizlenecektir.

Fiziksel Filtreleme: Tarım mantığına aykırı ani dalgalanmalar (örn: nemin anlık %0'dan %100'e çıkması) elenecektir.

Veri Dönüşümü (Data Transformation)

Normalizasyon: Farklı ölçeklerdeki verilerin modelde eşit ağırlığa sahip olması için Min-Max Scaling uygulanacaktır.

Kategorik Kodlama: Bitki türü veya toprak tipi gibi metinsel veriler sayısal matrislere dönüştürülecektir.

3. Özellik Mühendisliği (Feature Engineering)
Buharlaşma Katsayısı: Sıcaklık ve nem verisi kullanılarak bitki su ihtiyacı hassaslaştırılacaktır.

Gecikmeli Değişkenler: Geçmiş 24 saatlik nem trendi, sulama kararı için sisteme girdi olarak eklenecektir.
