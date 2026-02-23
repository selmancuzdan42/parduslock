import os
import sqlite3
import secrets
import threading
import calendar
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta, timezone

CONTACT_EMAIL    = os.environ.get("CONTACT_EMAIL", "")
CONTACT_PASSWORD = os.environ.get("CONTACT_PASSWORD", "")

# Türkiye saati (UTC+3, DST yok)
_TZ_TR = timezone(timedelta(hours=3))

def now_tr() -> datetime:
    """Türkiye saatinde naive datetime döner (veritabanı için)."""
    return datetime.now(_TZ_TR).replace(tzinfo=None)
from functools import wraps

from flask import (Flask, jsonify, redirect, render_template,
                   request, session, url_for)
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from werkzeug.security import check_password_hash, generate_password_hash

app = Flask(__name__)
app.permanent_session_lifetime = timedelta(hours=8)

# --- Secret Key ---
SECRET_KEY_FILE = "secret.key"
if os.path.exists(SECRET_KEY_FILE):
    with open(SECRET_KEY_FILE, "r") as f:
        app.secret_key = f.read().strip()
else:
    app.secret_key = secrets.token_hex(32)
    with open(SECRET_KEY_FILE, "w") as f:
        f.write(app.secret_key)

app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Strict"

# --- Rate Limiting ---
limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["200 per day", "50 per hour"]
)

# --- Hesap Kilitleme ---
_login_attempts = {}   # username -> {"count": int, "locked_until": datetime|None}
_login_lock     = threading.Lock()
MAX_LOGIN_ATTEMPTS = 5
LOCKOUT_MINUTES    = 10


def _login_allowed(username):
    """(izin_var, kalan_saniye) döner."""
    with _login_lock:
        entry = _login_attempts.get(username)
        if not entry:
            return True, 0
        lu = entry.get("locked_until")
        if lu and now_tr() < lu:
            return False, int((lu - now_tr()).total_seconds())
        return True, 0


def _record_failed(username):
    with _login_lock:
        entry = _login_attempts.setdefault(username, {"count": 0, "locked_until": None})
        entry["count"] += 1
        if entry["count"] >= MAX_LOGIN_ATTEMPTS:
            entry["locked_until"] = now_tr() + timedelta(minutes=LOCKOUT_MINUTES)


def _record_success(username):
    with _login_lock:
        _login_attempts.pop(username, None)

DB_PATH = "users.db"

def add_months(dt, months):
    """Bir tarihe ay ekler (ay sonu taşmalarını düzeltir)."""
    month = dt.month - 1 + months
    year  = dt.year + month // 12
    month = month % 12 + 1
    day   = min(dt.day, calendar.monthrange(year, month)[1])
    return dt.replace(year=year, month=month, day=day)


# Yayın (broadcast) komutu engellenecek board_id değerleri
BROADCAST_BLOCKLIST = {"*", "all", "tüm", "hepsi", "broadcast"}

# Komut TTL (saniye) — tahta bu sürede almazsa komut süresi dolar
COMMAND_TTL_SECONDS = 30


# ============================================================
# Veritabanı
# ============================================================

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    conn = get_db()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            username      TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            full_name     TEXT NOT NULL,
            role          TEXT NOT NULL CHECK(role IN ('admin', 'teacher'))
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS boards (
            board_id    TEXT PRIMARY KEY,
            name        TEXT NOT NULL,
            location    TEXT,
            agent_secret TEXT NOT NULL,
            last_seen   TEXT,
            is_active   INTEGER DEFAULT 1
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS commands (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            board_id    TEXT NOT NULL REFERENCES boards(board_id),
            command     TEXT NOT NULL CHECK(command IN ('unlock', 'lock', 'next', 'prev')),
            status      TEXT NOT NULL DEFAULT 'pending'
                            CHECK(status IN ('pending', 'processing', 'done', 'failed', 'expired')),
            issued_by   INTEGER REFERENCES users(id),
            issued_at   TEXT DEFAULT (datetime('now', '+3 hours')),
            executed_at TEXT,
            expires_at  TEXT NOT NULL
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS board_permissions (
            id       INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id  INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            board_id TEXT NOT NULL REFERENCES boards(board_id) ON DELETE CASCADE,
            UNIQUE(user_id, board_id)
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS audit_logs (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id    INTEGER REFERENCES users(id),
            board_id   TEXT,
            action     TEXT NOT NULL,
            ip_address TEXT,
            timestamp  TEXT DEFAULT (datetime('now', '+3 hours')),
            result     TEXT NOT NULL
        )
    """)

    # Demo lisans tablosu
    conn.execute("""
        CREATE TABLE IF NOT EXISTS demo_licenses (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            school_code     TEXT NOT NULL,
            school_name     TEXT NOT NULL,
            start_date      TEXT NOT NULL,
            duration_months INTEGER NOT NULL DEFAULT 2,
            end_date        TEXT NOT NULL,
            active          INTEGER DEFAULT 1,
            notes           TEXT,
            created_at      TEXT DEFAULT (datetime('now', '+3 hours'))
        )
    """)

    # Lisans yöneticileri (süper admin — normal adminlerden ayrı)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS license_managers (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            username      TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at    TEXT DEFAULT (datetime('now', '+3 hours'))
        )
    """)

    # Migration: school_code kolonları
    for migration in [
        "ALTER TABLE users  ADD COLUMN school_code TEXT NOT NULL DEFAULT ''",
        "ALTER TABLE boards ADD COLUMN school_code TEXT NOT NULL DEFAULT ''",
    ]:
        try:
            conn.execute(migration)
        except Exception:
            pass  # Kolon zaten varsa atla

    # Varsayılan admin hesabı
    exists = conn.execute(
        "SELECT id FROM users WHERE username = 'admin'"
    ).fetchone()
    if not exists:
        default_admin_pass = os.environ.get("DEFAULT_ADMIN_PASSWORD", "")
        if default_admin_pass:
            conn.execute(
                "INSERT INTO users (username, password_hash, full_name, role, school_code) VALUES (?, ?, ?, ?, ?)",
                ("admin", generate_password_hash(default_admin_pass), "Sistem Yöneticisi", "admin", ""),
            )

    # Varsayılan lisans yöneticisi
    sa_exists = conn.execute(
        "SELECT id FROM license_managers WHERE username = 'sadmin'"
    ).fetchone()
    if not sa_exists:
        default_sa_pass = os.environ.get("DEFAULT_SA_PASSWORD", "")
        if default_sa_pass:
            conn.execute(
                "INSERT INTO license_managers (username, password_hash) VALUES (?, ?)",
                ("sadmin", generate_password_hash(default_sa_pass)),
            )

    conn.commit()
    conn.close()


# ============================================================
# Yardımcı Fonksiyonlar
# ============================================================

def write_log(conn, user_id, board_id, action, result):
    ip = request.remote_addr
    conn.execute(
        "INSERT INTO audit_logs (user_id, board_id, action, ip_address, result) "
        "VALUES (?, ?, ?, ?, ?)",
        (user_id, board_id, action, ip, result)
    )


def expire_old_commands(conn):
    """Süresi dolmuş pending komutları expired olarak işaretle."""
    conn.execute(
        "UPDATE commands SET status = 'expired' "
        "WHERE status = 'pending' AND expires_at < datetime('now', '+3 hours')"
    )


def board_owned_by_school(conn, board_id, school_code):
    """Tahtanın verilen okula ait olup olmadığını kontrol eder."""
    row = conn.execute(
        "SELECT 1 FROM boards WHERE board_id = ? AND school_code = ?",
        (board_id, school_code)
    ).fetchone()
    return row is not None


def has_board_permission(conn, user_id, user_role, board_id, school_code=""):
    """Kullanıcının belirtilen tahtaya erişim yetkisi var mı?"""
    if user_role == "superadmin":
        # Süperadmin tüm tahtalara erişebilir
        return True
    if user_role == "admin":
        # Admin sadece kendi okulunun tahtalarına erişebilir
        board = conn.execute(
            "SELECT board_id FROM boards WHERE board_id = ? AND school_code = ?",
            (board_id, school_code)
        ).fetchone()
        return board is not None
    # Öğretmen: kendi okulunun tahtasıysa direkt erişebilir
    if school_code:
        board = conn.execute(
            "SELECT board_id FROM boards WHERE board_id = ? AND school_code = ?",
            (board_id, school_code)
        ).fetchone()
        if board is not None:
            return True
    # Yoksa explicit board_permissions kaydına bak
    row = conn.execute(
        "SELECT id FROM board_permissions WHERE user_id = ? AND board_id = ?",
        (user_id, board_id)
    ).fetchone()
    return row is not None


# ============================================================
# Dekoratörler
# ============================================================


def api_login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" not in session:
            return jsonify({"status": "error", "message": "Oturum açılmamış"}), 401
        return f(*args, **kwargs)
    return decorated


def sa_login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "sa_user_id" not in session:
            return redirect(url_for("sa_login_page"))
        return f(*args, **kwargs)
    return decorated


def api_admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" not in session:
            return jsonify({"status": "error", "message": "Oturum açılmamış"}), 401
        if session.get("role") != "admin":
            return jsonify({"status": "error", "message": "Yetkisiz erişim"}), 403
        return f(*args, **kwargs)
    return decorated


# ============================================================
# Tahta Ajanı Endpoint'leri  /api/board/…
# ============================================================

@app.route("/api/board/register", methods=["POST"])
@limiter.limit("30 per hour")
def board_register():
    """
    Tahta kendini sunucuya kaydeder.
    Body: { board_id, agent_secret, name, location }
    - İlk kayıt: board_id + secret ile yeni kayıt oluşturulur.
    - Sonraki kayıtlar: secret eşleşmeli, last_seen güncellenir.
    """
    data         = request.get_json(silent=True) or {}
    board_id     = (data.get("board_id") or "").strip()
    agent_secret = (data.get("agent_secret") or "").strip()
    name         = (data.get("name") or board_id).strip()
    location     = (data.get("location") or "").strip()
    school_code  = (data.get("school_code") or "").strip().upper()

    if not board_id or not agent_secret:
        return jsonify({"status": "error", "message": "board_id ve agent_secret zorunlu"}), 400

    if board_id.lower() in BROADCAST_BLOCKLIST:
        return jsonify({"status": "error", "message": "Geçersiz board_id"}), 400

    conn = get_db()
    existing = conn.execute(
        "SELECT board_id, agent_secret FROM boards WHERE board_id = ?", (board_id,)
    ).fetchone()

    if existing is None:
        conn.execute(
            "INSERT INTO boards (board_id, name, location, agent_secret, last_seen, school_code) "
            "VALUES (?, ?, ?, ?, datetime('now', '+3 hours'), ?)",
            (board_id, name, location, agent_secret, school_code)
        )
        conn.commit()
        conn.close()
        return jsonify({"status": "ok", "message": "Tahta kaydedildi"})

    if existing["agent_secret"] != agent_secret:
        conn.close()
        return jsonify({"status": "error", "message": "Geçersiz agent_secret"}), 403

    conn.execute(
        "UPDATE boards SET last_seen = datetime('now', '+3 hours'), is_active = 1, "
        "name = COALESCE(NULLIF(?, ''), name), "
        "location = COALESCE(NULLIF(?, ''), location), "
        "school_code = COALESCE(NULLIF(?, ''), school_code) "
        "WHERE board_id = ?",
        (name, location, school_code, board_id)
    )
    conn.commit()
    conn.close()
    return jsonify({"status": "ok", "message": "Tahta güncellendi"})


@app.route("/api/board/poll")
@limiter.limit("120 per minute")
def board_poll():
    """
    Tahta bekleyen komutunu sorgular.
    Headers: X-Board-ID, X-Agent-Secret
    Response: { command: "unlock"|"lock"|"next"|"prev"|null, command_id: int|null }
    """
    board_id     = request.headers.get("X-Board-ID", "").strip()
    agent_secret = request.headers.get("X-Agent-Secret", "").strip()

    if not board_id or not agent_secret:
        return jsonify({"status": "error", "message": "Başlıklar eksik"}), 400

    conn = get_db()
    board = conn.execute(
        "SELECT board_id, agent_secret, school_code FROM boards WHERE board_id = ? AND is_active = 1",
        (board_id,)
    ).fetchone()

    if not board or board["agent_secret"] != agent_secret:
        conn.close()
        return jsonify({"status": "error", "message": "Kimlik doğrulama başarısız"}), 403

    # Okulun lisansı kontrolü
    board_school = board["school_code"] or ""
    demo_expired_flag = False
    if board_school:
        today = now_tr().strftime("%Y-%m-%d")
        lic = conn.execute(
            "SELECT active, end_date FROM demo_licenses WHERE school_code = ? "
            "ORDER BY created_at DESC LIMIT 1",
            (board_school,)
        ).fetchone()
        if lic:
            if not lic["active"]:
                # Lisans askıya alındı — tamamen engelle
                conn.execute(
                    "UPDATE boards SET last_seen = datetime('now', '+3 hours') WHERE board_id = ?", (board_id,)
                )
                conn.commit()
                conn.close()
                return jsonify({
                    "command":        "lock",
                    "command_id":     None,
                    "license_expired": True,
                })
            elif lic["end_date"] < today:
                # Demo süresi doldu — kullanmaya devam edebilir, sadece uyarı
                demo_expired_flag = True

    # last_seen güncelle
    conn.execute(
        "UPDATE boards SET last_seen = datetime('now', '+3 hours') WHERE board_id = ?", (board_id,)
    )

    # Süresi dolmuş komutları temizle
    expire_old_commands(conn)

    # Bekleyen komutu al (en eski önce)
    cmd_row = conn.execute(
        "SELECT id, command FROM commands "
        "WHERE board_id = ? AND status = 'pending' AND expires_at > datetime('now', '+3 hours') "
        "ORDER BY issued_at ASC LIMIT 1",
        (board_id,)
    ).fetchone()

    if cmd_row:
        conn.execute(
            "UPDATE commands SET status = 'processing' WHERE id = ?", (cmd_row["id"],)
        )
        conn.commit()
        conn.close()
        return jsonify({"command": cmd_row["command"], "command_id": cmd_row["id"], "demo_expired": demo_expired_flag})

    conn.commit()
    conn.close()
    return jsonify({"command": None, "command_id": None, "demo_expired": demo_expired_flag})


@app.route("/api/board/ack", methods=["POST"])
@limiter.exempt
def board_ack():
    """
    Tahta komutu çalıştırdıktan sonra sonucu bildirir.
    Body: { command_id, result: "done"|"failed" }
    Headers: X-Board-ID, X-Agent-Secret
    """
    board_id     = request.headers.get("X-Board-ID", "").strip()
    agent_secret = request.headers.get("X-Agent-Secret", "").strip()
    data         = request.get_json(silent=True) or {}
    command_id   = data.get("command_id")
    result       = data.get("result", "done")

    if not board_id or not agent_secret or not command_id:
        return jsonify({"status": "error", "message": "Eksik parametre"}), 400

    conn = get_db()
    board = conn.execute(
        "SELECT board_id FROM boards WHERE board_id = ? AND agent_secret = ?",
        (board_id, agent_secret)
    ).fetchone()

    if not board:
        conn.close()
        return jsonify({"status": "error", "message": "Kimlik doğrulama başarısız"}), 403

    new_status = "done" if result == "done" else "failed"
    conn.execute(
        "UPDATE commands SET status = ?, executed_at = datetime('now', '+3 hours') "
        "WHERE id = ? AND board_id = ? AND status = 'processing'",
        (new_status, command_id, board_id)
    )
    conn.commit()
    conn.close()
    return jsonify({"status": "ok"})


# ============================================================
# Kimlik Doğrulama (Web)
# ============================================================


# ============================================================
# JSON API — Kimlik Doğrulama
# ============================================================

@app.route("/api/login", methods=["POST"])
@limiter.limit("5 per minute")
def api_login():
    data     = request.get_json(silent=True) or {}
    username = data.get("username", "").strip()
    password = data.get("password", "")
    if not username or not password:
        return jsonify({"status": "error", "message": "Kullanıcı adı ve şifre gerekli"}), 400

    allowed, remaining = _login_allowed(username)
    if not allowed:
        mins = remaining // 60
        secs = remaining % 60
        return jsonify({
            "status": "error",
            "message": f"Hesap kilitli. {mins} dakika {secs} saniye sonra tekrar deneyin."
        }), 429

    conn = get_db()

    # Önce süperadmin tablosunu kontrol et
    sa = conn.execute(
        "SELECT * FROM license_managers WHERE username = ?", (username,)
    ).fetchone()
    if sa and check_password_hash(sa["password_hash"], password):
        conn.close()
        _record_success(username)
        session.permanent    = True
        session["user_id"]   = None   # users tablosunda kaydı yok, NULL olarak sakla
        session["username"]  = sa["username"]
        session["full_name"] = "Süper Admin"
        session["role"]      = "superadmin"
        session["school_code"] = ""
        return jsonify({
            "status": "ok",
            "user": {
                "id":          sa["id"],
                "username":    sa["username"],
                "full_name":   "Süper Admin",
                "role":        "superadmin",
                "school_code": "",
            }
        })

    user = conn.execute(
        "SELECT * FROM users WHERE username = ?", (username,)
    ).fetchone()
    conn.close()
    if user and check_password_hash(user["password_hash"], password):
        # Okulun lisansı askıya alınmış mı?
        school_code = user["school_code"]
        if school_code:
            lic_conn = get_db()
            lic = lic_conn.execute(
                "SELECT active, end_date FROM demo_licenses WHERE school_code = ? "
                "ORDER BY created_at DESC LIMIT 1",
                (school_code,)
            ).fetchone()
            lic_conn.close()
            if lic:
                today = datetime.now().strftime("%Y-%m-%d")
                if not lic["active"]:
                    return jsonify({
                        "status": "error",
                        "message": "Kurumunuzun lisansı askıya alınmıştır. Lütfen yöneticinizle iletişime geçin."
                    }), 403
                if lic["end_date"] and lic["end_date"] < today:
                    return jsonify({
                        "status": "error",
                        "message": "Kurumunuzun demo lisansı sona ermiştir. Lütfen yöneticinizle iletişime geçin."
                    }), 403
        _record_success(username)
        session.clear()  # Session fixation koruması
        session.permanent = True
        session["user_id"]     = user["id"]
        session["username"]    = user["username"]
        session["full_name"]   = user["full_name"]
        session["role"]        = user["role"]
        session["school_code"] = user["school_code"]
        return jsonify({
            "status": "ok",
            "user": {
                "id":          user["id"],
                "username":    user["username"],
                "full_name":   user["full_name"],
                "role":        user["role"],
                "school_code": user["school_code"],
            }
        })
    _record_failed(username)
    allowed2, _ = _login_allowed(username)
    if not allowed2:
        return jsonify({
            "status": "error",
            "message": "Çok fazla hatalı giriş. Hesap 10 dakika kilitlendi."
        }), 429
    left = MAX_LOGIN_ATTEMPTS - _login_attempts.get(username, {}).get("count", 0)
    return jsonify({
        "status": "error",
        "message": f"Kullanıcı adı veya şifre hatalı. ({left} deneme hakkınız kaldı)"
    }), 401


@app.route("/api/logout", methods=["POST"])
def api_logout():
    session.clear()
    return jsonify({"status": "ok"})


@app.route("/api/me")
@api_login_required
def api_me():
    return jsonify({
        "status": "ok",
        "user": {
            "id":          session.get("user_id"),
            "username":    session.get("username"),
            "full_name":   session.get("full_name"),
            "role":        session.get("role"),
            "school_code": session.get("school_code", ""),
        }
    })


# ============================================================
# JSON API — Komut Gönderme
# ============================================================

@app.route("/api/send_command", methods=["POST"])
@api_login_required
def api_send_command():
    data     = request.get_json(silent=True) or {}
    board_id = (data.get("board_id") or "").strip()
    command  = (data.get("command") or "").strip()

    user_id   = session.get("user_id")
    user_role = session.get("role")

    # --- Broadcast koruması ---
    if not board_id or board_id.lower() in BROADCAST_BLOCKLIST:
        conn = get_db()
        write_log(conn, user_id, board_id or "BROADCAST",
                  f"send_command:{command}", "blocked_broadcast")
        conn.commit()
        conn.close()
        return jsonify({
            "status": "error",
            "message": "Yayın (broadcast) komutları engellenmiştir. Belirli bir tahta seçin."
        }), 403

    allowed = {"unlock", "lock", "next", "prev"}
    if command not in allowed:
        return jsonify({"status": "error", "message": "Geçersiz komut"}), 400

    conn = get_db()

    # Tahta kayıtlı mı?
    board = conn.execute(
        "SELECT board_id FROM boards WHERE board_id = ? AND is_active = 1", (board_id,)
    ).fetchone()
    if not board:
        conn.close()
        return jsonify({"status": "error", "message": "Tahta bulunamadı veya aktif değil"}), 404

    # Yetki kontrolü
    school_code = session.get("school_code", "")
    if not has_board_permission(conn, user_id, user_role, board_id, school_code):
        write_log(conn, user_id, board_id, f"send_command:{command}", "forbidden")
        conn.commit()
        conn.close()
        return jsonify({
            "status": "error",
            "message": "Bu tahtaya komut gönderme yetkiniz yok."
        }), 403

    # Komutu kuyruğa ekle
    expires_at = (now_tr() + timedelta(seconds=COMMAND_TTL_SECONDS)).strftime(
        "%Y-%m-%d %H:%M:%S"
    )
    cursor = conn.execute(
        "INSERT INTO commands (board_id, command, issued_by, expires_at) VALUES (?, ?, ?, ?)",
        (board_id, command, user_id, expires_at)
    )
    command_id = cursor.lastrowid
    write_log(conn, user_id, board_id, f"send_command:{command}", "queued")
    conn.commit()
    conn.close()

    return jsonify({"status": "ok", "command_id": command_id,
                    "message": f"Komut kuyruğa eklendi (ID: {command_id})"})


# ============================================================
# JSON API — Kullanıcı Yönetimi (Admin)
# ============================================================

@app.route("/api/admin/users", methods=["GET"])
@api_admin_required
def api_admin_users():
    conn  = get_db()
    school_code = session.get("school_code", "")
    users = conn.execute(
        "SELECT id, username, full_name, role FROM users "
        "WHERE school_code = ? ORDER BY role, full_name",
        (school_code,)
    ).fetchall()
    conn.close()
    return jsonify({
        "status": "ok",
        "users": [
            {"id": u["id"], "username": u["username"],
             "full_name": u["full_name"], "role": u["role"]}
            for u in users
        ]
    })


def _do_add_user(data):
    """Kullanıcı ekleme ortak mantığı."""
    username    = (data.get("username") or "").strip()
    password    = data.get("password") or ""
    full_name   = (data.get("full_name") or "").strip()
    role        = data.get("role", "teacher")
    school_code = session.get("school_code", "")
    if not username or not password or not full_name:
        return jsonify({"status": "error", "message": "Tüm alanlar zorunlu"}), 400
    if role not in ("admin", "teacher"):
        role = "teacher"
    conn = get_db()
    try:
        conn.execute(
            "INSERT INTO users (username, password_hash, full_name, role, school_code) VALUES (?, ?, ?, ?, ?)",
            (username, generate_password_hash(password), full_name, role, school_code),
        )
        conn.commit()
    except sqlite3.IntegrityError:
        conn.close()
        return jsonify({"status": "error", "message": "Kullanıcı adı zaten kullanımda"}), 409
    finally:
        conn.close()
    return jsonify({"status": "ok"})


@app.route("/api/admin/users", methods=["POST"])
@api_admin_required
def api_admin_users_post():
    return _do_add_user(request.get_json(silent=True) or {})


@app.route("/api/admin/add_user", methods=["POST"])
@api_admin_required
def api_add_user():
    return _do_add_user(request.get_json(silent=True) or {})


@app.route("/api/admin/users/<int:user_id>", methods=["DELETE"])
@api_admin_required
def api_delete_user(user_id):
    if user_id == session.get("user_id"):
        return jsonify({"status": "error", "message": "Kendinizi silemezsiniz"}), 400
    conn = get_db()
    # Sadece aynı okuldaki kullanıcıyı silebilir
    target = conn.execute(
        "SELECT school_code FROM users WHERE id = ?", (user_id,)
    ).fetchone()
    if not target or target["school_code"] != session.get("school_code", ""):
        conn.close()
        return jsonify({"status": "error", "message": "Yetkisiz işlem"}), 403
    try:
        # commands ve audit_logs'daki FK referanslarını temizle
        conn.execute("UPDATE commands SET issued_by = NULL WHERE issued_by = ?", (user_id,))
        conn.execute("UPDATE audit_logs SET user_id = NULL WHERE user_id = ?", (user_id,))
        # board_permissions ON DELETE CASCADE ile otomatik silinir
        conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
        conn.commit()
    except Exception as e:
        conn.rollback()
        conn.close()
        return jsonify({"status": "error", "message": "Kullanıcı silinemedi"}), 500
    conn.close()
    return jsonify({"status": "ok"})


@app.route("/api/admin/change_password", methods=["POST"])
@api_admin_required
def api_change_password():
    data         = request.get_json(silent=True) or {}
    user_id      = data.get("user_id")
    new_password = data.get("new_password", "")
    if not user_id or not new_password or len(new_password) < 6:
        return jsonify({"status": "error", "message": "Geçersiz istek"}), 400
    school_code = session.get("school_code", "")
    conn = get_db()
    cur = conn.execute(
        "UPDATE users SET password_hash = ? WHERE id = ? AND school_code = ?",
        (generate_password_hash(new_password), user_id, school_code),
    )
    conn.commit()
    conn.close()
    if cur.rowcount == 0:
        return jsonify({"status": "error", "message": "Kullanıcı bulunamadı"}), 403
    return jsonify({"status": "ok"})


# ============================================================
# JSON API — Tahta Yönetimi (Admin)
# ============================================================

@app.route("/api/admin/boards", methods=["GET"])
@api_admin_required
def api_admin_boards():
    conn   = get_db()
    school_code = session.get("school_code", "")
    if not school_code:
        conn.close()
        return jsonify({"status": "ok", "boards": []})
    boards = conn.execute(
        "SELECT board_id, name, location, last_seen, is_active FROM boards "
        "WHERE school_code = ? ORDER BY board_id",
        (school_code,)
    ).fetchall()
    conn.close()
    now = now_tr()
    result = []
    for b in boards:
        online = False
        if b["last_seen"]:
            try:
                ls = datetime.strptime(b["last_seen"], "%Y-%m-%d %H:%M:%S")
                online = (now - ls).total_seconds() < 30
            except ValueError:
                pass
        result.append({
            "board_id":  b["board_id"],
            "name":      b["name"],
            "location":  b["location"],
            "last_seen": b["last_seen"],
            "is_online": online,
            "is_active": bool(b["is_active"]),
        })
    return jsonify({"status": "ok", "boards": result})


@app.route("/api/admin/boards/<board_id>", methods=["DELETE"])
@api_admin_required
def api_admin_delete_board(board_id):
    conn = get_db()
    board = conn.execute(
        "SELECT school_code FROM boards WHERE board_id = ?", (board_id,)
    ).fetchone()
    if not board or board["school_code"] != session.get("school_code", ""):
        conn.close()
        return jsonify({"status": "error", "message": "Yetkisiz işlem"}), 403
    try:
        # commands.board_id NOT NULL — önce bu tahtanın komutlarını sil
        conn.execute("DELETE FROM commands WHERE board_id = ?", (board_id,))
        # audit_logs.board_id sadece metin, FK yok — NULL'a çek
        conn.execute("UPDATE audit_logs SET board_id = NULL WHERE board_id = ?", (board_id,))
        # board_permissions ON DELETE CASCADE ile otomatik silinir
        conn.execute("DELETE FROM boards WHERE board_id = ?", (board_id,))
        conn.commit()
        write_log(conn, session.get("user_id"), board_id, "delete_board", "ok")
        conn.commit()
    except Exception as e:
        conn.rollback()
        conn.close()
        return jsonify({"status": "error", "message": "Tahta silinemedi"}), 500
    conn.close()
    return jsonify({"status": "ok"})


@app.route("/api/admin/boards/<board_id>/deactivate", methods=["POST"])
@api_admin_required
def api_admin_deactivate_board(board_id):
    conn = get_db()
    board = conn.execute(
        "SELECT school_code FROM boards WHERE board_id = ?", (board_id,)
    ).fetchone()
    if not board or board["school_code"] != session.get("school_code", ""):
        conn.close()
        return jsonify({"status": "error", "message": "Yetkisiz işlem"}), 403
    conn.execute("UPDATE boards SET is_active = 0 WHERE board_id = ?", (board_id,))
    conn.commit()
    conn.close()
    return jsonify({"status": "ok"})


# --- Tahta İzinleri ---

@app.route("/api/admin/boards/<board_id>/permissions", methods=["GET"])
@api_admin_required
def api_board_permissions_get(board_id):
    conn = get_db()
    if not board_owned_by_school(conn, board_id, session.get("school_code", "")):
        conn.close()
        return jsonify({"status": "error", "message": "Yetkisiz işlem"}), 403
    rows = conn.execute(
        "SELECT u.id, u.username, u.full_name, u.role "
        "FROM board_permissions bp JOIN users u ON bp.user_id = u.id "
        "WHERE bp.board_id = ? ORDER BY u.full_name",
        (board_id,)
    ).fetchall()
    conn.close()
    return jsonify({
        "status": "ok",
        "board_id": board_id,
        "users": [{"id": r["id"], "username": r["username"],
                   "full_name": r["full_name"], "role": r["role"]} for r in rows]
    })


@app.route("/api/admin/boards/<board_id>/permissions", methods=["POST"])
@api_admin_required
def api_board_permissions_add(board_id):
    data    = request.get_json(silent=True) or {}
    user_id = data.get("user_id")
    if not user_id:
        return jsonify({"status": "error", "message": "user_id gerekli"}), 400
    conn = get_db()
    if not board_owned_by_school(conn, board_id, session.get("school_code", "")):
        conn.close()
        return jsonify({"status": "error", "message": "Yetkisiz işlem"}), 403
    try:
        conn.execute(
            "INSERT INTO board_permissions (user_id, board_id) VALUES (?, ?)",
            (user_id, board_id)
        )
        conn.commit()
    except sqlite3.IntegrityError:
        pass  # Zaten var
    finally:
        conn.close()
    return jsonify({"status": "ok"})


@app.route("/api/admin/boards/<board_id>/permissions/<int:user_id>", methods=["DELETE"])
@api_admin_required
def api_board_permissions_remove(board_id, user_id):
    conn = get_db()
    if not board_owned_by_school(conn, board_id, session.get("school_code", "")):
        conn.close()
        return jsonify({"status": "error", "message": "Yetkisiz işlem"}), 403
    conn.execute(
        "DELETE FROM board_permissions WHERE board_id = ? AND user_id = ?",
        (board_id, user_id)
    )
    conn.commit()
    conn.close()
    return jsonify({"status": "ok"})


# ============================================================
# JSON API — Dashboard (Canlı Tahta Durumu & İstatistikler)
# ============================================================

@app.route("/api/admin/dashboard")
@api_admin_required
def api_admin_dashboard():
    """
    Admin için özet istatistikler ve canlı tahta durumları.
    Yanıt:
      boards        : { total, online, offline }
      users         : { total, admins, teachers }
      commands      : { last_24h, done_24h, failed_24h, expired_24h }
      board_list    : tüm tahtalar + anlık online durumu
      recent_commands: son 10 komut
    """
    conn = get_db()
    now  = now_tr()

    school_code = session.get("school_code", "")
    if not school_code:
        conn.close()
        return jsonify({
            "status": "ok",
            "boards":   {"total": 0, "online": 0, "offline": 0},
            "users":    {"total": 0, "admins": 0, "teachers": 0},
            "commands": {"last_24h": 0, "done_24h": 0, "failed_24h": 0, "expired_24h": 0},
            "board_list": [],
            "recent_commands": [],
        })

    # ─ Tahtalar ─
    boards = conn.execute(
        "SELECT board_id, name, location, last_seen, is_active FROM boards "
        "WHERE school_code = ? ORDER BY name",
        (school_code,)
    ).fetchall()
    board_list   = []
    online_count = 0
    for b in boards:
        is_online = False
        if b["last_seen"] and b["is_active"]:
            try:
                ls = datetime.strptime(b["last_seen"], "%Y-%m-%d %H:%M:%S")
                is_online = (now - ls).total_seconds() < 30
            except ValueError:
                pass
        if is_online:
            online_count += 1
        board_list.append({
            "board_id":  b["board_id"],
            "name":      b["name"],
            "location":  b["location"],
            "is_online": is_online,
            "last_seen": b["last_seen"],
            "is_active": bool(b["is_active"]),
        })

    # ─ Kullanıcı sayıları ─
    user_counts = conn.execute(
        "SELECT role, COUNT(*) as cnt FROM users WHERE school_code = ? GROUP BY role",
        (school_code,)
    ).fetchall()
    admins = teachers = 0
    for r in user_counts:
        if r["role"] == "admin":
            admins = r["cnt"]
        elif r["role"] == "teacher":
            teachers = r["cnt"]

    # ─ Komut istatistikleri (son 24 saat) ─
    cmd_stats = conn.execute(
        "SELECT status, COUNT(*) as cnt FROM commands "
        "WHERE issued_at > datetime('now', '-24 hours') GROUP BY status"
    ).fetchall()
    cmd_map = {r["status"]: r["cnt"] for r in cmd_stats}

    # ─ Son 10 komut ─
    recent_cmds = conn.execute(
        "SELECT c.id, c.board_id, c.command, c.status, c.issued_at, u.full_name "
        "FROM commands c LEFT JOIN users u ON c.issued_by = u.id "
        "ORDER BY c.issued_at DESC LIMIT 10"
    ).fetchall()

    conn.close()
    return jsonify({
        "status": "ok",
        "boards": {
            "total":   len(boards),
            "online":  online_count,
            "offline": len(boards) - online_count,
        },
        "users": {
            "total":    admins + teachers,
            "admins":   admins,
            "teachers": teachers,
        },
        "commands": {
            "last_24h":    sum(cmd_map.values()),
            "done_24h":    cmd_map.get("done", 0),
            "failed_24h":  cmd_map.get("failed", 0),
            "expired_24h": cmd_map.get("expired", 0),
        },
        "board_list": board_list,
        "recent_commands": [
            {
                "id":        c["id"],
                "board_id":  c["board_id"],
                "command":   c["command"],
                "status":    c["status"],
                "issued_at": c["issued_at"],
                "issued_by": c["full_name"],
            } for c in recent_cmds
        ],
    })


# ============================================================
# JSON API — Toplu İzin Yönetimi
# ============================================================

@app.route("/api/admin/users/<int:user_id>/permissions", methods=["GET"])
@api_admin_required
def api_user_permissions_get(user_id):
    """Bir kullanıcının yetkili olduğu tüm tahtaları döner."""
    conn = get_db()
    rows = conn.execute(
        "SELECT b.board_id, b.name, b.location, b.is_active "
        "FROM board_permissions bp JOIN boards b ON bp.board_id = b.board_id "
        "WHERE bp.user_id = ? ORDER BY b.name",
        (user_id,)
    ).fetchall()
    conn.close()
    return jsonify({
        "status":  "ok",
        "user_id": user_id,
        "boards": [
            {
                "board_id":  r["board_id"],
                "name":      r["name"],
                "location":  r["location"],
                "is_active": bool(r["is_active"]),
            } for r in rows
        ],
    })


@app.route("/api/admin/users/<int:user_id>/permissions/bulk", methods=["POST"])
@api_admin_required
def api_user_permissions_bulk_add(user_id):
    """
    Kullanıcıya birden fazla tahtayı aynı anda atar.
    Body: { board_ids: ["b1", "b2", ...], replace: false }
    replace=true → önce mevcut tüm izinleri sil, sonra yenilerini ekle.
    replace=false (varsayılan) → mevcut izinlere ekle, çakışmaları atla.
    """
    data      = request.get_json(silent=True) or {}
    board_ids = data.get("board_ids", [])
    replace   = bool(data.get("replace", False))

    if not isinstance(board_ids, list):
        return jsonify({"status": "error", "message": "board_ids liste olmalı"}), 400

    conn = get_db()
    user = conn.execute("SELECT id FROM users WHERE id = ?", (user_id,)).fetchone()
    if not user:
        conn.close()
        return jsonify({"status": "error", "message": "Kullanıcı bulunamadı"}), 404

    if replace:
        conn.execute("DELETE FROM board_permissions WHERE user_id = ?", (user_id,))

    added = 0
    for bid in board_ids:
        bid = str(bid).strip()
        if not bid:
            continue
        try:
            conn.execute(
                "INSERT INTO board_permissions (user_id, board_id) VALUES (?, ?)",
                (user_id, bid)
            )
            added += 1
        except sqlite3.IntegrityError:
            pass  # Zaten var, atla

    conn.commit()
    conn.close()
    return jsonify({"status": "ok", "added": added})


@app.route("/api/admin/users/<int:user_id>/permissions/bulk", methods=["DELETE"])
@api_admin_required
def api_user_permissions_bulk_delete(user_id):
    """
    Kullanıcının belirtilen tahta izinlerini kaldırır.
    Body: { board_ids: ["b1", "b2"] }  → sadece bunları sil
    Body: {} (board_ids yok)            → kullanıcının tüm izinlerini sil
    """
    data      = request.get_json(silent=True) or {}
    board_ids = data.get("board_ids")

    conn = get_db()
    if board_ids is None:
        conn.execute("DELETE FROM board_permissions WHERE user_id = ?", (user_id,))
    else:
        for bid in board_ids:
            conn.execute(
                "DELETE FROM board_permissions WHERE user_id = ? AND board_id = ?",
                (user_id, str(bid).strip())
            )
    conn.commit()
    conn.close()
    return jsonify({"status": "ok"})


@app.route("/api/admin/boards/<board_id>/permissions/bulk", methods=["POST"])
@api_admin_required
def api_board_permissions_bulk(board_id):
    """
    Bir tahtaya birden fazla öğretmeni aynı anda atar.
    Body: { user_ids: [1, 2, 3], replace: false }
    replace=true → önce mevcut tüm izinleri sil, sonra yenilerini ekle.
    replace=false (varsayılan) → mevcut izinlere ekle, çakışmaları atla.
    """
    data     = request.get_json(silent=True) or {}
    user_ids = data.get("user_ids", [])
    replace  = bool(data.get("replace", False))

    if not isinstance(user_ids, list):
        return jsonify({"status": "error", "message": "user_ids liste olmalı"}), 400

    conn = get_db()
    if not board_owned_by_school(conn, board_id, session.get("school_code", "")):
        conn.close()
        return jsonify({"status": "error", "message": "Yetkisiz işlem"}), 403
    if replace:
        conn.execute("DELETE FROM board_permissions WHERE board_id = ?", (board_id,))

    added = 0
    for uid in user_ids:
        try:
            conn.execute(
                "INSERT INTO board_permissions (user_id, board_id) VALUES (?, ?)",
                (int(uid), board_id)
            )
            added += 1
        except (sqlite3.IntegrityError, ValueError):
            pass

    conn.commit()
    conn.close()
    return jsonify({"status": "ok", "added": added})


# --- Kullanıcının yetkili olduğu tahtaları getir ---

@app.route("/api/my_boards")
@api_login_required
def api_my_boards():
    """
    Giriş yapmış kullanıcının yetkilendirildiği tahtaları döner.
    Admin: tüm aktif tahtalar.
    Teacher: sadece board_permissions tablosundaki tahtalar.
    """
    user_id   = session.get("user_id")
    user_role = session.get("role")
    conn      = get_db()
    now       = now_tr()

    school_code = session.get("school_code", "")

    if user_role == "superadmin":
        # Süperadmin tüm tahtaları görür
        rows = conn.execute(
            "SELECT board_id, name, location, last_seen FROM boards "
            "WHERE is_active = 1 ORDER BY school_code, board_id"
        ).fetchall()
    elif not school_code:
        # Okul kodu atanmamış hesaplar hiç tahta göremez
        conn.close()
        return jsonify({"status": "ok", "boards": []})
    elif user_role == "admin":
        rows = conn.execute(
            "SELECT board_id, name, location, last_seen FROM boards "
            "WHERE is_active = 1 AND school_code = ? ORDER BY board_id",
            (school_code,)
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT b.board_id, b.name, b.location, b.last_seen "
            "FROM board_permissions bp JOIN boards b ON bp.board_id = b.board_id "
            "WHERE bp.user_id = ? AND b.is_active = 1 AND b.school_code = ? ORDER BY b.board_id",
            (user_id, school_code)
        ).fetchall()

    conn.close()
    result = []
    for b in rows:
        online = False
        if b["last_seen"]:
            try:
                ls = datetime.strptime(b["last_seen"], "%Y-%m-%d %H:%M:%S")
                online = (now - ls).total_seconds() < 30
            except ValueError:
                pass
        result.append({
            "board_id":  b["board_id"],
            "name":      b["name"],
            "location":  b["location"],
            "is_online": online,
        })
    return jsonify({"status": "ok", "boards": result})


# ============================================================
# Demo Config Endpoint (auth gerektirmez)
# ============================================================

@app.route("/api/demo-config")
@limiter.exempt
def api_demo_config():
    school = request.args.get("school", "").strip().upper()
    conn   = get_db()

    if not school:
        # Kurum kodu belirtilmemişse kısıtlama yok
        conn.close()
        return jsonify({"active": True, "demo_start": "", "demo_end": "2099-12-31"})

    # En son lisansı al (aktif ya da pasif)
    lic = conn.execute(
        "SELECT * FROM demo_licenses WHERE school_code = ? "
        "ORDER BY created_at DESC LIMIT 1",
        (school,)
    ).fetchone()
    conn.close()

    if not lic:
        # Bu okula ait lisans yoksa kısıtlama yok
        return jsonify({"active": True, "demo_start": "", "demo_end": "2099-12-31"})

    # Lisans pasife alınmışsa sistemi kilitli/süresi dolmuş göster
    if not lic["active"]:
        return jsonify({
            "active":      False,
            "demo_start":  lic["start_date"],
            "demo_end":    "2000-01-01",   # Geçmiş tarih → demo süresi dolmuş
            "school_code": lic["school_code"],
            "school_name": lic["school_name"],
            "suspended":   True,
        })

    return jsonify({
        "active":       True,
        "demo_start":   lic["start_date"],
        "demo_end":     lic["end_date"],
        "school_code":  lic["school_code"],
        "school_name":  lic["school_name"],
    })


# ============================================================
# Süper Admin Paneli  /sa/*
# ============================================================

@app.route("/sa")
def sa_index():
    if "sa_user_id" in session:
        return redirect(url_for("sa_dashboard"))
    return redirect(url_for("sa_login_page"))


@app.route("/sa/login", methods=["GET", "POST"])
@limiter.limit("10 per minute")
def sa_login_page():
    error = None
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        conn     = get_db()
        manager  = conn.execute(
            "SELECT * FROM license_managers WHERE username = ?", (username,)
        ).fetchone()
        conn.close()
        if manager and check_password_hash(manager["password_hash"], password):
            session["sa_user_id"]   = manager["id"]
            session["sa_username"]  = manager["username"]
            return redirect(url_for("sa_dashboard"))
        error = "Kullanıcı adı veya şifre hatalı."
    return render_template("sa_login.html", error=error)


@app.route("/sa/logout")
def sa_logout():
    session.pop("sa_user_id",  None)
    session.pop("sa_username", None)
    return redirect(url_for("sa_login_page"))


@app.route("/sa/dashboard")
@sa_login_required
def sa_dashboard():
    conn     = get_db()
    licenses = conn.execute(
        "SELECT * FROM demo_licenses ORDER BY created_at DESC"
    ).fetchall()
    managers = conn.execute(
        "SELECT id, username, created_at FROM license_managers ORDER BY created_at ASC"
    ).fetchall()
    school_admins = conn.execute(
        "SELECT id, username, full_name, school_code FROM users "
        "WHERE role = 'admin' ORDER BY school_code, full_name"
    ).fetchall()
    all_boards = conn.execute(
        "SELECT board_id, name, location, school_code FROM boards ORDER BY school_code, board_id"
    ).fetchall()
    conn.close()
    today = now_tr().strftime("%Y-%m-%d")
    return render_template(
        "sa_dashboard.html",
        licenses=licenses,
        managers=managers,
        school_admins=school_admins,
        all_boards=all_boards,
        today=today,
        current_user=session.get("sa_username"),
        current_sa_id=session.get("sa_user_id"),
    )


@app.route("/sa/board/delete", methods=["POST"])
@sa_login_required
def sa_board_delete():
    """Süper admin bir tahtayı siler."""
    board_id = request.form.get("board_id", "").strip()
    if not board_id:
        return redirect(url_for("sa_dashboard"))
    conn = get_db()
    conn.execute("DELETE FROM board_permissions WHERE board_id = ?", (board_id,))
    conn.execute("DELETE FROM commands WHERE board_id = ?", (board_id,))
    conn.execute("DELETE FROM audit_logs WHERE board_id = ?", (board_id,))
    conn.execute("DELETE FROM boards WHERE board_id = ?", (board_id,))
    conn.commit()
    conn.close()
    return redirect(url_for("sa_dashboard"))


@app.route("/sa/board/assign", methods=["POST"])
@sa_login_required
def sa_board_assign():
    """Bir tahtayı belirli bir okula atar."""
    board_id    = request.form.get("board_id", "").strip()
    school_code = request.form.get("school_code", "").strip().upper()
    if not board_id or not school_code:
        return redirect(url_for("sa_dashboard"))
    conn = get_db()
    conn.execute(
        "UPDATE boards SET school_code = ? WHERE board_id = ?",
        (school_code, board_id)
    )
    conn.commit()
    conn.close()
    return redirect(url_for("sa_dashboard"))


@app.route("/sa/school_admin/add", methods=["POST"])
@sa_login_required
def sa_school_admin_add():
    """Süperadmin belirli bir okula admin hesabı oluşturur."""
    username    = request.form.get("username", "").strip()
    password    = request.form.get("password", "")
    full_name   = request.form.get("full_name", "").strip()
    school_code = request.form.get("school_code", "").strip().upper()
    if not username or not password or not full_name or not school_code:
        return redirect(url_for("sa_dashboard"))
    if len(password) < 6:
        return redirect(url_for("sa_dashboard"))
    conn = get_db()
    try:
        conn.execute(
            "INSERT INTO users (username, password_hash, full_name, role, school_code) "
            "VALUES (?, ?, ?, 'admin', ?)",
            (username, generate_password_hash(password), full_name, school_code),
        )
        conn.commit()
    except sqlite3.IntegrityError:
        pass  # Kullanıcı adı zaten var
    finally:
        conn.close()
    return redirect(url_for("sa_dashboard"))


@app.route("/sa/school_admin/<int:user_id>/delete", methods=["POST"])
@sa_login_required
def sa_school_admin_delete(user_id):
    """Süperadmin bir okul admin hesabını siler."""
    conn = get_db()
    conn.execute("UPDATE commands    SET issued_by = NULL WHERE issued_by = ?", (user_id,))
    conn.execute("UPDATE audit_logs  SET user_id   = NULL WHERE user_id   = ?", (user_id,))
    conn.execute("DELETE FROM board_permissions WHERE user_id = ?", (user_id,))
    conn.execute("DELETE FROM users WHERE id = ? AND role = 'admin'", (user_id,))
    conn.commit()
    conn.close()
    return redirect(url_for("sa_dashboard"))


@app.route("/sa/license/add", methods=["POST"])
@sa_login_required
def sa_license_add():
    school_code     = request.form.get("school_code", "").strip().upper()
    school_name     = request.form.get("school_name", "").strip()
    start_date_str  = request.form.get("start_date", "").strip()
    duration_months = request.form.get("duration_months", "2")
    notes           = request.form.get("notes", "").strip()

    if not school_code or not school_name or not start_date_str:
        return redirect(url_for("sa_dashboard"))

    try:
        duration_months = int(duration_months)
        start_dt        = datetime.strptime(start_date_str, "%Y-%m-%d")
        end_dt          = add_months(start_dt, duration_months)
        end_date_str    = end_dt.strftime("%Y-%m-%d")
    except (ValueError, TypeError):
        return redirect(url_for("sa_dashboard"))

    conn = get_db()
    conn.execute(
        "INSERT INTO demo_licenses "
        "(school_code, school_name, start_date, duration_months, end_date, notes) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (school_code, school_name, start_date_str, duration_months, end_date_str, notes),
    )
    conn.commit()
    conn.close()
    return redirect(url_for("sa_dashboard"))


@app.route("/sa/license/<int:license_id>/toggle", methods=["POST"])
@sa_login_required
def sa_license_toggle(license_id):
    conn = get_db()
    lic  = conn.execute(
        "SELECT active FROM demo_licenses WHERE id = ?", (license_id,)
    ).fetchone()
    if lic:
        conn.execute(
            "UPDATE demo_licenses SET active = ? WHERE id = ?",
            (0 if lic["active"] else 1, license_id),
        )
        conn.commit()
    conn.close()
    return redirect(url_for("sa_dashboard"))


@app.route("/sa/license/<int:license_id>/delete", methods=["POST"])
@sa_login_required
def sa_license_delete(license_id):
    conn = get_db()
    conn.execute("DELETE FROM demo_licenses WHERE id = ?", (license_id,))
    conn.commit()
    conn.close()
    return redirect(url_for("sa_dashboard"))


# --- Lisans Yöneticisi Kullanıcı Yönetimi ---

@app.route("/sa/managers/add", methods=["POST"])
@sa_login_required
def sa_manager_add():
    username = request.form.get("username", "").strip()
    password = request.form.get("password", "")
    if not username or not password or len(password) < 6:
        return redirect(url_for("sa_dashboard"))
    conn = get_db()
    try:
        conn.execute(
            "INSERT INTO license_managers (username, password_hash) VALUES (?, ?)",
            (username, generate_password_hash(password)),
        )
        conn.commit()
    except sqlite3.IntegrityError:
        pass  # Kullanıcı adı zaten var
    finally:
        conn.close()
    return redirect(url_for("sa_dashboard"))


@app.route("/sa/managers/<int:manager_id>/delete", methods=["POST"])
@sa_login_required
def sa_manager_delete(manager_id):
    # Kendi hesabını silemesin
    if manager_id == session.get("sa_user_id"):
        return redirect(url_for("sa_dashboard"))
    conn = get_db()
    conn.execute("DELETE FROM license_managers WHERE id = ?", (manager_id,))
    conn.commit()
    conn.close()
    return redirect(url_for("sa_dashboard"))


@app.route("/sa/managers/<int:manager_id>/password", methods=["POST"])
@sa_login_required
def sa_manager_password(manager_id):
    new_password = request.form.get("new_password", "")
    if not new_password or len(new_password) < 6:
        return redirect(url_for("sa_dashboard"))
    conn = get_db()
    conn.execute(
        "UPDATE license_managers SET password_hash = ? WHERE id = ?",
        (generate_password_hash(new_password), manager_id),
    )
    conn.commit()
    conn.close()
    return redirect(url_for("sa_dashboard"))


# ============================================================
# Süperadmin JSON API (Android için)
# ============================================================

def api_sa_login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "sa_user_id" not in session:
            return jsonify({"status": "error", "message": "Yetkisiz erişim"}), 401
        return f(*args, **kwargs)
    return decorated


@app.route("/api/sa/login", methods=["POST"])
@limiter.limit("10 per minute")
def api_sa_login():
    data     = request.get_json(silent=True) or {}
    username = data.get("username", "").strip()
    password = data.get("password", "")
    if not username or not password:
        return jsonify({"status": "error", "message": "Kullanıcı adı ve şifre gerekli"}), 400
    conn    = get_db()
    manager = conn.execute(
        "SELECT * FROM license_managers WHERE username = ?", (username,)
    ).fetchone()
    conn.close()
    if not manager or not check_password_hash(manager["password_hash"], password):
        return jsonify({"status": "error", "message": "Kullanıcı adı veya şifre hatalı"}), 401
    session["sa_user_id"]  = manager["id"]
    session["sa_username"] = manager["username"]
    return jsonify({"status": "ok", "username": manager["username"]})


@app.route("/api/sa/logout", methods=["POST"])
def api_sa_logout():
    session.pop("sa_user_id",  None)
    session.pop("sa_username", None)
    return jsonify({"status": "ok"})


@app.route("/api/sa/dashboard")
@api_sa_login_required
def api_sa_dashboard():
    conn = get_db()
    licenses = conn.execute(
        "SELECT id, school_code, school_name, start_date, end_date, "
        "duration_months, active, notes, created_at "
        "FROM demo_licenses ORDER BY created_at DESC"
    ).fetchall()
    school_admins = conn.execute(
        "SELECT id, username, full_name, school_code FROM users "
        "WHERE role = 'admin' ORDER BY school_code, full_name"
    ).fetchall()
    all_boards = conn.execute(
        "SELECT board_id, name, location, school_code, is_active "
        "FROM boards ORDER BY school_code, board_id"
    ).fetchall()
    conn.close()
    return jsonify({
        "status":        "ok",
        "licenses":      [dict(r) for r in licenses],
        "school_admins": [dict(r) for r in school_admins],
        "boards":        [dict(r) for r in all_boards],
    })


@app.route("/api/sa/license/add", methods=["POST"])
@api_sa_login_required
def api_sa_license_add():
    data            = request.get_json(silent=True) or {}
    school_code     = data.get("school_code", "").strip().upper()
    school_name     = data.get("school_name", "").strip()
    start_date_str  = data.get("start_date", "").strip()
    duration_months = data.get("duration_months", 2)
    notes           = data.get("notes", "").strip()
    if not school_code or not school_name or not start_date_str:
        return jsonify({"status": "error", "message": "Eksik alan"}), 400
    try:
        duration_months = int(duration_months)
        start_dt        = datetime.strptime(start_date_str, "%Y-%m-%d")
        end_dt          = add_months(start_dt, duration_months)
        end_date_str    = end_dt.strftime("%Y-%m-%d")
    except (ValueError, TypeError):
        return jsonify({"status": "error", "message": "Geçersiz tarih"}), 400
    conn = get_db()
    conn.execute(
        "INSERT INTO demo_licenses "
        "(school_code, school_name, start_date, duration_months, end_date, notes) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (school_code, school_name, start_date_str, duration_months, end_date_str, notes),
    )
    conn.commit()
    conn.close()
    return jsonify({"status": "ok"})


@app.route("/api/sa/license/<int:license_id>/toggle", methods=["POST"])
@api_sa_login_required
def api_sa_license_toggle(license_id):
    conn = get_db()
    lic  = conn.execute(
        "SELECT active FROM demo_licenses WHERE id = ?", (license_id,)
    ).fetchone()
    if not lic:
        conn.close()
        return jsonify({"status": "error", "message": "Lisans bulunamadı"}), 404
    conn.execute(
        "UPDATE demo_licenses SET active = ? WHERE id = ?",
        (0 if lic["active"] else 1, license_id),
    )
    conn.commit()
    conn.close()
    return jsonify({"status": "ok"})


@app.route("/api/sa/license/<int:license_id>", methods=["DELETE"])
@api_sa_login_required
def api_sa_license_delete(license_id):
    conn = get_db()
    conn.execute("DELETE FROM demo_licenses WHERE id = ?", (license_id,))
    conn.commit()
    conn.close()
    return jsonify({"status": "ok"})


@app.route("/api/sa/school_admin/add", methods=["POST"])
@api_sa_login_required
def api_sa_school_admin_add():
    data        = request.get_json(silent=True) or {}
    username    = data.get("username", "").strip()
    password    = data.get("password", "")
    full_name   = data.get("full_name", "").strip()
    school_code = data.get("school_code", "").strip().upper()
    if not username or not password or not full_name or not school_code:
        return jsonify({"status": "error", "message": "Tüm alanlar gerekli"}), 400
    if len(password) < 6:
        return jsonify({"status": "error", "message": "Şifre en az 6 karakter olmalı"}), 400
    conn = get_db()
    try:
        conn.execute(
            "INSERT INTO users (username, password_hash, full_name, role, school_code) "
            "VALUES (?, ?, ?, 'admin', ?)",
            (username, generate_password_hash(password), full_name, school_code),
        )
        conn.commit()
    except sqlite3.IntegrityError:
        conn.close()
        return jsonify({"status": "error", "message": "Bu kullanıcı adı zaten var"}), 409
    conn.close()
    return jsonify({"status": "ok"})


@app.route("/api/sa/school_admin/<int:user_id>", methods=["DELETE"])
@api_sa_login_required
def api_sa_school_admin_delete(user_id):
    conn = get_db()
    conn.execute("UPDATE commands   SET issued_by = NULL WHERE issued_by = ?", (user_id,))
    conn.execute("UPDATE audit_logs SET user_id   = NULL WHERE user_id   = ?", (user_id,))
    conn.execute("DELETE FROM board_permissions WHERE user_id = ?", (user_id,))
    conn.execute("DELETE FROM users WHERE id = ? AND role = 'admin'", (user_id,))
    conn.commit()
    conn.close()
    return jsonify({"status": "ok"})


@app.route("/api/sa/board/assign", methods=["POST"])
@api_sa_login_required
def api_sa_board_assign():
    data        = request.get_json(silent=True) or {}
    board_id    = data.get("board_id", "").strip()
    school_code = data.get("school_code", "").strip().upper()
    if not board_id or not school_code:
        return jsonify({"status": "error", "message": "board_id ve school_code gerekli"}), 400
    conn = get_db()
    conn.execute(
        "UPDATE boards SET school_code = ? WHERE board_id = ?",
        (school_code, board_id)
    )
    conn.commit()
    conn.close()
    return jsonify({"status": "ok"})


@app.route("/api/sa/board/<board_id>", methods=["DELETE"])
@api_sa_login_required
def api_sa_board_delete(board_id):
    conn = get_db()
    conn.execute("DELETE FROM board_permissions WHERE board_id = ?", (board_id,))
    conn.execute("DELETE FROM commands           WHERE board_id = ?", (board_id,))
    conn.execute("DELETE FROM audit_logs         WHERE board_id = ?", (board_id,))
    conn.execute("DELETE FROM boards             WHERE board_id = ?", (board_id,))
    conn.commit()
    conn.close()
    return jsonify({"status": "ok"})


# ============================================================
# Dinamik Kurulum Script Endpoint'i
# ============================================================

WEB_BASE_URL = "http://YOUR_SERVER_IP:4234"

# İstemci sürümü — yeni binary build edilince burası güncellenir
CLIENT_VERSION = "1.6.0"


@app.route("/api/contact", methods=["POST"])
@limiter.limit("5 per hour")
def api_contact():
    data    = request.get_json(silent=True) or {}
    name    = data.get("name",    "").strip()
    email   = data.get("email",   "").strip()
    role    = data.get("role",    "").strip()
    subject = data.get("subject", "").strip()
    school  = data.get("school",  "").strip()
    message = data.get("message", "").strip()

    if not name or not email or not subject or not message:
        return jsonify({"status": "error", "message": "Zorunlu alanlar eksik"}), 400

    body = f"""Pardus Lock — Yeni İletişim Mesajı

İsim    : {name}
E-posta : {email}
Rol     : {role or '-'}
Kurum   : {school or '-'}
Konu    : {subject}

Mesaj:
{message}
"""
    try:
        msg = MIMEMultipart()
        msg["From"]    = CONTACT_EMAIL
        msg["To"]      = CONTACT_EMAIL
        msg["Subject"] = f"[Pardus Lock] {subject} — {name}"
        msg["Reply-To"] = email
        msg.attach(MIMEText(body, "plain", "utf-8"))

        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(CONTACT_EMAIL, CONTACT_PASSWORD)
            server.sendmail(CONTACT_EMAIL, CONTACT_EMAIL, msg.as_string())

        return jsonify({"status": "ok"})
    except Exception as e:
        return jsonify({"status": "error", "message": "Mail gönderilemedi"}), 500


@app.route("/api/version")
@limiter.exempt
def api_version():
    """
    Tahta istemcisinin sürüm kontrolü için kullanır.
    Her Pazartesi açılışta bu endpoint sorgulanır.
    """
    return jsonify({
        "version": CLIENT_VERSION,
        "downloads": {
            "debian10": f"{WEB_BASE_URL}/downloads/pardus-lock-debian10.tar.gz",
            "debian11": f"{WEB_BASE_URL}/downloads/pardus-lock-debian11.tar.gz",
            "debian12": f"{WEB_BASE_URL}/downloads/pardus-lock-debian12.tar.gz",
        }
    })


@app.route("/install/<school_code>")
def generate_install_script(school_code):
    """
    Kurum kodunu içine gömülü, Debian sürümünü otomatik tespit eden install.sh döner.
    Kullanım: curl -sSL http://<sunucu>:5000/install/550292 | bash
    """
    school_code = school_code.strip().upper()

    if not school_code or len(school_code) > 32:
        return "Geçersiz kurum kodu.", 400

    conn = get_db()
    lic  = conn.execute(
        "SELECT school_code FROM demo_licenses WHERE school_code = ?",
        (school_code,)
    ).fetchone()
    conn.close()
    if not lic:
        return "Bu kurum kodu için kayıt bulunamadı.", 404

    script = f"""#!/bin/bash
# ============================================================
# Pardus Smart Board Lock - Otomatik Kurulum
# Kurum Kodu: {school_code}
# ============================================================
set -e

RED='\\033[0;31m'; GREEN='\\033[0;32m'; YELLOW='\\033[1;33m'
BLUE='\\033[0;34m'; NC='\\033[0m'
log()  {{ echo -e "${{GREEN}}[OK]${{NC}} $1"; }}
warn() {{ echo -e "${{YELLOW}}[!]${{NC}} $1"; }}
error(){{ echo -e "${{RED}}[HATA]${{NC}} $1"; exit 1; }}
info() {{ echo -e "${{BLUE}}[*]${{NC}} $1"; }}

SCHOOL_CODE="{school_code}"
WEB_BASE="{WEB_BASE_URL}"
TMP_DIR="$(mktemp -d)"
INSTALL_DIR="$HOME/.local/share/pardus-lock"

echo ""
echo "============================================"
echo "  Pardus Smart Board Lock - Kurulum"
echo "  Kurum Kodu: $SCHOOL_CODE"
echo "============================================"
echo ""

# 1. Debian taban sürümünü tespit et
# /etc/debian_version Pardus dahil tüm Debian tabanlı sistemlerde bulunur
info "İşletim sistemi tespit ediliyor..."
if [ -f /etc/debian_version ]; then
    DEBIAN_VER=$(cut -d. -f1 /etc/debian_version)
else
    DEBIAN_VER="0"
fi

case "$DEBIAN_VER" in
    10) DEB_SLUG="debian10" ;;
    11) DEB_SLUG="debian11" ;;
    12) DEB_SLUG="debian12" ;;
    *)  error "Desteklenmeyen Debian taban sürümü: $DEBIAN_VER. Debian/Pardus 10, 11 veya 12 gereklidir." ;;
esac

DOWNLOAD_URL="$WEB_BASE/downloads/pardus-lock-$DEB_SLUG.tar.gz"
log "Debian $DEBIAN_VER tespit edildi → $DEB_SLUG paketi kullanılacak."

# 2. Benzersiz tahta ID'si oluştur (hostname + MAC son 4 karakter)
info "Tahta kimliği oluşturuluyor..."
DEFAULT_IFACE=$(ip route show default 2>/dev/null | awk '/default/ {{print $5}}' | head -1)
if [ -n "$DEFAULT_IFACE" ] && [ -f "/sys/class/net/$DEFAULT_IFACE/address" ]; then
    MAC_SUFFIX=$(cat "/sys/class/net/$DEFAULT_IFACE/address" | tr -d ':' | tail -c 9)
else
    MAC_SUFFIX=$(head -c 4 /dev/urandom | xxd -p 2>/dev/null | head -c 8 || printf '%08x' "$(date +%s)")
fi
BOARD_ID_VAL="${{HOSTNAME}}-${{MAC_SUFFIX}}"
log "Tahta ID: $BOARD_ID_VAL"

# 3. Binary indir
info "İstemci indiriliyor ($DEB_SLUG)..."
curl -fsSL "$DOWNLOAD_URL" -o "$TMP_DIR/pardus-lock.tar.gz" || error "İndirme başarısız: $DOWNLOAD_URL"
tar -xzf "$TMP_DIR/pardus-lock.tar.gz" -C "$TMP_DIR"
[ -f "$TMP_DIR/pardus-lock" ] || error "Binary bulunamadı arşivde."
log "İndirme tamamlandı."

# 4. Sistem kütüphaneleri
info "Sistem kütüphaneleri kontrol ediliyor..."
PKGS=""
for pkg in libxcb-xinerama0 libxcb-icccm4 libxcb-image0 libxcb-keysyms1 \\
           libxcb-randr0 libxcb-render-util0 libxkbcommon-x11-0 \\
           libxcb-shape0 libxcb-sync1 libxcb-xfixes0 \\
           libglib2.0-0 libdbus-1-3 python3-tk; do
    dpkg -s "$pkg" &>/dev/null 2>&1 || PKGS="$PKGS $pkg"
done
if [ -n "$PKGS" ]; then
    warn "Eksik kütüphaneler kuruluyor:$PKGS"
    sudo apt-get update -qq
    sudo apt-get install -y $PKGS || warn "Bazıları kurulamadı, devam ediliyor."
fi
log "Sistem kütüphaneleri hazır."

# 5. Binary'i kur
info "Program kuruluyor: $INSTALL_DIR"
mkdir -p "$INSTALL_DIR"
pkill -f "pardus-lock" 2>/dev/null && sleep 1 || true
cp "$TMP_DIR/pardus-lock" "$INSTALL_DIR/pardus-lock"
chmod +x "$INSTALL_DIR/pardus-lock"
[ -f "$TMP_DIR/logo.png" ] && cp "$TMP_DIR/logo.png" "$INSTALL_DIR/"

# 6. Kurum kodu ve tahta ID'sini kaydet
echo "$SCHOOL_CODE"   > "$INSTALL_DIR/school_code.txt"
echo "$BOARD_ID_VAL"  > "$INSTALL_DIR/board_id.txt"
log "Kurum kodu kaydedildi: $SCHOOL_CODE"
log "Tahta ID kaydedildi:   $BOARD_ID_VAL"

# 7. Çalıştırma scripti
cat > "$INSTALL_DIR/run.sh" << 'RUNEOF'
#!/bin/bash
export DISPLAY="${{DISPLAY:-:0}}"
export XAUTHORITY="${{XAUTHORITY:-$HOME/.Xauthority}}"
exec "$(dirname "$0")/pardus-lock" "$@"
RUNEOF
chmod +x "$INSTALL_DIR/run.sh"

# 8. XDG Autostart
mkdir -p "$HOME/.config/autostart"
cat > "$HOME/.config/autostart/pardus-lock.desktop" << DESKEOF
[Desktop Entry]
Type=Application
Name=Pardus Smart Board Lock
Exec=/bin/bash $INSTALL_DIR/run.sh
Hidden=false
NoDisplay=false
X-GNOME-Autostart-enabled=true
X-GNOME-Autostart-Delay=2
DESKEOF
log "XDG autostart kuruldu."

# 9. systemd user service
mkdir -p "$HOME/.config/systemd/user"
cat > "$HOME/.config/systemd/user/pardus-lock.service" << SVCEOF
[Unit]
Description=Pardus Smart Board Lock
After=graphical-session.target
Wants=graphical-session.target
StartLimitIntervalSec=0

[Service]
Type=simple
ExecStart=/bin/bash $INSTALL_DIR/run.sh
Restart=always
RestartSec=3
Environment=DISPLAY=:0
Environment=XAUTHORITY=$HOME/.Xauthority

[Install]
WantedBy=graphical-session.target
SVCEOF

if command -v systemctl &>/dev/null; then
    systemctl --user daemon-reload 2>/dev/null || true
    systemctl --user enable pardus-lock.service 2>/dev/null && \\
        log "systemd service etkinleştirildi." || \\
        warn "systemd service etkinleştirilemedi."
    sudo loginctl enable-linger "$USER" 2>/dev/null && \\
        log "loginctl linger etkinleştirildi." || true
fi

# 10. Temizlik
rm -rf "$TMP_DIR"

# 11. Başlat
nohup bash "$INSTALL_DIR/run.sh" &>/dev/null &
log "Kilit sistemi başlatıldı."

echo ""
echo "============================================"
echo "  Kurulum Tamamlandi!"
echo "  Kurum Kodu : $SCHOOL_CODE"
echo "  Tahta ID   : $BOARD_ID_VAL"
echo "  Debian     : $DEBIAN_VER ($DEB_SLUG)"
echo "  Sonraki acilista otomatik baslar."
echo ""
echo "  Komutlar:"
echo "    Durdur    : systemctl --user stop pardus-lock"
echo "    Devre disi: systemctl --user disable pardus-lock"
echo "    Durum     : systemctl --user status pardus-lock"
echo "============================================"
echo ""
"""

    from flask import Response
    return Response(
        script,
        mimetype="text/x-shellscript",
        headers={"Content-Disposition": f"inline; filename=install-{school_code}.sh"}
    )


# ============================================================

if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=5000)
