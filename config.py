# -*- coding: utf-8 -*-
"""
config.py
------------

Este módulo concentra a configuração de acesso ao banco de dados PostgreSQL e
a criação das tabelas necessárias para armazenar os dados extraídos dos
relatórios em PDF. Ao separar a configuração em um arquivo isolado, fica
mais fácil manter e reutilizar as definições de conexão e a lógica de
estruturação do banco sem poluir o restante do código de extração.

Para rodar este módulo isoladamente, execute:

    python config.py

Ele irá conectar‑se ao banco utilizando as credenciais informadas em
``DB_CONFIG`` e garantir que as tabelas ``veiculos_condutores`` e
``passagens`` existam. Caso já existam, nada será alterado.

É altamente recomendável salvar este arquivo com codificação UTF‑8 para
evitar problemas ao interpretar caracteres acentuados em ambientes
Windows. A primeira linha ``# -*- coding: utf-8 -*-`` instrui o
interpretador a ler o arquivo utilizando UTF‑8 independentemente das
configurações do sistema.
"""

import psycopg2
from psycopg2 import sql

# Configurações do banco de dados. Altere conforme sua instalação.
# A opção ``client_encoding`` garante que a conexão converse em UTF‑8
# evitando problemas com acentuação nos valores salvos.
DB_CONFIG = {
    "dbname": "veiculos_db",
    "user": "postgres",
    "password": "Jmkjmk.00",
    "host": "localhost",
    "port": 5432,
    "options": "-c client_encoding=UTF8",
}

# Comandos SQL para criação das tabelas. São executados em ordem e
# encapsulados dentro de ``CREATE TABLE IF NOT EXISTS`` para garantir
# idempotência. Os nomes das colunas utilizam apenas caracteres
# alfanuméricos e sublinhados para evitar problemas de codificação.
CREATE_TABLES = [
    """
    CREATE TABLE IF NOT EXISTS veiculos_condutores (
        id SERIAL PRIMARY KEY,
        placa VARCHAR(20),
        marca_modelo VARCHAR(100),
        tipo VARCHAR(50),
        ano_modelo VARCHAR(20),
        cor VARCHAR(50),
        local_emplacamento VARCHAR(100),
        transferencia_recente VARCHAR(50),
        suspeito VARCHAR(50),
        relevante VARCHAR(100),
        proprietario VARCHAR(100),
        cpf_cnpj_proprietario VARCHAR(30),
        condutor VARCHAR(100),
        cpf_condutor VARCHAR(20),
        cnh VARCHAR(20),
        validade_cnh DATE,
        local_cnh VARCHAR(100),
        suspeito_condutor VARCHAR(50),
        relevante_condutor VARCHAR(100),
        teve_mp VARCHAR(50),
        crime_prf VARCHAR(50),
        abordagem_prf VARCHAR(50)
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS passagens (
        id SERIAL PRIMARY KEY,
        placa VARCHAR(20),
        estado VARCHAR(10),
        municipio VARCHAR(100),
        rodovia VARCHAR(100),
        data DATE,
        hora TIME
    );
    """,
]


def criar_tabelas() -> None:
    """Cria as tabelas no banco de dados se ainda não existirem.

    Esta função abre uma conexão com o PostgreSQL a partir das
    configurações definidas em ``DB_CONFIG`` e executa cada comando em
    ``CREATE_TABLES``. Caso ocorra qualquer exceção durante a execução,
    ela será propagada para facilitar o diagnóstico.
    """
    conn = psycopg2.connect(**DB_CONFIG)
    try:
        cur = conn.cursor()
        for comando in CREATE_TABLES:
            cur.execute(sql.SQL(comando))
        conn.commit()
    finally:
        # Feche o cursor e a conexão mesmo que haja erro
        try:
            cur.close()
        except Exception:
            pass
        conn.close()


if __name__ == "__main__":
    try:
        criar_tabelas()
        print("✅ Tabelas criadas/verificadas com sucesso!")
    except Exception as e:
        # Exibe a mensagem de erro para facilitar depuração
        print(f"❌ Erro ao criar tabelas: {e}")