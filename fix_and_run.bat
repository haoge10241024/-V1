@echo off
echo 🔄 正在停止所有Python进程...
taskkill /F /IM python.exe >nul 2>&1

echo ⏳ 等待进程完全停止...
timeout /t 3 >nul

echo 🚀 启动期货持仓分析系统（优化版）...
echo.
echo 📌 重要提示：
echo    - 如果出现邮箱输入提示，直接按 Enter 跳过
echo    - 应用将在浏览器中自动打开
echo    - 地址：http://localhost:8502
echo.

set STREAMLIT_BROWSER_GATHER_USAGE_STATS=false
python -m streamlit run app_streamlit_optimized.py --server.port 8502

pause 