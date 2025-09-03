import psycopg2
from database import DB_CONFIG_TESTE as DB_CONFIG

# 2. Definição da função para criar as tabelas
def criar_tabelas():
    """Cria TODAS as tabelas no banco de dados com a estrutura correta e unificada."""
    conn = None
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()

        # --- Tabelas Adicionais da Aplicação Web ---
        cur.execute("""
            CREATE TABLE IF NOT EXISTS municipios (
                id SERIAL PRIMARY KEY,
                nome VARCHAR(255) NOT NULL,
                uf CHAR(2) NOT NULL
            );
        """)

        # Tabela de veículos (versão completa para extrator e app)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS veiculos (
                id SERIAL PRIMARY KEY,
                placa VARCHAR(10) UNIQUE NOT NULL,
                marca_modelo VARCHAR(255),
                tipo VARCHAR(100),
                ano_modelo VARCHAR(20),
                cor VARCHAR(50),
                local_emplacamento VARCHAR(255),
                transferencia_recente BOOLEAN DEFAULT FALSE,
                comunicacao_venda BOOLEAN DEFAULT FALSE,
                crime_prf BOOLEAN DEFAULT FALSE,
                abordagem_prf BOOLEAN DEFAULT FALSE
            );
        """)

        # Tabela de pessoas (versão completa para extrator e app)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS pessoas (
                id SERIAL PRIMARY KEY,
                veiculo_id INTEGER REFERENCES veiculos(id) ON DELETE CASCADE,
                nome VARCHAR(255),
                cpf_cnpj VARCHAR(20) UNIQUE NOT NULL,
                cnh VARCHAR(20),
                validade_cnh DATE,
                local_cnh VARCHAR(255),
                suspeito BOOLEAN DEFAULT FALSE,
                relevante BOOLEAN DEFAULT FALSE,
                proprietario BOOLEAN DEFAULT FALSE,
                condutor BOOLEAN DEFAULT FALSE,
                possuidor BOOLEAN DEFAULT FALSE
            );
        """)

        # Tabela de passagens (unificada com campos para o app)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS passagens (
                id SERIAL PRIMARY KEY,
                veiculo_id INTEGER REFERENCES veiculos(id) ON DELETE CASCADE,
                estado VARCHAR(255),
                municipio VARCHAR(255),
                rodovia VARCHAR(255),
                datahora TIMESTAMP NOT NULL,
                ilicito_ida BOOLEAN DEFAULT FALSE,
                ilicito_volta BOOLEAN DEFAULT FALSE
            );
        """)
        
        # Tabela de ocorrências (para o app)
        cur.execute("""
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
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS relato_extracao (
                id SERIAL PRIMARY KEY,
                relato TEXT NOT NULL,
                classe_risco VARCHAR(20),
                pontuacao NUMERIC,
                top_palavras JSONB,
                criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
                    
        # Tipos ENUM e tabela de apreensões (para o app)
        cur.execute("""
            DO $$ BEGIN
                CREATE TYPE tipo_apreensao_enum AS ENUM ('Maconha', 'Skunk', 'Cocaina', 'Crack', 'Sintéticos', 'Arma');
            EXCEPTION
                WHEN duplicate_object THEN null;
            END $$;
        """)
        cur.execute("""
            DO $$ BEGIN
                CREATE TYPE unidade_apreensao_enum AS ENUM ('kg', 'g', 'un');
            EXCEPTION
                WHEN duplicate_object THEN null;
            END $$;
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS apreensoes (
                id SERIAL PRIMARY KEY,
                ocorrencia_id INTEGER NOT NULL REFERENCES ocorrencias(id) ON DELETE CASCADE,
                tipo tipo_apreensao_enum NOT NULL,
                quantidade NUMERIC(10, 3) NOT NULL,
                unidade unidade_apreensao_enum NOT NULL
            );
        """)

        conn.commit()
        print("Estrutura das tabelas verificada com sucesso.")
    except psycopg2.Error as e:
        print(f"Erro ao criar tabelas: {e}")
        if conn:
            conn.rollback()
    finally:
        if conn:
            conn.close()




