"""
app.py - Server Entrypoint
Mengekspor aplikasi FastAPI utama agar kompatibel dengan Vercel & platform cloud lainnya.
"""

import os
import uvicorn
from main import app

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
