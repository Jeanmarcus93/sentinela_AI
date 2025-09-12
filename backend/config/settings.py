# config/settings.py
"""
Configurações principais do Sistema de Análise de Placas
Inclui configurações de banco de dados, Flask e sistema
"""

import os
from pathlib import Path
from sqlalchemy import create_engine, text
from typing import Dict, Any, Optional

# =============================================================================
# CONFIGURAÇÕES DE BANCO DE DADOS
# =============================================================================

# Banco principal (sistema)
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", "5432"))
DB_NAME = os.getenv("DB_NAME", "sentinela_teste")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "Jmkjmk.00")

# Banco de veículos (dados externos)
VEICULOS_DB_NAME = os.getenv("VEICULOS_DB_NAME", "veiculos_db")
VEICULOS_DB_USER = os.getenv("VEICULOS_DB_USER", "postgres")
VEICULOS_DB_PASSWORD = os.getenv("VEICULOS_DB_PASSWORD", "Jmkjmk.00")
VEICULOS_DB_HOST = os.getenv("VEICULOS_DB_HOST", "localhost")
VEICULOS_DB_PORT = int(os.getenv("VEICULOS_DB_PORT", "5432"))

# Dicionários de configuração para compatibilidade
DB_CONFIG = {
    "host": DB_HOST,
    "port": DB_PORT,
    "dbname": DB_NAME,
    "user": DB_USER,
    "password": DB_PASSWORD
}

VEICULOS_DB_CONFIG = {
    "host": VEICULOS_DB_HOST,
    "port": VEICULOS_DB_PORT,
    "dbname": VEICULOS_DB_NAME,
    "user": VEICULOS_DB_USER,
    "password": VEICULOS_DB_PASSWORD
}

# =============================================================================
# CONFIGURAÇÕES DO FLASK
# =============================================================================

class Config:
    """Configuração base do Flask"""
    
    # Configurações básicas
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
    DEBUG = os.getenv('FLASK_DEBUG', 'True').lower() in ('true', '1', 'yes')
    TESTING = False
    
    # JSON
    JSON_SORT_KEYS = False
    JSONIFY_PRETTYPRINT_REGULAR = True
    JSON_AS_ASCII = False
    
    # Upload de arquivos
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max
    UPLOAD_EXTENSIONS = ['.csv', '.xlsx', '.json']
    
    # Session
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    
    # CORS
    CORS_ORIGINS = ["http://localhost:3000", "http://localhost:5000"]
    
    # Cache
    CACHE_TYPE = "simple"
    CACHE_DEFAULT_TIMEOUT = 300
    
    # Rate Limiting
    RATELIMIT_ENABLED = True
    RATELIMIT_DEFAULT = "100 per hour"
    
    @staticmethod
    def init_app(app):
        """Inicialização específica da aplicação"""
        pass

class DevelopmentConfig(Config):
    """Configuração para desenvolvimento"""
    DEBUG = True
    TESTING = False
    
    # Logs mais verbosos
    LOG_LEVEL = 'DEBUG'
    
    # Sem HTTPS obrigatório
    SESSION_COOKIE_SECURE = False
    
    # CORS mais permissivo
    CORS_ORIGINS = ["*"]
    
    # Cache desabilitado
    CACHE_TYPE = "null"

class TestingConfig(Config):
    """Configuração para testes"""
    TESTING = True
    DEBUG = True
    
    # Base de dados em memória para testes
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    
    # Desabilitar CSRF para testes
    WTF_CSRF_ENABLED = False
    
    # Cache desabilitado
    CACHE_TYPE = "null"
    
    # Rate limiting desabilitado
    RATELIMIT_ENABLED = False

class ProductionConfig(Config):
    """Configuração para produção"""
    DEBUG = False
    TESTING = False
    
    # Logs menos verbosos
    LOG_LEVEL = 'INFO'
    
    # Segurança reforçada
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    
    # Rate limiting mais restrito
    RATELIMIT_DEFAULT = "50 per hour"
    
    @classmethod
    def init_app(cls, app):
        Config.init_app(app)
        
        # Log para syslog em produção
        import logging
        from logging.handlers import SysLogHandler
        
        syslog_handler = SysLogHandler()
        syslog_handler.setLevel(logging.WARNING)
        app.logger.addHandler(syslog_handler)

# Mapeamento de configurações
config_map = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}

def get_config(config_name: Optional[str] = None) -> Config:
    """Retorna configuração baseada no ambiente"""
    if config_name is None:
        config_name = os.getenv('FLASK_ENV', 'development')
    
    return config_map.get(config_name, DevelopmentConfig)

# =============================================================================
# FUNÇÕES DE BANCO DE DADOS
# =============================================================================

def get_engine(db_name: str = DB_NAME, user: str = DB_USER, 
               password: str = DB_PASSWORD, host: str = DB_HOST, 
               port: int = DB_PORT):
    """Retorna um engine SQLAlchemy para o banco especificado"""
    conn_str = f"postgresql+psycopg://{user}:{password}@{host}:{port}/{db_name}"
    return create_engine(
        conn_str, 
        echo=False, 
        future=True,
        pool_pre_ping=True,
        pool_recycle=3600,
        pool_size=10,
        max_overflow=20
    )

def get_veiculos_engine():
    """Engine específico para o banco de veículos"""
    return get_engine(
        db_name=VEICULOS_DB_NAME,
        user=VEICULOS_DB_USER, 
        password=VEICULOS_DB_PASSWORD,
        host=VEICULOS_DB_HOST,
        port=VEICULOS_DB_PORT
    )

def validate_db_connection(db_config: Dict[str, Any]) -> bool:
    """Valida conectividade com o banco de dados"""
    try:
        engine = create_engine(
            f"postgresql+psycopg://{db_config['user']}:{db_config['password']}"
            f"@{db_config['host']}:{db_config['port']}/{db_config['dbname']}"
        )
        
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        
        return True
    except Exception as e:
        print(f"❌ Erro de conexão com banco {db_config['dbname']}: {e}")
        return False

# =============================================================================
# CRIAÇÃO DE TABELAS
# =============================================================================

def criar_tabelas():
    """Cria as tabelas necessárias no banco, se não existirem"""
    print("📋 Criando/verificando estrutura do banco de dados...")
    
    engine = get_engine()
    
    with engine.connect() as conn:
        # Tabela de veículos
        conn.execute(text("""
        CREATE TABLE IF NOT EXISTS veiculos (
            id SERIAL PRIMARY KEY,
            placa VARCHAR(10) UNIQUE NOT NULL,
            marca_modelo VARCHAR(200),
            cor VARCHAR(50),
            tipo VARCHAR(100),
            ano_modelo INTEGER,
            local_emplacamento VARCHAR(100),
            criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            atualizado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """))
        
        # Índices para veículos
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_veiculos_placa ON veiculos(placa)"))
        
        # Tabela de pessoas
        conn.execute(text("""
        CREATE TABLE IF NOT EXISTS pessoas (
            id SERIAL PRIMARY KEY,
            nome VARCHAR(200),
            cpf_cnpj VARCHAR(20) UNIQUE,
            veiculo_id INTEGER REFERENCES veiculos(id) ON DELETE CASCADE,
            relevante BOOLEAN DEFAULT TRUE,
            condutor BOOLEAN DEFAULT FALSE,
            possuidor BOOLEAN DEFAULT FALSE,
            criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """))
        
        # Índices para pessoas
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_pessoas_cpf_cnpj ON pessoas(cpf_cnpj)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_pessoas_veiculo ON pessoas(veiculo_id)"))
        
        # Tabela de passagens
        conn.execute(text("""
        CREATE TABLE IF NOT EXISTS passagens (
            id SERIAL PRIMARY KEY,
            veiculo_id INTEGER REFERENCES veiculos(id) ON DELETE CASCADE,
            datahora TIMESTAMP NOT NULL,
            municipio VARCHAR(200),
            estado VARCHAR(5),
            rodovia VARCHAR(100),
            ilicito_ida BOOLEAN DEFAULT FALSE,
            ilicito_volta BOOLEAN DEFAULT FALSE,
            criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """))
        
        # Índices para passagens
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_passagens_veiculo ON passagens(veiculo_id)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_passagens_datahora ON passagens(datahora)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_passagens_municipio ON passagens(municipio)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_passagens_ilicito_ida ON passagens(ilicito_ida) WHERE ilicito_ida = TRUE"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_passagens_ilicito_volta ON passagens(ilicito_volta) WHERE ilicito_volta = TRUE"))
        
        # Enum para tipos de apreensão
        conn.execute(text("""
        DO $$ BEGIN
            CREATE TYPE tipo_apreensao_enum AS ENUM (
                'Maconha', 'Skunk', 'Cocaina', 'Crack', 'Sintéticos', 'Arma'
            );
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$
        """))
        
        # Tabela de ocorrências
        conn.execute(text("""
        CREATE TABLE IF NOT EXISTS ocorrencias (
            id SERIAL PRIMARY KEY,
            veiculo_id INTEGER REFERENCES veiculos(id) ON DELETE CASCADE,
            tipo VARCHAR(50) NOT NULL,
            datahora TIMESTAMP NOT NULL,
            datahora_fim TIMESTAMP,
            relato TEXT,
            ocupantes JSONB,
            presos JSONB,
            apreensoes JSONB,
            veiculos JSONB,
            criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            atualizado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """))
        
        # Índices para ocorrências
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_ocorrencias_veiculo ON ocorrencias(veiculo_id)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_ocorrencias_datahora ON ocorrencias(datahora)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_ocorrencias_tipo ON ocorrencias(tipo)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_ocorrencias_relato ON ocorrencias USING gin(to_tsvector('portuguese', relato)) WHERE relato IS NOT NULL"))
        
        # Tabela normalizada de apreensões
        conn.execute(text("""
        CREATE TABLE IF NOT EXISTS apreensoes (
            id SERIAL PRIMARY KEY,
            ocorrencia_id INTEGER REFERENCES ocorrencias(id) ON DELETE CASCADE,
            tipo tipo_apreensao_enum NOT NULL,
            quantidade NUMERIC(10,3) NOT NULL,
            unidade VARCHAR(10) NOT NULL,
            criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """))
        
        # Índices para apreensões
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_apreensoes_ocorrencia ON apreensoes(ocorrencia_id)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_apreensoes_tipo ON apreensoes(tipo)"))
        
        # Tabela de municípios (para normalização)
        conn.execute(text("""
        CREATE TABLE IF NOT EXISTS municipios (
            id SERIAL PRIMARY KEY,
            nome VARCHAR(200) NOT NULL,
            uf VARCHAR(5) NOT NULL,
            codigo_ibge VARCHAR(10),
            regiao VARCHAR(50),
            eh_fronteira BOOLEAN DEFAULT FALSE,
            eh_suspeito BOOLEAN DEFAULT FALSE,
            criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """))
        
        # Índices para municípios
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_municipios_nome ON municipios(nome)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_municipios_uf ON municipios(uf)"))
        conn.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS idx_municipios_nome_uf ON municipios(nome, uf)"))
        
        # Tabela para cache de análises (otimização)
        conn.execute(text("""
        CREATE TABLE IF NOT EXISTS cache_analises (
            id SERIAL PRIMARY KEY,
            chave_cache VARCHAR(64) UNIQUE NOT NULL,
            placa VARCHAR(10) NOT NULL,
            resultado JSONB NOT NULL,
            data_calculo TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            valido_ate TIMESTAMP DEFAULT (CURRENT_TIMESTAMP + INTERVAL '24 hours')
        )
        """))
        
        # Índices para cache
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_cache_chave ON cache_analises(chave_cache)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_cache_placa ON cache_analises(placa)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_cache_valido_ate ON cache_analises(valido_ate)"))
        
        # Tabela para logs de análise (auditoria)
        conn.execute(text("""
        CREATE TABLE IF NOT EXISTS logs_analise (
            id SERIAL PRIMARY KEY,
            placa VARCHAR(10) NOT NULL,
            tipo_analise VARCHAR(50) NOT NULL,
            tempo_execucao NUMERIC(8,3),
            sucesso BOOLEAN DEFAULT TRUE,
            erro TEXT,
            metadados JSONB,
            criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """))
        
        # Índices para logs
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_logs_placa ON logs_analise(placa)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_logs_tipo ON logs_analise(tipo_analise)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_logs_criado_em ON logs_analise(criado_em)"))
        
        # Trigger para atualizar campo atualizado_em
        conn.execute(text("""
        CREATE OR REPLACE FUNCTION atualizar_timestamp()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.atualizado_em = CURRENT_TIMESTAMP;
            RETURN NEW;
        END;
        $$ language 'plpgsql'
        """))
        
        # Aplicar trigger nas tabelas relevantes
        for tabela in ['veiculos', 'ocorrencias']:
            conn.execute(text(f"""
            DROP TRIGGER IF EXISTS trigger_atualizar_{tabela} ON {tabela};
            CREATE TRIGGER trigger_atualizar_{tabela}
                BEFORE UPDATE ON {tabela}
                FOR EACH ROW
                EXECUTE FUNCTION atualizar_timestamp()
            """))
        
        # Commit das alterações
        conn.commit()
    
    print("✅ Estruturas de tabelas verificadas/criadas com sucesso!")
    
    # Verificar se há dados básicos de municípios
    with engine.connect() as conn:
        result = conn.execute(text("SELECT COUNT(*) FROM municipios"))
        count = result.scalar()
        
        if count == 0:
            print("📍 Inserindo dados básicos de municípios...")
            inserir_municipios_basicos(conn)

def inserir_municipios_basicos(conn):
    """Insere municípios básicos para o sistema"""
    municipios_basicos = [
        # Fronteiras importantes
        ('Foz do Iguaçu', 'PR', True, True),
        ('Ponta Porã', 'MS', True, True), 
        ('Corumbá', 'MS', True, True),
        ('Uruguaiana', 'RS', True, True),
        ('Santana do Livramento', 'RS', True, True),
        ('Jaguarão', 'RS', True, True),
        
        # Capitais importantes
        ('São Paulo', 'SP', False, False),
        ('Rio de Janeiro', 'RJ', False, False),
        ('Brasília', 'DF', False, False),
        ('Belo Horizonte', 'MG', False, False),
        ('Porto Alegre', 'RS', False, False),
        ('Curitiba', 'PR', False, False),
        ('Salvador', 'BA', False, False),
        ('Recife', 'PE', False, False),
        ('Fortaleza', 'CE', False, False),
        ('Manaus', 'AM', False, False),
    ]
    
    for nome, uf, eh_fronteira, eh_suspeito in municipios_basicos:
        conn.execute(text("""
        INSERT INTO municipios (nome, uf, eh_fronteira, eh_suspeito)
        VALUES (:nome, :uf, :eh_fronteira, :eh_suspeito)
        ON CONFLICT (nome, uf) DO NOTHING
        """), {
            "nome": nome, 
            "uf": uf, 
            "eh_fronteira": eh_fronteira,
            "eh_suspeito": eh_suspeito
        })
    
    conn.commit()
    print("✅ Municípios básicos inseridos!")

# =============================================================================
# CONFIGURAÇÕES DE CAMINHOS
# =============================================================================

# Diretório base do projeto
BASE_DIR = Path(__file__).parent.parent

# Diretórios importantes
STATIC_DIR = BASE_DIR / 'static'
TEMPLATES_DIR = BASE_DIR / 'app' / 'templates'
MODELS_DIR = BASE_DIR / 'ml_models'
LOGS_DIR = BASE_DIR / 'logs'
CONFIG_DIR = BASE_DIR / 'config'

# Criar diretórios se não existirem
for directory in [MODELS_DIR, LOGS_DIR]:
    directory.mkdir(exist_ok=True)

# =============================================================================
# CONFIGURAÇÕES DE ML
# =============================================================================

ML_CONFIG = {
    'models_dir': MODELS_DIR / 'trained',
    'spacy_model': os.getenv('SPACY_PT_MODEL', 'pt_core_news_sm'),
    'sentence_transformer': os.getenv('SENTENCE_EMB_MODEL', 'sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2'),
    'cache_size': 1000,
    'embedding_dim': 384
}

# =============================================================================
# EXPORTS
# =============================================================================

__all__ = [
    # Classes de configuração
    'Config', 'DevelopmentConfig', 'TestingConfig', 'ProductionConfig',
    
    # Configurações de banco
    'DB_CONFIG', 'VEICULOS_DB_CONFIG', 
    
    # Funções
    'get_config', 'get_engine', 'get_veiculos_engine', 'criar_tabelas',
    'validate_db_connection',
    
    # Constantes
    'ML_CONFIG', 'BASE_DIR', 'STATIC_DIR', 'TEMPLATES_DIR'
]

print("⚙️ Settings module loaded successfully")