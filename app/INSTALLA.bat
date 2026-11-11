@echo off
setlocal
cd /d "%~dp0"
title Installazione Trascrittore
echo ============================================
echo    Installazione Trascrittore - by Error404.ntf
echo ============================================
echo.

rem ---- 1. Trova Python (o lo installa) ----
set "PY="
python --version >nul 2>&1 && set "PY=python"
if not defined PY if exist "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" set "PY=%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
if not defined PY (
    echo [1/4] Python non trovato: lo installo...
    winget install -e --id Python.Python.3.12 --scope user --accept-package-agreements --accept-source-agreements
)
if not defined PY if exist "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" set "PY=%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
if not defined PY (
    echo.
    echo ERRORE: non riesco a installare Python da solo.
    echo Scaricalo da https://www.python.org/downloads/
    echo spunta "Add Python to PATH" e poi rilancia INSTALLA.bat
    pause
    exit /b 1
)
echo [1/4] Python trovato.

rem ---- 2. Componenti del programma ----
echo [2/4] Installo i componenti (qualche minuto)...
"%PY%" -m pip install --upgrade pip --quiet
"%PY%" -m pip install --upgrade faster-whisper sounddevice "av<15"
if errorlevel 1 (
    echo.
    echo ERRORE durante l'installazione dei componenti. Controlla la connessione e riprova.
    pause
    exit /b 1
)

rem ---- 3. Scheda video NVIDIA (se c'e') ----
nvidia-smi >nul 2>&1
if errorlevel 1 (
    echo [3/4] Nessuna scheda NVIDIA: usero' il processore.
) else (
    echo [3/4] Scheda NVIDIA trovata: installo il supporto GPU, circa 1 GB...
    "%PY%" -m pip install --upgrade nvidia-cublas-cu12 "nvidia-cudnn-cu12==9.*"
)

rem ---- 4. Icona sul desktop ----
echo [4/4] Creo l'icona sul desktop...
for /f "delims=" %%i in ('call "%PY%" -c "import sys,os;print(os.path.join(os.path.dirname(sys.executable),'pythonw.exe'))"') do set "PYW=%%i"
powershell -NoProfile -ExecutionPolicy Bypass -Command "$s=(New-Object -ComObject WScript.Shell).CreateShortcut([Environment]::GetFolderPath('Desktop')+'\Trascrittore.lnk'); $s.TargetPath='%PYW%'; $s.Arguments='\"%~dp0trascrittore.py\"'; $s.WorkingDirectory='%~dp0'; $s.Description='Trascrittore - by Error404.ntf'; $s.IconLocation='%~dp0app.ico,0'; $s.Save()"

echo.
echo ============================================
echo    Fatto! Avvia "Trascrittore" dal desktop.
echo ============================================
pause
