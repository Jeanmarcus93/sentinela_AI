@echo off
echo 🚀 Iniciando Sentinela IA - Backend e Frontend
echo ==============================================
echo.

echo 📡 Iniciando Backend (Flask)...
start "Sentinela Backend" cmd /k "cd backend && python run.py"

echo ⏳ Aguardando 5 segundos para o backend inicializar...
timeout /t 5 /nobreak > nul

echo 🎨 Iniciando Frontend (Webpack)...
start "Sentinela Frontend" cmd /k ".\start_frontend.bat"

echo.
echo ✅ Ambos os serviços foram iniciados!
echo 📋 Backend: http://localhost:5000
echo 📋 Frontend: http://localhost:3000
echo.
echo Pressione qualquer tecla para fechar esta janela...
pause > nul
