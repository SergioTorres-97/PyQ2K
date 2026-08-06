@echo off
cd /d %~dp0
echo Iniciando servidor Django PYQ2K...
echo Abre http://127.0.0.1:8080 en tu navegador
echo.
..\\.venv\Scripts\python.exe manage.py runserver 8080
pause
