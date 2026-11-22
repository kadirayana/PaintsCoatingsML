@echo off
REM ============================================================
REM  Paint Formulation AI - tek dosya EXE olusturur (dist\PaintFormulationAI.exe)
REM  Once scripts\setup_windows.bat calistirilmis olmalidir.
REM ============================================================
chcp 65001 >nul
cd /d "%~dp0.."
if not exist venv\Scripts\python.exe (
    echo Once scripts\setup_windows.bat dosyasini calistirin.
    pause
    exit /b 1
)
venv\Scripts\python.exe -m PyInstaller --noconfirm --clean build_spec.spec || goto :error
echo.
echo EXE hazir: dist\PaintFormulationAI.exe
echo Not: EXE ilk calistiginda yanina data_storage, logs ve assets klasorlerini olusturur;
echo      bu yuzden yazma izni olan bir klasorde (orn. Belgeler) calistirin, Program Files'ta degil.
pause
exit /b 0

:error
echo [HATA] EXE olusturulamadi.
pause
exit /b 1
