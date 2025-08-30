# -*- coding: utf-8 -*-
"""
config.py
Configurações de banco de dados e criação de tabelas.
"""

import psycopg2

DB_CONFIG = {
    "dbname": "veiculos_db",
    "user": "postgres",
    "password": "Jmkjmk.00",   # ⚠️ use apenas letras/números/underscore
    "host": "localhost",
    "port": "5432"
}

def criar_tabelas():
    """Cria as tabelas necessárias no banco, se não existirem."""
    # Forçar client_encoding em UTF-8 para evitar erros de caracteres
    conn = psycopg2.connect(**DB_CONFIG, options='-c client_encoding=UTF8')
    cur = conn.cursor()

    # ---------- Tabela de veículos ----------
    cur.execute("""
        CREATE TABLE IF NOT EXISTS veiculos (
            id SERIAL PRIMARY KEY,
            placa VARCHAR(20) UNIQUE NOT NULL,
            marca_modelo TEXT,
            tipo TEXT,
            ano_modelo TEXT,
            cor TEXT,
            local_emplacamento TEXT,
            transferencia_recente TEXT,
            suspeito TEXT,
            relevante TEXT,
            crime_prf TEXT,
            abordagem_prf TEXT
        );
    """)

    # ---------- Tabela de pessoas ----------
    cur.execute("""
        CREATE TABLE IF NOT EXISTS pessoas (
            id SERIAL PRIMARY KEY,
            veiculo_id INTEGER REFERENCES veiculos(id) ON DELETE CASCADE,
            nome TEXT,
            cpf_cnpj VARCHAR(50) UNIQUE,
            cnh TEXT,
            validade_cnh DATE,
            local_cnh TEXT,
            suspeito TEXT,
            relevante TEXT,
            proprietario BOOLEAN DEFAULT FALSE,
            condutor BOOLEAN DEFAULT FALSE
        );
    """)

    # ---------- Tabela de passagens ----------
    cur.execute("""
        CREATE TABLE IF NOT EXISTS passagens (
            id SERIAL PRIMARY KEY,
            veiculo_id INTEGER REFERENCES veiculos(id) ON DELETE CASCADE,
            estado TEXT,
            municipio TEXT,
            rodovia TEXT,
            data DATE,
            hora TEXT
        );
    """)

    conn.commit()
    cur.close()
    conn.close()
