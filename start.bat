@echo off
REM 띵조 AI 스탠드얼론 실행 (더블클릭). uv 가 의존성 자동 설치 후 서버 기동 + 브라우저 오픈.
cd /d "%~dp0backend"
uv run run.py
pause
