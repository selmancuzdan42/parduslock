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

from PyQt5.QtWidgets import QApplication, QMainWindow, QLabel, QVBoxLayout, QHBoxLayout, QWidget
from PyQt5.QtCore import Qt, pyqtSignal, QObject, QTimer, QTime, QDate, QLocale, QThread
from PyQt5.QtGui import QPixmap, QImage, QFont

# --- Sunucu ---
VDS_URL = os.environ.get("VDS_URL", "http://YOUR_SERVER_IP:5000")

# --- Sürüm ---
CLIENT_VERSION = "1.6.0"

# --- Demo ---
# Sunucuya erişilemezse bu tarih yedek olarak kullanılır
DEMO_EXPIRY_FALLBACK = datetime(2026, 4, 20)

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


def check_and_update(status_cb=None):
    """
    Sunucudaki sürümü kontrol eder.
    Yeni sürüm varsa binary'yi indirir, mevcut binary'nin üzerine yazar.
    True döner → güncelleme uygulandı (çağıran çıkmalı).
    False döner → güncelleme yok veya hata.
    """
    def _log(msg):
        print(msg)
        if status_cb:
            status_cb(msg)

    try:
        _log(f"Güncellemeler kontrol ediliyor... (v{CLIENT_VERSION})")
        r = requests.get(f"{VDS_URL}/api/version", timeout=10)
        data = r.json()
        server_version = data.get("version", "")

        if not server_version or server_version == CLIENT_VERSION:
            _log(f"GÜNCEL")
            return False

        slug = _detect_debian_slug()
        download_url = data.get("downloads", {}).get(slug)
        if not download_url:
            _log("GÜNCEL")
            return False

        _log(f"Yeni sürüm bulundu: {server_version}\nİndiriliyor...")

        with tempfile.TemporaryDirectory() as tmp:
            tar_path = os.path.join(tmp, "update.tar.gz")

            r2 = requests.get(download_url, timeout=120, stream=True)
            with open(tar_path, "wb") as f:
                for chunk in r2.iter_content(chunk_size=65536):
                    f.write(chunk)

            with tarfile.open(tar_path) as tar:
                tar.extractall(tmp)

            new_binary = os.path.join(tmp, "pardus-lock")
            if not os.path.exists(new_binary):
                _log("GÜNCEL")
                return False

            os.chmod(new_binary, 0o755)

            current_binary = sys.executable
            tmp_new = current_binary + ".new"
            shutil.copy2(new_binary, tmp_new)
            os.replace(tmp_new, current_binary)

        _log(f"Güncelleme tamamlandı\n{CLIENT_VERSION} → {server_version}")
        return True

    except Exception as e:
        print(f"Güncelleme kontrolü başarısız: {e}")
        return False


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


class StartupCheckThread(QThread):
    step_update    = pyqtSignal(str, str)  # step_id, 'checking'|'ok'|'fail'
    retry_tick     = pyqtSignal(int)       # geri sayım saniyesi
    retry_reset    = pyqtSignal()          # tekrar deneniyor
    update_msg     = pyqtSignal(str)       # güncelleme durum mesajı
    all_done       = pyqtSignal()
    update_applied = pyqtSignal()

    def run(self):
        is_monday = datetime.now().weekday() == 0

        while True:
            # 1. İnternet kontrolü
            self.step_update.emit("internet", "checking")
            if self._check_internet():
                self.step_update.emit("internet", "ok")
            else:
                self.step_update.emit("internet", "fail")
                self._countdown()
                continue

            # 2. Sunucu kontrolü
            self.step_update.emit("server", "checking")
            if self._check_server():
                self.step_update.emit("server", "ok")
            else:
                self.step_update.emit("server", "fail")
                self._countdown()
                continue

            break  # ikisi de başarılı

        # Board'u kaydet
        register_board()

        # 3. Güncelleme kontrolü (sadece Pazartesi)
        if is_monday:
            self.step_update.emit("update", "checking")
            applied = check_and_update(
                status_cb=lambda msg: self.update_msg.emit(msg)
            )
            if applied:
                self.update_applied.emit()
                return
            self.step_update.emit("update", "ok")

        self.all_done.emit()

    def _countdown(self):
        for i in range(10, 0, -1):
            self.retry_tick.emit(i)
            time.sleep(1)
        self.retry_reset.emit()

    def _check_internet(self):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(5)
            s.connect(("8.8.8.8", 53))
            s.close()
            return True
        except Exception:
            return False

    def _check_server(self):
        try:
            r = requests.get(f"{VDS_URL}/api/version", timeout=5)
            return r.status_code == 200
        except Exception:
            return False


class StartupWindow(QMainWindow):
    ready = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Pardus Smart Board Lock")
        self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint)
        self.showFullScreen()
        self.setStyleSheet("""
            QMainWindow { background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                stop:0 #2C3E50, stop:1 #4CA1AF); }
            QLabel { color: white; font-family: 'Segoe UI', sans-serif; }
        """)

        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(8)
        layout.addStretch()

        # Logo
        logo_label = QLabel()
        script_dir = os.path.dirname(os.path.abspath(__file__))
        logo_pixmap = QPixmap(os.path.join(script_dir, "logo.png"))
        if not logo_pixmap.isNull():
            logo_label.setPixmap(logo_pixmap.scaled(
                90, 90, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        logo_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(logo_label)
        layout.addSpacing(24)

        # Adım satırları
        is_monday = datetime.now().weekday() == 0
        steps = [
            ("internet", "İnternet bağlantısı"),
            ("server",   "Sunucuya bağlanıyor"),
        ]
        if is_monday:
            steps.append(("update", "Güncelleme kontrol ediliyor"))

        self._icons  = {}
        self._labels = {}

        for step_id, step_name in steps:
            row_w = QWidget()
            row   = QHBoxLayout(row_w)
            row.setContentsMargins(0, 0, 0, 0)
            row.setSpacing(14)

            icon = QLabel("○")
            icon.setFont(QFont("Segoe UI", 16))
            icon.setStyleSheet("color: rgba(255,255,255,0.35);")
            icon.setFixedWidth(26)
            icon.setAlignment(Qt.AlignCenter)

            lbl = QLabel(step_name)
            lbl.setFont(QFont("Segoe UI", 15))
            lbl.setStyleSheet("color: rgba(255,255,255,0.5);")

            row.addWidget(icon)
            row.addWidget(lbl)

            self._icons[step_id]  = icon
            self._labels[step_id] = lbl

            center = QHBoxLayout()
            center.addStretch()
            center.addWidget(row_w)
            center.addStretch()
            layout.addLayout(center)

        layout.addSpacing(20)

        # Alt mesaj (geri sayım / güncelleme bilgisi)
        self._msg = QLabel("")
        self._msg.setFont(QFont("Segoe UI", 12))
        self._msg.setStyleSheet("color: rgba(255,255,255,0.55);")
        self._msg.setAlignment(Qt.AlignCenter)
        layout.addWidget(self._msg)

        layout.addStretch()

        # Thread
        self._thread = StartupCheckThread()
        self._thread.step_update.connect(self._on_step)
        self._thread.retry_tick.connect(
            lambda s: self._msg.setText(f"Bağlanılamadı. {s} saniye sonra tekrar denenecek..."))
        self._thread.retry_reset.connect(
            lambda: self._msg.setText("Tekrar deneniyor..."))
        self._thread.update_msg.connect(self._msg.setText)
        self._thread.all_done.connect(self._on_done)
        self._thread.update_applied.connect(self._on_update_applied)
        self._thread.start()

    def _on_step(self, step_id, status):
        if step_id not in self._icons:
            return
        icon = self._icons[step_id]
        lbl  = self._labels[step_id]
        if status == "checking":
            icon.setText("◌")
            icon.setStyleSheet("color: rgba(255,255,255,0.8);")
            lbl.setStyleSheet("color: rgba(255,255,255,0.9);")
            self._msg.setText("")
        elif status == "ok":
            icon.setText("✓")
            icon.setStyleSheet("color: #2ecc71;")
            lbl.setStyleSheet("color: rgba(255,255,255,0.9);")
        elif status == "fail":
            icon.setText("✗")
            icon.setStyleSheet("color: #e74c3c;")
            lbl.setStyleSheet("color: #e74c3c;")

    def _on_done(self):
        self._msg.setText("")
        QTimer.singleShot(600, self.ready.emit)

    def _on_update_applied(self):
        self._msg.setStyleSheet("color: #f1c40f;")
        self._msg.setText("Güncelleme tamamlandı. Yeniden başlatılıyor...")
        QTimer.singleShot(2000, lambda: os._exit(0))


class DemoWarningPopup(QMainWindow):
    """Demo süresi dolduğunda gösterilen kapat butonlu uyarı penceresi."""

    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)

        central = QWidget()
        central.setStyleSheet("""
            QWidget {
                background-color: #1a1a2e;
                border: 2px solid #f39c12;
                border-radius: 14px;
            }
        """)
        self.setCentralWidget(central)

        layout = QVBoxLayout(central)
        layout.setContentsMargins(28, 20, 28, 20)
        layout.setSpacing(12)

        # Başlık
        title = QLabel("⚠  Demo Süresi Doldu")
        title.setFont(QFont("Segoe UI", 15, QFont.Bold))
        title.setStyleSheet("color: #f39c12; border: none;")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        # Mesaj
        msg = QLabel(
            "Tahtanız demo süreniz boyunca ücretsiz kullanıma açık kalmıştır.\n"
            "Pro versiyona geçmek için bizimle iletişime geçin:\n"
            "your-contact@example.com"
        )
        msg.setFont(QFont("Segoe UI", 12))
        msg.setStyleSheet("color: #ecf0f1; border: none;")
        msg.setAlignment(Qt.AlignCenter)
        msg.setWordWrap(True)
        layout.addWidget(msg)

        # Kapat butonu
        close_btn = QLabel("Kapat  ✕")
        close_btn.setFont(QFont("Segoe UI", 11, QFont.Bold))
        close_btn.setAlignment(Qt.AlignCenter)
        close_btn.setStyleSheet("""
            QLabel {
                background-color: #f39c12;
                color: #1a1a2e;
                border-radius: 8px;
                padding: 8px 24px;
                border: none;
            }
            QLabel:hover { background-color: #e67e22; }
        """)
        close_btn.setCursor(Qt.PointingHandCursor)
        close_btn.mousePressEvent = lambda _: self.close()
        layout.addWidget(close_btn)

        self.adjustSize()
        self._center()

    def _center(self):
        screen = QApplication.primaryScreen().availableGeometry()
        self.move(
            screen.center().x() - self.width() // 2,
            screen.center().y() - self.height() // 2,
        )


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

            if data.get("demo_expired"):
                server_signals.demo_expired.emit()

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
        self._demo_expired = False   # demo süresi doldu mu?
        self._warning_popup = None   # popup referansı
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
        if hasattr(self, "license_overlay"):
            self.license_overlay.setGeometry(x, y, ow, oh)

    def show_demo_expired(self):
        print("Demo süresi doldu — kilit kaldırılıyor, popup gösteriliyor.")
        self._demo_expired = True
        self.unlock_screen()

    def _show_demo_warning_popup(self):
        if self._warning_popup and self._warning_popup.isVisible():
            return
        self._warning_popup = DemoWarningPopup()
        self._warning_popup.show()

    def show_license_expired(self):
        print("Lisans süresi doldu — overlay gösteriliyor.")
        self.license_overlay.show()
        self.license_overlay.raise_()

    def unlock_screen(self):
        print("Kilit açıldı.")
        self.license_overlay.hide()
        self.releaseKeyboard()
        self.hide()
        if self._demo_expired:
            self._show_demo_warning_popup()

    def lock_screen(self):
        if self._demo_expired:
            print("Demo süresi dolmuş — kilitleme atlandı.")
            return
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


def _fix_service_file():
    """StartLimitBurst/Interval kısıtlamasını kaldırır (varsa)."""
    svc = os.path.expanduser("~/.config/systemd/user/pardus-lock.service")
    if not os.path.exists(svc):
        return
    with open(svc, "r") as f:
        lines = f.readlines()
    new_lines = []
    changed = False
    for line in lines:
        if line.startswith("StartLimitBurst"):
            changed = True
            continue
        if line.startswith("StartLimitIntervalSec") and "=0" not in line:
            line = "StartLimitIntervalSec=0\n"
            changed = True
        new_lines.append(line)
    if changed:
        with open(svc, "w") as f:
            f.writelines(new_lines)
        os.system("systemctl --user daemon-reload 2>/dev/null")
        print("Servis dosyası güncellendi.")


def main():
    global server_signals

    _fix_service_file()

    print(f"Tahta ID : {BOARD_ID}")
    print(f"Sunucu   : {VDS_URL}")

    app = QApplication(sys.argv)
    server_signals = ServerSignals()

    _main_window = None

    def _launch_main():
        nonlocal _main_window
        demo_expired = check_demo()
        _main_window = LockWindow()
        _main_window.show()
        t = threading.Thread(target=poll_loop, daemon=True)
        t.start()
        if demo_expired:
            _main_window.show_demo_expired()

    splash = StartupWindow()
    splash.ready.connect(lambda: (splash.close(), _launch_main()))

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
