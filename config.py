import psycopg
import sys
import os

# Garante que o script encontre o arquivo database.py
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from database import DB_CONFIG

# Definição da função para criar as tabelas
def criar_tabelas():
    """Cria TODAS as tabelas no banco de dados com a estrutura correta e unificada."""
    conn = None
    try:
        # Usa a configuração principal do banco de dados
        conn = psycopg.connect(**DB_CONFIG)
        cur = conn.cursor()

        # --- Tabelas Adicionais da Aplicação Web ---
        cur.execute("""
            CREATE TABLE IF NOT EXISTS municipios (
                id SERIAL PRIMARY KEY,
                nome VARCHAR(255) NOT NULL,
                uf CHAR(2) NOT NULL
            );
        """)

        # Tabela de veículos
        cur.execute("""
            CREATE TABLE IF NOT EXISTS veiculos (
                id SERIAL PRIMARY KEY,
                placa VARCHAR(10) UNIQUE NOT NULL,
                marca_modelo VARCHAR(255),
                tipo VARCHAR(100),
                ano_modelo VARCHAR(20),
                cor VARCHAR(50),
                local_emplacamento VARCHAR(255)
            );
        """)

        # Tabela de pessoas
        cur.execute("""
            CREATE TABLE IF NOT EXISTS pessoas (
                id SERIAL PRIMARY KEY,
                veiculo_id INTEGER REFERENCES veiculos(id) ON DELETE CASCADE,
                nome VARCHAR(255),
                cpf_cnpj VARCHAR(20) UNIQUE
            );
        """)

        # Tabela de passagens
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
        
        # Tabela de ocorrências (COM A COLUNA CORRIGIDA)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS ocorrencias (
                id SERIAL PRIMARY KEY,
                veiculo_id INTEGER REFERENCES veiculos(id), -- ESTA LINHA É ESSENCIAL
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
                    
        # Tipos ENUM e tabela de apreensões
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
        print("Estrutura das tabelas verificada/criada com sucesso.")
    except psycopg.Error as e:
        print(f"Erro ao criar tabelas: {e}")
        if conn:
            conn.rollback()
    finally:
        if conn:
            conn.close()

