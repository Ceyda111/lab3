import os
import csv
import io
import sqlite3
import hashlib
import secrets
from datetime import datetime
from functools import wraps
from flask import Flask, request, session, redirect, render_template, flash, abort
from kurallar import kontrolleri_calistir

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024
app.secret_key = os.environ.get("SECRET_KEY", "yalnizca-yerel-demo-gizli-anahtar")

DB_DOSYA = "staj_vize.db"
YUKLEME_YERI = "yuklenen_dosyalar"
IZINLI_TIPLER = [".doc", ".docx", ".pdf", ".jpeg", ".jpg", ".png"]


def baglan():
    conn = sqlite3.connect(DB_DOSYA)
    conn.row_factory = sqlite3.Row
    return conn


def sifre_cevir(sifre):
    # Sifreleri acik tutmamak icin sha256 ile hashliyoruz
    metin = "kou_tuz_" + sifre
    return hashlib.sha256(metin.encode("utf-8")).hexdigest()


def tablolari_kur():
    if not os.path.exists(YUKLEME_YERI):
        os.makedirs(YUKLEME_YERI)

    conn = baglan()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS Kullanicilar (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            eposta TEXT UNIQUE,
            sifre_hash TEXT,
            rol TEXT,
            hatali_deneme INTEGER DEFAULT 0,
            kilitli INTEGER DEFAULT 0
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS GirisLoglari (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            eposta TEXT,
            basarili INTEGER,
            tarih TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS Ogrenciler (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            kullanici_id INTEGER UNIQUE,
            ad_soyad TEXT,
            tc_no TEXT,
            uyruk TEXT,
            ogrenci_no TEXT,
            adres TEXT,
            bolum TEXT,
            teslim_yili TEXT,
            onceki_gun INTEGER,
            eposta TEXT,
            telefon TEXT,
            dogum_tarihi TEXT,
            saglik_yardimi TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS Basvurular (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ogrenci_id INTEGER,
            dosya_yolu TEXT,
            statu TEXT,
            ogretim_yili TEXT,
            gun_sayisi INTEGER,
            muhendis_sayisi INTEGER,
            sonuc_notu TEXT,
            tarih TEXT
        )
    """)

    # Eski staj_vize.db dosyalarini silmeden yeni sutunlari ekle.
    mevcut = {r[1] for r in cur.execute("PRAGMA table_info(Ogrenciler)")}
    for sutun in ("dogum_tarihi", "saglik_yardimi"):
        if sutun not in mevcut:
            cur.execute(f"ALTER TABLE Ogrenciler ADD COLUMN {sutun} TEXT")

    # Test edebilmek icin 1 admin 1 ogrenci ekliyoruz
    admin_var = cur.execute("SELECT id FROM Kullanicilar WHERE eposta = 'admin@kou.edu.tr'").fetchone()
    if not admin_var:
        cur.execute(
            "INSERT INTO Kullanicilar (eposta, sifre_hash, rol) VALUES (?, ?, ?)",
            ("admin@kou.edu.tr", sifre_cevir("admin123"), "ROLE_ADMIN")
        )

    ogr_var = cur.execute("SELECT id FROM Kullanicilar WHERE eposta = 'ogrenci@kou.edu.tr'").fetchone()
    if not ogr_var:
        cur.execute(
            "INSERT INTO Kullanicilar (eposta, sifre_hash, rol) VALUES (?, ?, ?)",
            ("ogrenci@kou.edu.tr", sifre_cevir("123456"), "ROLE_STUDENT")
        )
        kul_id = cur.lastrowid
        cur.execute("""
            INSERT INTO Ogrenciler (kullanici_id, ad_soyad, tc_no, uyruk, ogrenci_no, adres, bolum, teslim_yili, onceki_gun, eposta, telefon)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            kul_id, "Ceyda Yilmaz", "12345678901", "TC", "2602289085",
            "Kabaoglu Mah, Merkez Cad, No:5, D:1, Izmit/Kocaeli",
            "Yazilim Muhendisligi", "2025-2026", 0, "ogrenci@kou.edu.tr", "+90 555 111 22 33"
        ))

    conn.commit()
    conn.close()


# YETKILENDIRME (403 KONTROLU)


def rol_kontrol(gerekli_rol):
    def dis(fonksiyon):
        @wraps(fonksiyon)
        def ic(*args, **kwargs):
            if "kullanici_id" not in session:
                return redirect("/")
            if session.get("rol") != gerekli_rol:
                abort(403)
            return fonksiyon(*args, **kwargs)
        return ic
    return dis


@app.errorhandler(403)
def yetkisiz_sayfa(e):
    return "<h3>403 - Bu sayfaya erisim yetkiniz yok!</h3><a href='/'>Girise Don</a>", 403



# SAYFALAR (GIRIS, OGRENCI, ADMIN)


@app.route("/", methods=["GET", "POST"])
def giris_yap():
    if request.method == "POST":
        eposta = request.form["eposta"].strip()
        sifre = request.form["sifre"]
        simdi = datetime.now().strftime("%Y-%m-%d %H:%M")

        conn = baglan()
        kul = conn.execute("SELECT * FROM Kullanicilar WHERE eposta = ?", (eposta,)).fetchone()

        if kul and kul["kilitli"] == 1:
            conn.close()
            flash("Hesabiniz 5 hatali deneme yuzunden kilitlenmistir!")
            return redirect("/")

        if kul and kul["sifre_hash"] == sifre_cevir(sifre):
            conn.execute("UPDATE Kullanicilar SET hatali_deneme = 0 WHERE id = ?", (kul["id"],))
            conn.execute("INSERT INTO GirisLoglari (eposta, basarili, tarih) VALUES (?, 1, ?)", (eposta, simdi))
            conn.commit()
            conn.close()

            session["kullanici_id"] = kul["id"]
            session["rol"] = kul["rol"]

            if kul["rol"] == "ROLE_ADMIN":
                return redirect("/admin")
            return redirect("/ogrenci")

        # Yanlis giris durumunda sayaci artir ve logla
        if kul:
            yeni_sayac = kul["hatali_deneme"] + 1
            kilit = 1 if yeni_sayac >= 5 else 0
            conn.execute("UPDATE Kullanicilar SET hatali_deneme = ?, kilitli = ? WHERE id = ?", (yeni_sayac, kilit, kul["id"]))
        conn.execute("INSERT INTO GirisLoglari (eposta, basarili, tarih) VALUES (?, 0, ?)", (eposta, simdi))
        conn.commit()
        conn.close()
        flash("E-posta veya sifre hatali!")

    return render_template("giris.html")


@app.route("/cikis")
def cikis_yap():
    session.clear()
    return redirect("/")


@app.route("/ogrenci", methods=["GET", "POST"])
@rol_kontrol("ROLE_STUDENT")
def ogrenci_sayfasi():
    conn = baglan()
    ogr = conn.execute("SELECT * FROM Ogrenciler WHERE kullanici_id = ?", (session["kullanici_id"],)).fetchone()

    if request.method == "POST":
        dosya = request.files.get("evrak")
        uzanti = os.path.splitext(dosya.filename)[1].lower() if dosya else ""
        if uzanti not in IZINLI_TIPLER:
            flash("Sadece .doc, .docx, .pdf, .jpeg, .png yukleyebilirsiniz!")
            conn.close()
            return redirect("/ogrenci")

        try:
            belge_gun = int(request.form.get("belge_gun", ""))
            muhendis = int(request.form.get("muhendis", ""))
            if belge_gun < 0 or muhendis < 0:
                raise ValueError
        except (TypeError, ValueError):
            flash("Belgedeki gun ve muhendis sayisi gecerli bir pozitif sayi olmali.")
            conn.close()
            return redirect("/ogrenci")

        veri = {
            "ad_soyad": request.form["ad_soyad"],
            "uyruk": request.form["uyruk"],
            "kimlik_no": request.form["kimlik_no"],
            "adres": request.form["adres"],
            "telefon": request.form["telefon"],
            "eposta": request.form["eposta"],
            "ogretim_yili": request.form["ogretim_yili"],
            "baslangic": request.form["baslangic"],
            "bitis": request.form["bitis"],
            "gunler": request.form.getlist("gunler"),
            "belge_gun": belge_gun,
            "muhendis": muhendis,
            "teslim_tarihi": request.form.get("teslim_tarihi", ""),
            "muh_bolum": request.form.get("muh_bolum", ""),
            "ogr_onay": "ogr_onay" in request.form,
            "danisman_onay": "danisman_onay" in request.form,
            "isveren_onay": "isveren_onay" in request.form,
            "db_ogrenci": dict(ogr)
        }

        hatalar, gun = kontrolleri_calistir(veri)
        statu = "Inceleniyor" if len(hatalar) == 0 else "Hatali / Eksik"
        sonuc_notu = ("Form on kontrolu basarili; belge icerigi OCR ile dogrulanmadi."
                      if len(hatalar) == 0 else " | ".join(hatalar))

        # Ön doğrulama bittikten sonra dosyayı kaydet.
        dosya_adi = f"{ogr['ogrenci_no']}_{secrets.token_hex(8)}{uzanti}"
        kayit_yolu = os.path.join(YUKLEME_YERI, dosya_adi)
        dosya.save(kayit_yolu)

        conn.execute("""
            INSERT INTO Basvurular (ogrenci_id, dosya_yolu, statu, ogretim_yili, gun_sayisi, muhendis_sayisi, sonuc_notu, tarih)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (ogr["id"], kayit_yolu, statu, veri["ogretim_yili"], gun, veri["muhendis"], sonuc_notu, datetime.now().strftime("%Y-%m-%d %H:%M")))
        conn.commit()
        flash(f"Evrak yuklendi! Durum: {statu}")

    basvurular = conn.execute("SELECT * FROM Basvurular WHERE ogrenci_id = ? ORDER BY id DESC", (ogr["id"],)).fetchall()
    conn.close()

    return render_template("ogrenci.html", ogr=ogr, basvurular=basvurular)


@app.route("/admin", methods=["GET", "POST"])
@rol_kontrol("ROLE_ADMIN")
def admin_sayfasi():
    conn = baglan()

    if request.method == "POST" and "csv_dosya" in request.files:
        try:
            dosya_metni = request.files["csv_dosya"].stream.read().decode("utf-8-sig")
            okuyucu = csv.DictReader(io.StringIO(dosya_metni))
            gerekli = {"eposta", "ad_soyad", "tc_no", "uyruk", "ogrenci_no", "adres",
                       "bolum", "teslim_yili", "onceki_gun", "telefon", "dogum_tarihi", "saglik_yardimi"}
            if not okuyucu.fieldnames or not gerekli.issubset(set(okuyucu.fieldnames)):
                raise ValueError("CSV sutunlari eksik: " + ", ".join(sorted(gerekli - set(okuyucu.fieldnames or []))))
            satirlar = list(okuyucu)
        except (UnicodeError, ValueError) as exc:
            flash(f"CSV okunamadi: {exc}")
            conn.close()
            return redirect("/admin")
        try:
            for satir in satirlar:
                var_mi = conn.execute("SELECT id FROM Kullanicilar WHERE eposta = ?", (satir["eposta"],)).fetchone()
                if not var_mi:
                    cur = conn.execute(
                        "INSERT INTO Kullanicilar (eposta, sifre_hash, rol) VALUES (?, ?, 'ROLE_STUDENT')",
                        (satir["eposta"], sifre_cevir("123456"))
                    )
                    conn.execute("""
                        INSERT INTO Ogrenciler (kullanici_id, ad_soyad, tc_no, uyruk, ogrenci_no, adres, bolum, teslim_yili, onceki_gun, eposta, telefon, dogum_tarihi, saglik_yardimi)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        cur.lastrowid, satir["ad_soyad"], satir["tc_no"], satir["uyruk"], satir["ogrenci_no"],
                        satir["adres"], satir["bolum"], satir["teslim_yili"], int(satir["onceki_gun"] or 0),
                        satir["eposta"], satir["telefon"], satir["dogum_tarihi"], satir["saglik_yardimi"]
                    ))
            conn.commit()
            flash("Test veri seti basariyla yuklendi.")
        except (sqlite3.Error, ValueError, KeyError) as exc:
            conn.rollback()
            flash(f"CSV aktarilamadi: {exc}")

    ogrenciler = conn.execute("SELECT ad_soyad, ogrenci_no, bolum FROM Ogrenciler ORDER BY id DESC").fetchall()
    basvurular = conn.execute("""
        SELECT b.id, o.ad_soyad, b.statu, b.tarih
        FROM Basvurular b
        JOIN Ogrenciler o ON b.ogrenci_id = o.id
        ORDER BY b.id DESC
    """).fetchall()
    conn.close()

    return render_template("admin.html", ogrenciler=ogrenciler, basvurular=basvurular)


if __name__ == "__main__":
    tablolari_kur()
    app.run(debug=True)