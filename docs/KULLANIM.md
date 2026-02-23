# Kullanım Kılavuzu

---

## Genel Akış

```
1. Uygulamaya giriş yap
        ↓
2. Tahtanın QR kodunu oku
        ↓
3. Komut gönder (aç / kapat / slayt)
        ↓
4. (Admin) Kullanıcı ve tahta yönetimi
```

---

## Mobil Uygulama Kullanımı

### Giriş

1. Uygulamayı aç
2. **Kullanıcı adı** ve **şifre** gir
3. **Giriş Yap** butonuna bas

> Sunucu varsayılan olarak `http://YOUR_SERVER_IP:5000` adresine bağlanır.

---

### QR Kod Okuma

Giriş başarılı olunca kamera ekranı açılır.

1. Kamerayı tahtadaki QR koda doğrult
2. QR otomatik okunur — yeşil onay görünür
3. Kontrol ekranına geçilir

> QR kodu sadece o tahtayı hedefler. Başka tahtanın QR'ı okunursa başka tahta kontrol edilir.

---

### Komut Gönderme

Kontrol ekranında 4 buton vardır:

| Buton | Renk | İşlev |
|-------|------|--------|
| **Kilit Aç** | Yeşil | Kilit ekranını kapatır, tahtayı kullanıma açar |
| **Kilitle** | Kırmızı | Tahtayı kilitler, kilit ekranı gösterilir |
| **Önceki** | Mavi | Sol ok tuşuna basar (önceki slayt) |
| **Sonraki** | Turuncu | Sağ ok tuşuna basar (sonraki slayt) |

Komut gönderildikten sonra tahta **en fazla 2-3 saniye içinde** tepki verir.

---

### Çıkış

Sağ üstteki **çıkış ikonuna** bas → onayla → giriş ekranına dön.

---

## Admin Paneli

Sadece `admin` rolündeki kullanıcılar erişebilir.

Kontrol ekranındaki **"Kullanıcı Yönetimi"** butonuna bas.

---

### Kullanıcı Yönetimi

#### Yeni Kullanıcı Ekle

1. **+** butonuna bas (Android: sağ alt FAB, iOS: sağ üst ikon)
2. Formu doldur:
   - **Ad Soyad**
   - **Kullanıcı Adı**
   - **Şifre** (min. 6 karakter)
   - **Rol:** Öğretmen veya Yönetici
3. **Ekle / Kaydet**

#### Şifre Değiştir

- Android: Kullanıcı kartındaki **"Şifre Değiştir"** butonu
- iOS: Kullanıcı satırındaki **"…"** menüsü → Şifre Değiştir

#### Kullanıcı Sil

- Android: Kullanıcı kartındaki **"Sil"** butonu → Onayla
- iOS: **"…"** menüsü → Sil → Onayla

> Kendi hesabını silemezsin.

---

### Tahta Yönetimi

#### Tahta Panelini Aç

- Android: Admin panel sağ üstündeki **"Tahtalar"** butonu
- iOS: Admin panel sağ üstündeki **monitör ikonu**

#### Tahta Listesi

Her satırda:
- **●** → Yeşil: çevrimiçi (son 30sn içinde poll yaptı), Kırmızı: çevrimdışı
- **Tahta ID** ve adı
- **Yetkiler** butonu

> Tahtalar, `lock_system.py` ilk çalıştırıldığında otomatik olarak listeye eklenir. Elle ekleme gerekmez.

#### Öğretmene Tahta Yetkisi Ver

1. İlgili tahtanın **"Yetkiler"** butonuna bas
2. Açılan listede öğretmenleri **işaretle** (erişim olacaklar) / **kaldır** (erişim olmayacaklar)
3. **Kaydet**

> `admin` rolündeki kullanıcılar tüm tahtalara otomatik erişebilir, yetki atamasına gerek yoktur.

---

## Tahta İstemcisi (lock_system.py)

### Ekranda Ne Görünür?

- Kilit ekranı tam ekran açılır
- Saat ve tarih (Türkçe)
- **"Tahta: ETAP1"** — hangi tahta olduğunu gösterir
- **QR kod** — mobil uygulama bu kodu okur
- "Kilidi açmak için QR Kodu okutunuz" talimatı

### Kilit Açıldığında

- Ekran gizlenir
- Klavye kilidi kalkar
- Tahta normal kullanıma geçer

### Kilitlendiğinde

- Tam ekran kilit ekranı tekrar açılır
- Klavye kilitlenir

### Çıkış

Kilit ekranında **ESC** tuşuna bas → uygulama kapanır.

---

## Roller ve Yetkiler

| Özellik | Öğretmen | Yönetici |
|---------|----------|----------|
| Giriş yapma | ✅ | ✅ |
| QR okutma | ✅ | ✅ |
| Komut gönderme (yetkili tahta) | ✅ | ✅ |
| Komut gönderme (tüm tahtalar) | ❌ | ✅ |
| Kullanıcı ekleme / silme | ❌ | ✅ |
| Tahta yetki yönetimi | ❌ | ✅ |
| Broadcast komutu | ❌ | ❌ (varsayılan kapalı) |

---

## Sık Sorulan Sorular

**S: Öğretmen "komut gönderilemedi" hatası alıyor.**
C: Admin panelinden o öğretmene ilgili tahta için yetki verilmemiş. Tahta Yönetimi → Yetkiler.

**S: Tahta listede görünmüyor.**
C: O tahtada `lock_system.py` çalışıyor mu? İlk çalıştırmada otomatik kayıt olur.

**S: Komut gönderildikten sonra tahta tepki vermiyor.**
C: Tahta çevrimiçi mi? (yeşil nokta). `lock_system.py` çalışıyor mu?

**S: QR kodu okunamıyor.**
C: Kamera izni verildi mi? Tahta ekranı parlak mı, QR net görünüyor mu?

**S: Bir öğretmen birden fazla tahtayı kontrol edebilir mi?**
C: Evet. Tahta Yönetimi'nde her tahta için ayrı ayrı yetki verilir.
