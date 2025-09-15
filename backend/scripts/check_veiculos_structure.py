#!/usr/bin/env python3
"""
Script para verificar estrutura da tabela veiculos
"""

import psycopg

def check_veiculos_structure():
    """Verifica estrutura da tabela veiculos"""
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
            # Verificar estrutura da tabela veiculos
            cur.execute("""
                SELECT column_name, data_type, is_nullable 
                FROM information_schema.columns 
                WHERE table_name = 'veiculos' 
                ORDER BY ordinal_position;
            """)
            colunas = cur.fetchall()
            print("🚗 Estrutura da tabela veiculos:")
            for coluna in colunas:
                print(f"   - {coluna[0]} ({coluna[1]}) - Nullable: {coluna[2]}")
            
            # Verificar dados de um veículo específico
            cur.execute("SELECT * FROM veiculos WHERE placa = 'ITD4J47';")
            veiculo = cur.fetchone()
            if veiculo:
                print(f"\n📋 Dados do veículo ITD4J47:")
                cur.execute("""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name = 'veiculos' 
                    ORDER BY ordinal_position;
                """)
                nomes_colunas = [row[0] for row in cur.fetchall()]
                for i, valor in enumerate(veiculo):
                    print(f"   - {nomes_colunas[i]}: {valor}")
            
    except Exception as e:
        print(f"❌ Erro: {e}")
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    check_veiculos_structure()




