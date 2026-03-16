@echo off
chcp 65001 >nul
setlocal

pushd "%~dp0" || (
    echo ERRO: nao foi possivel acessar a pasta do script.
    pause
    exit /b 1
)

echo ============================================
echo   Iniciando Consulta de Carteiras (CVM)
echo ============================================
echo.

set "PYTHON_CMD="
where python >nul 2>&1
if %errorlevel%==0 set "PYTHON_CMD=python"

if not defined PYTHON_CMD (
    where py >nul 2>&1
    if %errorlevel%==0 set "PYTHON_CMD=py -3"
)

if not defined PYTHON_CMD (
    echo ERRO: Python nao encontrado.
    echo Instale o Python e execute novamente.
    echo.
    popd
    pause
    exit /b 1
)

for /f "tokens=2 delims=:" %%a in ('ipconfig ^| findstr /c:"IPv4"') do (
    for /f "tokens=1" %%b in ("%%a") do (
        echo   Compartilhe este endereco com seu colega:
        echo.
        echo   http://%%b:8501
        echo.
    )
)

echo   Para encerrar, feche esta janela.
echo ============================================
echo.

%PYTHON_CMD% -m streamlit run 03_app_consulta.py --server.address 0.0.0.0 --server.port 8501

popd
