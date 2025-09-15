# Script de Criação de Banco PostgreSQL

Este script cria um novo banco de dados PostgreSQL com a estrutura completa necessária para o sistema Sentinela IA, incluindo a tabela `passagens` com todas as colunas especificadas.

## Estrutura da Tabela Passagens

A tabela `passagens` será criada com as seguintes colunas:

| Coluna | Tipo | Descrição |
|--------|------|-----------|
| `id` | SERIAL PRIMARY KEY | ID único |
| `dataHoraUTC` | TIMESTAMP | Data e hora em UTC |
| `placa` | VARCHAR(10) | Placa do veículo |
| `pontoCaptura` | VARCHAR(200) | Ponto de captura |
| `cidade` | VARCHAR(200) | Cidade |
| `uf` | VARCHAR(5) | Unidade Federativa |
| `codigoEquipamento` | VARCHAR(100) | Código do equipamento |
| `codigoRodovia` | VARCHAR(50) | Código da rodovia |
| `km` | NUMERIC(10,3) | Quilometragem |
| `faixa` | INTEGER | Faixa da rodovia |
| `sentido` | VARCHAR(50) | Sentido da via |
| `velocidade` | NUMERIC(5,2) | Velocidade registrada |
| `latitude` | NUMERIC(10,8) | Latitude GPS |
| `longitude` | NUMERIC(11,8) | Longitude GPS |
| `refImagem1` | VARCHAR(500) | Referência da imagem 1 |
| `refImagem2` | VARCHAR(500) | Referência da imagem 2 |
| `sistemaOrigem` | VARCHAR(100) | Sistema de origem |
| `ehEquipamentoMovel` | BOOLEAN | Se é equipamento móvel |
| `ehLeituraHumana` | BOOLEAN | Se é leitura humana |
| `tipoInferidoIA` | VARCHAR(100) | Tipo inferido por IA |
| `marcaModeloInferidoIA` | VARCHAR(200) | Marca/modelo inferido por IA |
| `criado_em` | TIMESTAMP | Data de criação |
| `atualizado_em` | TIMESTAMP | Data de atualização |

## Como Usar

### Opção 1: Script Interativo (Windows)

```bash
# Execute o arquivo .bat
scripts\create_new_db.bat
```

### Opção 2: Linha de Comando

```bash
# Navegue até o diretório backend
cd backend

# Execute o script Python
python scripts\create_database.py --db-name "meu_novo_banco" --host localhost --port 5432 --user postgres --password "sua_senha"
```

### Opção 3: Com Arquivo de Configuração

1. Copie o arquivo de exemplo:
```bash
cp scripts\database_config_example.env .env
```

2. Edite o arquivo `.env` com suas configurações

3. Execute o script:
```bash
python scripts\create_database.py --db-name "meu_banco"
```

## Parâmetros do Script

| Parâmetro | Obrigatório | Padrão | Descrição |
|-----------|-------------|--------|-----------|
| `--db-name` | ✅ Sim | - | Nome do banco de dados |
| `--host` | ❌ Não | localhost | Host do PostgreSQL |
| `--port` | ❌ Não | 5432 | Porta do PostgreSQL |
| `--user` | ❌ Não | postgres | Usuário do PostgreSQL |
| `--password` | ❌ Não | Jmkjmk.00 | Senha do PostgreSQL |
| `--force` | ❌ Não | False | Forçar recriação se existir |

## Tabelas Criadas

O script cria as seguintes tabelas:

1. **veiculos** - Informações dos veículos
2. **pessoas** - Pessoas relacionadas aos veículos
3. **passagens** - Registros de passagens (tabela principal)
4. **ocorrencias** - Ocorrências policiais
5. **apreensoes** - Apreensões de drogas/armas
6. **municipios** - Municípios do Brasil
7. **cache_analises** - Cache de análises
8. **logs_analise** - Logs de análises

## Índices Criados

O script cria índices otimizados para:

- Consultas por data (`dataHoraUTC`)
- Consultas por placa (`placa`)
- Consultas por cidade (`cidade`)
- Consultas por UF (`uf`)
- Consultas por rodovia (`codigoRodovia`)
- Consultas por equipamento (`codigoEquipamento`)
- Consultas por sistema origem (`sistemaOrigem`)
- Consultas compostas (`placa + dataHoraUTC`)

## Dados Iniciais

O script insere municípios básicos do Brasil, incluindo:

- **Cidades de fronteira**: Foz do Iguaçu, Ponta Porã, Corumbá, Uruguaiana, etc.
- **Capitais**: São Paulo, Rio de Janeiro, Brasília, etc.

## Exemplo de Uso Completo

```bash
# Criar banco para desenvolvimento
python scripts\create_database.py --db-name "sentinela_dev" --host localhost --port 5432 --user postgres --password "minha_senha"

# Criar banco para produção
python scripts\create_database.py --db-name "sentinela_prod" --host "192.168.1.100" --port 5432 --user "sentinela_user" --password "senha_forte"
```

## Verificação

Após criar o banco, você pode verificar se tudo foi criado corretamente:

```sql
-- Conectar ao banco criado
\c seu_nome_do_banco

-- Verificar tabelas
\dt

-- Verificar estrutura da tabela passagens
\d passagens

-- Verificar índices
\di

-- Contar registros
SELECT COUNT(*) FROM municipios;
```

## Troubleshooting

### Erro de Conexão
- Verifique se o PostgreSQL está rodando
- Confirme host, porta, usuário e senha
- Verifique se o usuário tem permissão para criar bancos

### Erro de Permissão
- Execute como superusuário do PostgreSQL
- Ou conceda permissões ao usuário:
```sql
GRANT CREATEDB TO seu_usuario;
```

### Banco Já Existe
- Use `--force` para recriar
- Ou escolha outro nome para o banco

## Logs

O script gera logs detalhados mostrando:
- ✅ Sucessos
- ❌ Erros
- 📋 Progresso da criação
- 📊 Informações finais

## Suporte

Para problemas ou dúvidas:
1. Verifique os logs do script
2. Confirme as configurações do PostgreSQL
3. Teste a conexão manualmente
4. Consulte a documentação do PostgreSQL

