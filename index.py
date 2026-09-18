import os
import sys

# Tambahkan direktori root proyek ke sys.path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from main import app as original_app


async def app(scope, receive, send):
    """
    ASGI Entrypoint untuk deployment Vercel Serverless.
    Mengatasi isu rewrite URL proxy Vercel dan memulihkan path asli
    sehingga endpoint POST/GET/DELETE/PATCH tidak memicu HTTP 405 Method Not Allowed.
    """
    if scope.get("type") == "http":
        headers = dict(scope.get("headers", []))

        # Cek apakah Vercel menyertakan header rute asli
        matched_path = (
            headers.get(b"x-matched-path")
            or headers.get(b"x-forwarded-uri")
            or headers.get(b"x-original-url")
            or headers.get(b"x-rewrite-url")
        )

        if matched_path:
            try:
                target = matched_path.decode("utf-8", errors="ignore").split("?")[0]
                if target and target not in ("/api/index.py", "/api/index"):
                    scope["path"] = target
                    scope["raw_path"] = target.encode("utf-8")
            except Exception:
                pass

        # Normalisasi fallback jika path masih bernilai file serverless Vercel
        current_path = scope.get("path", "")
        if current_path in ("/api/index.py", "/api/index"):
            scope["path"] = "/"
            scope["raw_path"] = b"/"

    await original_app(scope, receive, send)
