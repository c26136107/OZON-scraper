@echo off
chcp 65001 >nul
title OZON商品采集
echo ========================================
echo   OZON商品采集系统启动
echo ========================================
echo.

cd /d "%~dp0"

REM 检查Python是否安装
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未检测到Python，请先安装Python 3.10+
    echo 下载地址: https://www.python.org/downloads/
    pause
    exit /b 1
)

REM 检查依赖是否安装
python -c "import PySide6" >nul 2>&1
if errorlevel 1 (
    echo [提示] 正在安装依赖包...
    pip install -r requirements.txt
    if errorlevel 1 (
        echo [错误] 依赖安装失败
        pause
        exit /b 1
    )
)

echo [启动] 正在启动OZON商品采集系统...
python main.py

pause