# Sentinela Treino API

Este documento descreve as APIs específicas para o banco `sentinela_treino`, que contém dados normalizados de veículos e passagens.

## 🏗️ Estrutura do Banco

### Tabela `veiculos`
- **id**: ID único do veículo
- **placa**: Placa do veículo (única)
- **marca_modelo**: Marca e modelo inferidos pela IA
- **tipo**: Tipo do veículo inferido pela IA
- **total_passagens**: Total de passagens (atualizado automaticamente)
- **primeira_passagem**: Data da primeira passagem
- **ultima_passagem**: Data da última passagem
- **cidades_visitadas**: Array de cidades únicas visitadas
- **ufs_visitadas**: Array de UFs únicas visitadas
- **sistemas_origem**: Array de sistemas origem únicos

### Tabela `passagens`
- **id**: ID único da passagem
- **veiculo_id**: Referência ao veículo (chave estrangeira)
- **dataHoraUTC**: Data e hora da passagem
- **pontoCaptura**: Ponto de captura
- **cidade**: Cidade da passagem
- **uf**: UF da passagem
- **codigoEquipamento**: Código do equipamento
- **codigoRodovia**: Código da rodovia
- **km**: Quilometragem
- **faixa**: Faixa da rodovia
- **sentido**: Sentido da passagem
- **velocidade**: Velocidade registrada
- **latitude**: Latitude (precisão aumentada)
- **longitude**: Longitude (precisão aumentada)
- **refImagem1**: Referência da primeira imagem
- **refImagem2**: Referência da segunda imagem
- **sistemaOrigem**: Sistema de origem
- **ehEquipamentoMovel**: Se é equipamento móvel
- **ehLeituraHumana**: Se é leitura humana
- **tipoInferidoIA**: Tipo inferido pela IA
- **marcaModeloInferidoIA**: Marca/modelo inferido pela IA

## 🚀 Como Iniciar

### 1. Verificar Dependências
```bash
pip install flask flask-cors psycopg sqlalchemy pandas requests
```

### 2. Iniciar Servidor
```bash
python scripts/start_sentinela_treino.py
```

### 3. Testar APIs
```bash
python scripts/test_sentinela_treino_api.py
```

## 📡 Endpoints Disponíveis

### Sistema e Saúde
- `GET /api/treino/health` - Status da API
- `GET /api/treino/info` - Informações da API

### Veículos
- `GET /api/treino/vehicles/search?q=<termo>` - Buscar veículos
- `GET /api/treino/vehicles/<id>` - Detalhes de um veículo
- `GET /api/treino/vehicles/<id>/passages` - Passagens de um veículo

### Análises e Estatísticas
- `GET /api/treino/analytics` - Análises gerais
- `GET /api/treino/dashboard` - Dados para dashboard
- `GET /api/treino/passages/analytics` - Análises de passagens

### Consultas Específicas
- `GET /api/treino/consulta_placa/<placa>` - Consulta por placa
- `GET /api/treino/municipios` - Lista de municípios

### Exportação
- `GET /api/treino/export/vehicles` - Exportar veículos (CSV)
- `GET /api/treino/export/passages/<id>` - Exportar passagens (CSV)

## 🔍 Exemplos de Uso

### Buscar Veículos
```bash
curl "http://localhost:5000/api/treino/vehicles/search?q=ABC&limit=10"
```

### Obter Detalhes de um Veículo
```bash
curl "http://localhost:5000/api/treino/vehicles/123"
```

### Consultar por Placa
```bash
curl "http://localhost:5000/api/treino/consulta_placa/ABC1234"
```

### Obter Análises Gerais
```bash
curl "http://localhost:5000/api/treino/analytics"
```

### Dashboard
```bash
curl "http://localhost:5000/api/treino/dashboard"
```

## 📊 Estrutura das Respostas

### Resposta de Veículo
```json
{
  "veiculo": {
    "id": 123,
    "placa": "ABC1234",
    "marca_modelo": "VOLKSWAGEN GOL",
    "tipo": "AUTOMOVEL",
    "total_passagens": 45,
    "primeira_passagem": "2024-01-01T10:00:00",
    "ultima_passagem": "2024-12-31T15:30:00",
    "cidades_visitadas": ["São Paulo", "Rio de Janeiro"],
    "ufs_visitadas": ["SP", "RJ"],
    "sistemas_origem": ["Sistema A", "Sistema B"]
  },
  "estatisticas": {
    "total_passagens": 45,
    "primeira_passagem": "2024-01-01T10:00:00",
    "ultima_passagem": "2024-12-31T15:30:00",
    "cidades_unicas": 2,
    "ufs_unicas": 2,
    "rodovias_unicas": 3
  },
  "top_cidades": [
    {"cidade": "São Paulo", "uf": "SP", "passagens": 25},
    {"cidade": "Rio de Janeiro", "uf": "RJ", "passagens": 20}
  ]
}
```

### Resposta de Análises
```json
{
  "estatisticas_gerais": {
    "total_veiculos": 276105,
    "total_passagens": 368367,
    "media_passagens_por_veiculo": 1.3,
    "max_passagens": 1086
  },
  "top_veiculos": [
    {
      "placa": "UNKNOWN",
      "total_passagens": 1086,
      "primeira_passagem": "2024-01-01T00:00:00",
      "ultima_passagem": "2024-12-31T23:59:59"
    }
  ],
  "distribuicao_uf": [
    {"uf": "SP", "veiculos": 50000},
    {"uf": "RJ", "veiculos": 30000}
  ]
}
```

## 🛠️ Configuração

### Variáveis de Ambiente
```bash
# Banco sentinela_treino
SENTINELA_TREINO_HOST=localhost
SENTINELA_TREINO_PORT=5432
SENTINELA_TREINO_DB=sentinela_treino
SENTINELA_TREINO_USER=postgres
SENTINELA_TREINO_PASSWORD=Jmkjmk.00
```

### Configuração Padrão
Se as variáveis de ambiente não estiverem definidas, serão usados os valores padrão:
- Host: localhost
- Port: 5432
- Database: sentinela_treino
- User: postgres
- Password: Jmkjmk.00

## 🔧 Troubleshooting

### Erro de Conexão com Banco
1. Verifique se o PostgreSQL está rodando
2. Confirme se o banco `sentinela_treino` existe
3. Verifique as credenciais de acesso

### Banco Vazio
1. Execute o script de importação:
```bash
python scripts/import_normalized_fixed.py "C:\Users\jeanm\Downloads\export.csv"
```

### Erro de Dependências
1. Instale as dependências necessárias:
```bash
pip install -r requirements.txt
```

### APIs Não Respondendo
1. Verifique se o servidor está rodando:
```bash
curl http://localhost:5000/api/treino/health
```

2. Verifique os logs do servidor para erros

## 📈 Performance

### Otimizações Implementadas
- Índices em colunas frequentemente consultadas
- Paginação em endpoints de listagem
- Cache de conexões de banco
- Serialização otimizada de datas

### Limites de Requisição
- Busca de veículos: máximo 100 resultados
- Passagens por veículo: máximo 1000 por requisição
- Exportação: máximo 10.000 registros

## 🔒 Segurança

### CORS
- Configurado para permitir requisições do frontend
- Em desenvolvimento: permite todas as origins
- Em produção: restrito a domínios específicos

### Validação
- Validação de parâmetros de entrada
- Sanitização de dados de busca
- Limites de tamanho de resposta

## 📝 Logs

### Níveis de Log
- **DEBUG**: Desenvolvimento (requisições detalhadas)
- **INFO**: Produção (eventos importantes)
- **WARNING**: Problemas não críticos
- **ERROR**: Erros que precisam atenção

### Localização dos Logs
- Desenvolvimento: Console
- Produção: Arquivo de log configurável

## 🚀 Próximos Passos

### Melhorias Planejadas
1. **Cache Redis**: Para melhorar performance
2. **Autenticação**: Sistema de autenticação JWT
3. **Rate Limiting**: Limitação de requisições por IP
4. **Monitoramento**: Métricas de performance
5. **Documentação**: Swagger/OpenAPI

### Integração com Frontend
1. **Dashboard**: Interface para visualizar análises
2. **Busca**: Interface de busca de veículos
3. **Relatórios**: Geração de relatórios personalizados
4. **Exportação**: Interface para exportar dados

## 📞 Suporte

Para suporte ou dúvidas:
1. Verifique os logs do servidor
2. Execute os testes de API
3. Consulte a documentação do banco
4. Verifique a configuração de rede

---

**Versão**: 1.0.0  
**Última atualização**: Dezembro 2024  
**Autor**: Sistema Sentinela IA

