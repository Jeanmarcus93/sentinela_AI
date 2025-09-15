@echo off
title Sentinela IA - Parando Servicos
color 0C

echo.
echo  ===============================================
echo  🛑 SENTINELA IA - PARANDO SERVIÇOS
echo  ===============================================
echo.

echo 🔍 Procurando processos Python (Backend)...
taskkill /f /im python.exe 2>nul
if %errorlevel% equ 0 (
    echo ✅ Processos Python finalizados
) else (
    echo ⚠️ Nenhum processo Python encontrado
)

echo.
echo 🔍 Procurando processos Node.js (Frontend)...
taskkill /f /im node.exe 2>nul
if %errorlevel% equ 0 (
    echo ✅ Processos Node.js finalizados
) else (
    echo ⚠️ Nenhum processo Node.js encontrado
)

echo.
echo 🔍 Procurando processos npm...
taskkill /f /im npm.cmd 2>nul
if %errorlevel% equ 0 (
    echo ✅ Processos npm finalizados
) else (
    echo ⚠️ Nenhum processo npm encontrado
)

echo.
echo ✅ TODOS OS SERVIÇOS FORAM PARADOS!
echo.
echo Pressione qualquer tecla para fechar esta janela...
pause > nul
