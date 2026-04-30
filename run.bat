@echo off
setlocal enabledelayedexpansion

set "PROJECT_DIR=%~dp0"
set "PYTHON_EXE=%PROJECT_DIR%.venv\Scripts\python.exe"

if not exist "%PYTHON_EXE%" (
  echo Nao foi encontrado o Python do ambiente virtual em "%PYTHON_EXE%".
  echo Execute a criacao da venv antes de usar este script.
  exit /b 1
)

if "%~1"=="" (
  echo Uso:
  echo   run.bat "C:\Pedidos\PDF" [MaxOrders] [".\automation_config.json"] [LogLevel]
  exit /b 1
)

set "OUTPUT_DIR=%~1"
set "MAX_ORDERS=%~2"
set "CONFIG=%~3"
set "LOG_LEVEL=%~4"

if "%CONFIG%"=="" set "CONFIG=%PROJECT_DIR%automation_config.json"
if "%LOG_LEVEL%"=="" set "LOG_LEVEL=INFO"

pushd "%PROJECT_DIR%"
if "%MAX_ORDERS%"=="" (
  "%PYTHON_EXE%" -m src.main --output-dir "%OUTPUT_DIR%" --config "%CONFIG%" --log-level "%LOG_LEVEL%"
) else (
  "%PYTHON_EXE%" -m src.main --output-dir "%OUTPUT_DIR%" --config "%CONFIG%" --max-orders "%MAX_ORDERS%" --log-level "%LOG_LEVEL%"
)
set "EXIT_CODE=%ERRORLEVEL%"
popd

exit /b %EXIT_CODE%
