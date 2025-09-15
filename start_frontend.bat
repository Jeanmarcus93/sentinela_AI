@echo off
echo 🚀 Iniciando Frontend Sentinela IA...
echo.

cd frontend
if exist package.json (
    echo ✅ Diretório frontend encontrado
    if exist node_modules (
        echo ✅ Dependências instaladas
        echo 🎨 Iniciando servidor webpack...
        echo 📋 Frontend será disponível em: http://localhost:3000
        echo.
        npm start
    ) else (
        echo ❌ Dependências não instaladas. Execute: npm install
        pause
    )
) else (
    echo ❌ Diretório frontend não encontrado!
    pause
)
