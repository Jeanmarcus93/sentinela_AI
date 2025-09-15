#!/usr/bin/env python3
"""
Script para verificar dados no banco
"""

import psycopg

def check_data():
    """Verifica dados no banco"""
    try:
        # Conectar ao banco
        conn = psycopg.connect(
            host="localhost",
            port=5432,
            dbname="veiculos_db",
            user="postgres",
            password="Jmkjmk.00"
        )
        
        with conn.cursor() as cur:
            # Verificar veículos
            cur.execute("SELECT placa, marca_modelo FROM veiculos LIMIT 5;")
            veiculos = cur.fetchall()
            print("🚗 Veículos encontrados:")
            for veiculo in veiculos:
                print(f"   - {veiculo[0]} | {veiculo[1]}")
            
            # Verificar pessoas
            cur.execute("SELECT nome, cpf_cnpj, possuidor, condutor, passageiro, relevante FROM pessoas LIMIT 5;")
            pessoas = cur.fetchall()
            print("\n👤 Pessoas encontradas:")
            for pessoa in pessoas:
                nome, cpf, possuidor, condutor, passageiro, relevante = pessoa
                print(f"   - {nome} | CPF: {cpf}")
                print(f"     Proprietário: {possuidor} | Condutor: {condutor} | Passageiro: {passageiro} | Relevante: {relevante}")
            
            # Verificar estrutura da tabela pessoas
            cur.execute("""
                SELECT column_name, data_type, is_nullable 
                FROM information_schema.columns 
                WHERE table_name = 'pessoas' 
                ORDER BY ordinal_position;
            """)
            colunas = cur.fetchall()
            print("\n📋 Estrutura da tabela pessoas:")
            for coluna in colunas:
                print(f"   - {coluna[0]} ({coluna[1]}) - Nullable: {coluna[2]}")
            
    except Exception as e:
        print(f"❌ Erro: {e}")
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    check_data()




