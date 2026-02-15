@echo off
setlocal

cd /d %~dp0

where python >nul 2>nul
if errorlevel 1 (
  echo [ERROR] Python не найден в PATH. Установите Python 3.9+ и отметьте "Add to PATH".
  pause
  exit /b 1
)

python launcher.py

if errorlevel 1 (
  echo.
  echo [ERROR] Лаунчер завершился с ошибкой. Проверьте сообщение выше.
  pause
  exit /b 1
)

endlocal
