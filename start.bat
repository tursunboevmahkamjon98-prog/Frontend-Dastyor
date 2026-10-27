@echo off
chcp 65001 >nul
title Dastyor - ishga tushirish
cd /d "%~dp0"

echo.
echo   DASTYOR
echo   ===============================
echo.

echo   [1/4] Eski jarayonlarni yopish...
for /f "tokens=5" %%p in ('netstat -ano ^| findstr ":8009" ^| findstr LISTENING') do taskkill /PID %%p /F >nul 2>&1
for /f "tokens=5" %%p in ('netstat -ano ^| findstr ":3000" ^| findstr LISTENING') do taskkill /PID %%p /F >nul 2>&1
timeout /t 2 /nobreak >nul

if not exist "%~dp0backend\logs" mkdir "%~dp0backend\logs"

echo   [2/4] Backend...
start "Dastyor backend" /min cmd /c "cd /d "%~dp0backend" && venv313\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8009 > "%~dp0backend\logs\run-backend.log" 2>&1"

echo   [3/4] Frontend...
start "Dastyor frontend" /min cmd /c "cd /d "%~dp0frontend" && npm run dev > "%~dp0frontend\run-frontend.log" 2>&1"

echo   [4/4] Kutish (25 soniya)...
timeout /t 25 /nobreak >nul

echo.
echo   ===============================
echo   TEKSHIRUV
echo   ===============================
powershell -NoProfile -Command "try { $r = Invoke-WebRequest 'http://127.0.0.1:8009/api/health' -UseBasicParsing -TimeoutSec 5; Write-Host '   backend  (8009): ISHLAYAPTI' } catch { Write-Host '   backend  (8009): ISHLAMAYAPTI' }"
powershell -NoProfile -Command "try { $r = Invoke-WebRequest 'http://localhost:3000/' -UseBasicParsing -TimeoutSec 10; Write-Host '   frontend (3000): ISHLAYAPTI' } catch { Write-Host '   frontend (3000): ISHLAMAYAPTI' }"
echo.
echo   Agar ikkalasi ham ISHLAYAPTI bo'lsa:
echo      http://localhost:3000
echo      +992997777777  /  superadmin@123
echo.
echo   Agar ISHLAMAYAPTI bo'lsa - Claude'ga ayting,
echo   u log fayllarni o'qib sababini aytadi.
echo   ===============================
echo.
pause
