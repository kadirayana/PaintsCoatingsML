@echo off
REM ============================================================
REM  Paint Formulation AI - Windows kurulum
REM  Sanal ortam (venv) olusturur ve bagimliliklari yukler.
REM  Bir kez calistirmaniz yeterli.
REM ============================================================
chcp 65001 >nul
cd /d "%~dp0.."

where py >nul 2>nul
if %errorlevel%==0 (
    set "PY=py -3"
) else (
    where python >nul 2>nul
    if errorlevel 1 (
        echo [HATA] Python bulunamadi. https://www.python.org/downloads/ adresinden
        echo        Python 3.10 veya ustunu kurun ve "Add python.exe to PATH" secenegini isaretleyin.
        pause
        exit /b 1
    )
    set "PY=python"
)

if not exist venv (
    echo Sanal ortam olusturuluyor...
    %PY% -m venv venv || goto :error
)

echo Bagimliliklar yukleniyor (birkac dakika surebilir)...
venv\Scripts\python.exe -m pip install --upgrade pip || goto :error
venv\Scripts\python.exe -m pip install -r requirements.txt || goto :error

echo.
echo Kurulum tamamlandi. Uygulamayi baslatmak icin scripts\run_windows.bat dosyasini calistirin.
pause
exit /b 0

:error
echo.
echo [HATA] Kurulum basarisiz oldu. Yukaridaki mesajlari kontrol edin.
pause
exit /b 1
