# 🌾 Akıllı Tarım Veri Analizi Platformu (SFDAP) - Hafta 1 Analiz Raporu

**Hazırlayan:** Emirhan  
**Pozisyon:** Yazılım Mühendisi Adayı / Veri Analizi Sorumlusu  
**Tarih:** Mart 2026  
**Kurum:** Fırat Üniversitesi Yazılım Mühendisliği  

---

## 1. Proje Vizyonu ve Stratejik Amaçlar
Bu projenin temel vizyonu, geleneksel tarım pratiklerini dijital bir ekosisteme dönüştürerek **"Hassas Tarım" (Precision Agriculture)** prensiplerini hayata geçirmektir. Hedefimiz, çiftçilerin toprağını ve mahsulünü sadece gözlemle değil, bilimsel verilerle yönetmesini sağlamaktır.

> **Temel Misyon:** Veri odaklı kararlarla kaynak israfını önlemek ve tarımsal verimliliği sürdürülebilir kılmak.

### Stratejik Hedefler:
* **Kaynak Optimizasyonu:** Toprak nem ve sıcaklık sensörlerinden gelen verileri analiz ederek, su tüketiminde **%30'a varan** tasarruf sağlamak.
* **Yapay Zeka Destekli Erken Uyarı:** Derin öğrenme (Deep Learning) modelleri ile bitki hastalıklarını henüz başlangıç aşamasındayken teşhis etmek.
* **Karar Destek Sistemi:** Çiftçilere sulama, gübreleme ve hasat zamanlaması konularında veriye dayalı anlık rehberlik sunmak.

---

## 2. Teknik Kapsam ve Sistem Mimarisi
SFDAP, uçtan uca bir veri işleme hattı (Data Pipeline) olarak tasarlanmıştır. Sistem şu dört ana katmandan oluşmaktadır:



* **Veri Toplama (IoT & API):** Saha sensörlerinden (nem, pH, sıcaklık) gelen canlı verilerin ve harici meteoroloji servislerinin sisteme entegrasyonu.
* **Analiz Katmanı (AI & ML):** TensorFlow kullanılarak eğitilen modellerin, bitki sağlığı görüntülerini sınıflandırması ve risk tahminleri üretmesi.
* **Veri Yönetimi (Backend):** Ham verilerin Pandas kütüphanesiyle işlenmesi ve SQL tabanlı veritabanlarında yapılandırılmış olarak saklanması.
* **Görselleştirme (Frontend):** Karmaşık verilerin; ısı haritaları, grafikler ve mobil bildirimler aracılığıyla kullanıcıya sunulması.

---

## 3. Kullanılacak Kritik Veri Kaynakları
Platformun analiz gücü, aşağıdaki yüksek kaliteli veri setlerinden ve servislerden beslenecektir:

| Veri Kategorisi | Kaynak / Araç | Kullanım Amacı |
| :--- | :--- | :--- |
| **Meteoroloji** | OpenWeatherMap API | Yağış tahmini, don riski ve nem dengesi analizi. |
| **Bitki Sağlığı** | PlantVillage (Kaggle) | 50.000+ etiketli görsel ile hastalık tespit modelinin eğitilmesi. |
| **Saha Verileri** | IoT Sensör Simülasyonu | Gerçek zamanlı toprak nemi, sıcaklık ve pH takibi. |
| **Analiz Kütüphaneleri** | TensorFlow & Pandas | Derin öğrenme modelleri ve veri manipülasyonu. |

---

## 4. Beklenen Somut Sonuçlar (KPI)
Proje süreci sonunda aşağıdaki başarı kriterlerine (Key Performance Indicators) ulaşılması hedeflenmektedir:

1.  **Maliyet Azaltımı:** Optimize edilmiş sulama ve gübreleme takvimi sayesinde operasyonel maliyetlerde **%25 düşüş**.
2.  **Yüksek Teşhis Doğruluğu:** Bitki hastalıkları sınıflandırma modelinde minimum **%90 doğruluk** oranı.
3.  **Sürdürülebilirlik:** Gereksiz ilaç kullanımının önüne geçilerek toprak kalitesinin korunması ve çevre dostu üretim.
4.  **Erişilebilirlik:** Teknik bilgisi sınırlı çiftçilerin bile kullanabileceği, sade ve mobil uyumlu bir yönetim paneli.

---

## 5. Riskler ve Çözüm Yaklaşımları
* **Hatalı Veri Girişi:** Sensör arızalarından kaynaklanabilecek veri kayıpları için "ortalama değer atama" algoritmaları kullanılacaktır.
* **İnternet Kesintileri:** Sahadaki veri kaybını önlemek için cihazlarda yerel depolama ve senkronizasyon yapısı kurgulanacaktır.
