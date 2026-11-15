# Vize için minimal düzeltmeler

`app.py`, `kurallar.py` ve `templates/ogrenci.html` üzerinde sınırlı değişiklik yapıldı.
`templates/admin.html` ve `templates/giris.html` aynen korundu.
Eski SQLite veritabanına iki sütun `ALTER TABLE` ile eklenir, veritabanını silmeyin.

**Önemli sınırlar:** Gerçek belge içeriği OCR ile okunmaz. Formdaki `belge_gun` ve onay kutuları öğrenci beyanıdır. Resmî tatiller yalnızca 2026-2027 tam gün tarihleriyle hesaplanır; arifeler ayrı uyarıdır. Akademik yıl kontrolünde 1 Eylül - 31 Ağustos *demo varsayımı* kullanılır; Kocaeli Üniversitesi'nin resmî döneme göre güncelleyin. Yeni sütunlar eski kayıtlar için NULL kalır. CSV'de `dogum_tarihi`, `saglik_yardimi` alanları zorunlu. Mevcut hash yöntemi ve demo parolaları güvenli dağıtım için uygun değildir. Uygulamayı internete açmayın.

Kurulum: `pip install flask` ; `python app.py`.

Test CSV: `ornek_ogrenciler.csv`, kurgusal bilgi içerir.
Not: Test kaydındaki TC kimlik numarası format test içindir, gerçek T.C. kimlik kontrol basamağı hesaplanmaz.
Tatil kaynakları: https://dhmi.gov.tr/AIPDocuments/LT_GEN_2_1_en.pdf ; https://diyanet.gov.tr/dini-gun-geceler ; https://www.borsaistanbul.com/resmi-tatil-gunleri
