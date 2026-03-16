@echo off
chcp 65001 >nul
setlocal

pushd "%~dp0" || (
    echo ERRO: nao foi possivel acessar a pasta do script.
    pause
    exit /b 1
)

echo ============================================
echo   Instalar Dependencias do Sistema (CVM)
echo ============================================
echo.

if not exist requirements.txt (
    echo ERRO: arquivo requirements.txt nao encontrado nesta pasta.
    echo Pasta atual: %cd%
    echo.
    popd
    pause
    exit /b 1
)

set "PYTHON_CMD="
where python >nul 2>&1
if %errorlevel%==0 set "PYTHON_CMD=python"

if not defined PYTHON_CMD (
    where py >nul 2>&1
    if %errorlevel%==0 set "PYTHON_CMD=py -3"
)

if not defined PYTHON_CMD (
    echo ERRO: Python nao encontrado.
    echo Instale o Python: https://www.python.org/downloads/
    echo Depois tente novamente.
    echo.
    popd
    pause
    exit /b 1
)

echo Usando comando: %PYTHON_CMD%
echo.
echo Atualizando instalador (pip)...
%PYTHON_CMD% -m pip install --upgrade pip
if errorlevel 1 (
    echo.
    echo AVISO: nao foi possivel atualizar o pip. Tentando continuar...
    echo.
)

echo Instalando dependencias do requirements.txt...
%PYTHON_CMD% -m pip install -r requirements.txt
if errorlevel 1 (
    echo.
    echo ERRO: falha ao instalar dependencias.
    echo.
    popd
    pause
    exit /b 1
)

echo.
echo ============================================
echo   Instalacao concluida com sucesso.
echo   Agora execute: iniciar.bat
echo ============================================
echo.

popd
pause

