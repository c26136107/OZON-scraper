@echo off
chcp 65001 >nul 2>&1
set PATH=%PATH%;C:\Program Files\Git\bin
cd /d "%~dp0"

echo ===== 开始备份 OZON商品采集 =====
echo.

:: 检查更改
git status
echo.

:: 有更改才提交
git diff --quiet
if errorlevel 1 (
    echo [发现更改，正在提交...]
    git add -A
    for /f "tokens=2-4 delims=/ " %%a in ('date /t') do set DATETIME=%%a-%%b-%%c
    for /f "tokens=1-2 delims=: " %%a in ('time /t') do set DATETIME=!DATETIME! %%a%%b
    git commit -m "OZON商品采集 - 更新备份 !DATETIME!"
    echo [正在推送到GitHub...]
    git push origin main
    echo.
    echo ===== 备份完成 =====
) else (
    echo 无更改，跳过提交。
    echo 如需强制推送，请运行: git push origin main --force
)

echo.
pause