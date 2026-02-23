#!/bin/bash
# ============================================================
# Pardus Smart Board Lock - Kurulum Scripti
# Hedef makinede (akıllı tahta) çalıştırın.
# ============================================================

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log()  { echo -e "${GREEN}[OK]${NC} $1"; }
warn() { echo -e "${YELLOW}[!]${NC} $1"; }
error(){ echo -e "${RED}[HATA]${NC} $1"; exit 1; }
info() { echo -e "${BLUE}[*]${NC} $1"; }

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INSTALL_DIR="$HOME/.local/share/pardus-lock"

# Kurum kodu: pakete gömülü değişken (build sırasında set edilir)
SCHOOL_CODE="__SCHOOL_CODE__"

echo ""
echo "============================================"
echo "  Pardus Smart Board Lock - Kurulum"
echo "============================================"
echo ""

# ── 1. Binary var mı? ─────────────────────────────────────────
[ -f "$SCRIPT_DIR/pardus-lock" ] || error "pardus-lock binary bulunamadı: $SCRIPT_DIR"
log "Binary bulundu."

# ── 2. Sistem kütüphaneleri ───────────────────────────────────
info "Sistem kütüphaneleri kontrol ediliyor..."
PKGS=""
for pkg in libxcb-xinerama0 libxcb-icccm4 libxcb-image0 libxcb-keysyms1 \
           libxcb-randr0 libxcb-render-util0 libxkbcommon-x11-0 \
           libxcb-shape0 libxcb-sync1 libxcb-xfixes0 \
           libglib2.0-0 libdbus-1-3 python3-tk; do
    dpkg -s "$pkg" &>/dev/null 2>&1 || PKGS="$PKGS $pkg"
done
if [ -n "$PKGS" ]; then
    warn "Eksik kütüphaneler kuruluyor:$PKGS"
    sudo apt-get update -qq
    sudo apt-get install -y $PKGS || warn "Bazıları kurulamadı, devam ediliyor."
fi
log "Sistem kütüphaneleri hazır."

# ── 3. Binary'i kur ───────────────────────────────────────────
info "Program kuruluyor: $INSTALL_DIR"
mkdir -p "$INSTALL_DIR"

# Çalışıyorsa durdur (Text file busy hatasını önler)
if pkill -f "pardus-lock" 2>/dev/null; then
    sleep 1
fi

cp "$SCRIPT_DIR/pardus-lock" "$INSTALL_DIR/pardus-lock"
chmod +x "$INSTALL_DIR/pardus-lock"
[ -f "$SCRIPT_DIR/logo.png" ] && cp "$SCRIPT_DIR/logo.png" "$INSTALL_DIR/"

# Kurum kodunu kaydet
if [ -n "$SCHOOL_CODE" ] && [ "$SCHOOL_CODE" != "__SCHOOL_CODE__" ]; then
    echo "$SCHOOL_CODE" > "$INSTALL_DIR/school_code.txt"
    log "Kurum kodu kaydedildi: $SCHOOL_CODE"
else
    warn "Kurum kodu tanımlı değil. Tahta 'Atanmamış' olarak görünecek."
fi

log "Program kuruldu."

# ── 4. Çalıştırma scripti ─────────────────────────────────────
cat > "$INSTALL_DIR/run.sh" << 'EOF'
#!/bin/bash
export DISPLAY="${DISPLAY:-:0}"
export XAUTHORITY="${XAUTHORITY:-$HOME/.Xauthority}"
exec "$(dirname "$0")/pardus-lock" "$@"
EOF
chmod +x "$INSTALL_DIR/run.sh"

# ── 5. XDG Autostart ──────────────────────────────────────────
info "XDG autostart kuruluyor..."
mkdir -p "$HOME/.config/autostart"
cat > "$HOME/.config/autostart/pardus-lock.desktop" << EOF
[Desktop Entry]
Type=Application
Name=Pardus Smart Board Lock
Exec=/bin/bash $INSTALL_DIR/run.sh
Hidden=false
NoDisplay=false
X-GNOME-Autostart-enabled=true
X-GNOME-Autostart-Delay=2
EOF
log "XDG autostart kuruldu."

# ── 6. systemd user service ───────────────────────────────────
info "systemd user service kuruluyor..."
mkdir -p "$HOME/.config/systemd/user"
cat > "$HOME/.config/systemd/user/pardus-lock.service" << EOF
[Unit]
Description=Pardus Smart Board Lock
After=graphical-session.target
Wants=graphical-session.target

[Service]
Type=simple
ExecStart=/bin/bash $INSTALL_DIR/run.sh
Restart=always
RestartSec=3
Environment=DISPLAY=:0
Environment=XAUTHORITY=$HOME/.Xauthority
StartLimitIntervalSec=0

[Install]
WantedBy=graphical-session.target
EOF

if command -v systemctl &>/dev/null; then
    systemctl --user daemon-reload 2>/dev/null || true
    systemctl --user enable pardus-lock.service 2>/dev/null && \
        log "systemd service etkinleştirildi." || \
        warn "systemd service etkinleştirilemedi."
    sudo loginctl enable-linger "$USER" 2>/dev/null && \
        log "loginctl linger etkinleştirildi." || true
fi

# ── 7. Şimdi başlat ───────────────────────────────────────────
echo ""
read -t 10 -r -p "Kilit sistemi şimdi başlatılsın mı? [E/h]: " START_NOW || START_NOW="e"
if [[ "$START_NOW" =~ ^[Ee]?$ ]]; then
    nohup bash "$INSTALL_DIR/run.sh" &>/dev/null &
    log "Kilit sistemi başlatıldı."
fi

echo ""
echo "============================================"
echo "  Kurulum Tamamlandi!"
echo "  Kurulum dizini : $INSTALL_DIR"
echo "  Sonraki acilista otomatik baslar."
echo ""
echo "  Komutlar:"
echo "    Durdur    : systemctl --user stop pardus-lock"
echo "    Devre disi: systemctl --user disable pardus-lock"
echo "    Durum     : systemctl --user status pardus-lock"
echo "============================================"
echo ""
