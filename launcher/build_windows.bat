@echo off
setlocal
cd /d "%~dp0\.."

echo ==========================================
echo  BUILD FSS CONTROL CENTER - WINDOWS
echo ==========================================

where py >nul 2>nul
if errorlevel 1 (
    echo Python Launcher tidak ditemukan.
    pause
    exit /b 1
)

if not exist ".venv-build\Scripts\python.exe" (
    py -3.14 -m venv .venv-build
    if errorlevel 1 goto :error
)

call ".venv-build\Scripts\activate.bat"
python -m pip install --upgrade pip
if errorlevel 1 goto :error

pip install -r be\requirements.txt
if errorlevel 1 goto :error
pip install pyinstaller
if errorlevel 1 goto :error

if not exist "fe\node_modules" (
    pushd fe
    call npm install
    if errorlevel 1 goto :error_pop
    popd
)

pushd fe
call npm run build
if errorlevel 1 goto :error_pop
popd

if not exist "fe\dist\index.html" (
    echo Build frontend tidak menghasilkan fe\dist\index.html.
    goto :error
)

pyinstaller --noconfirm --clean --onedir --windowed ^
  --name FSSControlCenter ^
  --paths be ^
  --add-data "be\app;be\app" ^
  --add-data "fe\dist;fe\dist" ^
  --collect-all fastapi ^
  --collect-all uvicorn ^
  --collect-all pandas ^
  --collect-all openpyxl ^
  --collect-all xlwings ^
  --hidden-import win32com.client ^
  --hidden-import pythoncom ^
  --hidden-import pywintypes ^
  launcher\main.py

if errorlevel 1 goto :error

powershell -NoProfile -Command "Compress-Archive -Path 'dist\FSSControlCenter\*' -DestinationPath 'dist\FSS-Control-Center-Windows.zip' -Force"
if errorlevel 1 goto :error

echo.
echo BUILD BERHASIL.
echo Folder aplikasi : dist\FSSControlCenter
echo File distribusi : dist\FSS-Control-Center-Windows.zip
echo.
pause
exit /b 0

:error_pop
popd
:error
echo.
echo BUILD GAGAL. Periksa pesan error di atas.
pause
exit /b 1
