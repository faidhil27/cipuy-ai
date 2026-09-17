"""
database.py - Modul Manajemen Database Ultra Cepat (SQLite & Supabase)
Mendukung pencatatan real-time instan, status pending, dan manajemen storage admin.
"""

import os
import sqlite3
import uuid
import datetime
from typing import Dict, List, Optional, Any, Tuple
from dotenv import load_dotenv

load_dotenv()

DATABASE_TYPE = os.getenv("DATABASE_TYPE", "sqlite").lower()
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")

# Inisialisasi Supabase client jika diaktifkan
supabase_client = None
if DATABASE_TYPE == "supabase" and SUPABASE_URL and SUPABASE_KEY:
    try:
        from supabase import create_client, Client
        supabase_client: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
        print(" Connected to Supabase Cloud Database successfully.")
    except Exception as e:
        print(f" Failed to initialize Supabase client: {e}. Falling back to SQLite.")
        supabase_client = None
        DATABASE_TYPE = "sqlite"

# Di lingkungan serverless Vercel / AWS Lambda, filesystem adalah read-only kecuali /tmp
IS_SERVERLESS = bool(os.getenv("VERCEL") or os.getenv("AWS_LAMBDA_FUNCTION_NAME"))
if IS_SERVERLESS:
    SQLITE_PATH = "/tmp/chats.db"
else:
    SQLITE_PATH = os.path.join(os.path.dirname(__file__), "chats.db")


def get_sqlite_conn() -> sqlite3.Connection:
    """Membuka koneksi SQLite dengan mode WAL (Write-Ahead Logging) atau fallback aman di serverless."""
    conn = sqlite3.connect(SQLITE_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("PRAGMA journal_mode = WAL;")
        conn.execute("PRAGMA synchronous = NORMAL;")
    except Exception:
        pass
    return conn


def init_db():
    """Inisialisasi tabel SQLite (selalu siap sebagai database lokal utama atau fallback ultra-cepat)."""
    try:
        conn = get_sqlite_conn()
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS chat_sessions (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS chat_messages (
                id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                model_name TEXT DEFAULT 'gemini-1.5-pro',
                status TEXT DEFAULT 'completed',
                character_count INTEGER DEFAULT 0,
                storage_bytes INTEGER DEFAULT 0,
                client_ip TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (session_id) REFERENCES chat_sessions(id) ON DELETE CASCADE
            );
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'user',
                status TEXT NOT NULL DEFAULT 'active',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        # Cek apakah kolom status sudah ada (migrasi otomatis)
        cursor.execute("PRAGMA table_info(users);")
        columns = [row["name"] for row in cursor.fetchall()]
        if "status" not in columns:
            cursor.execute("ALTER TABLE users ADD COLUMN status TEXT DEFAULT 'active';")

        cursor.execute("CREATE INDEX IF NOT EXISTS idx_chat_messages_session ON chat_messages(session_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_chat_messages_created ON chat_messages(created_at DESC);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_chat_messages_status ON chat_messages(status);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);")

        # Pastikan akun admin default tersedia
        admin_pass = os.getenv("ADMIN_SECRET_KEY", "admin123")
        cursor.execute("SELECT id FROM users WHERE username = 'admin';")
        admin_row = cursor.fetchone()
        if not admin_row:
            cursor.execute("""
                INSERT INTO users (id, username, password, role, status)
                VALUES (?, ?, ?, 'admin', 'active');
            """, (str(uuid.uuid4()), "admin", admin_pass))
            print(" Default admin account created: username='admin'")
        else:
            # Update status admin jika belum active
            cursor.execute("UPDATE users SET status = 'active' WHERE username = 'admin';")

        conn.commit()
        conn.close()
        print(" SQLite database initialized with high-performance WAL mode & users table.")
    except Exception as e:
        print(f"Error initializing SQLite db: {e}")

    # Sinkronisasi admin ke Supabase jika tabel users ada
    if DATABASE_TYPE == "supabase" and supabase_client:
        try:
            admin_check = supabase_client.table("users").select("id").eq("username", "admin").execute()
            if not admin_check.data or len(admin_check.data) == 0:
                admin_pass = os.getenv("ADMIN_SECRET_KEY", "admin123")
                now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
                supabase_client.table("users").insert({
                    "id": str(uuid.uuid4()),
                    "username": "admin",
                    "password": admin_pass,
                    "role": "admin",
                    "status": "active",
                    "created_at": now_iso
                }).execute()
                print(" Default admin account synchronized to Supabase.")
        except Exception as e:
            print(f"Supabase users table init note (will use SQLite fallback): {e}")


# Inisialisasi awal
init_db()


def ensure_session(session_id: str, title: str = "Percakapan Baru") -> str:
    """Memastikan sesi chat sudah ada atau membuat sesi baru."""
    now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
    if DATABASE_TYPE == "supabase" and supabase_client:
        try:
            res = supabase_client.table("chat_sessions").select("id").eq("id", session_id).execute()
            if not res.data:
                supabase_client.table("chat_sessions").insert({
                    "id": session_id,
                    "title": title[:100],
                    "created_at": now_iso,
                    "updated_at": now_iso
                }).execute()
            return session_id
        except Exception as e:
            print(f"Supabase ensure_session error: {e}")

    # Fallback / SQLite
    conn = get_sqlite_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM chat_sessions WHERE id = ?", (session_id,))
    if not cursor.fetchone():
        cursor.execute(
            "INSERT INTO chat_sessions (id, title, created_at, updated_at) VALUES (?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)",
            (session_id, title[:100])
        )
        conn.commit()
    conn.close()
    return session_id


def record_user_prompt(session_id: str, prompt: str, client_ip: str = "127.0.0.1") -> str:
    """Mencatat prompt user ke database secepat kilat (status completed)."""
    msg_id = str(uuid.uuid4())
    char_count = len(prompt)
    storage_bytes = len(prompt.encode("utf-8"))
    now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()

    if DATABASE_TYPE == "supabase" and supabase_client:
        try:
            supabase_client.table("chat_messages").insert({
                "id": msg_id,
                "session_id": session_id,
                "role": "user",
                "content": prompt,
                "model_name": "user-prompt",
                "status": "completed",
                "character_count": char_count,
                "storage_bytes": storage_bytes,
                "client_ip": client_ip,
                "created_at": now_iso,
                "updated_at": now_iso
            }).execute()
            return msg_id
        except Exception as e:
            print(f"Supabase record_user_prompt error: {e}")

    conn = get_sqlite_conn()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO chat_messages 
        (id, session_id, role, content, model_name, status, character_count, storage_bytes, client_ip)
        VALUES (?, ?, 'user', ?, 'user-prompt', 'completed', ?, ?, ?)
    """, (msg_id, session_id, prompt, char_count, storage_bytes, client_ip))
    conn.commit()
    conn.close()
    return msg_id


def create_pending_response(session_id: str, model_name: str = "gemini-1.5-pro") -> str:
    """Membuat record model berstatus 'pending' secara instan sebelum Gemini mulai menjawab."""
    msg_id = str(uuid.uuid4())
    now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()

    if DATABASE_TYPE == "supabase" and supabase_client:
        try:
            supabase_client.table("chat_messages").insert({
                "id": msg_id,
                "session_id": session_id,
                "role": "model",
                "content": "",
                "model_name": model_name,
                "status": "pending",
                "character_count": 0,
                "storage_bytes": 0,
                "created_at": now_iso,
                "updated_at": now_iso
            }).execute()
            return msg_id
        except Exception as e:
            print(f"Supabase create_pending_response error: {e}")

    conn = get_sqlite_conn()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO chat_messages 
        (id, session_id, role, content, model_name, status, character_count, storage_bytes)
        VALUES (?, ?, 'model', '', ?, 'pending', 0, 0)
    """, (msg_id, session_id, model_name))
    conn.commit()
    conn.close()
    return msg_id


def update_response_completed(message_id: str, content: str, status: str = "completed"):
    """Meng-update record respons AI dengan jawaban final, jumlah karakter, dan byte size."""
    char_count = len(content)
    storage_bytes = len(content.encode("utf-8"))
    now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()

    if DATABASE_TYPE == "supabase" and supabase_client:
        try:
            supabase_client.table("chat_messages").update({
                "content": content,
                "status": status,
                "character_count": char_count,
                "storage_bytes": storage_bytes,
                "updated_at": now_iso
            }).eq("id", message_id).execute()
            return
        except Exception as e:
            print(f"Supabase update_response_completed error: {e}")

    conn = get_sqlite_conn()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE chat_messages 
        SET content = ?, status = ?, character_count = ?, storage_bytes = ?, updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
    """, (content, status, char_count, storage_bytes, message_id))
    conn.commit()
    conn.close()


def update_session_title_if_default(session_id: str, prompt_text: str):
    """Memperbarui judul sesi berdasarkan prompt pertama jika masih berjudul Percakapan Baru."""
    new_title = prompt_text.strip().replace("\n", " ")[:35]
    if len(prompt_text) > 35:
        new_title += "..."

    if DATABASE_TYPE == "supabase" and supabase_client:
        try:
            res = supabase_client.table("chat_sessions").select("title").eq("id", session_id).execute()
            if res.data and res.data[0]["title"] in ["Percakapan Baru", "New Chat"]:
                supabase_client.table("chat_sessions").update({"title": new_title}).eq("id", session_id).execute()
            return
        except Exception as e:
            print(f"Supabase update_session_title error: {e}")

    conn = get_sqlite_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT title FROM chat_sessions WHERE id = ?", (session_id,))
    row = cursor.fetchone()
    if row and row["title"] in ["Percakapan Baru", "New Chat"]:
        cursor.execute("UPDATE chat_sessions SET title = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?", (new_title, session_id))
        conn.commit()
    conn.close()


def get_sessions() -> List[Dict[str, Any]]:
    """Mengambil riwayat daftar sesi untuk sidebar."""
    if DATABASE_TYPE == "supabase" and supabase_client:
        try:
            res = supabase_client.table("chat_sessions").select("*").order("updated_at", desc=True).limit(50).execute()
            return res.data or []
        except Exception as e:
            print(f"Supabase get_sessions error: {e}")

    conn = get_sqlite_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM chat_sessions ORDER BY updated_at DESC LIMIT 50")
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows


def get_session_messages(session_id: str) -> List[Dict[str, Any]]:
    """Mengambil semua percakapan di dalam sesi tertentu."""
    if DATABASE_TYPE == "supabase" and supabase_client:
        try:
            res = supabase_client.table("chat_messages").select("*").eq("session_id", session_id).order("created_at", desc=False).execute()
            return res.data or []
        except Exception as e:
            print(f"Supabase get_session_messages error: {e}")

    conn = get_sqlite_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM chat_messages WHERE session_id = ? ORDER BY created_at ASC", (session_id,))
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows


def delete_session(session_id: str) -> bool:
    """Menghapus seluruh sesi beserta semua pesannya."""
    if DATABASE_TYPE == "supabase" and supabase_client:
        try:
            supabase_client.table("chat_messages").delete().eq("session_id", session_id).execute()
            supabase_client.table("chat_sessions").delete().eq("id", session_id).execute()
            return True
        except Exception as e:
            print(f"Supabase delete_session error: {e}")
            return False

    conn = get_sqlite_conn()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM chat_messages WHERE session_id = ?", (session_id,))
    cursor.execute("DELETE FROM chat_sessions WHERE id = ?", (session_id,))
    conn.commit()
    conn.close()
    return True


# ==========================================
# ADMIN & STORAGE MONITORING FUNCTIONS
# ==========================================

def get_admin_logs(query: str = "", limit: int = 100, offset: int = 0) -> Dict[str, Any]:
    """Mengambil semua log pencarian user untuk keperluan audit dan monitoring admin."""
    if DATABASE_TYPE == "supabase" and supabase_client:
        try:
            db_query = supabase_client.table("chat_messages").select("*, chat_sessions(title)")
            if query:
                db_query = db_query.ilike("content", f"%{query}%")
            res = db_query.order("created_at", desc=True).range(offset, offset + limit - 1).execute()
            
            # Count total
            count_res = supabase_client.table("chat_messages").select("id", count="exact").execute()
            total_count = count_res.count if hasattr(count_res, "count") else len(res.data)
            return {
                "logs": res.data or [],
                "total": total_count,
                "db_type": "Supabase Cloud"
            }
        except Exception as e:
            print(f"Supabase get_admin_logs error: {e}")

    conn = get_sqlite_conn()
    cursor = conn.cursor()
    if query:
        search_pattern = f"%{query}%"
        cursor.execute("SELECT COUNT(*) as total FROM chat_messages WHERE content LIKE ?", (search_pattern,))
        total = cursor.fetchone()["total"]
        cursor.execute("""
            SELECT m.*, s.title as session_title 
            FROM chat_messages m
            LEFT JOIN chat_sessions s ON m.session_id = s.id
            WHERE m.content LIKE ?
            ORDER BY m.created_at DESC
            LIMIT ? OFFSET ?
        """, (search_pattern, limit, offset))
    else:
        cursor.execute("SELECT COUNT(*) as total FROM chat_messages")
        total = cursor.fetchone()["total"]
        cursor.execute("""
            SELECT m.*, s.title as session_title 
            FROM chat_messages m
            LEFT JOIN chat_sessions s ON m.session_id = s.id
            ORDER BY m.created_at DESC
            LIMIT ? OFFSET ?
        """, (limit, offset))

    logs = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return {
        "logs": logs,
        "total": total,
        "db_type": "SQLite Local"
    }


def delete_message(message_id: str) -> bool:
    """Menghapus satu record pesan tertentu untuk menghemat database."""
    if DATABASE_TYPE == "supabase" and supabase_client:
        try:
            supabase_client.table("chat_messages").delete().eq("id", message_id).execute()
            return True
        except Exception as e:
            print(f"Supabase delete_message error: {e}")
            return False

    conn = get_sqlite_conn()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM chat_messages WHERE id = ?", (message_id,))
    conn.commit()
    conn.close()
    return True


def clear_old_logs(days: int = 30) -> int:
    """Membersihkan log percakapan yang lebih lama dari sekian hari."""
    cutoff = (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=days)).isoformat()
    
    if DATABASE_TYPE == "supabase" and supabase_client:
        try:
            res = supabase_client.table("chat_messages").delete().lt("created_at", cutoff).execute()
            return len(res.data) if res.data else 0
        except Exception as e:
            print(f"Supabase clear_old_logs error: {e}")
            return 0

    conn = get_sqlite_conn()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM chat_messages WHERE created_at < datetime('now', ?)", (f"-{days} days",))
    deleted_count = cursor.rowcount
    conn.commit()
    cursor.execute("VACUUM;")
    conn.close()
    return deleted_count


def clear_all_data() -> bool:
    """Menghapus SELURUH data pesan & sesi untuk mengosongkan storage secara total."""
    if DATABASE_TYPE == "supabase" and supabase_client:
        try:
            supabase_client.table("chat_messages").delete().neq("id", "none").execute()
            supabase_client.table("chat_sessions").delete().neq("id", "none").execute()
            return True
        except Exception as e:
            print(f"Supabase clear_all_data error: {e}")
            return False

    conn = get_sqlite_conn()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM chat_messages")
    cursor.execute("DELETE FROM chat_sessions")
    conn.commit()
    cursor.execute("VACUUM;")
    conn.close()
    return True


def get_storage_stats() -> Dict[str, Any]:
    """Menghitung kapasitas database yang terpakai dan jumlah pesan secara real-time."""
    if DATABASE_TYPE == "supabase" and supabase_client:
        try:
            # Query count and approximate bytes
            msg_res = supabase_client.table("chat_messages").select("id, role, status, storage_bytes", count="exact").execute()
            session_res = supabase_client.table("chat_sessions").select("id", count="exact").execute()
            
            data = msg_res.data or []
            total_bytes = sum((item.get("storage_bytes") or 0) for item in data)
            total_pending = sum(1 for item in data if item.get("status") == "pending")
            total_user_prompts = sum(1 for item in data if item.get("role") == "user")
            total_ai_responses = sum(1 for item in data if item.get("role") == "model")
            
            return {
                "db_engine": "Supabase Cloud (PostgreSQL)",
                "total_sessions": session_res.count if hasattr(session_res, "count") else 0,
                "total_messages": len(data),
                "total_user_prompts": total_user_prompts,
                "total_ai_responses": total_ai_responses,
                "total_pending": total_pending,
                "total_bytes": total_bytes,
                "storage_kb": round(total_bytes / 1024, 2),
                "storage_mb": round(total_bytes / (1024 * 1024), 4),
                "free_tier_limit_mb": 500.0,
                "usage_percentage": round((total_bytes / (500 * 1024 * 1024)) * 100, 4)
            }
        except Exception as e:
            print(f"Supabase get_storage_stats error: {e}")

    conn = get_sqlite_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) as count FROM chat_sessions")
    total_sessions = cursor.fetchone()["count"]

    cursor.execute("SELECT COUNT(*) as count FROM chat_messages")
    total_messages = cursor.fetchone()["count"]

    cursor.execute("SELECT COUNT(*) as count FROM chat_messages WHERE role = 'user'")
    total_prompts = cursor.fetchone()["count"]

    cursor.execute("SELECT COUNT(*) as count FROM chat_messages WHERE role = 'model'")
    total_responses = cursor.fetchone()["count"]

    cursor.execute("SELECT COUNT(*) as count FROM chat_messages WHERE status = 'pending'")
    total_pending = cursor.fetchone()["count"]

    cursor.execute("SELECT COALESCE(SUM(storage_bytes), 0) as total_bytes FROM chat_messages")
    total_bytes = cursor.fetchone()["total_bytes"]

    # Ukuran file DB di disk
    file_size = 0
    if os.path.exists(SQLITE_PATH):
        file_size = os.path.getsize(SQLITE_PATH)

    conn.close()

    effective_bytes = max(total_bytes, file_size)

    return {
        "db_engine": "SQLite High-Speed WAL (Lokal)",
        "total_sessions": total_sessions,
        "total_messages": total_messages,
        "total_user_prompts": total_prompts,
        "total_ai_responses": total_responses,
        "total_pending": total_pending,
        "total_bytes": effective_bytes,
        "storage_kb": round(effective_bytes / 1024, 2),
        "storage_mb": round(effective_bytes / (1024 * 1024), 4),
        "free_tier_limit_mb": 500.0,
        "usage_percentage": round((effective_bytes / (500 * 1024 * 1024)) * 100, 4)
    }


# ==========================================
# USER AUTHENTICATION & MANAGEMENT FUNCTIONS
# ==========================================

def authenticate_user(username: str, password: str) -> Tuple[bool, Any]:
    """
    Memvalidasi kredensial pengguna.
    Mengembalikan (True, user_dict) jika berhasil dan akun aktif.
    Mengembalikan (False, error_message) jika gagal atau akun dinonaktifkan.
    """
    username = (username or "").strip()
    password = (password or "").strip()
    if not username or not password:
        return False, "Username dan password wajib diisi."

    # Cek Supabase jika aktif
    if DATABASE_TYPE == "supabase" and supabase_client:
        try:
            res = supabase_client.table("users").select("*").eq("username", username).execute()
            if res.data and len(res.data) > 0:
                user = res.data[0]
                if user.get("password") != password:
                    return False, "Username atau password salah."
                if user.get("status") != "active":
                    return False, "Akun Anda sedang dinonaktifkan sementara oleh Admin."
                return True, {
                    "id": user.get("id"),
                    "username": user.get("username"),
                    "role": user.get("role", "user"),
                    "status": user.get("status", "active")
                }
        except Exception as e:
            print(f"Supabase auth fallback to SQLite: {e}")

    # Cek SQLite
    conn = get_sqlite_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE username = ?;", (username,))
    row = cursor.fetchone()
    conn.close()

    if not row:
        return False, "Username atau password salah."

    if row["password"] != password:
        return False, "Username atau password salah."

    if row["status"] != "active":
        return False, "Akun Anda sedang dinonaktifkan sementara oleh Admin."

    return True, {
        "id": row["id"],
        "username": row["username"],
        "role": row["role"],
        "status": row["status"]
    }


def get_all_users() -> List[Dict[str, Any]]:
    """Mengambil daftar semua pengguna terdaftar tanpa password."""
    users_list = []
    if DATABASE_TYPE == "supabase" and supabase_client:
        try:
            res = supabase_client.table("users").select("id, username, role, status, created_at").order("created_at", desc=False).execute()
            if res.data:
                return res.data
        except Exception as e:
            print(f"Supabase get_all_users fallback to SQLite: {e}")

    conn = get_sqlite_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT id, username, role, status, created_at FROM users ORDER BY created_at ASC;")
    rows = cursor.fetchall()
    conn.close()

    for r in rows:
        users_list.append({
            "id": r["id"],
            "username": r["username"],
            "role": r["role"],
            "status": r["status"] if "status" in r.keys() else "active",
            "created_at": r["created_at"]
        })
    return users_list


def create_user(username: str, password: str, role: str = "user") -> Tuple[bool, str]:
    """Membuat pengguna baru oleh Admin."""
    username = (username or "").strip()
    password = (password or "").strip()
    role = role.strip().lower() if role in ["admin", "user"] else "user"

    if len(username) < 3:
        return False, "Username minimal harus 3 karakter."
    if len(password) < 4:
        return False, "Password minimal harus 4 karakter."
    if " " in username:
        return False, "Username tidak boleh mengandung spasi."

    now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
    new_id = str(uuid.uuid4())

    # Jika Supabase aktif
    if DATABASE_TYPE == "supabase" and supabase_client:
        try:
            check = supabase_client.table("users").select("id").eq("username", username).execute()
            if check.data and len(check.data) > 0:
                return False, f"Username '{username}' sudah digunakan. Pilih username lain."
            supabase_client.table("users").insert({
                "id": new_id,
                "username": username,
                "password": password,
                "role": role,
                "status": "active",
                "created_at": now_iso
            }).execute()
            return True, f"Pengguna '{username}' berhasil ditambahkan."
        except Exception as e:
            print(f"Supabase create_user fallback to SQLite: {e}")

    # SQLite
    conn = get_sqlite_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM users WHERE username = ?;", (username,))
    if cursor.fetchone():
        conn.close()
        return False, f"Username '{username}' sudah digunakan. Pilih username lain."

    cursor.execute("""
        INSERT INTO users (id, username, password, role, status, created_at)
        VALUES (?, ?, ?, ?, 'active', CURRENT_TIMESTAMP);
    """, (new_id, username, password, role))
    conn.commit()
    conn.close()
    return True, f"Pengguna '{username}' berhasil ditambahkan."


def toggle_user_status(username: str, new_status: str, current_admin: str) -> Tuple[bool, str]:
    """Mengubah status user (active / inactive). Admin utama tidak bisa dinonaktifkan."""
    username = (username or "").strip()
    new_status = new_status.strip().lower()
    if new_status not in ["active", "inactive"]:
        return False, "Status harus 'active' atau 'inactive'."

    if username.lower() == "admin" or username.lower() == current_admin.lower():
        return False, "Akun admin utama tidak dapat dinonaktifkan demi keamanan."

    if DATABASE_TYPE == "supabase" and supabase_client:
        try:
            supabase_client.table("users").update({"status": new_status}).eq("username", username).execute()
            status_text = "diaktifkan" if new_status == "active" else "dinonaktifkan sementara"
            return True, f"Pengguna '{username}' berhasil {status_text}."
        except Exception as e:
            print(f"Supabase toggle_user_status fallback to SQLite: {e}")

    conn = get_sqlite_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM users WHERE username = ?;", (username,))
    if not cursor.fetchone():
        conn.close()
        return False, f"Pengguna '{username}' tidak ditemukan."

    cursor.execute("UPDATE users SET status = ? WHERE username = ?;", (new_status, username))
    conn.commit()
    conn.close()

    status_text = "diaktifkan kembali" if new_status == "active" else "dinonaktifkan sementara"
    return True, f"Pengguna '{username}' berhasil {status_text}."


def delete_user(username: str, current_admin: str) -> Tuple[bool, str]:
    """Menghapus akun pengguna oleh Admin. Admin utama tidak bisa dihapus."""
    username = (username or "").strip()
    if username.lower() == "admin" or username.lower() == current_admin.lower():
        return False, "Akun admin utama tidak dapat dihapus demi keamanan."

    if DATABASE_TYPE == "supabase" and supabase_client:
        try:
            supabase_client.table("users").delete().eq("username", username).execute()
            return True, f"Pengguna '{username}' berhasil dihapus dari database."
        except Exception as e:
            print(f"Supabase delete_user fallback to SQLite: {e}")

    conn = get_sqlite_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM users WHERE username = ?;", (username,))
    if not cursor.fetchone():
        conn.close()
        return False, f"Pengguna '{username}' tidak ditemukan."

    cursor.execute("DELETE FROM users WHERE username = ?;", (username,))
    conn.commit()
    conn.close()
    return True, f"Pengguna '{username}' berhasil dihapus dari database."

