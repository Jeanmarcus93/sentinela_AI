# database.py
from sqlalchemy import create_engine
import psycopg

# ================== CONFIGURAÇÃO CENTRAL ==================
# Mantenha suas credenciais de banco de dados aqui.
DB_CONFIG = {
    "host": "localhost",
    "dbname": "veiculos_db",
    "user": "postgres",
    "password": "Jmkjmk.00" # ATENÇÃO: Troque pela sua senha
}

def get_engine():
    """Cria e retorna uma engine do SQLAlchemy para uso com Pandas."""
    port = DB_CONFIG.get('port', 5432)
    return create_engine(
        f"postgresql+psycopg2://{DB_CONFIG['user']}:{DB_CONFIG['password']}@{DB_CONFIG['host']}:{port}/{DB_CONFIG['dbname']}"
    )

def get_db_connection():
    """Cria e retorna uma conexão direta com o banco de dados usando Psycopg."""
    return psycopg.connect(**DB_CONFIG)