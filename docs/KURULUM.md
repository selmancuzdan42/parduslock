# Kurulum Kılavuzu

---

## 1. Sunucu Kurulumu

### Gereksinimler
- Python 3.8+
- Ubuntu / Debian / Pardus

### Adımlar

```bash
# Bağımlılıkları kur
pip3 install flask flask-limiter werkzeug

# Sunucu dosyasını çalıştır
cd server/
python3 app.py
```

Sunucu `http://0.0.0.0:5000` adresinde başlar.

### Systemd Servisi Olarak Kurmak (Önerilen)

```bash
# Servis dosyası oluştur
sudo nano /etc/systemd/system/pardus-lock.service
```

```ini
[Unit]
Description=Pardus Lock System
After=network.target

[Service]
User=root
WorkingDirectory=/root/pardus_lock
ExecStart=/usr/bin/python3 /root/pardus_lock/app.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable pardus-lock
sudo systemctl start pardus-lock

# Durumu kontrol et
sudo systemctl status pardus-lock
```

### Varsayılan Admin Hesabı

| Kullanıcı Adı | Şifre |
|---------------|-------|
| `admin` | `admin123` |

> **Uyarı:** İlk girişten sonra şifreyi değiştirin.

---

## 2. Tahta İstemcisi Kurulumu

Her akıllı tahtada ayrı ayrı kurulur.

### Gereksinimler
- Python 3.8+ (veya PyQt6 destekli sürüm)
- PyQt6, requests, qrcode, pyautogui

```bash
pip3 install PyQt6 requests "qrcode[pil]" pyautogui
```

### Tahta ID Belirleme

**Yöntem 1 — Dosya ile (önerilen):**
```bash
echo "ETAP1" > client/board_id.txt
```

**Yöntem 2 — Ortam değişkeni ile:**
```bash
export BOARD_ID=ETAP1
```

**Yöntem 3 — Otomatik:** Belirtilmezse sistem hostname'i kullanılır.

> Her tahta için benzersiz bir ID seçin. Örnek: `ETAP1`, `A-101`, `B-203`

### Sunucu Adresi Belirleme

Varsayılan adres `http://YOUR_SERVER_IP:5000`'dir.
Değiştirmek için:

```bash
export VDS_URL=http://SUNUCU_IP:5000
```

### Çalıştırma

```bash
cd client/
python3 lock_system.py
```

İlk çalıştırmada:
- `board_secret.key` otomatik oluşturulur (sakla, silme)
- Tahta sunucuya kayıt olur
- Kilit ekranı açılır, QR kod gösterilir

### Otomatik Başlatma (Pardus/Linux)

```bash
# Masaüstü otomatik başlatma
mkdir -p ~/.config/autostart
cat > ~/.config/autostart/pardus-lock.desktop << EOF
[Desktop Entry]
Type=Application
Name=Pardus Lock
Exec=python3 /home/kullanici/pardus_lock_system/client/lock_system.py
Hidden=false
NoDisplay=false
X-GNOME-Autostart-enabled=true
EOF
```

---

## 3. Android Uygulaması Kurulumu

### Hazır APK ile (En Kolay)

1. `PardusLock.apk` dosyasını telefona aktar
2. **Ayarlar → Güvenlik → Bilinmeyen Kaynaklar** → Açık
3. APK'ya dokunarak kur

### Geliştirici Modundan Kurulum

```bash
# USB ile bağlı telefonа kur
adb install PardusLock.apk
```

### Kaynaktan Derleme

```bash
cd android/
./gradlew assembleDebug
# APK: android/app/build/outputs/apk/debug/app-debug.apk
```

> **Not:** `local.properties` dosyasında Android SDK yolu tanımlı olmalı:
> ```
> sdk.dir=/home/kullanici/android-sdk
> ```

---

## 4. iOS Uygulaması Kurulumu

> iOS build için **macOS + Xcode 15+** zorunludur.

```bash
# Mac terminalinde
open ios/PardusLockApp.xcodeproj
```

1. Xcode açılınca **TARGETS → PardusLockApp → Signing & Capabilities**
2. **Team** bölümünden Apple ID'ni seç
3. iPhone'u USB ile bağla
4. **Run** (⌘R)

---

## 5. Ağ Gereksinimleri

- Tahtalar ve mobil cihazlar sunucuya HTTP erişebilmeli
- Sunucu portu: **5000** (güvenlik duvarında açık olmalı)
- HTTP kullanıldığı için (HTTPS değil) aynı ağda çalışması önerilir

```bash
# UFW ile port açmak
sudo ufw allow 5000/tcp
```

---

## Sorun Giderme

| Sorun | Çözüm |
|-------|-------|
| Tahta sunucuya bağlanamıyor | `VDS_URL` doğru mu kontrol et, sunucu çalışıyor mu? |
| `board_secret.key` kayboldu | Tahtayı sunucu DB'den sil, yeniden kayıt olur |
| APK kurulmuyor | Bilinmeyen kaynaklar açık mı? |
| QR okunamıyor | Kamera izni verildi mi? |
| Komut gönderilemiyor | Öğretmene tahta yetkisi verildi mi? |
