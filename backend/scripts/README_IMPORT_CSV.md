# Importação de Dados CSV para Sentinela Treino

Este guia explica como importar dados CSV para o banco `sentinela_treino`, especificamente para a tabela `passagens`.

## 📋 Estrutura Esperada do CSV

A tabela `passagens` espera as seguintes colunas:

| Coluna | Tipo | Obrigatório | Descrição |
|--------|------|-------------|-----------|
| `dataHoraUTC` | TIMESTAMP | ✅ Sim | Data e hora em UTC |
| `placa` | VARCHAR(10) | ✅ Sim | Placa do veículo |
| `pontoCaptura` | VARCHAR(200) | ❌ Não | Ponto de captura |
| `cidade` | VARCHAR(200) | ❌ Não | Cidade |
| `uf` | VARCHAR(5) | ❌ Não | Unidade Federativa |
| `codigoEquipamento` | VARCHAR(100) | ❌ Não | Código do equipamento |
| `codigoRodovia` | VARCHAR(50) | ❌ Não | Código da rodovia |
| `km` | NUMERIC(10,3) | ❌ Não | Quilometragem |
| `faixa` | INTEGER | ❌ Não | Faixa da rodovia |
| `sentido` | VARCHAR(50) | ❌ Não | Sentido da via |
| `velocidade` | NUMERIC(5,2) | ❌ Não | Velocidade registrada |
| `latitude` | NUMERIC(10,8) | ❌ Não | Latitude GPS |
| `longitude` | NUMERIC(11,8) | ❌ Não | Longitude GPS |
| `refImagem1` | VARCHAR(500) | ❌ Não | Referência da imagem 1 |
| `refImagem2` | VARCHAR(500) | ❌ Não | Referência da imagem 2 |
| `sistemaOrigem` | VARCHAR(100) | ❌ Não | Sistema de origem |
| `ehEquipamentoMovel` | BOOLEAN | ❌ Não | Se é equipamento móvel |
| `ehLeituraHumana` | BOOLEAN | ❌ Não | Se é leitura humana |
| `tipoInferidoIA` | VARCHAR(100) | ❌ Não | Tipo inferido por IA |
| `marcaModeloInferidoIA` | VARCHAR(200) | ❌ Não | Marca/modelo inferido por IA |

## 🚀 Scripts Disponíveis

### 1. Script Completo (`import_csv.py`)

Script avançado com análise automática e mapeamento de colunas.

```bash
# Analisar apenas (não importar)
python scripts/import_csv.py dados.csv --analyze-only

# Importar com análise automática
python scripts/import_csv.py dados.csv

# Importar com lote personalizado
python scripts/import_csv.py dados.csv --batch-size 500

# Verificar dados já importados
python scripts/import_csv.py dados.csv --verify
```

**Recursos:**
- ✅ Análise automática da estrutura do CSV
- ✅ Mapeamento inteligente de colunas
- ✅ Importação em lotes para arquivos grandes
- ✅ Tratamento de erros
- ✅ Estatísticas detalhadas
- ✅ Verificação pós-importação

### 2. Script Simples (`import_simple.py`)

Script básico para importação rápida.

```bash
python scripts/import_simple.py dados.csv
```

**Recursos:**
- ✅ Importação direta
- ✅ Mapeamento básico de colunas
- ✅ Ideal para arquivos pequenos

## 📊 Exemplo de Uso

### Passo 1: Preparar o CSV

Certifique-se de que seu CSV tem pelo menos as colunas obrigatórias:
- `dataHoraUTC` (formato: YYYY-MM-DD HH:MM:SS)
- `placa` (formato: ABC1234)

### Passo 2: Analisar o Arquivo

```bash
python scripts/import_csv.py meu_arquivo.csv --analyze-only
```

Isso mostrará:
- Colunas encontradas
- Mapeamento proposto
- Primeiras linhas do arquivo

### Passo 3: Importar os Dados

```bash
python scripts/import_csv.py meu_arquivo.csv
```

### Passo 4: Verificar a Importação

```bash
python scripts/import_csv.py meu_arquivo.csv --verify
```

## 🔧 Mapeamento de Colunas

O script reconhece automaticamente variações de nomes de colunas:

| Coluna do Banco | Nomes Reconhecidos |
|-----------------|-------------------|
| `dataHoraUTC` | datahorautc, data_hora_utc, timestamp, datahora |
| `placa` | placa, plate, matricula |
| `cidade` | cidade, city, municipio |
| `uf` | uf, estado, state |
| `velocidade` | velocidade, speed, vel |
| `latitude` | latitude, lat |
| `longitude` | longitude, lng, lon |

## 📝 Formato de Dados

### Datas
- Formato esperado: `YYYY-MM-DD HH:MM:SS`
- Exemplo: `2024-01-15 10:30:00`

### Valores Booleanos
- `true`, `false`, `1`, `0`, `sim`, `não`

### Valores Nulos
- Células vazias, `NULL`, `null`, `''`

## ⚠️ Considerações Importantes

### Tamanho do Arquivo
- Arquivos grandes (>100MB): Use `--batch-size` menor
- Arquivos pequenos (<10MB): Use o script simples

### Performance
- Importação em lotes é mais eficiente
- Índices são criados automaticamente
- Transações são commitadas por lote

### Tratamento de Erros
- Linhas com erro são puladas
- Logs detalhados são gerados
- Estatísticas de sucesso/erro são mostradas

## 🧪 Teste com Dados de Exemplo

Use o arquivo de exemplo incluído:

```bash
python scripts/import_simple.py scripts/exemplo_passagens.csv
```

## 🔍 Verificação Pós-Importação

Após importar, você pode verificar os dados:

```sql
-- Conectar ao banco
\c sentinela_treino

-- Contar registros
SELECT COUNT(*) FROM passagens;

-- Ver últimas importações
SELECT placa, cidade, uf, dataHoraUTC 
FROM passagens 
ORDER BY dataHoraUTC DESC 
LIMIT 10;

-- Estatísticas por cidade
SELECT cidade, uf, COUNT(*) as total
FROM passagens 
GROUP BY cidade, uf 
ORDER BY total DESC;
```

## 🚨 Solução de Problemas

### Erro de Conexão
```
❌ Erro ao conectar: connection failed
```
**Solução:** Verifique se o PostgreSQL está rodando e as credenciais estão corretas.

### Erro de Mapeamento
```
❌ Nenhuma coluna foi mapeada!
```
**Solução:** Verifique se o CSV tem pelo menos `dataHoraUTC` e `placa`.

### Erro de Formato de Data
```
❌ Erro na linha X: invalid input syntax for type timestamp
```
**Solução:** Verifique o formato das datas no CSV.

### Erro de Memória
```
❌ MemoryError
```
**Solução:** Use `--batch-size` menor ou divida o arquivo.

## 📞 Suporte

Para problemas:
1. Verifique os logs do script
2. Teste com o arquivo de exemplo
3. Confirme a estrutura do CSV
4. Verifique as permissões do banco

