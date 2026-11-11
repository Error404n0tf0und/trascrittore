@echo off
setlocal
cd /d "%~dp0"
title Trascrittore - preparazione componenti
echo ============================================
echo    Trascrittore - by Error404.ntf
echo    Preparo Python e i componenti...
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
if not defined PY goto nopython
echo [1/4] Python trovato.

rem ---- 2. Componenti del programma ----
echo [2/4] Installo i componenti, qualche minuto...
"%PY%" -m pip install --upgrade pip --quiet
"%PY%" -m pip install --upgrade faster-whisper sounddevice
if errorlevel 1 goto errpip

rem ---- 3. Scheda video NVIDIA (se c'e') ----
nvidia-smi >nul 2>&1
if errorlevel 1 (
    echo [3/4] Nessuna scheda NVIDIA: usero' il processore.
) else (
    echo [3/4] Scheda NVIDIA trovata: installo il supporto GPU, circa 1 GB...
    "%PY%" -m pip install --upgrade nvidia-cublas-cu12 "nvidia-cudnn-cu12==9.*"
)

rem ---- 4. Avviatore senza finestra nera, usato dalle icone ----
echo [4/4] Preparo l'avvio del programma...
set "PYW="
for /f "delims=" %%i in ('call "%PY%" -c "import sys,os;print(os.path.join(os.path.dirname(sys.executable),'pythonw.exe'))"') do set "PYW=%%i"
if not defined PYW goto errpip
> "%~dp0avvia.vbs" echo CreateObject("WScript.Shell").Run """%PYW%"" ""%~dp0trascrittore.py""", 0, False

echo.
echo Tutto pronto!
exit /b 0

:nopython
echo.
echo ERRORE: non riesco a installare Python da solo.
echo Scaricalo da https://www.python.org/downloads/
echo spunta "Add Python to PATH" e poi reinstalla Trascrittore.
pause
exit /b 1

:errpip
echo.
echo ERRORE durante l'installazione dei componenti.
echo Controlla la connessione a internet e reinstalla Trascrittore.
pause
exit /b 2
