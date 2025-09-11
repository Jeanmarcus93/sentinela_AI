# database.py - Versão com credenciais diretas
from sqlalchemy import create_engine
import psycopg

# ================== CONFIGURAÇÃO DIRETA ==================
DB_CONFIG = {
    "host": "localhost",
    "dbname": "veiculos_db",
    "user": "postgres",
    "password": "Jmkjmk.00",  # <<< coloque sua senha do PostgreSQL aqui
    "port": "5432"
}

DB_CONFIG_TESTE = {
    "host": "localhost",
    "dbname": "sentinela_teste",
    "user": "postgres",
    "password": "Jmkjmk.00",  # <<< mesma senha ou outra, dependendo do banco de teste
    "port": "5432"
}

# Validação de configuração
def validate_db_config(config, config_name="DB"):
    """Valida se todas as configurações necessárias estão presentes."""
    required_fields = ["host", "dbname", "user", "password"]
    missing_fields = [field for field in required_fields if not config.get(field)]
    
    if missing_fields:
        raise ValueError(f"Configuração {config_name} incompleta. Campos faltando: {missing_fields}")
    
    return True

def get_engine():
    """Cria e retorna uma engine do SQLAlchemy para uso com Pandas."""
    validate_db_config(DB_CONFIG, "Produção")
    port = DB_CONFIG.get('port', 5432)
    return create_engine(
        f"postgresql+psycopg2://{DB_CONFIG['user']}:{DB_CONFIG['password']}@{DB_CONFIG['host']}:{port}/{DB_CONFIG['dbname']}",
        pool_pre_ping=True,  # Verifica conexões antes de usar
        pool_recycle=3600    # Recria conexões a cada hora
    )

def get_db_connection():
    """Cria e retorna uma conexão direta com o banco de dados usando Psycopg."""
    validate_db_config(DB_CONFIG, "Produção")
    return psycopg.connect(**DB_CONFIG)
