import psycopg

DB_CONFIG = {
    "dbname": "veiculos_db",
    "user": "postgres",
    "password": "Jmkjmk.00",  # ajuste conforme seu ambiente
    "host": "localhost",
    "port": "5432",
}


def criar_tabelas():
    """Cria/ajusta o esquema com chaves únicas esperadas pelos upserts."""
    with psycopg.connect(**DB_CONFIG) as conn:
        with conn.cursor() as cur:
            # --- veiculos ---
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS veiculos (
                    id SERIAL PRIMARY KEY,
                    placa VARCHAR(10) UNIQUE,
                    marca_modelo VARCHAR(100),
                    tipo VARCHAR(50),
                    ano_modelo VARCHAR(20),
                    cor VARCHAR(30),
                    local_emplacamento VARCHAR(100),
                    transferencia_recente VARCHAR(100),
                    comunicacao_venda VARCHAR(100),
                    suspeito BOOLEAN DEFAULT FALSE,
                    relevante BOOLEAN DEFAULT FALSE,
                    crime_prf VARCHAR(50),
                    abordagem_prf VARCHAR(50)
                );
                """
            )

            # --- pessoas ---
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS pessoas (
                    id SERIAL PRIMARY KEY,
                    veiculo_id INTEGER REFERENCES veiculos(id) ON DELETE CASCADE,
                    nome VARCHAR(150),
                    cpf_cnpj VARCHAR(30) UNIQUE,
                    cnh VARCHAR(20),
                    validade_cnh DATE,
                    local_cnh VARCHAR(100),
                    suspeito BOOLEAN DEFAULT FALSE,
                    relevante BOOLEAN DEFAULT FALSE,
                    proprietario BOOLEAN DEFAULT FALSE,
                    condutor BOOLEAN DEFAULT FALSE,
                    possuidor BOOLEAN DEFAULT FALSE
                );
                """
            )

            # --- passagens ---
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS passagens (
                    id SERIAL PRIMARY KEY,
                    veiculo_id INTEGER REFERENCES veiculos(id) ON DELETE CASCADE,
                    estado VARCHAR(100),
                    municipio VARCHAR(200),
                    rodovia VARCHAR(300),
                    datahora TIMESTAMP,
                    ilicito BOOLEAN DEFAULT FALSE
                );
                """
            )

        conn.commit()
