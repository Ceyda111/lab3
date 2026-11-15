import re
from datetime import datetime, date, timedelta

# 2025-2026 egitim-ogretim yili icin 2025 ve 2026 Turkiye resmi tatilleri.
# Sadece TAM gun tatiller otomatik olarak gun sayisindan dusulur.
# Kaynak: Borsa Istanbul resmi tatil listesi ve Diyanet dini gunler takvimi.
RESMI_TATILLER = {
    # 2025
    date(2025, 1, 1),
    date(2025, 3, 30), date(2025, 3, 31), date(2025, 4, 1),
    date(2025, 4, 23), date(2025, 5, 1), date(2025, 5, 19),
    date(2025, 6, 6), date(2025, 6, 7), date(2025, 6, 8), date(2025, 6, 9),
    date(2025, 7, 15), date(2025, 8, 30), date(2025, 10, 29),
    # 2026
    date(2026, 1, 1),
    date(2026, 3, 20), date(2026, 3, 21), date(2026, 3, 22),
    date(2026, 4, 23), date(2026, 5, 1), date(2026, 5, 19),
    date(2026, 5, 27), date(2026, 5, 28), date(2026, 5, 29), date(2026, 5, 30),
    date(2026, 7, 15), date(2026, 8, 30), date(2026, 10, 29),
}
# Arife ve 28 Ekim: 13.00'ten itibaren yarim gun tatil.
YARIM_GUN_TATILLER = {
    date(2025, 3, 29), date(2025, 6, 5), date(2025, 10, 28),
    date(2026, 3, 19), date(2026, 5, 26), date(2026, 10, 28),
}
# Bu iki yil disinda takvim hesabi kesinlestirilmez.
TAKVIM_YILLARI = {2025, 2026}

class Dogrulayici:
    def __init__(self):
        # Kapsulleme: hata listesini disaridan gizli tutuyoruz
        self.__hatalar = []

    def hata_ekle(self, mesaj):
        self.__hatalar.append(mesaj)

    def hatalari_getir(self):
        return self.__hatalar

    def kontrol_et(self, veri):
        # Soyutlama: alt sınıflar bu metodu kendi kuralina gore yazacak
        raise NotImplementedError("Alt sinif kontrol_et metodunu yazmali")


class FormatKontrol(Dogrulayici):
    def kontrol_et(self, veri):
        adres_parcalari = []
        for parca in veri["adres"].split(","):
            if parca.strip() != "":
                adres_parcalari.append(parca.strip())

        if len(adres_parcalari) < 5:
            self.hata_ekle("Adres Mahalle, Cadde, Bina No, Daire No, Ilce/Il sirasinda olmali.")

        if not re.fullmatch(r"\+90 \d{3} \d{3} \d{2} \d{2}", veri.get("telefon", "").strip()):
            self.hata_ekle("Telefon +90 xxx xxx xx xx formatinda olmali.")

        if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", veri.get("eposta", "").strip()):
            self.hata_ekle("Gecerli bir e-posta adresi girilmeli.")


class KimlikKontrol(Dogrulayici):
    def kontrol_et(self, veri):
        no = veri["kimlik_no"].strip()
        uyruk = veri["uyruk"]

        if len(no) != 11 or not no.isdigit():
            self.hata_ekle("Kimlik numarasi 11 haneli ve sadece rakam olmali.")
        elif uyruk == "TC" and no[0] == "0":
            self.hata_ekle("TC kimlik numarasi 0 ile baslayamaz.")
        elif uyruk != "TC" and not no.startswith("99"):
            self.hata_ekle("Yabanci kimlik numarasi 99 ile baslamali.")

        # DB'deki ogrenci bilgileriyle karsilastirma
        db_ogr = veri["db_ogrenci"]
        if veri["ad_soyad"].strip().lower() != db_ogr["ad_soyad"].strip().lower():
            self.hata_ekle("Ad soyad veritabanindaki kayitla uyusmuyor.")
        if no != db_ogr["tc_no"].strip():
            self.hata_ekle("Kimlik no veritabanindaki kayitla uyusmuyor.")


class TarihVeGunKontrol(Dogrulayici):
    GUN_SOZLUGU = {"Pzt": 0, "Sal": 1, "Car": 2, "Per": 3, "Cum": 4, "Cmt": 5}

    def kontrol_et(self, veri):
        self.hesaplanan_gun = 0

        # Ogretim yili kontrolu (Orn: 2025-2026 Bahar)
        eslesme = re.match(r"^(\d{4})-(\d{4})\s+(Guz|Bahar|Yaz)$", veri["ogretim_yili"].strip())
        if not eslesme or int(eslesme.group(2)) != int(eslesme.group(1)) + 1:
            self.hata_ekle("Ogretim yili '2025-2026 Bahar' seklinde ardisik olmali.")

        try:
            bas = date.fromisoformat(veri.get("baslangic", ""))
            bit = date.fromisoformat(veri.get("bitis", ""))
            teslim = date.fromisoformat(veri.get("teslim_tarihi", ""))
        except (ValueError, TypeError):
            self.hata_ekle("Baslangic, bitis ve teslim tarihi gecerli olmalidir.")
            return

        if bit < bas:
            self.hata_ekle("Bitis tarihi baslangictan once olamaz.")
            return

        # En az 30 takvim gunu once teslim (formda bildirilen tarih).
        if teslim > bas - timedelta(days=30):
            onerilen = (bas - timedelta(days=30)).strftime("%Y-%m-%d")
            self.hata_ekle(f"Belge baslangictan en az 30 gun once verilmeli (Son tarih: {onerilen}).")

        # Öğretim yılını 1 Eylul - 31 Agustos araligi olarak kabul eden demo kuralı.
        # Gerçek akademik takvim farklıysa dersin ilan ettiği tarihlerle güncellenmeli.
        if eslesme and int(eslesme.group(2)) == int(eslesme.group(1)) + 1:
            ilk_yil, son_yil = int(eslesme.group(1)), int(eslesme.group(2))
            if not (date(ilk_yil, 9, 1) <= bas <= bit <= date(son_yil, 8, 31)):
                self.hata_ekle("Staj tarihleri secilen ogretim yili araliginda olmali (demo: Eylul-Agustos).")

        # Secilen haftalik gunlerden resmi tatilleri duserek gun sayma
        secilen_indeksler = []
        for g in veri["gunler"]:
            if g in self.GUN_SOZLUGU:
                secilen_indeksler.append(self.GUN_SOZLUGU[g])

        if not secilen_indeksler:
            self.hata_ekle("En az bir staj gunu secilmelidir.")
        sayac = 0
        yarim_gunler = []
        bilinmeyen_takvim = False
        gecici_tarih = bas
        while gecici_tarih <= bit:
            tatil_mi = gecici_tarih in RESMI_TATILLER
            if gecici_tarih.weekday() in secilen_indeksler:
                if gecici_tarih.year not in TAKVIM_YILLARI:
                    bilinmeyen_takvim = True
                elif gecici_tarih in YARIM_GUN_TATILLER:
                    yarim_gunler.append(gecici_tarih)
                elif not tatil_mi:
                    sayac += 1
            gecici_tarih += timedelta(days=1)

        self.hesaplanan_gun = sayac
        if bilinmeyen_takvim:
            self.hata_ekle("Bu tarih araliginin tum resmi tatilleri takvimde yok; gun sayisi kesinlestirilemedi.")
        if yarim_gunler:
            self.hata_ekle("Yarim gun resmi tatiller icin staj sayim politikasi netlestirilmeli: " +
                           ", ".join(d.strftime("%d.%m.%Y") for d in yarim_gunler))
        if not bilinmeyen_takvim and not yarim_gunler and sayac != veri["belge_gun"]:
            self.hata_ekle(f"Hesaplanan gun ({sayac}) ile belgedeki gun ({veri['belge_gun']}) tutmuyor.")

        # Imza / onay ve muhendis kurallari
        if veri["ogr_onay"] or veri["danisman_onay"] or not veri["isveren_onay"]:
            self.hata_ekle("Ogrenci ve danisman onayi bos, isveren kismi (kase+imza) dolu olmali.")

        if veri["muhendis"] < 1:
            self.hata_ekle("Isyerinde en az 1 muhendis bulunmali.")
        elif veri["muhendis"] < 5 and veri["muh_bolum"].strip() == "":
            self.hata_ekle("Muhendis sayisi 5'ten azsa mezun oldugu bolum yazilmali.")


def kontrolleri_calistir(veri):
    # Cok bicimlilik: farkli siniflari ayni dongude calistiriyoruz
    tarih_kontrol = TarihVeGunKontrol()
    kontroller = [FormatKontrol(), KimlikKontrol(), tarih_kontrol]

    tum_hatalar = []
    for k in kontroller:
        k.kontrol_et(veri)
        tum_hatalar.extend(k.hatalari_getir())

    return tum_hatalar, tarih_kontrol.hesaplanan_gun
