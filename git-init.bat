chcp 65001 >nul
set PATH=%PATH%;C:\Program Files\Git\bin
cd /d "%~dp0"
git config --global core.autocrlf false
git config --global core.quotepath false
git init
git add -A
git commit -m "OZON商品采集 - v1.0 初始版本"
git status
echo.
echo 完成!
pause