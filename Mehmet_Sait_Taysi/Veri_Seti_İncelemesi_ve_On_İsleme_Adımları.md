# 🌾 Akıllı Tarım Veri Analizi Platformu
## 📊 Veri İnceleme ve Ön İşleme Stratejisi Raporu

Bu belge, Akıllı Tarım Veri Analizi Platformu kapsamında kullanılacak ham veri setlerinin incelenmesi ve makine öğrenimi (ML) modellerinin (sulama optimizasyonu, gübreleme önerileri, hastalık tahmini) eğitilmeden önce uygulanacak **veri ön işleme** adımlarını tanımlar.

---

### 🗂️ 1. Veri Kaynakları ve Profili
Proje kapsamında üç ana veri akışı işlenecektir:

* **Toprak Sensörü Verileri:** Nem, sıcaklık, pH seviyesi ve NPK (Azot, Fosfor, Potasyum) değerleri (Zaman serisi / Tabular).
* **Hava Durumu API Verileri:** Saatlik/Günlük sıcaklık, yağış miktarı, rüzgar hızı ve güneşlenme süresi (Zaman serisi / Tabular).
* **Bitki Sağlığı Görüntüleri:** İHA (Drone) veya sabit kameralardan alınan, hastalık tespiti için kullanılacak RGB/Multispektral görüntüler (Görüntü verisi).

---

### 🧹 2. Eksik Veri Tamamlama (Imputation)
Sensör arızaları veya ağ kesintileri nedeniyle oluşabilecek eksik veriler (NaN/Null) aşağıdaki stratejilerle yönetilecektir:

#### **Zaman Serisi Verileri (Sensör ve Hava Durumu):**
* **Kısa süreli kesintiler (< 3 saat):** İleri/Geri Doldurma (*Forward/Backward Fill*) veya Doğrusal İnterpolasyon (*Linear Interpolation*) kullanılacaktır.
* **Uzun süreli kesintiler (> 3 saat):** O günün tarihsel ortalaması veya hareketli ortalama (*Moving Average*) kullanılacaktır.

#### **Kategorik Veriler (Örn: Toprak Tipi):**
* Eksik değerler veri setinin mod (en çok tekrar eden) değeri ile doldurulacak veya modelin öğrenmesi için "Bilinmiyor" olarak etiketlenecektir.

#### **Görüntü Verileri:**
* Bozuk (*corrupted*) veya metadatasında eksiklik olan görüntü dosyaları analiz boru hattından (*pipeline*) tamamen çıkarılacaktır.

---

### 🚨 3. Aykırı Değer Tespiti (Outlier Detection)
Sensörlerin yanlış kalibrasyonu veya anlık hatalı okumaları sonucu ortaya çıkan aykırı değerlerin tespiti için hibrit bir yaklaşım benimsenecektir:

1.  **İstatistiksel Yöntemler:** Tabular verilerde, verinin dağılımına göre **Z-Skoru** (Z-Score > 3) veya **Çeyrekler Açıklığı (IQR)** yöntemleri uygulanarak istatistiksel aykırılıklar tespit edilecektir.
2.  **Alan Bilgisine (Domain Knowledge) Dayalı Filtreleme:** Mantıksal sınırların dışındaki değerler doğrudan filtrelenecektir.
    * *Örnek:* Toprak neminin %0'dan küçük veya %100'den büyük olması, pH değerinin 0-14 aralığı dışında olması gibi durumlarda bu veriler "Eksik Veri" (NaN) olarak işaretlenip, 2. adımdaki tamamlama yöntemlerine tabi tutulacaktır.

---

### 🔄 4. Veri Dönüşümü ve Normalizasyon (Data Transformation)
Modellerin daha hızlı ve kararlı öğrenebilmesi için veri setleri standart formatlara dönüştürülecektir.

#### **A. Tabular Veriler (Pandas & Scikit-learn)**
* **Ölçeklendirme (Scaling):** NPK değerleri, sıcaklık ve yağış gibi farklı birimlerdeki veriler aynı ölçeğe getirilmek için `MinMaxScaler` veya `StandardScaler` kullanılarak normalize edilecektir.
* **Zaman Özelliklerinin Çıkarılması (Feature Engineering):** `Datetime` sütunları parçalanarak modele "Ay", "Gün", "Mevsim" ve "Günün Saati" gibi yeni anlamlı özellikler (*features*) olarak eklenecektir.
* **Kategorik Veri Dönüşümü:** Toprak türü, bitki türü gibi metinsel veriler **One-Hot Encoding** yöntemi ile sayısal vektörlere dönüştürülecektir.

#### **B. Görüntü Verileri (TensorFlow/Keras & OpenCV)**
* **Yeniden Boyutlandırma (Resizing):** Tüm bitki sağlığı görüntüleri model mimarisine (örn: ResNet veya özel CNN) uygun standart bir boyuta (örn: 224x224 piksel) getirilecektir.
* **Piksel Normalizasyonu:** Görüntülerin piksel değerleri (0-255 aralığı), `1/255` ile çarpılarak **0 ile 1** arasına çekilecektir.
* **Veri Çoğaltma (Data Augmentation):** Görüntü tabanlı modelin ezberlemesini (*overfitting*) önlemek için; rastgele döndürme, yakınlaştırma (*zoom*), yatay/dikey çevirme (*flip*) ve parlaklık ayarı gibi işlemler uygulanacaktır.

---

### 🛠️ 5. Kullanılacak Teknolojiler ve Kütüphaneler
Bu aşamada aşağıdaki teknolojilerden yararlanılacaktır:

* **Veri Manipülasyonu:** Pandas, NumPy
* **Makine Öğrenimi Hazırlığı:** Scikit-learn
* **Görüntü İşleme:** OpenCV, TensorFlow/Keras (`tf.data.Dataset`)
* **Veritabanı (SQL):** Gelen ham verilerin sorgulanması ve işlenmiş verilerin (*Clean Data*) buluta (**AWS/GCP/Azure**) yazılması.
