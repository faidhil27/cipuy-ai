"""
main.py - Server Aplikasi Web AI Pribadi Mirip Google Gemini Pro
Dibangun dengan FastAPI, streaming response SSE, pencatatan database instan,
dan Admin Storage Manager.
"""

import os
import json
import uuid
from typing import Optional
from fastapi import FastAPI, Request, HTTPException, Header, Depends
from fastapi.responses import HTMLResponse, StreamingResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

import database as db
import gemini_service

load_dotenv()

app = FastAPI(
    title="Cipuy Pro - New Era New AI",
    description="Web AI Pribadi - New Era New AI + Cloud Database & Admin Storage Manager",
    version="1.0.0",
    redirect_slashes=False
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Setup direktori static dan templates
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")

try:
    os.makedirs(STATIC_DIR, exist_ok=True)
    os.makedirs(os.path.join(STATIC_DIR, "css"), exist_ok=True)
    os.makedirs(os.path.join(STATIC_DIR, "js"), exist_ok=True)
    os.makedirs(TEMPLATES_DIR, exist_ok=True)
except Exception:
    pass

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
templates = Jinja2Templates(directory=TEMPLATES_DIR)

ADMIN_SECRET_KEY = os.getenv("ADMIN_SECRET_KEY", "admin123")


# ==========================================
# PYDANTIC SCHEMAS
# ==========================================

class ChatRequest(BaseModel):
    session_id: Optional[str] = None
    prompt: str
    model: Optional[str] = "gemini-3.6-flash"


class CreateSessionRequest(BaseModel):
    title: Optional[str] = "Percakapan Baru"


class AdminVerifyRequest(BaseModel):
    secret_key: str


class AdminCleanRequest(BaseModel):
    secret_key: str
    days: Optional[int] = 30
    wipe_all: Optional[bool] = False


class LoginRequest(BaseModel):
    username: str
    password: str


class CreateUserRequest(BaseModel):
    username: str
    password: str
    role: Optional[str] = "user"
    secret_key: Optional[str] = None


class ToggleStatusRequest(BaseModel):
    status: str
    secret_key: Optional[str] = None


# ==========================================
# AUTH / SECURITY HELPER & ROUTES
# ==========================================

def verify_admin(secret_key: Optional[str] = None):
    if not secret_key or secret_key != ADMIN_SECRET_KEY:
        raise HTTPException(status_code=401, detail="Kunci otorisasi admin tidak valid.")
    return True


@app.post("/api/auth/login")
@app.post("/auth/login")
async def login_route(body: LoginRequest):
    """Autentikasi login pengguna dan admin di awal."""
    success, res = db.authenticate_user(body.username, body.password)
    if not success:
        raise HTTPException(status_code=401, detail=res)
    return {
        "success": True,
        "message": "Login berhasil.",
        "user": res,
        "secret_key": ADMIN_SECRET_KEY if res.get("role") == "admin" else ""
    }


@app.post("/api/admin/verify")
@app.post("/admin/verify")
async def verify_admin_route(body: AdminVerifyRequest):
    """Memverifikasi otentikasi login pemilik/admin."""
    verify_admin(body.secret_key)
    return {"valid": True, "message": "Otorisasi admin berhasil."}


@app.get("/api/admin/users")
@app.get("/admin/users")
async def get_admin_users(secret_key: Optional[str] = None):
    """Mendapatkan daftar semua akun pengguna terdaftar."""
    verify_admin(secret_key)
    users = db.get_all_users()
    return {"success": True, "users": users}


@app.post("/api/admin/users")
@app.post("/admin/users")
async def add_new_user(body: CreateUserRequest, secret_key: Optional[str] = None):
    """Admin membuat akun pengguna baru."""
    verify_admin(secret_key or body.secret_key)
    success, msg = db.create_user(body.username, body.password, body.role or "user")
    if not success:
        raise HTTPException(status_code=400, detail=msg)
    return {"success": True, "message": msg}


@app.patch("/api/admin/users/{username}/status")
@app.patch("/admin/users/{username}/status")
async def change_user_status(username: str, body: ToggleStatusRequest, secret_key: Optional[str] = None):
    """Admin mengaktifkan atau menonaktifkan akun user sementara."""
    verify_admin(secret_key or body.secret_key)
    success, msg = db.toggle_user_status(username, body.status, current_admin="admin")
    if not success:
        raise HTTPException(status_code=400, detail=msg)
    return {"success": True, "message": msg}


@app.delete("/api/admin/users/{username}")
@app.delete("/admin/users/{username}")
async def remove_user(username: str, secret_key: Optional[str] = None):
    """Admin menghapus akun user secara permanen."""
    verify_admin(secret_key)
    success, msg = db.delete_user(username, current_admin="admin")
    if not success:
        raise HTTPException(status_code=400, detail=msg)
    return {"success": True, "message": msg}


# ==========================================
# WEB PAGE ROUTES
# ==========================================

@app.get("/", response_class=HTMLResponse)
@app.get("/api", response_class=HTMLResponse)
@app.get("/api/", response_class=HTMLResponse)
async def home_page(request: Request):
    """Menampilkan antarmuka utama kloning Google Gemini Pro."""
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={}
    )


@app.get("/uji-coba", response_class=HTMLResponse)
@app.get("/uji_coba.html", response_class=HTMLResponse)
async def test_white_page(request: Request):
    """Menampilkan halaman uji coba latar putih dengan background maskot."""
    return templates.TemplateResponse(
        request=request,
        name="uji_coba.html",
        context={}
    )


# ==========================================
# CHAT & SESSION API
# ==========================================

@app.get("/api/sessions")
@app.get("/sessions")
async def list_sessions():
    """Mengambil daftar riwayat sesi untuk sidebar."""
    sessions = db.get_sessions()
    return {"sessions": sessions}


@app.post("/api/sessions")
@app.post("/sessions")
async def create_new_session(req: CreateSessionRequest):
    """Membuat sesi chat baru."""
    session_id = str(uuid.uuid4())
    db.ensure_session(session_id, req.title or "Percakapan Baru")
    return {"session_id": session_id, "title": req.title}


@app.get("/api/sessions/{session_id}")
@app.get("/sessions/{session_id}")
async def get_session_details(session_id: str):
    """Mengambil seluruh riwayat pesan dari sesi tertentu."""
    messages = db.get_session_messages(session_id)
    return {"session_id": session_id, "messages": messages}


@app.delete("/api/sessions/{session_id}")
@app.delete("/sessions/{session_id}")
async def delete_session(session_id: str):
    """Menghapus sebuah sesi percakapan."""
    success = db.delete_session(session_id)
    return {"success": success}


@app.post("/api/chat/stream")
@app.post("/chat/stream")
async def chat_stream(request: Request, body: ChatRequest):
    """
    Endpoint Streaming Utama:
    1. Mencatat prompt user ke Database secara instan (status: completed).
    2. Membuat record response di Database secara instan (status: pending).
    3. Memanggil Gemini Pro API dengan streaming Server-Sent Events (SSE).
    4. Setelah stream selesai, meng-update record response (status: completed + storage bytes).
    """
    client_ip = request.client.host if request.client else "127.0.0.1"
    session_id = body.session_id or str(uuid.uuid4())
    prompt = body.prompt.strip()
    model_name = body.model or os.getenv("GEMINI_MODEL", "gemini-1.5-pro")

    if not prompt:
        raise HTTPException(status_code=400, detail="Prompt tidak boleh kosong.")

    # 1. Pastikan sesi ada & catat prompt user secepat kilat
    db.ensure_session(session_id)
    user_msg_id = db.record_user_prompt(session_id, prompt, client_ip)
    db.update_session_title_if_default(session_id, prompt)

    # 2. Buat record AI pending di database secepat kilat
    model_msg_id = db.create_pending_response(session_id, model_name)

    # 3. Ambil riwayat percakapan untuk konteks multi-turn Gemini
    all_msgs = db.get_session_messages(session_id)
    gemini_history = gemini_service.format_chat_history(all_msgs)

    # 4. Stream generator
    async def sse_event_generator():
        # Kirim event metadata awal
        initial_meta = json.dumps({
            "type": "start",
            "session_id": session_id,
            "user_msg_id": user_msg_id,
            "model_msg_id": model_msg_id,
            "status": "pending"
        })
        yield f"data: {initial_meta}\n\n"

        accumulated_text = ""
        is_error = False

        try:
            async for chunk in gemini_service.stream_gemini_response(gemini_history, model_name):
                accumulated_text += chunk
                chunk_json = json.dumps({
                    "type": "chunk",
                    "text": chunk
                })
                yield f"data: {chunk_json}\n\n"
        except Exception as e:
            is_error = True
            accumulated_text += f"\n\n❌ *Error streaming*: {str(e)}"
            error_json = json.dumps({
                "type": "error",
                "message": str(e)
            })
            yield f"data: {error_json}\n\n"

        # 5. Update hasil ke database secara instan
        final_status = "error" if is_error else "completed"
        db.update_response_completed(model_msg_id, accumulated_text, final_status)

        # Kirim event selesai beserta estimasi bytes
        done_json = json.dumps({
            "type": "done",
            "model_msg_id": model_msg_id,
            "bytes": len(accumulated_text.encode("utf-8")),
            "status": final_status
        })
        yield f"data: {done_json}\n\n"

    return StreamingResponse(
        sse_event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


# ==========================================
# ADMIN STORAGE & LOG MONITORING API
# ==========================================

@app.get("/api/admin/stats")
@app.get("/admin/stats")
async def get_admin_stats(secret_key: Optional[str] = None):
    """Mendapatkan ringkasan kapasitas storage dan statistik chat."""
    verify_admin(secret_key)
    stats = db.get_storage_stats()
    return stats


@app.get("/api/admin/logs")
@app.get("/admin/logs")
async def get_admin_logs(
    secret_key: Optional[str] = None,
    query: str = "",
    limit: int = 100,
    offset: int = 0
):
    """Melihat semua riwayat pencarian/prompt user yang tersimpan di database."""
    verify_admin(secret_key)
    result = db.get_admin_logs(query=query, limit=limit, offset=offset)
    return result


@app.delete("/api/admin/logs/{message_id}")
@app.delete("/admin/logs/{message_id}")
async def delete_log_message(message_id: str, secret_key: Optional[str] = None):
    """Menghapus satu pesan tertentu dari database."""
    verify_admin(secret_key)
    success = db.delete_message(message_id)
    return {"success": success, "message_id": message_id}


@app.post("/api/admin/clean")
@app.post("/admin/clean")
async def clean_database_logs(body: AdminCleanRequest):
    """Membersihkan database untuk mengosongkan storage."""
    verify_admin(body.secret_key)
    if body.wipe_all:
        db.clear_all_data()
        return {"success": True, "message": "Semua data percakapan berhasil dibersihkan."}
    else:
        days = body.days or 30
        count = db.clear_old_logs(days=days)
        return {"success": True, "deleted_count": count, "message": f"{count} pesan lama berhasil dihapus."}


@app.get("/{full_path:path}", response_class=HTMLResponse)
async def catch_all_routes(request: Request, full_path: str):
    """Fallback router untuk SPA dan routing Vercel."""
    api_prefixes = ("api/", "auth/", "chat/", "sessions", "admin/", "static/")
    if any(full_path.startswith(prefix) for prefix in api_prefixes):
        raise HTTPException(status_code=404, detail="Not Found")
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={"admin_key_default": ADMIN_SECRET_KEY}
    )


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)

