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
        CREATE TABLE IF NOT EXISTS ocorrencias (
            id SERIAL PRIMARY KEY,
            veiculo_id INTEGER REFERENCES veiculos(id),
            tipo VARCHAR(50) NOT NULL,
            datahora TIMESTAMP NOT NULL,
            datahora_fim TIMESTAMP,
            relato TEXT,
            ocupantes JSONB,
            presos JSONB,
            veiculos JSONB
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
        # --- NOVOS TIPOS E TABELA PARA APREENSÕES ---
        """
        DO $$ BEGIN
            CREATE TYPE tipo_apreensao_enum AS ENUM ('Maconha', 'Skunk', 'Cocaina', 'Crack', 'Sintéticos', 'Arma');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
        """,
        """
        DO $$ BEGIN
            CREATE TYPE unidade_apreensao_enum AS ENUM ('kg', 'g', 'un');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
        """,
        """
        CREATE TABLE IF NOT EXISTS apreensoes (
            id SERIAL PRIMARY KEY,
            ocorrencia_id INTEGER NOT NULL REFERENCES ocorrencias(id) ON DELETE CASCADE,
            tipo tipo_apreensao_enum NOT NULL,
            quantidade NUMERIC(10, 3) NOT NULL,
            unidade unidade_apreensao_enum NOT NULL
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

def atualizar_esquema():
    """Garante que colunas mais recentes existam na tabela. Usado para migrações."""
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                # Garante que a coluna JSONB antiga ainda exista para a migração
                cur.execute("ALTER TABLE ocorrencias ADD COLUMN IF NOT EXISTS apreensoes JSONB;")
        print("Esquema do banco de dados verificado/atualizado para migração.")
    except Exception as e:
        print(f"Ocorreu um erro ao atualizar o esquema: {e}")
        pass

def finalizar_migracao_apreensoes():
    """Remove a coluna antiga 'apreensoes' da tabela 'ocorrencias' após a migração dos dados."""
    print("Tentando remover coluna antiga de apreensões da tabela 'ocorrencias'...")
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                # Remove a coluna JSONB que não é mais necessária
                cur.execute("ALTER TABLE ocorrencias DROP COLUMN IF EXISTS apreensoes;")
                # Remove outras colunas que foram normalizadas ou não são mais usadas
                cur.execute("ALTER TABLE ocorrencias DROP COLUMN IF EXISTS quantidade_total_kg;")
                cur.execute("ALTER TABLE ocorrencias DROP COLUMN IF EXISTS tipos_apreensao;")
        print("Coluna antiga 'apreensoes' removida com sucesso.")
    except Exception as e:
        print(f"Erro ao remover coluna antiga: {e}")
