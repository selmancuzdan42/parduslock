# Geliştirme ve İyileştirme Planı

## Kritik Sorunlar (P0 — Hemen Düzeltilmeli)

### 1. HTTP → HTTPS Geçişi
**Etkilenen dosyalar:** `ios/PardusLockApp/Data/Constants.swift`, `android/.../Constants.kt`, `client/lock_system.py`

Tüm uygulamalar `http://YOUR_SERVER_IP:5000` adresine plaintext bağlanıyor.
Araya giren biri ağ trafiğini okuyabilir ve komutları manipüle edebilir (MITM).

- Sunucuya SSL sertifikası ekle (Let's Encrypt ücretsiz)
- URL'leri `https://` olarak güncelle
- iOS ve Android'e certificate pinning ekle

---

### 2. Klavye Bypass Açığı
**Etkilenen dosya:** `client/lock_system.py`

Kilit ekranı aktifken ESC tuşuna basılınca ekran kapanabiliyor.
Ayrıca Alt+Tab ve Alt+F4 engellenmemiş.

- ESC, Alt+F4, Alt+Tab tuşlarını tamamen deaktif et
- Kapatmak yerine bu tuşlara basılınca loglama yap

---

### 3. QR Kodun Tekrar Kullanılabilmesi
**Etkilenen dosyalar:** `client/lock_system.py`, `server/app.py`, tüm mobil uygulamalar

QR kod yalnızca `board_id` içeriyor, her zaman aynı. Birisi QR kodu fotoğraflayıp
daha sonra tekrar kullanabilir.

- Sunucu tarafında TTL'li (örn. 30 saniye) tek kullanımlık token üret
- QR kodu her gösterimde değiştir
- Kullanılan token'ı geçersiz kıl

---

### 4. Varsayılan Admin Şifresi
**Etkilenen dosya:** `server/app.py`

İlk kurulumda admin şifresi `admin123` olarak sabit geliyor.
Değiştirilmezse sistem baştan ele geçirilebilir.

- İlk çalıştırmada şifre belirlenmesini zorunlu kıl
- Ya da `ADMIN_PASSWORD` environment variable'ı zorunlu yap

---

### 5. Board Secret Plaintext Dosyada
**Etkilened dosya:** `client/lock_system.py`

`board_secret.key` dosyası düz metin olarak disk üzerinde duruyor.
Dosyaya erişen biri tahta kimliğini çalabilir.

- Dosya permission'ını `600` yap (sadece root okusun)
- Tercihen sistem keyring'e (keyctl / libsecret) taşı

---

## Önemli İyileştirmeler (P1 — Yakın Vadede)

### 6. Android'de Log Seviyesi
**Etkilened dosya:** `android/app/src/main/java/.../data/api/ApiClient.kt`

`HttpLoggingInterceptor.Level.BODY` production'da açık bırakılmış.
Şifreler ve session token'lar loglanıyor.

```kotlin
// Şu an
.setLevel(HttpLoggingInterceptor.Level.BODY)

// Olması gereken
.setLevel(if (BuildConfig.DEBUG) Level.BODY else Level.NONE)
```

---

### 7. CSRF Koruması
**Etkilened dosya:** `server/app.py`

POST istekler CSRF token doğrulaması olmadan işleniyor.
Flask-WTF ile kolayca eklenebilir.

```python
from flask_wtf.csrf import CSRFProtect
csrf = CSRFProtect(app)
```

---

### 8. Session Süresi
**Etkilened dosya:** `server/app.py`

Session 8 saat açık kalıyor. Okul ortamında masa başı oturumu
düşünüldüğünde bu çok uzun.

- Session süresini 30-60 dakikaya indir
- Hareketsizlik sonrası otomatik oturum kapatma ekle

---

### 9. SessionManager Kullanılmıyor (Android)
**Etkilened dosya:** `android/app/src/main/java/.../data/SessionManager.kt`

Dosya yazılmış ama hiçbir yerde kullanılmıyor. Ölü kod.

- Ya kullan ya sil

---

### 10. Biyometrik Doğrulama
**Etkilened dosyalar:** iOS ve Android uygulamaları

Şu an sadece kullanıcı adı + şifre var.

- iOS: Face ID / Touch ID (LocalAuthentication framework)
- Android: BiometricPrompt API

---

## Genel Kalite İyileştirmeleri (P2 — Uzun Vadede)

### 11. Test Eksikliği
Projede hiç test yok.

| Platform | Önerilen Framework |
|---|---|
| Python server | pytest |
| Android | JUnit + Espresso |
| iOS | XCTest |

---

### 12. SQLite → PostgreSQL
**Etkilened dosya:** `server/app.py`

SQLite birden fazla eş zamanlı yazma işleminde kilitlenebilir.
Okul ortamında çok kullanıcı olduğunda sorun çıkarabilir.

---

### 13. API Versioning
**Etkilened dosya:** `server/app.py`

Endpoint'lerde `/api/v1/` prefix yok. İleride breaking change yapıldığında
eski istemciler çalışmayı durdurur.

---

### 14. Rate Limiting Güçlendirme
**Etkilened dosya:** `server/app.py`

Board endpoint'leri `@limiter.exempt` ile tamamen muaf tutulmuş.
Login için "5 per minute" brute force için yeterince kısıtlayıcı değil.

---

## Özet Tablo

| # | Sorun | Şiddet | Dosya |
|---|---|---|---|
| 1 | HTTP trafiği (MITM riski) | Kritik | Tüm istemciler |
| 2 | Klavye bypass (ESC) | Kritik | `client/lock_system.py` |
| 3 | QR kodun tekrar kullanılabilmesi | Kritik | Server + istemciler |
| 4 | Varsayılan admin şifresi `admin123` | Kritik | `server/app.py` |
| 5 | Board secret plaintext dosyada | Yüksek | `client/lock_system.py` |
| 6 | Production'da BODY level log | Yüksek | `android/ApiClient.kt` |
| 7 | CSRF koruması yok | Yüksek | `server/app.py` |
| 8 | Session süresi 8 saat | Orta | `server/app.py` |
| 9 | SessionManager kullanılmıyor | Düşük | `android/SessionManager.kt` |
| 10 | Biyometrik doğrulama yok | Düşük | iOS + Android |
| 11 | Test yok | Orta | Tüm proje |
| 12 | SQLite production'da | Orta | `server/app.py` |
| 13 | API versioning yok | Düşük | `server/app.py` |
| 14 | Rate limiting zayıf | Orta | `server/app.py` |
