#!/bin/bash
# ============================================================
# Pardus Smart Board Lock - ELF Binary Derleme
# Debian 12 hedef makinelerle uyumlu binary üretir.
# Docker kullanarak GLIBC uyumunu garanti eder.
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
cd "$SCRIPT_DIR"

# Hedef Debian sürümü (12=bookworm, 11=bullseye, 10=buster)
TARGET_DEBIAN="${1:-12}"

case "$TARGET_DEBIAN" in
    10) DOCKER_IMAGE="python:3.7-buster"   ;;
    11) DOCKER_IMAGE="python:3.9-bullseye" ;;
    12) DOCKER_IMAGE="python:3.11-bookworm";;
    *)  error "Geçersiz hedef: $TARGET_DEBIAN (10, 11 veya 12 olmalı)" ;;
esac

echo ""
echo "============================================"
echo "  Pardus Smart Board Lock - ELF Derleme"
echo "  Hedef: Debian $TARGET_DEBIAN ($DOCKER_IMAGE)"
echo "============================================"
echo ""

# ── 1. Docker kontrolü ───────────────────────────────────────
info "Docker kontrol ediliyor..."
if ! command -v docker &>/dev/null; then
    warn "Docker bulunamadı, kuruluyor..."
    sudo apt-get update -qq
    sudo apt-get install -y ca-certificates curl gnupg
    sudo install -m 0755 -d /etc/apt/keyrings
    curl -fsSL https://download.docker.com/linux/debian/gpg | \
        sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
    sudo chmod a+r /etc/apt/keyrings/docker.gpg
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
https://download.docker.com/linux/debian $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
        sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
    sudo apt-get update -qq
    sudo apt-get install -y docker-ce docker-ce-cli containerd.io
    sudo usermod -aG docker "$USER"
    warn "Docker kuruldu. Bu terminali kapatıp açın, sonra tekrar çalıştırın."
    warn "Veya: sudo bash build_elf.sh $TARGET_DEBIAN"
    exit 1
fi

# Docker çalışıyor mu?
if ! docker info &>/dev/null; then
    warn "Docker servisi başlatılıyor..."
    sudo systemctl start docker || error "Docker başlatılamadı."
fi
log "Docker hazır."

# ── 2. Eski build temizle ─────────────────────────────────────
info "Eski build temizleniyor..."
rm -rf "$SCRIPT_DIR/dist" 2>/dev/null || true

# ── 3. Logo --add-data argümanı ───────────────────────────────
ADD_DATA=""
if [ -f "$SCRIPT_DIR/logo.png" ]; then
    ADD_DATA="--add-data /app/logo.png:."
    log "logo.png binary'e eklenecek."
fi

# ── 4. Docker içinde PyInstaller ile derle ────────────────────
info "Docker imajı indiriliyor: $DOCKER_IMAGE ..."
docker pull "$DOCKER_IMAGE" -q

info "ELF binary derleniyor (birkaç dakika sürebilir)..."

mkdir -p "$SCRIPT_DIR/dist"

docker run --rm \
    -v "$SCRIPT_DIR":/app \
    -v "$SCRIPT_DIR/dist":/dist \
    "$DOCKER_IMAGE" \
    bash -c "
        set -e

        echo '[*] Sistem paketleri kuruluyor...'
        apt-get update -qq
        apt-get install -y -q libxcb-xinerama0 libxcb-icccm4 libxcb-image0 \
            libxcb-keysyms1 libxcb-randr0 libxcb-render-util0 \
            libxkbcommon-x11-0 libglib2.0-0 libdbus-1-3 \
            libxcb-shape0 libxcb-sync1 libxcb-xfixes0 libxcb-glx0 \
            python3-xlib python3-tk tk-dev scrot binutils

        echo '[*] pip güncelleniyor...'
        pip install --upgrade pip -q

        echo '[*] PyInstaller ve bağımlılıklar kuruluyor...'
        pip install pyinstaller -q
        pip install -r /app/requirements.txt -q

        echo '[*] ELF derleniyor...'
        pyinstaller \
            --onefile \
            --noconsole \
            --name pardus-lock \
            --hidden-import PyQt5.sip \
            --hidden-import PyQt5.QtPrintSupport \
            --hidden-import qrcode.image.pil \
            --hidden-import pyautogui \
            --hidden-import Xlib \
            --hidden-import Xlib.display \
            --exclude-module matplotlib \
            --exclude-module numpy \
            --strip \
            --log-level WARN \
            --distpath /dist \
            --workpath /tmp/build \
            --specpath /tmp \
            $ADD_DATA \
            /app/lock_system.py

        echo '[OK] Derleme tamamlandı.'
        chmod 755 /dist/pardus-lock
    "

# ── 5. Sonuç kontrol ──────────────────────────────────────────
BINARY="$SCRIPT_DIR/dist/pardus-lock"
if [ ! -f "$BINARY" ]; then
    error "Derleme başarısız: dist/pardus-lock oluşturulamadı."
fi

# Docker root olarak çalıştığı için dosya sahipliğini düzelt
sudo chown "$USER:$USER" "$BINARY"
chmod +x "$BINARY"
BINARY_SIZE=$(du -sh "$BINARY" | cut -f1)
log "ELF binary oluşturuldu: dist/pardus-lock ($BINARY_SIZE)"

# ── 6. Dağıtım paketi ─────────────────────────────────────────
info "Dağıtım paketi hazırlanıyor..."
PAKET="$SCRIPT_DIR/dist/paket"
mkdir -p "$PAKET"

cp "$BINARY"                "$PAKET/pardus-lock"
cp "$SCRIPT_DIR/install.sh" "$PAKET/install.sh"
chmod +x "$PAKET/pardus-lock"
chmod +x "$PAKET/install.sh"

[ -f "$SCRIPT_DIR/logo.png" ] && cp "$SCRIPT_DIR/logo.png" "$PAKET/"

echo ""
echo "============================================"
echo "  HAZIR!"
echo ""
echo "  Dağıtılacak klasör : dist/paket/"
echo "    - pardus-lock  ($BINARY_SIZE, Debian $TARGET_DEBIAN uyumlu ELF)"
echo "    - install.sh"
echo ""
echo "  Farklı Debian sürümü için:"
echo "    bash build_elf.sh 10   # Debian 10"
echo "    bash build_elf.sh 11   # Debian 11"
echo "    bash build_elf.sh 12   # Debian 12 (varsayılan)"
echo ""
echo "  Hedef makinede tek komut:"
echo "    bash install.sh"
echo "============================================"
echo ""
