@echo off
title Cipuy Pro Web AI Launcher
echo ===================================================
echo     MENYALAKAN CIPUY PRO & CLOUDFLARE TUNNEL
echo ===================================================
echo.
echo 1. Menjalankan Server Cipuy di http://localhost:8000 ...
start /B python main.py
timeout /t 3 >nul
echo.
echo 2. Menjalankan Tunnel Publik Cloudflare...
echo Link publik Anda akan muncul di bawah ini:
echo ---------------------------------------------------
"C:\Program Files (x86)\cloudflared\cloudflared.exe" tunnel --url http://localhost:8000
pause

