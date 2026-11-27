@echo off
REM Starts backend (8000) and frontend (3000) in two windows.
start "DineX backend" cmd /k "cd /d %~dp0..\dinex && venv\Scripts\activate && python manage.py runserver 8000"
start "DineX web" cmd /k "cd /d %~dp0..\dinex-web && npm run dev"
