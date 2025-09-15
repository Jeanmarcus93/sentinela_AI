# Sistema de Teste e Feedback Semântico

## Como usar o sistema

### Modo Offline (Recomendado para testes)
```bash
python semantic-feedback-system.py --offline
```

### Modo com Banco de Dados
```bash
python semantic-feedback-system.py
```

### Configuração do Banco de Dados

Se você quiser usar o banco de dados, você precisa:

1. **Instalar PostgreSQL** (se ainda não tiver)
2. **Criar o banco de dados**:
   ```sql
   CREATE DATABASE sentinela_teste;
   ```
3. **Configurar as credenciais** de uma das formas:

#### Opção 1: Variáveis de ambiente
```bash
set DB_HOST=localhost
set DB_PORT=5432
set DB_NAME=sentinela_teste
set DB_USER=postgres
set DB_PASSWORD=sua_senha_aqui
python semantic-feedback-system.py
```

#### Opção 2: Argumentos de linha de comando
```bash
python semantic-feedback-system.py --db-host localhost --db-user postgres --db-password sua_senha_aqui
```

#### Opção 3: Arquivo .env
Crie um arquivo `.env` na pasta `backend/` com:
```
DB_HOST=localhost
DB_PORT=5432
DB_NAME=sentinela_teste
DB_USER=postgres
DB_PASSWORD=sua_senha_aqui
```

## Funcionalidades

- ✅ **Classificação semântica** de relatos
- ✅ **Coleta de feedback** do usuário
- ✅ **Estatísticas** de acurácia
- ✅ **Modo offline** para testes sem banco
- ✅ **Logging estruturado**
- ✅ **Validação robusta** de entrada

## Comandos disponíveis durante execução

- Digite relatos para análise
- Digite `stats` para ver estatísticas
- Digite `quit` para sair

