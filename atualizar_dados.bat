@echo off
chcp 65001 >nul
setlocal

pushd "%~dp0" || (
    echo ERRO: nao foi possivel acessar a pasta do script.
    pause
    exit /b 1
)

echo ============================================
echo   Atualizando Dados da CVM
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

echo [1/2] Baixando dados mais recentes...
%PYTHON_CMD% 01_baixar_dados.py
if errorlevel 1 (
    echo.
    echo ERRO: falha no download dos dados.
    echo.
    popd
    pause
    exit /b 1
)

echo [2/2] Processando dados...
%PYTHON_CMD% 02_processar_dados.py
if errorlevel 1 (
    echo.
    echo ERRO: falha no processamento dos dados.
    echo.
    popd
    pause
    exit /b 1
)

echo.
echo ============================================
echo   Atualizacao concluida com sucesso.
echo ============================================
echo.

popd
pause
