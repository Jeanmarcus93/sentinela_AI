#!/bin/bash

# Sentinela IA - Script de Desenvolvimento
# Inicia Backend (Flask) e Frontend (Webpack) simultaneamente

echo "🚀 Iniciando Sentinela IA - Desenvolvimento"
echo "=========================================="
echo ""

# Função para verificar se o comando existe
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Verificar dependências
if ! command_exists python3 && ! command_exists python; then
    echo "❌ Python não encontrado!"
    exit 1
fi

if ! command_exists npm; then
    echo "❌ npm não encontrado!"
    exit 1
fi

# Determinar comando Python
PYTHON_CMD="python3"
if ! command_exists python3; then
    PYTHON_CMD="python"
fi

echo "📡 Iniciando Backend (Flask)..."
gnome-terminal --title="Sentinela Backend" -- bash -c "cd backend && $PYTHON_CMD run.py; exec bash" 2>/dev/null || \
xterm -title "Sentinela Backend" -e "cd backend && $PYTHON_CMD run.py; bash" 2>/dev/null || \
osascript -e 'tell app "Terminal" to do script "cd backend && $PYTHON_CMD run.py"' 2>/dev/null || \
echo "⚠️ Não foi possível abrir nova janela para o backend. Execute manualmente: cd backend && $PYTHON_CMD run.py"

echo "⏳ Aguardando 3 segundos..."
sleep 3

echo "🎨 Iniciando Frontend (Webpack)..."
gnome-terminal --title="Sentinela Frontend" -- bash -c "cd frontend && npm start; exec bash" 2>/dev/null || \
xterm -title "Sentinela Frontend" -e "cd frontend && npm start; bash" 2>/dev/null || \
osascript -e 'tell app "Terminal" to do script "cd frontend && npm start"' 2>/dev/null || \
echo "⚠️ Não foi possível abrir nova janela para o frontend. Execute manualmente: cd frontend && npm start"

echo ""
echo "✅ Ambos os serviços foram iniciados!"
echo "📋 Backend: http://localhost:5000"
echo "📋 Frontend: http://localhost:3000"
echo ""
echo "💡 Para parar os serviços, feche as janelas individuais"
echo ""
echo "Pressione Enter para fechar esta janela..."
read
