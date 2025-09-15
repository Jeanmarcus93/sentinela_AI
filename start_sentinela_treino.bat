@echo off
echo 🛡️ Iniciando Sentinela IA - Banco de Treino
echo ================================================

echo.
echo 📋 Verificando dependências...

REM Verificar se o backend está no ambiente virtual
if not exist "backend\venv\Scripts\activate.bat" (
    echo ❌ Ambiente virtual do backend não encontrado
    echo    Execute: cd backend && python -m venv venv
    pause
    exit /b 1
)

REM Verificar se o frontend tem node_modules
if not exist "frontend\node_modules" (
    echo ❌ Dependências do frontend não encontradas
    echo    Execute: cd frontend && npm install
    pause
    exit /b 1
)

echo ✅ Dependências verificadas
echo.

echo 🚀 Iniciando Backend...
start "Sentinela IA Backend" cmd /k "cd backend && .\venv\Scripts\activate.bat && python run.py"

echo ⏳ Aguardando backend inicializar...
timeout /t 5 /nobreak > nul

echo 🌐 Iniciando Frontend...
start "Sentinela IA Frontend" cmd /k "cd frontend && set NODE_OPTIONS=--no-deprecation && npm start"

echo.
echo ✅ Sistema iniciado com sucesso!
echo.
echo 📌 URLs disponíveis:
echo    Backend:  http://localhost:5000
echo    Frontend: http://localhost:3000
echo    Banco Treino: http://localhost:3000/index_treino.html
echo.
echo 🛑 Para parar: Feche as janelas do terminal
echo.
pause

