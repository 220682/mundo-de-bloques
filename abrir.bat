@echo off
rem Abre el juego. Si el servidor ya esta corriendo, solo abre el navegador.
cd /d "%~dp0"
netstat -ano | findstr /r /c:":8766 .*LISTENING" >nul
if %errorlevel%==0 (
  start "" http://localhost:8766/juego.html
  exit /b
)
python servidor.py
