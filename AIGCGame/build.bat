@echo off
setlocal

python -m pip install -r requirements.txt
python -m PyInstaller --noconfirm --clean yi_jian.spec

if errorlevel 1 (
    echo Build failed.
    exit /b 1
)

echo Build success: dist\YiJianYouYiJian.exe
