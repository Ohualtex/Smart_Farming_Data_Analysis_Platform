# Akıllı Tarım Veri Analizi Platformu (SFDAP)
## Kullanıcı Arayüzü (UI) ve Deneyimi (UX) Tasarım Raporu

Proje geliştirme sürecimizdeki Çekici Model'in "Büyüleme" aşamasına uygun olarak, hedef kitlemiz olan çiftçiler ve ziraat mühendisleri için görsel açıdan tatmin edici ve karmaşıklıktan uzak bir arayüz kurgulanmıştır.

### 1. Kullanıcı Deneyimi (UX) Tasarımının Yapılması
* **Bilişsel Yükün Optimizasyonu:** Tarladaki yoğun çalışma koşulları göz önüne alınarak, sensör verileri karmaşık grafikler yerine "Don Riski: Yüksek" veya "Sulama Gerekli" gibi net, eyleme dönüştürülebilir bildirimlere indirgenmiştir.
* **Erişilebilirlik ve Kontrast:** Güneş ışığı altında bile ekranın rahat okunabilmesi için yüksek kontrastlı renk paletleri ve okunaklı, büyük tipografiler tercih edilmiştir.
* **Hata Önleme ve Güven:** Sensörlerle bağlantı kopması durumunda sistem kullanıcıyı paniğe sevk etmeden, en son alınan güvenilir verileri ve bağlantı durumunu şeffaf bir şekilde sunar.

### 2. İnteraktif Özelliklerin Belirlenmesi
* **Dinamik Otonom Şalteri (Toggle):** Kullanıcı "Otonom Sulama" modunu tek bir dokunuşla aktif ettiğinde, arayüz anında güncellenerek kontrolün yapay zekaya (hava durumu ve nem sensörleri) geçtiğini görsel geri bildirimlerle belirtir.
* **Gerçek Zamanlı Yapay Zeka (AI) Etkileşimi:** "Bitki Sağlığı" modülünde, kullanıcı sisteme hastalıklı bir yaprak fotoğrafı yüklediği an arka planda analiz başlar ve saniyeler içinde teşhis/öneri kartı ekranda belirir.
* **Hızlı Aksiyon Menüleri:** Acil durumlarda (örneğin ani sıcaklık düşüşü) tek tıkla vanaları açma veya gübreleme sistemini başlatma gibi kısayollar Dashboard (Ana Panel) ekranına sabitlenmiştir.

---
### 3. Arayüz Tasarımları (High-Fidelity Wireframes)
Aşağıda belirtilen UX prensipleri ve interaktif özellikler doğrultusunda hazırlanan ekran tasarımlarımız yer almaktadır:

![Giriş Ekranı](SFDAP_Wireframe_01_Login.png)
![Dashboard (Ana Panel)](SFDAP_Wireframe_02_Dashboard.png)
![Sulama Kontrolü](SFDAP_Wireframe_03_Sulama.png)
![Bitki Sağlığı Analizi](SFDAP_Wireframe_04_Bitki_Sagligi.png)
![Gübreleme Takibi](SFDAP_Wireframe_05_Gubreleme.png)
![Hava Durumu ve Tahminler](SFDAP_Wireframe_06_Hava_Durumu.png)