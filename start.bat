@echo off
REM 띵조 AI 실행 (더블클릭). uv 가 의존성 자동 설치 후 네이티브 창으로 띄움(브라우저 X).
cd /d "%~dp0backend"
uv run desktop.py
pause
