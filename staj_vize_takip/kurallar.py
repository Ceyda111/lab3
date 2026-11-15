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

        if not re.match(r"^\+90 \d{3} \d{3} \d{2} \d{2}$", veri["telefon"]):
            self.hata_ekle("Telefon +90 xxx xxx xx xx formatinda olmali.")

        if not re.match(r"^[^@]+@[^@]+\.[^@]+$", veri["eposta"]):
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

        bas = datetime.strptime(veri["baslangic"], "%Y-%m-%d").date()
        bit = datetime.strptime(veri["bitis"], "%Y-%m-%d").date()

        if bit < bas:
            self.hata_ekle("Bitis tarihi baslangictan once olamaz.")
            return

        # En az 30 gun once teslim kurali
        if (bas - date.today()).days < 30:
            onerilen = (bas - timedelta(days=30)).strftime("%Y-%m-%d")
            self.hata_ekle(f"Belge baslangictan en az 30 gun once verilmeli (Onerilen: {onerilen}).")

        # Secilen haftalik gunlerden resmi tatilleri duserek gun sayma
        secilen_indeksler = []
        for g in veri["gunler"]:
            if g in self.GUN_SOZLUGU:
                secilen_indeksler.append(self.GUN_SOZLUGU[g])

        sayac = 0
        gecici_tarih = bas
        while gecici_tarih <= bit:
            tatil_mi = (gecici_tarih.month, gecici_tarih.day) in RESMI_TATILLER
            if gecici_tarih.weekday() in secilen_indeksler and not tatil_mi:
                sayac += 1
            gecici_tarih += timedelta(days=1)

        self.hesaplanan_gun = sayac
        if sayac != veri["belge_gun"]:
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
