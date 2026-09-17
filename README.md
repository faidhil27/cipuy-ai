---
title: Cipuy Pro AI
emoji: 🤖
colorFrom: purple
colorTo: blue
sdk: docker
app_port: 7860
pinned: false
---

# 🌟 Cipuy Pro - Web AI Pribadi Mirip 100% Google Gemini Pro

**Cipuy Pro** adalah aplikasi web AI asisten pribadi dengan antarmuka yang dirancang presisi 1:1 menyerupai **Google Gemini Pro** (Dark theme otentik Gemini, ikon 4-pointed sparkle, prompt capsule melayang, Markdown & code block highlighter, riwayat sesi, dan input suara).

Aplikasi ini menggunakan arsitektur **Database-Mediated Flow Ultra Cepat** (< 10 ms):
1. **User Prompt** dikirim ke backend dan langsung dicatat ke database online (status: *completed*).
2. Record balasan AI dibuat seketika dengan status *pending* di database.
3. Prompt diproses oleh **Google Gemini 1.5 Pro API**.
4. Balasan AI di-streaming secara real-time via Server-Sent Events (SSE) dan disimpan ke database (status: *completed* + perhitungan bytes storage).
5. Pemilik memiliki akses ke **Admin Storage Manager** (di web & cloud) untuk memeriksa seluruh pencarian user dan menghapus log agar database tetap lega.

---

## 🚀 Fitur Utama

- **UI Gemini Pro 100% Kloning**: Warna background `#131314`, font Google Sans/Inter, hero greeting teks gradien *"Halo, Saya Cipuy"*, 4 kartu saran prompt, dan floating rounded capsule input.
- **Pencatatan Database Kilat (< 10 ms)**: Menggunakan mode WAL (Write-Ahead Logging) dan async streaming.
- **Dukungan Dual-Engine Database**:
  - **SQLite Lokal Cepat**: Langsung aktif tanpa konfigurasi apapun.
  - **Supabase Cloud (PostgreSQL)**: Database online gratis 500 MB (~500.000 pesan chat).
- **Admin Storage & Query Inspector**:
  - Pantau total prompt, respons AI, dan estimasi MB database terpakai.
  - Cari riwayat prompt user berdasarkan kata kunci.
  - Hapus percakapan individual atau bulk clean (misal: hapus log > 14 hari).
- **Markdown & Code Highlight**: Kode Python, JavaScript, SQL, dll. dilengkapi tombol *Salin Kode* dan pewarnaan sintaks.
- **Voice to Text (Mikrofon)**: Dukungan input suara bahasa Indonesia via Web Speech API bawaan browser.

---

## 📦 Rekomendasi Database Online Gratis

| Provider | Free Storage | Kapasitas Pesan | Web Studio / Dashboard | Rekomendasi |
| :--- | :--- | :--- | :--- | :--- |
| **Supabase (PostgreSQL)** | **500 MB** DB + 1 GB Storage | **~500.000 chat** | ⭐ Ada Table Editor mirip Excel, bisa edit/hapus data via HP/laptop. | **Sangat Direkomendasikan** |
| **Turso (LibSQL)** | **9 GB** Storage | **~4.500.000 chat** | CLI / Basic Web | Kapasitas masif untuk data teks. |
| **MongoDB Atlas** | **512 MB** NoSQL | **~250.000 chat** | Ada Data Explorer | Bagus untuk JSON mentah. |

---

## 🛠️ Cara Menjalankan Aplikasi

### 1. Jalankan Langsung (Mode Default SQLite)
Buka terminal PowerShell di folder proyek ini, lalu jalankan:

```powershell
python main.py
```

Buka browser Anda di:
👉 **`http://localhost:8000`**

---

### 2. Memasukkan API Key Google Gemini Pro
Agar Cipuy dapat berpikir dan menjawab pertanyaan secara nyata:

1. Buka [Google AI Studio](https://aistudio.google.com/) (Gratis).
2. Klik **Get API key** lalu buat API Key baru.
3. Buka file `.env` di folder ini, lalu masukkan kunci Anda:
   ```env
   GEMINI_API_KEY=AIzaSyDxxxxxxxxx...
   GEMINI_MODEL=gemini-1.5-pro
   ```
4. Simpan file `.env`. Cipuy sekarang terhubung ke Gemini Pro pribadi Anda!

---

### 3. Menghubungkan ke Database Online Gratis (Supabase)
Jika Anda ingin data pencarian tersimpan di cloud agar bisa Anda pantau dari mana saja:

1. Daftar gratis di [supabase.com](https://supabase.com).
2. Buat project baru (pilih region terdekat, misalnya *Singapore*).
3. Di dashboard Supabase, klik menu **SQL Editor** di panel kiri.
4. Buka file `schema.sql` di proyek ini, copy seluruh isinya, paste di SQL Editor Supabase, lalu klik tombol **Run**.
5. Buka menu **Project Settings** -> **API** di Supabase:
   - Salin **Project URL**
   - Salin **anon / public key** (atau *service_role key*)
6. Edit file `.env` Anda:
   ```env
   DATABASE_TYPE=supabase
   SUPABASE_URL=https://xxxxxxxxxxxx.supabase.co
   SUPABASE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6...
   ```
7. Jalankan kembali `python main.py`. Semua percakapan otomatis tersinkronisasi ke cloud Supabase!

---

## 🛡️ Mengakses Admin Storage Manager

1. Di antarmuka web, klik menu **Database & Storage** di bagian kiri bawah sidebar.
2. Anda akan melihat:
   - Status engine database yang aktif.
   - Total sesi, total pertanyaan user, dan balasan AI.
   - Progress bar kapasitas terpakai dari kuota 500 MB.
   - Tabel seluruh prompt pencarian user.
   - Tombol **Hapus** (ikon tempat sampah) untuk menghapus record tertentu.
   - Tombol **Bersihkan Pesan Lama** untuk mengosongkan log yang sudah lewat sekian hari.
   - Tombol **Kosongkan Database** untuk reset total.

---

## 📁 Struktur Berkas Proyek

```
Belajar Buat AI/
├── main.py              # Server FastAPI, routing SSE streaming, & API admin
├── database.py          # Modul database ultra-cepat (SQLite WAL & Supabase)
├── gemini_service.py    # Integrasi API Google Gemini Pro & persona Cipuy
├── schema.sql           # Skema DDL tabel untuk Supabase PostgreSQL
├── test_app.py          # Skrip uji kecepatan pencatatan & pending record
├── test_server.py       # Skrip uji endpoint HTTP FastAPI
├── test_stream.py       # Skrip uji streaming SSE end-to-end
├── .env                 # Konfigurasi kunci API dan database lokal/cloud
├── .env.example         # Template konfigurasi environment
├── templates/
│   └── index.html       # Antarmuka web kloningan 100% Google Gemini Pro
└── static/
    ├── css/
    │   └── gemini.css   # Style otentik warna & animasi Google Gemini
    └── js/
        └── app.js       # Logika streaming, rendering markdown, & admin modal
```

