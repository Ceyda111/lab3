import unittest
from kurallar import kontrolleri_calistir

class KuralTestleri(unittest.TestCase):
    def veri(self, **degisiklik):
        d = dict(ad_soyad='Ceyda Yilmaz', uyruk='TC', kimlik_no='12345678901',
                 adres='Kabaoglu Mah, Merkez Cad, No:5, D:1, Izmit/Kocaeli',
                 telefon='+90 555 111 22 33', eposta='ogrenci@kou.edu.tr',
                 ogretim_yili='2026-2027 Yaz', baslangic='2027-07-05',
                 bitis='2027-07-09', teslim_tarihi='2027-06-01',
                 gunler=['Pzt', 'Sal', 'Car', 'Per', 'Cum'], belge_gun=5,
                 muhendis=3, muh_bolum='Yazilim', ogr_onay=False,
                 danisman_onay=False, isveren_onay=True,
                 db_ogrenci={'ad_soyad':'Ceyda Yilmaz','tc_no':'12345678901'})
        d.update(degisiklik)
        return d

    def test_gecerli_form(self):
        self.assertEqual(kontrolleri_calistir(self.veri()), ([], 5))

    def test_gec_teslim(self):
        errors, _ = kontrolleri_calistir(self.veri(teslim_tarihi='2027-06-20'))
        self.assertTrue(any('30 gun' in e for e in errors))

    def test_bitis_once(self):
        errors, _ = kontrolleri_calistir(self.veri(bitis='2027-07-01'))
        self.assertTrue(any('Bitis' in e for e in errors))

    def test_bos_tarih_sayfayi_cokertmez(self):
        errors, _ = kontrolleri_calistir(self.veri(baslangic=''))
        self.assertTrue(any('tarihi' in e for e in errors))

    def test_tatil_cikarma(self):
        errors, gun = kontrolleri_calistir(self.veri(baslangic='2027-07-12', bitis='2027-07-16', belge_gun=4))
        self.assertEqual(gun, 4)  # 15 Temmuz resmi tatil
        self.assertEqual(errors, [])

    def test_bilinmeyen_takvim(self):
        errors, _ = kontrolleri_calistir(self.veri(baslangic='2028-07-03',bitis='2028-07-07',ogretim_yili='2027-2028 Yaz'))
        self.assertTrue(any('takvimde yok' in e for e in errors))

    def test_yarim_gun_uyarisi(self):
        errors, _ = kontrolleri_calistir(self.veri(baslangic='2027-03-08',bitis='2027-03-12',ogretim_yili='2026-2027 Bahar',belge_gun=1))
        self.assertTrue(any('Yarim gun' in e for e in errors))

if __name__ == '__main__': unittest.main()
