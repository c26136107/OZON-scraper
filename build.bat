@echo off
chcp 65001 >nul
title OZON商品采集 - 打包为EXE
echo ========================================
echo   OZON商品采集 - 打包为独立EXE
echo ========================================
echo.

cd /d "%~dp0"

REM 检查Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未检测到Python，请先安装Python 3.10+
    pause
    exit /b 1
)

REM 安装pyinstaller
pip show pyinstaller >nul 2>&1
if errorlevel 1 (
    echo [提示] 正在安装PyInstaller...
    pip install pyinstaller
)

REM 打包
echo [打包] 正在打包为独立EXE...
pyinstaller --onefile --windowed --name "OZON商品采集" --noconfirm main.py

echo.
echo ========================================
echo   打包完成！
echo   EXE文件位置: dist\OZON商品采集.exe
echo ========================================
pause