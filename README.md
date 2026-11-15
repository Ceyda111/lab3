Staj Evrak Doğrulama ve Yönetim Sistemi -----------------Vize Projesi

Kocaeli Üniversitesi Yazılım Mühendisliği Bölümü Programlama Laboratuvarı III dersi vize projesidir.

Proje Kapsamı
E-posta ve şifre ile giriş yapma (Şifreler SHA-256 ile hashleniyor)

5 hatalı giriş denemesinde hesabın kilitlenmesi ve giriş loglarının tutulması

Rol tabanlı yetkilendirme (ROLE_ADMIN ve ROLE_STUDENT)

Admin panelinden CSV ile öğrenci veri seti yükleme

Nesne Yönelimli Programlama (NYP) prensiplerine uygun kural kontrol mimarisi (kurallar.py dosyasında)

Adres, telefon, e-posta, kimlik numarası, tarih aralığı, resmi tatil hesabı ve imza kontrolleri

Kullanılan Teknolojiler

Python 3

Flask

SQLite

Kurulum ve Çalıştırma

Projeyi çalıştırmak için terminalde şu adımları izleyebilirsiniz:

Gerekli kütüphaneyi yükleyin:
pip install flask

Uygulamayı başlatın:
python app.py

Tarayıcınızdan http://127.0.0.1:5000 adresine giriş yapabilirsiniz.

Test Hesapları

Admin: admin@kou.edu.tr / admin123

Öğrenci: ogrenci@kou.edu.tr / 123456

Dosya Yapısı

app.py: Ana Flask uygulaması ve rota tanımları

kurallar.py: OOP kuralları ve doğrulama sınıfları

staj_vize.db: SQLite veritabanı (otomatik oluşur)

templates/: HTML arayüz dosyaları (giris, ogrenci, admin)

yuklenen_dosyalar/: Yüklenen belgelerin saklandığı klasör
