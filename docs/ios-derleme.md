# iOS Derleme Rehberi

## Gereksinimler

- Mac bilgisayar (zorunlu)
- Xcode (App Store'dan ücretsiz)
- Apple ID (ücretsiz, test için yeterli)

---

## 1. Projeyi Aç

`ios/PardusLockApp.xcodeproj` dosyasına çift tıkla. Xcode otomatik açılır.

---

## 2. Signing Ayarı

Sol panelden **PardusLockApp** projesine tıkla → **Signing & Capabilities** sekmesi:

- **Team** alanından Apple ID'ni seç
- Hesap yoksa **Add Account** ile ekle
- **Bundle Identifier** benzersiz olmalı, örn: `com.senin-adin.pardus-lock-app`

---

## 3. Derleme

### Simülatörde Test
Üstteki cihaz menüsünden bir iPhone simülatörü seç, ardından:
```
Cmd + R
```

### Gerçek Cihaza Yükleme
1. iPhone'u Mac'e USB ile bağla
2. "Trust This Computer" çıkarsa iPhone'dan **Güven** de
3. Xcode'da cihazını seç
4. `Cmd + R`

---

## 4. Notlar

- `Info.plist` içinde `NSAllowsArbitraryLoads` ve `NSCameraUsageDescription` zaten tanımlı, ek bir şey yapmana gerek yok.
- Uygulama yalnızca **dikey** yönde çalışacak şekilde ayarlı.
- Tema **Dark Mode** olarak sabitlenmiş.

---

## Olası Sorunlar

| Sorun | Çözüm |
|---|---|
| "No signing certificate" | Signing & Capabilities'de Team seç |
| "Trust This Computer" uyarısı | iPhone'dan "Güven" de |
| HTTP bağlantı hatası | `Info.plist`'te `NSAllowsArbitraryLoads: true` olduğunu kontrol et |
| Camera izni hatası | `Info.plist`'te `NSCameraUsageDescription` olduğunu kontrol et |
