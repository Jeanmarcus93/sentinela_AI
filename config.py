from sqlalchemy import create_engine, text

# ======================
# Configurações do Banco
# ======================
DB_HOST = "localhost"
DB_PORT = 5432
DB_NAME = "sentinela_teste"
DB_USER = "postgres"
DB_PASSWORD = "Jmkjmk.00"

# Banco de veículos
VEICULOS_DB_NAME = "veiculos_db"
VEICULOS_DB_USER = "postgres"
VEICULOS_DB_PASSWORD = "Jmkjmk.00"
VEICULOS_DB_HOST = "localhost"
VEICULOS_DB_PORT = 5432

# ======================
# Funções de conexão
# ======================
def get_engine(db_name=DB_NAME, user=DB_USER, password=DB_PASSWORD, host=DB_HOST, port=DB_PORT):
    """Retorna um engine SQLAlchemy para o banco especificado."""
    conn_str = f"postgresql+psycopg://{user}:{password}@{host}:{port}/{db_name}"
    return create_engine(conn_str, echo=False, future=True)

def criar_tabelas():
    """Cria as tabelas necessárias no banco, se não existirem."""
    engine = get_engine()
    with engine.connect() as conn:
        conn.execute(text("""
        CREATE TABLE IF NOT EXISTS veiculos (
            id SERIAL PRIMARY KEY,
            placa VARCHAR(10) UNIQUE NOT NULL,
            modelo VARCHAR(100),
            cor VARCHAR(50),
            ano INTEGER,
            criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """))

        conn.execute(text("""
        CREATE TABLE IF NOT EXISTS ocorrencias (
            id SERIAL PRIMARY KEY,
            veiculo_id INT REFERENCES veiculos(id) ON DELETE CASCADE,
            tipo VARCHAR(50),
            descricao TEXT,
            data_ocorrencia TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """))

        conn.commit()

    print("✅ Estruturas de tabelas verificadas/criadas com sucesso!")
