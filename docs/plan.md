# VDS Sistemi - Plan

## 1. VDS'e ne ekleniyor? (app.py)
2 yeni endpoint:
- `GET /download/version.json` → `{"version": "1.0.0"}` döner
- `GET /download/pardus-lock-debian12` → binary dosyayı indirir

VDS'te yeni `downloads/` klasörü oluşur:
```
server/
└── downloads/
    ├── version.json
    ├── pardus-lock-debian10
    ├── pardus-lock-debian11
    └── pardus-lock-debian12
```

---

## 2. build_elf.sh ne yapacak?
- Debian 10, 11, 12 için Docker ile ELF derler
- Derleme bitince VDS'e scp ile yükler
- version.json'ı günceller (versiyon numarasını artırır)

---

## 3. Tahtaya atılacak şey ne?
Sadece küçük bir `installer.sh` (~40 satır):
```
1. Debian sürümünü tespit et (debian_version dosyasından)
2. VDS'ten doğru binary'yi indir (curl)
3. Çalıştırılabilir yap
4. Autostart kur (XDG + systemd)
5. Başlat
```

---

## 4. Tahta her açılışta ne yapacak?
`run.sh` şunu yapar:
```
1. VDS'ten version.json çek
2. ~/.local/share/pardus-lock/version ile karşılaştır
3. Yeniyse: yeni binary'yi indir, eski ile değiştir
4. pardus-lock'u çalıştır
```

---

## Sonuç
- Tahtaya sadece 1 dosya atıyorsun (installer.sh)
- Güncelleme için sadece `bash build_elf.sh` çalıştırıyorsun
- Tüm tahtalar bir sonraki açılışta otomatik güncellenir
