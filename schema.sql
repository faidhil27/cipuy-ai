-- SQL Schema untuk Supabase / PostgreSQL
-- Jalankan skrip ini di SQL Editor Supabase untuk membuat tabel dan mengatur hak akses (RLS)

CREATE TABLE IF NOT EXISTS chat_sessions (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS chat_messages (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL REFERENCES chat_sessions(id) ON DELETE CASCADE,
    role TEXT NOT NULL CHECK (role IN ('user', 'model')),
    content TEXT NOT NULL,
    model_name TEXT DEFAULT 'gemini-1.5-pro',
    status TEXT DEFAULT 'completed' CHECK (status IN ('pending', 'completed', 'error')),
    character_count INTEGER DEFAULT 0,
    storage_bytes INTEGER DEFAULT 0,
    client_ip TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Index agar pencarian dan penghapusan data log sangat cepat
CREATE INDEX IF NOT EXISTS idx_chat_messages_session ON chat_messages(session_id);
CREATE INDEX IF NOT EXISTS idx_chat_messages_created ON chat_messages(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_chat_messages_role ON chat_messages(role);
CREATE INDEX IF NOT EXISTS idx_chat_messages_status ON chat_messages(status);

-- =========================================================================
-- TABEL PENGGUNA & ADMIN (USER MANAGEMENT)
-- =========================================================================
CREATE TABLE IF NOT EXISTS users (
    id TEXT PRIMARY KEY,
    username TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'user',
    status TEXT NOT NULL DEFAULT 'active',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);

-- =========================================================================
-- IZIN AKSES (PENTING AGAR API BISA MENULIS & MEMBACA DATA CHAT & USER)
-- =========================================================================
ALTER TABLE chat_sessions DISABLE ROW LEVEL SECURITY;
ALTER TABLE chat_messages DISABLE ROW LEVEL SECURITY;
ALTER TABLE users DISABLE ROW LEVEL SECURITY;

-- Akun admin awal default (akan disinkronkan otomatis)
INSERT INTO users (id, username, password, role, status)
VALUES ('admin-01', 'admin', 'admin123', 'admin', 'active')
ON CONFLICT (username) DO NOTHING;
