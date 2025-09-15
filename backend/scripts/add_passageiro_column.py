#!/usr/bin/env python3
"""
Script para adicionar a coluna 'passageiro' na tabela pessoas
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.models.database import get_db_connection

def add_passageiro_column():
    """Adiciona a coluna 'passageiro' na tabela pessoas"""
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                # Verificar se a coluna já existe
                cur.execute("""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name = 'pessoas' AND column_name = 'passageiro'
                """)
                
                result = cur.fetchone()
                if result:
                    print("✅ Coluna 'passageiro' já existe na tabela pessoas")
                    return True
                
                # Adicionar a coluna
                cur.execute("""
                    ALTER TABLE pessoas 
                    ADD COLUMN passageiro BOOLEAN DEFAULT FALSE
                """)
                
                print("✅ Coluna 'passageiro' adicionada com sucesso na tabela pessoas")
                return True
            
    except Exception as e:
        print(f"❌ Erro ao adicionar coluna 'passageiro': {e}")
        return False

if __name__ == "__main__":
    print("🔧 Adicionando coluna 'passageiro' na tabela pessoas...")
    success = add_passageiro_column()
    
    if success:
        print("🎉 Migração concluída com sucesso!")
    else:
        print("💥 Falha na migração!")
        sys.exit(1)
