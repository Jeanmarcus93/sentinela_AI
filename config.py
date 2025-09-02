# config.py
from database import get_db_connection

def criar_tabelas():
    """Verifica e cria as tabelas necessárias para a aplicação, se não existirem."""
    
    # Comandos SQL para criar cada tabela
    comandos_sql = [
        """
        CREATE TABLE IF NOT EXISTS municipios (
            id SERIAL PRIMARY KEY,
            nome VARCHAR(255) NOT NULL,
            uf CHAR(2) NOT NULL
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS veiculos (
            id SERIAL PRIMARY KEY,
            placa VARCHAR(10) UNIQUE NOT NULL,
            marca_modelo VARCHAR(100),
            tipo VARCHAR(50),
            ano_modelo VARCHAR(10),
            cor VARCHAR(50),
            local_emplacamento VARCHAR(100)
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS pessoas (
            id SERIAL PRIMARY KEY,
            veiculo_id INTEGER REFERENCES veiculos(id),
            nome VARCHAR(255),
            cpf_cnpj VARCHAR(20) UNIQUE,
            relevante BOOLEAN,
            condutor BOOLEAN,
            possuidor BOOLEAN
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS passagens (
            id SERIAL PRIMARY KEY,
            veiculo_id INTEGER REFERENCES veiculos(id),
            datahora TIMESTAMP NOT NULL,
            municipio VARCHAR(255),
            estado CHAR(2),
            rodovia VARCHAR(50),
            ilicito_ida BOOLEAN DEFAULT FALSE,
            ilicito_volta BOOLEAN DEFAULT FALSE
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS ocorrencias (
            id SERIAL PRIMARY KEY,
            veiculo_id INTEGER REFERENCES veiculos(id),
            tipo VARCHAR(50) NOT NULL,
            datahora TIMESTAMP NOT NULL,
            datahora_fim TIMESTAMP,
            relato TEXT,
            ocupantes JSONB,
            apreensoes JSONB,
            presos JSONB,
            veiculos JSONB
        );
        """
    ]
    
    try:
        # Conecta ao banco e executa os comandos
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                for comando in comandos_sql:
                    cur.execute(comando)
        print("Estrutura das tabelas verificada com sucesso.")
    except Exception as e:
        print(f"Ocorreu um erro ao criar as tabelas: {e}")
        raise e