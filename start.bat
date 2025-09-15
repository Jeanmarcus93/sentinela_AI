@echo off
title Sentinela IA - Iniciando Servicos
color 0A

echo.
echo  ===============================================
echo  🚀 SENTINELA IA - SISTEMA DE DESENVOLVIMENTO
echo  ===============================================
echo.

echo 📡 Iniciando Backend (Flask) na porta 5000...
start "Sentinela Backend" cmd /k "cd /d %~dp0backend && python run.py"

echo ⏳ Aguardando 3 segundos para o backend inicializar...
timeout /t 3 /nobreak > nul

echo 🎨 Iniciando Frontend (Webpack) na porta 3000...
start "Sentinela Frontend" cmd /k "cd /d %~dp0frontend && npm start"

echo.
echo ✅ SERVIÇOS INICIADOS COM SUCESSO!
echo.
echo 📋 Backend:  http://localhost:5000
echo 📋 Frontend: http://localhost:3000
echo.
echo 💡 Para parar os serviços, feche as janelas individuais
echo.
echo Pressione qualquer tecla para fechar esta janela...
pause > nul
