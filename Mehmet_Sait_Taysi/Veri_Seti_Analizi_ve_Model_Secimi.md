# 🌾 Akıllı Tarım Veri Analizi Platformu
## 📈 Keşifsel Veri Analizi (EDA) ve Algoritma Ön Değerlendirme Raporu

> **Hazırlayan:** Mehmet Sait Taysi
> **Görev:** Veri Seti Analizi ve Model Seçimi
> **Tarih:** 08.03.2026

---

Bu belge, Akıllı Tarım platformumuzdaki veri setlerinin istatistiksel dağılımlarını, değişkenler arası ilişkilerini ve korelasyonlarını analiz eder. Analiz bulguları ışığında, projedeki farklı görevler (sulama, gübreleme, hastalık tespiti) için en uygun makine öğrenimi algoritmaları değerlendirilmiştir.

### 🔍 1. Değişken Dağılımları ve İlişkisel Analiz
Veri setinin yapısını ve özelliklerini anlamak için aşağıdaki analizler gerçekleştirilecektir:

* **Tek Değişkenli Analiz (Univariate):** Sıcaklık, Nem, pH ve NPK (Azot, Fosfor, Potasyum) değerlerinin dağılımları histogramlar ve kutu grafikleri (Boxplot) ile incelenecektir. Bu sayede verinin normal dağılıma uyup uymadığı ve çarpıklık (skewness) oranları belirlenecektir.
* **İki Değişkenli Analiz (Bivariate):**
  * Çiftçinin sulama ve gübreleme alışkanlıkları ile mahsul verimi arasındaki doğrusal veya doğrusal olmayan ilişkiler dağılım grafikleri (Scatter Plot) ile analiz edilecektir.

### 🔗 2. Korelasyon ve Hedef Değişken Analizi
Özelliklerin (features) birbirleriyle ve tahmin etmeye çalıştığımız hedef değişkenle (target) ne kadar ilişkili olduğunu anlamak model başarısı için kritiktir.

* **Korelasyon Matrisi (Heatmap):** Değişkenler arasındaki Pearson ve Spearman korelasyon katsayıları hesaplanacaktır.
  * *Çoklu Doğrusallık (Multicollinearity) Tespiti:* Birbiriyle %85'in üzerinde yüksek korelasyona sahip bağımsız değişkenler tespit edilip, modelin aşırı öğrenmesini engellemek için biri veri setinden çıkarılacaktır.
* **Hedef Değişkenle İlişki:** Hastalık durumu (Var/Yok) veya Mahsul Verimi (Ton) gibi hedef değişkenlerimizi en çok etkileyen özellikler (Feature Importance) belirlenecektir.

---

### 🤖 3. Makine Öğrenimi Algoritmaları Ön Değerlendirmesi
Tarım veri setimizin karmaşık yapısına uygun algoritma eşleştirmeleri aşağıda sunulmuştur:

#### A. Sulama ve Gübreleme Optimizasyonu (Tabular Veri)
**Önerilen Algoritma: Random Forest (Rastgele Orman) / XGBoost**
* **Veri Eşleşmesi:** Sensör verilerindeki doğrusal olmayan ilişkileri modellemek için idealdir.
* **Güçlü Yönleri:** Aşırı öğrenmeye (overfitting) karşı dirençlidir. Karmaşık verilerde yüksek doğruluk sağlar.
* **Zayıf Yönleri:** Parametre optimizasyonu (tuning) zaman alabilir ve daha fazla hesaplama gücü gerektirir.

#### B. Bitki Hastalığı Tahmini (Görüntü Verisi)
**Önerilen Algoritma: Convolutional Neural Networks - CNN (Örn: ResNet50 veya MobileNet)**
* **Veri Eşleşmesi:** Görüntüdeki doku/renk değişimlerini (hastalık lekeleri) yakalamak için özel olarak tasarlanmıştır.
* **Güçlü Yönleri:** Transfer Öğrenme (Transfer Learning) ile yüksek başarı elde edilebilir. Edge Computing (kenar bilişim) için uygun hafif versiyonları vardır.
* **Zayıf Yönleri:** Kara Kutu (Black Box) yapısındadır. Eğitimi için yüksek GPU gücü ve çok sayıda etiketli görüntü gerektirir.

#### C. Hava ve Toprak Nemi Tahmini (Zaman Serisi Verisi)
**Önerilen Algoritma: LSTM (Long Short-Term Memory) Ağları**
* **Veri Eşleşmesi:** Sensörlerden akan zaman serisi verilerindeki "zaman" bağıntısını hatırlamak için biçilmiş kaftandır.
* **Güçlü Yönleri:** Uzun vadeli bağımlılıkları (örn. geçmiş yağışların bugünkü neme etkisi) öğrenebilir.
* **Zayıf Yönleri:** Eğitimi donanım açısından maliyetlidir.
