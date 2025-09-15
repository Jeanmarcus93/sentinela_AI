#!/usr/bin/env python3
"""
Script para verificar a estrutura da tabela feedback
"""

import os
import psycopg

# Configuração do banco de dados
DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": int(os.getenv("DB_PORT", "5432")),
    "dbname": os.getenv("DB_NAME", "veiculos_db"),
    "user": os.getenv("DB_USER", "postgres"),
    "password": os.getenv("DB_PASSWORD", "Jmkjmk.00")
}

def verificar_tabela_feedback():
    """Verifica se a tabela feedback existe e tem a estrutura correta"""
    try:
        with psycopg.connect(**DB_CONFIG) as conn:
            with conn.cursor() as cur:
                # Verificar se a tabela existe
                cur.execute("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_schema = 'public' 
                        AND table_name = 'feedback'
                    );
                """)
                
                tabela_existe = cur.fetchone()[0]
                
                if not tabela_existe:
                    print("ERRO - Tabela 'feedback' nao existe")
                    return False
                
                print("OK - Tabela 'feedback' existe")
                
                # Verificar estrutura da tabela
                cur.execute("""
                    SELECT column_name, data_type, is_nullable, column_default
                    FROM information_schema.columns 
                    WHERE table_name = 'feedback'
                    ORDER BY ordinal_position;
                """)
                
                colunas = cur.fetchall()
                
                print("\nEstrutura da tabela 'feedback':")
                print("-" * 60)
                for coluna in colunas:
                    nome, tipo, nullable, default = coluna
                    nullable_str = "NULL" if nullable == "YES" else "NOT NULL"
                    default_str = f", DEFAULT: {default}" if default else ""
                    print(f"  {nome}: {tipo} {nullable_str}{default_str}")
                
                # Verificar se tem dados
                cur.execute("SELECT COUNT(*) FROM feedback")
                total_registros = cur.fetchone()[0]
                print(f"\n📊 Total de registros: {total_registros}")
                
                if total_registros > 0:
                    # Mostrar alguns exemplos
                    cur.execute("""
                        SELECT placa, classificacao_usuario, feedback_usuario, criado_em
                        FROM feedback 
                        ORDER BY criado_em DESC 
                        LIMIT 5
                    """)
                    
                    exemplos = cur.fetchall()
                    print("\n📝 Últimos 5 registros:")
                    print("-" * 60)
                    for exemplo in exemplos:
                        placa, class_user, feedback_user, criado_em = exemplo
                        print(f"  {placa} | {class_user} | {feedback_user} | {criado_em}")
                
                return True
                
    except Exception as e:
        print(f"ERRO ao verificar tabela feedback: {e}")
        return False

def criar_tabela_feedback():
    """Cria a tabela feedback se não existir"""
    try:
        with psycopg.connect(**DB_CONFIG, autocommit=True) as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS feedback (
                        id SERIAL PRIMARY KEY,
                        placa VARCHAR(10) NOT NULL,
                        texto_relato TEXT NOT NULL,
                        classificacao_usuario VARCHAR(20) NOT NULL,
                        classificacao_modelo VARCHAR(20),
                        confianca_modelo DECIMAL(5,4),
                        feedback_usuario VARCHAR(20) NOT NULL,
                        observacoes TEXT,
                        usuario VARCHAR(50),
                        contexto VARCHAR(50),
                        datahora TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    );
                """)
                
                print("Tabela 'feedback' criada com sucesso")
                return True
                
    except Exception as e:
        print(f"ERRO ao criar tabela feedback: {e}")
        return False

def main():
    """Função principal"""
    print("Verificacao da Tabela Feedback")
    print("=" * 40)
    
    # Verificar se a tabela existe
    if not verificar_tabela_feedback():
        print("\nCriando tabela 'feedback'...")
        if criar_tabela_feedback():
            print("Tabela criada com sucesso!")
            verificar_tabela_feedback()  # Verificar novamente
        else:
            print("Falha ao criar tabela")
    else:
        print("\nTabela 'feedback' está pronta para uso!")

if __name__ == "__main__":
    main()