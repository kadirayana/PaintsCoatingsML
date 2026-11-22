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
echo Veriler ve loglar %%LOCALAPPDATA%%\PaintFormulationAI klasorune yazilir.
pause
exit /b 0

:error
echo [HATA] EXE olusturulamadi.
pause
exit /b 1
