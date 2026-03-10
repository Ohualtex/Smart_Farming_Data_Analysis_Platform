# Akıllı Tarım Veri Analizi Platformu (Smart Farming Data Analysis Platform / SFDAP)
Çiftçilerin tarımsal verimliliğini en üst düzeye çıkarmak amacıyla toprak sensörleri, hava durumu verileri ve bitki sağlığı görüntülerini entegre bir şekilde analiz eden kapsamlı bir veri analizi ve karar destek platformudur. Bu sistem, elde edilen verileri işleyerek sulama optimizasyonu, gübreleme önerileri ve erken hastalık tahmini gibi kritik konularda çiftçilere eyleme dönüştürülebilir içgörüler sunar.

# 🌟 Temel Özellikler
💧 Sulama Optimizasyonu: Toprak nem sensörleri ve anlık hava durumu verilerini kullanarak su israfını önler ve bitkinin ihtiyacı olan optimum su miktarını belirler.

🌱 Akıllı Gübreleme Önerileri: Toprak analizi verilerine dayanarak verimi artıracak en uygun gübre karışımlarını ve uygulama zamanlarını tavsiye eder.

🦠 Erken Hastalık Tahmini: Bitki sağlığı görüntülerini makine öğrenimi teknikleriyle analiz ederek potansiyel hastalıkları ve zararlıları önceden tespit eder.

📊 Görselleştirme ve Raporlama: Karmaşık tarımsal verileri anlaşılır grafiklere, ısı haritalarına ve periyodik raporlara dönüştürür.

# 🛠️ Kullanılan Teknolojiler
Platform, güçlü ve ölçeklenebilir bir mimari üzerine inşa edilmiştir:

Programlama Dili: Python

Makine Öğrenimi: TensorFlow, Keras

Veri İşleme ve Analiz: Pandas, NumPy

Veritabanı Yönetimi: SQL

Bulut Bilişim (Cloud Computing): AWS / Azure / GCP (Sunucu yönetimi, model dağıtımı ve veri depolama için)

# 📦 Proje Modülleri ve Teslim Edilenler
Bu depo aşağıdaki temel bileşenleri ve altyapıları içermektedir:

Veri Toplama ve İşleme Altyapısı: IoT toprak sensörlerinden ve hava durumu API'lerinden gelen ham verilerin toplanması, temizlenmesi ve veritabanına aktarılmasını sağlayan veri boru hatları (data pipelines).

Makine Öğrenimi Modelleri: Görüntü işleme ve tahmine dayalı analizler için TensorFlow kullanılarak geliştirilmiş modeller.

Web Tabanlı Kullanıcı Arayüzü: Çiftçilerin platformla etkileşime girebileceği kullanıcı dostu önyüz.

API Entegrasyonları: Dış servislerle haberleşen ve ön yüz ile arka yüz arasındaki iletişimi sağlayan uç noktalar.

Raporlama ve Görselleştirme Araçları: SQL sorguları ve Python veri analizi kütüphaneleri ile desteklenen dinamik paneller.

# 🚀 Kurulum ve Çalıştırma
Platformu yerel ortamınızda çalıştırmak için aşağıdaki adımları izleyin:

1. Depoyu klonlayın:

Bash
git clone https://github.com/Ohualtex/Smart_Farming_Data_Analysis_Platform.git
cd Smart_Farming_Data_Analysis_Platform

2. Gerekli kütüphaneleri yükleyin:
Proje dizininde sanal ortamınızı (virtual environment) oluşturduktan sonra bağımlılıkları yükleyin:

Bash
pip install -r requirements.txt

3. Çevresel değişkenleri (Environment Variables) ayarlayın:
Gerekli .env dosyasını oluşturarak içerisine kendi SQL veritabanı bağlantı bilgilerinizi ve bulut API anahtarlarınızı girin.

4. Uygulamayı başlatın:
(Kullandığınız web framework'üne göre başlatma komutunu buraya ekleyebilirsiniz, örneğin Flask/Django veya FastAPI)

Bash
python main.py

# 🤝 Katkıda Bulunma
Projeye katkıda bulunmak isterseniz, lütfen bir "Pull Request" oluşturmadan önce ilgili dokümantasyonları inceleyin. Her türlü geri bildirim ve hata bildirimi için projenin Issues sekmesini kullanabilirsiniz.
