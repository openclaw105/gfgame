@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo 正在启动本地服务器...
echo 启动后在浏览器打开: http://127.0.0.1:8790/
echo 关闭本窗口即可停止服务器。
python -m http.server 8790
pause
