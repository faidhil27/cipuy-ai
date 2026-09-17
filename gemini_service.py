"""
gemini_service.py - Layanan Komunikasi dengan Google Gemini Pro API
Mendukung streaming respon secara real-time via Server-Sent Events (SSE)
dan pemeliharaan konteks percakapan multi-turn.
"""

import os
import json
import httpx
from typing import AsyncGenerator, List, Dict, Any
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.6-flash").strip()

BASE_URL = "https://generativelanguage.googleapis.com/v1beta"


def get_headers():
    return {
        "Content-Type": "application/json"
    }


def format_chat_history(messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Mengubah riwayat pesan dari database menjadi format Google Gemini API:
    [
        {"role": "user", "parts": [{"text": "..."}]},
        {"role": "model", "parts": [{"text": "..."}]}
    ]
    """
    contents = []
    for msg in messages:
        # Hanya ambil pesan yang sudah completed
        if msg.get("status") != "completed":
            continue
            
        role = "user" if msg.get("role") == "user" else "model"
        text = msg.get("content", "").strip()
        if text:
            contents.append({
                "role": role,
                "parts": [{"text": text}]
            })
    return contents


async def stream_gemini_response(
    contents: List[Dict[str, Any]],
    model_name: str = None
) -> AsyncGenerator[str, None]:
    """
    Melakukan streaming respons dari Gemini Pro secara asinkron (SSE).
    Menghasilkan chunk teks kata-demi-kata ke frontend.
    """
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    target_model = model_name or os.getenv("GEMINI_MODEL", "gemini-1.5-pro").strip()

    if not api_key or api_key == "YOUR_GEMINI_API_KEY_HERE":
        yield (
            "⚠️ **Gemini API Key belum dikonfigurasi.**\n\n"
            "Untuk menghubungkan ke Gemini Pro pribadi Anda:\n"
            "1. Buka [Google AI Studio](https://aistudio.google.com/) dan buat API Key gratis.\n"
            "2. Buka file `.env` di folder proyek ini.\n"
            "3. Masukkan kunci Anda pada `GEMINI_API_KEY=AIzaSy...`\n"
            "4. Simpan file `.env`, lalu kirim pesan lagi."
        )
        return

    url = f"{BASE_URL}/models/{target_model}:streamGenerateContent?alt=sse&key={api_key}"

    payload = {
        "contents": contents,
        "systemInstruction": {
            "parts": [
                {
                    "text": (
                        "Nama kamu adalah Cipuy. Kamu adalah asisten AI pribadi yang sangat cerdas, "
                        "ramah, sopan, solutif, dan berpengetahuan luas. "
                        "Jika ditanya siapa namamu atau siapa kamu, jawablah bahwa kamu adalah Cipuy, asisten AI pribadi. "
                        "Berikan jawaban yang jelas, terstruktur, menggunakan format Markdown rapi dan kode program jika relevan."
                    )
                }
            ]
        },
        "generationConfig": {
            "temperature": 0.7,
            "topP": 0.95,
            "topK": 40,
            "maxOutputTokens": 8192
        }
    }

    models_to_try = [target_model]
    for alt in ["gemini-3.6-flash", "gemini-3.5-flash", "gemini-flash-latest", "gemini-3.1-flash-lite"]:
        if alt not in models_to_try:
            models_to_try.append(alt)

    async with httpx.AsyncClient(timeout=60.0) as client:
        last_error = ""
        success = False

        for current_model in models_to_try:
            url = f"{BASE_URL}/models/{current_model}:streamGenerateContent?alt=sse&key={api_key}"
            try:
                async with client.stream("POST", url, headers=get_headers(), json=payload) as response:
                    if response.status_code != 200:
                        error_detail = await response.aread()
                        try:
                            err_json = json.loads(error_detail.decode("utf-8"))
                            last_error = err_json.get("error", {}).get("message", str(error_detail))
                        except Exception:
                            last_error = error_detail.decode("utf-8")
                        # Jika 503 atau 404 atau 429, coba model berikutnya
                        if response.status_code in [503, 404, 429]:
                            continue
                        yield f"❌ **Error dari Gemini API ({response.status_code})**: {last_error}"
                        return

                    # Parse Server-Sent Events (SSE)
                    async for line in response.aiter_lines():
                        if line.startswith("data: "):
                            json_str = line[6:].strip()
                            if not json_str:
                                continue
                            try:
                                chunk_data = json.loads(json_str)
                                candidates = chunk_data.get("candidates", [])
                                if candidates:
                                    parts = candidates[0].get("content", {}).get("parts", [])
                                    for part in parts:
                                        text_piece = part.get("text", "")
                                        if text_piece:
                                            success = True
                                            yield text_piece
                            except Exception:
                                continue
                    if success:
                        return
            except httpx.ConnectError:
                yield "❌ **Gagal terhubung ke server Google Gemini.** Periksa koneksi internet Anda."
                return
            except httpx.TimeoutException:
                continue
            except Exception as e:
                yield f"❌ **Terjadi kesalahan tak terduga**: {str(e)}"
                return

        if not success:
            yield f"❌ **Gagal memproses dengan model**: {last_error}"


async def generate_gemini_response_sync(
    contents: List[Dict[str, Any]],
    model_name: str = None
) -> str:
    """Mengambil satu respons utuh tanpa streaming."""
    full_text = ""
    async for chunk in stream_gemini_response(contents, model_name):
        full_text += chunk
    return full_text
