@echo off
REM One-time local setup on Windows. Needs Python 3.12+ and Node.js 20+.
cd /d "%~dp0..\dinex"
if not exist venv python -m venv venv
call venv\Scripts\activate
pip install -q --upgrade pip
pip install -q -r requirements.txt
if not exist .env copy .env.example .env
python manage.py migrate -v0
echo Loading demo data (about 2 minutes)...
python manage.py seed_demo --reset
cd /d "%~dp0..\dinex-web"
if not exist .env.local copy .env.example .env.local
call npm install --no-audit --no-fund
echo.
echo Ready. Run scripts\dev.bat   (web http://localhost:3000, API docs http://localhost:8000/api/docs/)
