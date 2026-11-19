@echo off
setlocal
cd /d "%~dp0"
title VISION AI - Live Monitoring
color 0B
echo ============================================================
echo                 VISION AI - LIVE PLATFORM
echo ============================================================
where python >nul 2>nul || (echo ERROR: Instala Python 3.11 de 64 bits y activa Add Python to PATH.& pause & exit /b 1)
where node >nul 2>nul || (echo ERROR: Instala Node.js 20 o superior.& pause & exit /b 1)
where npm >nul 2>nul || (echo ERROR: npm no esta disponible. Reinstala Node.js.& pause & exit /b 1)
if not exist "backend\.venv\Scripts\python.exe" (
  echo [1/4] Creando entorno Python...
  cd backend
  python -m venv .venv
  if errorlevel 1 (echo ERROR creando entorno Python.& pause & exit /b 1)
  call .venv\Scripts\activate
  python -m pip install --upgrade pip
  pip install -r requirements.txt
  if errorlevel 1 (echo ERROR instalando dependencias Python. Revisa Internet y vuelve a ejecutar.& pause & exit /b 1)
  cd ..
) else (call backend\.venv\Scripts\activate)
echo [2/4] Iniciando API y motor YOLO...
start "VISION AI - API" cmd /k "cd /d ""%~dp0backend"" && call .venv\Scripts\activate && uvicorn app.main:app --reload --host 127.0.0.1 --port 8000"
echo [3/4] Instalando dependencias de interfaz (primera vez)...
cd frontend
if not exist node_modules (
  npm install
  if errorlevel 1 (echo ERROR instalando dependencias web. Revisa Internet y vuelve a ejecutar.& pause & exit /b 1)
)
echo [4/4] Iniciando interfaz web...
start "VISION AI - WEB" cmd /k "cd /d ""%~dp0frontend"" && npm run dev"
cd ..
timeout /t 7 >nul
start http://localhost:5173
echo.
echo VISION AI esta iniciando. Mantén abiertas las ventanas de API y WEB.
echo La primera ejecucion puede descargar los pesos de YOLO automaticamente.
echo Usa localhost para permitir el acceso a la camara del navegador.
pause
