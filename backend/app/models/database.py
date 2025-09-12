# backend/app/models/database.py
"""
Database Core Module - Sentinela IA v2.0

Gerencia:
- Conexões com PostgreSQL
- Configurações de banco
- Pool de conexões
- Health checks
- Migrations básicas

Supports:
- Environment variables
- Multiple database configs (production, development, testing)
- Connection pooling
- Automatic reconnection
- Health monitoring
"""

import os
import logging
import time
from typing import Dict, Any, Optional, Union
from contextlib import contextmanager
from dataclasses import dataclass

import psycopg
from psycopg.rows import dict_row
from sqlalchemy import create_engine, text
from sqlalchemy.pool import QueuePool
import sqlalchemy.exc as sql_exc


# ==========================================
# CONFIGURAÇÕES DE BANCO
# ==========================================

@dataclass
class DatabaseConfig:
    """Configuração de banco de dados"""
    host: str
    port: int
    dbname: str
    user: str
    password: str
    
    def to_dict(self) -> Dict[str, Union[str, int]]:
        """Converte para dicionário para psycopg"""
        return {
            "host": self.host,
            "port": self.port, 
            "dbname": self.dbname,
            "user": self.user,
            "password": self.password
        }
    
    def to_sqlalchemy_url(self) -> str:
        """Converte para URL do SQLAlchemy"""
        return f"postgresql+psycopg://{self.user}:{self.password}@{self.host}:{self.port}/{self.dbname}"


# ==========================================
# CONFIGURAÇÕES POR AMBIENTE
# ==========================================

def get_database_config(environment: str = None) -> DatabaseConfig:
    """
    Retorna configuração de banco baseada no ambiente
    
    Args:
        environment: 'development', 'production', 'testing' ou None (auto-detect)
    
    Returns:
        DatabaseConfig: Configuração do banco
    """
    if environment is None:
        environment = os.getenv('FLASK_ENV', 'development')
    
    # Configuração padrão (desenvolvimento/produção)
    config = DatabaseConfig(
        host=os.getenv('DB_HOST', 'localhost'),
        port=int(os.getenv('DB_PORT', 5432)),
        dbname=os.getenv('DB_NAME', 'veiculos_db'),
        user=os.getenv('DB_USER', 'postgres'),
        password=os.getenv('DB_PASSWORD', 'Jmkjmk.00')
    )
    
    # Configurações específicas por ambiente
    if environment == 'testing':
        config.dbname = os.getenv('TEST_DB_NAME', f"{config.dbname}_test")
    
    elif environment == 'production':
        # Em produção, todas as variáveis devem estar definidas
        required_vars = ['DB_HOST', 'DB_NAME', 'DB_USER', 'DB_PASSWORD']
        missing_vars = [var for var in required_vars if not os.getenv(var)]
        
        if missing_vars:
            raise ValueError(f"Variáveis de ambiente obrigatórias em produção: {missing_vars}")
    
    return config


# ==========================================
# CONFIGURAÇÃO GLOBAL
# ==========================================

# Configuração principal - pode ser alterada dinamicamente
DB_CONFIG: Optional[DatabaseConfig] = None

def init_db_config(environment: str = None) -> DatabaseConfig:
    """
    Inicializa configuração global do banco
    
    Args:
        environment: Ambiente alvo
        
    Returns:
        DatabaseConfig: Configuração inicializada
    """
    global DB_CONFIG
    DB_CONFIG = get_database_config(environment)
    
    logging.info(f"Database configurado: {DB_CONFIG.host}:{DB_CONFIG.port}/{DB_CONFIG.dbname}")
    return DB_CONFIG


# Inicialização automática
if DB_CONFIG is None:
    try:
        DB_CONFIG = init_db_config()
    except Exception as e:
        logging.error(f"Erro ao inicializar configuração do banco: {e}")
        # Configuração fallback para evitar crashes
        DB_CONFIG = DatabaseConfig(
            host='localhost',
            port=5432, 
            dbname='postgres',
            user='postgres',
            password=''
        )


# ==========================================
# CONEXÕES PSYCOPG (TRANSAÇÕES)
# ==========================================

@contextmanager
def get_db_connection(config: DatabaseConfig = None):
    """
    Context manager para conexão com PostgreSQL usando psycopg
    
    Args:
        config: Configuração customizada (opcional)
        
    Yields:
        psycopg.Connection: Conexão ativa
        
    Example:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM veiculos")
                results = cur.fetchall()
    """
    if config is None:
        config = DB_CONFIG
    
    if config is None:
        raise ValueError("Configuração de banco não inicializada")
    
    connection = None
    try:
        # Conectar com configuração otimizada
        connection = psycopg.connect(
            **config.to_dict(),
            autocommit=False,
            prepare_threshold=0,  # Disable prepared statements by default
            options="-c statement_timeout=30000"  # 30s timeout
        )
        
        yield connection
        
    except psycopg.Error as e:
        if connection:
            connection.rollback()
        logging.error(f"Erro na conexão do banco: {e}")
        raise
        
    except Exception as e:
        if connection:
            connection.rollback()
        logging.error(f"Erro inesperado na conexão: {e}")
        raise
        
    finally:
        if connection:
            connection.close()


def get_db_connection_dict():
    """
    Retorna configuração como dicionário para compatibilidade
    
    Returns:
        Dict: Configuração em formato dict
    """
    if DB_CONFIG is None:
        raise ValueError("Configuração de banco não inicializada")
    
    return DB_CONFIG.to_dict()


# ==========================================
# ENGINE SQLALCHEMY (ANALYTICS)
# ==========================================

_engine = None
_engine_config = None

def get_engine(config: DatabaseConfig = None, **kwargs) -> Any:
    """
    Retorna engine SQLAlchemy para analytics e pandas
    
    Args:
        config: Configuração customizada (opcional)
        **kwargs: Argumentos adicionais para create_engine
        
    Returns:
        sqlalchemy.Engine: Engine configurada
    """
    global _engine, _engine_config
    
    if config is None:
        config = DB_CONFIG
    
    if config is None:
        raise ValueError("Configuração de banco não inicializada")
    
    # Reutilizar engine se mesma configuração
    if _engine is not None and _engine_config == config:
        return _engine
    
    # Configurações padrão otimizadas
    default_kwargs = {
        'poolclass': QueuePool,
        'pool_size': 5,
        'max_overflow': 10,
        'pool_timeout': 30,
        'pool_recycle': 3600,
        'pool_pre_ping': True,
        'echo': os.getenv('SQL_ECHO', 'false').lower() == 'true'
    }
    
    # Merge com kwargs fornecidos
    engine_kwargs = {**default_kwargs, **kwargs}
    
    try:
        _engine = create_engine(
            config.to_sqlalchemy_url(),
            **engine_kwargs
        )
        _engine_config = config
        
        logging.info("SQLAlchemy engine criada com sucesso")
        return _engine
        
    except Exception as e:
        logging.error(f"Erro ao criar SQLAlchemy engine: {e}")
        raise


# ==========================================
# HEALTH CHECKS & MONITORING
# ==========================================

def test_connection(config: DatabaseConfig = None) -> Dict[str, Any]:
    """
    Testa conexão com o banco
    
    Args:
        config: Configuração customizada (opcional)
        
    Returns:
        Dict: Resultado do teste
    """
    if config is None:
        config = DB_CONFIG
    
    result = {
        "success": False,
        "error": None,
        "response_time": None,
        "server_version": None
    }
    
    start_time = time.time()
    
    try:
        with get_db_connection(config) as conn:
            with conn.cursor() as cur:
                # Teste básico
                cur.execute("SELECT version(), current_timestamp")
                version, timestamp = cur.fetchone()
                
                result.update({
                    "success": True,
                    "response_time": time.time() - start_time,
                    "server_version": version,
                    "server_timestamp": str(timestamp)
                })
                
    except Exception as e:
        result.update({
            "error": str(e),
            "response_time": time.time() - start_time
        })
        
    return result


def get_database_info(config: DatabaseConfig = None) -> Dict[str, Any]:
    """
    Retorna informações detalhadas do banco
    
    Args:
        config: Configuração customizada (opcional)
        
    Returns:
        Dict: Informações do banco
    """
    if config is None:
        config = DB_CONFIG
    
    info = {
        "connection": test_connection(config),
        "config": {
            "host": config.host,
            "port": config.port, 
            "database": config.dbname,
            "user": config.user
            # Password omitida por segurança
        },
        "tables": [],
        "indexes": [],
        "size": None
    }
    
    if not info["connection"]["success"]:
        return info
    
    try:
        with get_db_connection(config) as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                # Listar tabelas
                cur.execute("""
                    SELECT table_name, table_type
                    FROM information_schema.tables 
                    WHERE table_schema = 'public'
                    ORDER BY table_name
                """)
                info["tables"] = cur.fetchall()
                
                # Listar índices
                cur.execute("""
                    SELECT indexname, tablename, indexdef
                    FROM pg_indexes 
                    WHERE schemaname = 'public'
                    ORDER BY tablename, indexname
                """)
                info["indexes"] = cur.fetchall()
                
                # Tamanho do banco
                cur.execute("""
                    SELECT pg_size_pretty(pg_database_size(current_database())) as size
                """)
                info["size"] = cur.fetchone()["size"]
                
    except Exception as e:
        info["error"] = str(e)
        logging.error(f"Erro ao obter informações do banco: {e}")
        
    return info


# ==========================================
# VALIDAÇÃO E UTILITÁRIOS
# ==========================================

def validate_db_config(config: DatabaseConfig, test_connection_flag: bool = True) -> bool:
    """
    Valida configuração de banco
    
    Args:
        config: Configuração a ser validada
        test_connection_flag: Se deve testar conexão real
        
    Returns:
        bool: True se válida
    """
    # Validações básicas
    required_fields = ['host', 'port', 'dbname', 'user', 'password']
    
    for field in required_fields:
        value = getattr(config, field, None)
        if not value:
            logging.error(f"Campo obrigatório ausente: {field}")
            return False
    
    if not isinstance(config.port, int) or config.port <= 0:
        logging.error("Porta deve ser um número inteiro positivo")
        return False
    
    # Teste de conexão real (opcional)
    if test_connection_flag:
        test_result = test_connection(config)
        if not test_result["success"]:
            logging.error(f"Teste de conexão falhou: {test_result['error']}")
            return False
    
    return True


def create_database_if_not_exists(config: DatabaseConfig) -> bool:
    """
    Cria banco de dados se não existir
    
    Args:
        config: Configuração do banco a ser criado
        
    Returns:
        bool: True se criado ou já existe
    """
    # Conexão temporária com postgres para criar o banco
    temp_config = DatabaseConfig(
        host=config.host,
        port=config.port,
        dbname='postgres',  # Conectar ao postgres padrão
        user=config.user,
        password=config.password
    )
    
    try:
        with get_db_connection(temp_config) as conn:
            # Não pode usar transação para CREATE DATABASE
            conn.autocommit = True
            with conn.cursor() as cur:
                # Verificar se já existe
                cur.execute("""
                    SELECT 1 FROM pg_database WHERE datname = %s
                """, (config.dbname,))
                
                if cur.fetchone():
                    logging.info(f"Banco {config.dbname} já existe")
                    return True
                
                # Criar banco
                cur.execute(f'CREATE DATABASE "{config.dbname}"')
                logging.info(f"Banco {config.dbname} criado com sucesso")
                return True
                
    except Exception as e:
        logging.error(f"Erro ao criar banco {config.dbname}: {e}")
        return False


# ==========================================
# COMPATIBILITY LAYER
# ==========================================

# Para compatibilidade com código existente
def get_db_connection_legacy():
    """Função de compatibilidade para código antigo"""
    return get_db_connection()


# Exports para compatibilidade
__all__ = [
    # Core classes
    'DatabaseConfig',
    
    # Configuration
    'get_database_config', 
    'init_db_config',
    'DB_CONFIG',
    
    # Connections
    'get_db_connection',
    'get_db_connection_dict',
    'get_engine',
    
    # Health & Info
    'test_connection',
    'get_database_info',
    'validate_db_config',
    
    # Utilities
    'create_database_if_not_exists',
    
    # Legacy
    'get_db_connection_legacy'
]


# ==========================================
# LOGGING & INITIALIZATION
# ==========================================

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Log de inicialização
if DB_CONFIG:
    logger.info(f"✅ Database module initialized - {DB_CONFIG.host}:{DB_CONFIG.port}/{DB_CONFIG.dbname}")
    
    # Teste inicial (não bloquear se falhar)
    try:
        test_result = test_connection()
        if test_result["success"]:
            logger.info(f"✅ Database connection test passed ({test_result['response_time']:.3f}s)")
        else:
            logger.warning(f"⚠️ Database connection test failed: {test_result['error']}")
    except Exception as e:
        logger.warning(f"⚠️ Could not perform initial connection test: {e}")
        
else:
    logger.error("❌ Database module failed to initialize")


# ==========================================
# ENVIRONMENT INFO
# ==========================================

def print_env_info():
    """Imprime informações do ambiente (debug)"""
    print("🔍 Database Environment Info:")
    print(f"   FLASK_ENV: {os.getenv('FLASK_ENV', 'not set')}")
    print(f"   DB_HOST: {os.getenv('DB_HOST', 'not set')}")
    print(f"   DB_PORT: {os.getenv('DB_PORT', 'not set')}")  
    print(f"   DB_NAME: {os.getenv('DB_NAME', 'not set')}")
    print(f"   DB_USER: {os.getenv('DB_USER', 'not set')}")
    print(f"   DB_PASSWORD: {'***' if os.getenv('DB_PASSWORD') else 'not set'}")


if __name__ == "__main__":
    # Executar como script para debugging
    print_env_info()
    
    print("\n🧪 Testing database connection...")
    result = test_connection()
    print(f"Connection test: {'✅ SUCCESS' if result['success'] else '❌ FAILED'}")
    
    if result['success']:
        print(f"Response time: {result['response_time']:.3f}s")
        print(f"Server version: {result['server_version'][:50]}...")
    else:
        print(f"Error: {result['error']}")
    
    print("\n📊 Database info:")
    info = get_database_info()
    print(f"Tables: {len(info['tables'])}")
    print(f"Database size: {info.get('size', 'unknown')}")
