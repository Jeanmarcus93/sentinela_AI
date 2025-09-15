# 🚀 Scripts de Desenvolvimento - Sentinela IA

Este diretório contém scripts para facilitar o desenvolvimento do sistema Sentinela IA.

## 📋 Scripts Disponíveis

### 🟢 **start.bat** (Windows - Recomendado)
Script principal para iniciar ambos os serviços simultaneamente.

**Como usar:**
```bash
# Duplo clique no arquivo ou execute no terminal:
start.bat
```

**O que faz:**
- ✅ Inicia o Backend (Flask) na porta 5000
- ✅ Inicia o Frontend (Webpack) na porta 3000
- ✅ Abre cada serviço em uma janela separada
- ✅ Aguarda 3 segundos entre as inicializações

### 🟡 **start_dev.bat** (Windows - Alternativo)
Versão alternativa com mais informações de debug.

### 🔵 **start_dev.ps1** (PowerShell)
Script PowerShell com tratamento de erros avançado.

**Como usar:**
```powershell
# Execute no PowerShell:
.\start_dev.ps1
```

### 🟠 **start_dev.sh** (Linux/macOS)
Script para sistemas Unix/Linux/macOS.

**Como usar:**
```bash
# Torne executável e execute:
chmod +x start_dev.sh
./start_dev.sh
```

### 🔴 **stop.bat** (Windows)
Script para parar todos os serviços.

**Como usar:**
```bash
# Duplo clique no arquivo ou execute no terminal:
stop.bat
```

**O que faz:**
- ✅ Para todos os processos Python (Backend)
- ✅ Para todos os processos Node.js (Frontend)
- ✅ Para todos os processos npm

## 🌐 URLs dos Serviços

Após executar os scripts de inicialização:

- **Backend API:** http://localhost:5000
- **Frontend:** http://localhost:3000
- **API Info:** http://localhost:5000/api/info
- **Health Check:** http://localhost:5000/api/health

## 📝 Pré-requisitos

### Backend
- ✅ Python 3.8+ instalado
- ✅ Dependências instaladas: `pip install -r backend/requirements.txt`
- ✅ Banco de dados configurado

### Frontend
- ✅ Node.js 16+ instalado
- ✅ Dependências instaladas: `npm install` (na pasta frontend)

## 🛠️ Instalação Inicial

Se for a primeira vez executando o projeto:

```bash
# 1. Instalar dependências do Backend
cd backend
pip install -r requirements.txt

# 2. Instalar dependências do Frontend
cd ../frontend
npm install

# 3. Voltar para a raiz e executar
cd ..
start.bat
```

## 🐛 Solução de Problemas

### Erro: "python não é reconhecido"
- Instale Python 3.8+ e adicione ao PATH
- Ou use `py` em vez de `python` no Windows

### Erro: "npm não é reconhecido"
- Instale Node.js 16+ e adicione ao PATH

### Porta já em uso
- Execute `stop.bat` para parar serviços anteriores
- Ou altere as portas nos arquivos de configuração

### Frontend não carrega
- Verifique se o backend está rodando na porta 5000
- Verifique o console do navegador para erros de CORS

## 📞 Suporte

Se encontrar problemas:
1. Verifique se todos os pré-requisitos estão instalados
2. Execute `stop.bat` e tente novamente
3. Verifique os logs nas janelas individuais dos serviços
4. Consulte a documentação do projeto principal
