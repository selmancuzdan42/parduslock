import sys
import os
import time
import socket
import threading
import secrets
import shutil
import tarfile
import tempfile
import requests
import qrcode
from datetime import datetime
from io import BytesIO
import pyautogui

from PyQt5.QtWidgets import QApplication, QMainWindow, QLabel, QVBoxLayout, QWidget
from PyQt5.QtCore import Qt, pyqtSignal, QObject, QTimer, QTime, QDate, QLocale
from PyQt5.QtGui import QPixmap, QImage, QFont

# --- Sunucu ---
VDS_URL = os.environ.get("VDS_URL", "http://YOUR_SERVER_IP:5000")

# --- Sürüm ---
CLIENT_VERSION = "1.1.0"

# --- Demo ---
# Sunucuya erişilemezse bu tarih yedek olarak kullanılır
DEMO_EXPIRY_FALLBACK = datetime(2026, 4, 20)
DEMO_EXPIRED_MESSAGE = (
    "Demo süresi doldu.\n"
    "Pro versiyonu için iletişime geçin:\n"
    "your-contact@example.com"
)


def _get_base_dir() -> str:
    """PyInstaller onefile binary'de sys.executable dizinini, normal scriptte __file__ dizinini döner."""
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def _detect_debian_slug() -> str:
    """Sistemin Debian taban sürümünü tespit eder."""
    try:
        with open("/etc/debian_version") as f:
            major = f.read().strip().split(".")[0]
        return {"10": "debian10", "11": "debian11", "12": "debian12"}.get(major, "debian12")
    except Exception:
        return "debian12"


def check_and_update():
    """
    Sunucudaki sürümü kontrol eder.
    Yeni sürüm varsa binary'yi indirir, mevcut binary'nin üzerine yazar ve çıkar.
    systemd Restart=always ile yeni binary otomatik başlar.
    """
    try:
        print(f"Güncelleme kontrolü yapılıyor... (Mevcut sürüm: {CLIENT_VERSION})")
        r = requests.get(f"{VDS_URL}/api/version", timeout=10)
        data = r.json()
        server_version = data.get("version", "")

        if not server_version or server_version == CLIENT_VERSION:
            print(f"Güncelleme yok. Sürüm güncel: {CLIENT_VERSION}")
            return

        slug = _detect_debian_slug()
        download_url = data.get("downloads", {}).get(slug)
        if not download_url:
            print(f"İndirme adresi bulunamadı ({slug}).")
            return

        print(f"Yeni sürüm: {server_version}. İndiriliyor ({slug})...")

        with tempfile.TemporaryDirectory() as tmp:
            tar_path = os.path.join(tmp, "update.tar.gz")

            # Yeni binary'yi indir
            r2 = requests.get(download_url, timeout=120, stream=True)
            with open(tar_path, "wb") as f:
                for chunk in r2.iter_content(chunk_size=65536):
                    f.write(chunk)

            # Arşivi aç
            with tarfile.open(tar_path) as tar:
                tar.extractall(tmp)

            new_binary = os.path.join(tmp, "pardus-lock")
            if not os.path.exists(new_binary):
                print("Arşivde binary bulunamadı, güncelleme iptal.")
                return

            os.chmod(new_binary, 0o755)

            # Mevcut binary'nin üzerine atomik olarak yaz
            current_binary = sys.executable
            tmp_new = current_binary + ".new"
            shutil.copy2(new_binary, tmp_new)
            os.replace(tmp_new, current_binary)  # Linux'ta atomik

        print(f"Güncelleme tamamlandı: {CLIENT_VERSION} → {server_version}")
        print("Yeniden başlatılıyor (systemd restart=always)...")
        sys.exit(0)  # systemd otomatik yeniden başlatır

    except Exception as e:
        print(f"Güncelleme kontrolü başarısız: {e}")


# --- Tahta Kimliği ---
# Öncelik: BOARD_ID ortam değişkeni > board_id.txt dosyası > sistem hostname
def _load_board_id() -> str:
    env_id = os.environ.get("BOARD_ID", "").strip()
    if env_id:
        return env_id
    id_file = os.path.join(_get_base_dir(), "board_id.txt")
    if os.path.exists(id_file):
        with open(id_file, "r") as f:
            stored = f.read().strip()
        if stored:
            return stored
    return socket.gethostname()

# --- Ajan Gizli Anahtarı ---
# İlk çalıştırmada üretilir, board_secret.key dosyasına kaydedilir.
def _load_agent_secret() -> str:
    secret_file = os.path.join(_get_base_dir(), "board_secret.key")
    if os.path.exists(secret_file):
        with open(secret_file, "r") as f:
            secret = f.read().strip()
        if secret:
            return secret
    secret = secrets.token_hex(32)
    with open(secret_file, "w") as f:
        f.write(secret)
    return secret


def _load_school_code() -> str:
    env_sc = os.environ.get("SCHOOL_CODE", "").strip()
    if env_sc:
        return env_sc.upper()
    sc_file = os.path.join(_get_base_dir(), "school_code.txt")
    if os.path.exists(sc_file):
        with open(sc_file, "r") as f:
            stored = f.read().strip()
        if stored:
            return stored.upper()
    return ""


BOARD_ID     = _load_board_id()
AGENT_SECRET = _load_agent_secret()
SCHOOL_CODE  = _load_school_code()

POLL_HEADERS = {
    "X-Board-ID":     BOARD_ID,
    "X-Agent-Secret": AGENT_SECRET,
}


def check_demo() -> bool:
    """
    Sunucudan demo config çeker.
    True  → demo süresi dolmuş, uygulama kilitlenmeli
    False → demo geçerli, normal çalış
    """
    try:
        r    = requests.get(f"{VDS_URL}/api/demo-config", timeout=5)
        data = r.json()
        active   = data.get("active", True)
        demo_end = data.get("demo_end", "2099-12-31")
        if not active:
            return True
        end_dt = datetime.strptime(demo_end, "%Y-%m-%d")
        return datetime.now() >= end_dt
    except Exception:
        # Sunucuya erişilemedi → fallback tarihe bak
        return datetime.now() >= DEMO_EXPIRY_FALLBACK


class ServerSignals(QObject):
    unlock_requested = pyqtSignal()
    lock_requested   = pyqtSignal()
    demo_expired     = pyqtSignal()
    license_expired  = pyqtSignal()


# QApplication oluşturulduktan sonra main() içinde atanır
server_signals: "ServerSignals | None" = None


def poll_loop():
    """Sunucuya her 2 saniyede bir komut var mı diye sorar.
    Her 10 dakikada bir demo kontrolü de yapar."""
    demo_check_interval = 600  # saniye
    last_demo_check     = 0

    while True:
        now = time.time()

        # Demo kontrolü (her 10 dakikada bir)
        if now - last_demo_check >= demo_check_interval:
            if check_demo():
                server_signals.demo_expired.emit()
            last_demo_check = now

        if server_signals is None:
            time.sleep(2)
            continue

        try:
            r   = requests.get(f"{VDS_URL}/api/board/poll",
                               headers=POLL_HEADERS, timeout=5)
            data = r.json()
            cmd        = data.get("command")
            command_id = data.get("command_id")

            if cmd == "unlock":
                server_signals.unlock_requested.emit()
                _ack(command_id, "done")
            elif cmd == "lock":
                server_signals.lock_requested.emit()
                if data.get("license_expired"):
                    server_signals.license_expired.emit()
                _ack(command_id, "done")
            elif cmd == "next":
                pyautogui.press("right")
                _ack(command_id, "done")
            elif cmd == "prev":
                pyautogui.press("left")
                _ack(command_id, "done")
        except Exception:
            pass
        time.sleep(2)


def _ack(command_id, result: str):
    """Komut çalıştırıldı bildirimi."""
    if not command_id:
        return
    try:
        requests.post(
            f"{VDS_URL}/api/board/ack",
            json={"command_id": command_id, "result": result},
            headers=POLL_HEADERS,
            timeout=5,
        )
    except Exception:
        pass


# --- PyQt Uygulaması ---
class LockWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Pardus Smart Board Lock")
        self.setWindowFlags(
            Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint
        )
        self.showFullScreen()

        self.setStyleSheet("""
            QMainWindow {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #2C3E50, stop:1 #4CA1AF);
            }
            QLabel { color: white; font-family: 'Segoe UI', sans-serif; }
        """)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(15)
        layout.addStretch(1)

        # Okul adı
        school_label = QLabel("MİLLİ EĞİTİM BAKANLIĞI")
        school_label.setFont(QFont("Arial", 16, QFont.Bold))
        school_label.setStyleSheet("color: rgba(255,255,255,0.7); letter-spacing: 2px;")
        school_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(school_label)

        # Logo
        logo_label = QLabel()
        script_dir = os.path.dirname(os.path.abspath(__file__))
        logo_path  = os.path.join(script_dir, "logo.png")
        logo_pixmap = QPixmap(logo_path)
        if not logo_pixmap.isNull():
            logo_pixmap = logo_pixmap.scaled(
                120, 120,
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation,
            )
            logo_label.setPixmap(logo_pixmap)
        logo_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(logo_label)

        # Saat
        self.clock_label = QLabel()
        self.clock_label.setFont(QFont("Segoe UI", 60, QFont.Bold))
        self.clock_label.setStyleSheet("color: #ecf0f1; margin: 0px;")
        self.clock_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.clock_label)

        # Tarih
        self.date_label = QLabel()
        self.date_label.setFont(QFont("Segoe UI", 20))
        self.date_label.setStyleSheet("color: #bdc3c7; margin-bottom: 20px;")
        self.date_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.date_label)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_clock)
        self.timer.start(1000)
        self.update_clock()

        # Başlık + Tahta ID
        title_label = QLabel("PARDUS AKILLI TAHTA")
        title_label.setFont(QFont("Arial", 42, QFont.Bold))
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("color: white; margin-bottom: 4px;")
        layout.addWidget(title_label)

        board_id_label = QLabel(f"Tahta: {BOARD_ID}")
        board_id_label.setFont(QFont("Consolas", 16))
        board_id_label.setStyleSheet("color: rgba(255,255,200,0.85); margin-bottom: 16px;")
        board_id_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(board_id_label)

        # QR Kod
        qr_container = QWidget()
        qr_layout    = QVBoxLayout(qr_container)

        instr_label = QLabel("Kilidi açmak için QR Kodu okutunuz")
        instr_label.setFont(QFont("Arial", 18))
        instr_label.setStyleSheet("color: rgba(255,255,255,0.9); margin-bottom: 15px;")
        instr_label.setAlignment(Qt.AlignCenter)
        qr_layout.addWidget(instr_label)

        self.qr_label = QLabel()
        self.qr_label.setAlignment(Qt.AlignCenter)
        self.qr_label.setStyleSheet("""
            border: 8px solid rgba(255,255,255,0.2);
            border-radius: 20px;
            background-color: white;
            padding: 20px;
        """)
        qr_layout.addWidget(self.qr_label)
        layout.addWidget(qr_container)

        # Footer
        footer_label = QLabel("Pendik İTO Mesleki Ve Teknik Anadolu Lisesi Tarafından Geliştirilmiştir.")
        footer_label.setFont(QFont("Arial", 11))
        footer_label.setStyleSheet("color: rgba(255,255,255,0.5); margin-top: 20px;")
        footer_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(footer_label)
        layout.addStretch(1)

        # Demo süresi doldu overlay (başlangıçta gizli)
        self.demo_overlay = QLabel(self.centralWidget())
        self.demo_overlay.setText(DEMO_EXPIRED_MESSAGE)
        self.demo_overlay.setFont(QFont("Arial", 22, QFont.Bold))
        self.demo_overlay.setAlignment(Qt.AlignCenter)
        self.demo_overlay.setStyleSheet("""
            QLabel {
                background-color: rgba(0, 0, 0, 0.88);
                color: #F39C12;
                border: 3px solid #F39C12;
                border-radius: 16px;
                padding: 40px 60px;
            }
        """)
        self.demo_overlay.setWordWrap(True)
        self.demo_overlay.hide()

        # Lisans süresi doldu overlay (başlangıçta gizli)
        self.license_overlay = QLabel(self.centralWidget())
        self.license_overlay.setText(
            "Bu cihazın lisans süresi dolmuştur.\n\n"
            "Lisans yenileme için lütfen iletişime geçiniz:\n"
            "your-contact@example.com"
        )
        self.license_overlay.setFont(QFont("Arial", 22, QFont.Bold))
        self.license_overlay.setAlignment(Qt.AlignCenter)
        self.license_overlay.setStyleSheet("""
            QLabel {
                background-color: rgba(0, 0, 0, 0.90);
                color: #E74C3C;
                border: 3px solid #E74C3C;
                border-radius: 16px;
                padding: 40px 60px;
            }
        """)
        self.license_overlay.setWordWrap(True)
        self.license_overlay.hide()

        self.generate_qr()
        server_signals.unlock_requested.connect(self.unlock_screen)
        server_signals.lock_requested.connect(self.lock_screen)
        server_signals.demo_expired.connect(self.show_demo_expired)
        server_signals.license_expired.connect(self.show_license_expired)
        self.grabKeyboard()

    def update_clock(self):
        current_time = QTime.currentTime().toString("HH:mm")
        locale       = QLocale(QLocale.Turkish, QLocale.Turkey)
        current_date = locale.toString(QDate.currentDate(), "d MMMM yyyy, dddd")
        self.clock_label.setText(current_time)
        self.date_label.setText(current_date)

    def generate_qr(self):
        """QR kodu sadece board_id içerir — mobil uygulama bunu okur."""
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_H,
            box_size=20,
            border=4,
        )
        qr.add_data(BOARD_ID)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")

        img_bytes = BytesIO()
        img.save(img_bytes, format="PNG")
        qimg   = QImage.fromData(img_bytes.getvalue())
        pixmap = QPixmap.fromImage(qimg)

        # Ekran yüksekliğinin %30'u kadar ölçekle, keskinliği koru
        screen   = QApplication.primaryScreen().size()
        qr_size  = int(screen.height() * 0.30)
        pixmap   = pixmap.scaled(
            qr_size, qr_size,
            Qt.KeepAspectRatio,
            Qt.FastTransformation,
        )
        self.qr_label.setPixmap(pixmap)
        print(f"BOARD_ID: {BOARD_ID}")
        sys.stdout.flush()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        ow = min(self.width() - 120, 800)
        oh = 260
        x  = (self.width() - ow) // 2
        y  = (self.height() - oh) // 2
        if hasattr(self, "demo_overlay"):
            self.demo_overlay.setGeometry(x, y, ow, oh)
        if hasattr(self, "license_overlay"):
            self.license_overlay.setGeometry(x, y, ow, oh)

    def show_demo_expired(self):
        print("Demo süresi doldu — overlay gösteriliyor.")
        self.demo_overlay.show()
        self.demo_overlay.raise_()

    def show_license_expired(self):
        print("Lisans süresi doldu — overlay gösteriliyor.")
        self.license_overlay.show()
        self.license_overlay.raise_()

    def unlock_screen(self):
        print("Kilit açıldı.")
        self.license_overlay.hide()
        self.demo_overlay.hide()
        self.releaseKeyboard()
        self.hide()

    def lock_screen(self):
        print("Kilitlendi.")
        self.showFullScreen()
        self.grabKeyboard()

    def keyPressEvent(self, event):
        # Tüm tuş kombinasyonlarını engelle (Alt+F4, Ctrl+W, Escape vb.)
        event.accept()

    def mousePressEvent(self, event):
        event.accept()

    def mouseReleaseEvent(self, event):
        event.accept()

    def wheelEvent(self, event):
        event.accept()

    def closeEvent(self, event):
        # Pencere kapatma girişimlerini engelle
        event.ignore()


def register_board():
    """Sunucuya tahta kaydını gönderir."""
    name     = os.environ.get("BOARD_NAME", BOARD_ID)
    location = os.environ.get("BOARD_LOCATION", "")
    try:
        r = requests.post(
            f"{VDS_URL}/api/board/register",
            json={
                "board_id":     BOARD_ID,
                "agent_secret": AGENT_SECRET,
                "name":         name,
                "location":     location,
                "school_code":  SCHOOL_CODE,
            },
            timeout=10,
        )
        data = r.json()
        print(f"Kayıt: {data.get('message', data)}")
    except Exception as e:
        print(f"Kayıt hatası: {e}")


def main():
    global server_signals

    print(f"Tahta ID : {BOARD_ID}")
    print(f"Sunucu   : {VDS_URL}")

    register_board()

    # Her Pazartesi açılışta güncelleme kontrolü
    # weekday() → 0=Pazartesi, ..., 6=Pazar
    if datetime.now().weekday() == 0:
        check_and_update()
        # check_and_update() güncelleme varsa sys.exit(0) çağırır;
        # buraya gelindiyse güncelleme yoktu, normal devam.

    # Başlangıçta demo kontrolü
    demo_expired_at_start = check_demo()

    # QApplication önce oluşturulmalı — QObject (ServerSignals) bundan sonra yaratılır
    app = QApplication(sys.argv)

    # server_signals QApplication'dan sonra oluşturuluyor (PyQt5 gereksinimi)
    server_signals = ServerSignals()

    window = LockWindow()
    window.show()

    # Thread, pencere ve sinyaller hazır olduktan sonra başlatılır
    t = threading.Thread(target=poll_loop, daemon=True)
    t.start()

    if demo_expired_at_start:
        window.show_demo_expired()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
