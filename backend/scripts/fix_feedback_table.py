#!/usr/bin/env python3
"""
Script para corrigir a estrutura da tabela feedback
"""

import psycopg
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from app.models.database import get_db_connection

def fix_feedback_table():
    """Corrige a estrutura da tabela feedback"""
    
    print("🔧 Corrigindo estrutura da tabela 'feedback'...")
    
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                # Verificar estrutura atual
                cur.execute("""
                    SELECT column_name, data_type, is_nullable 
                    FROM information_schema.columns 
                    WHERE table_name = 'feedback' 
                    ORDER BY ordinal_position;
                """)
                columns = cur.fetchall()
                
                print("📋 Estrutura atual:")
                for col in columns:
                    print(f"  {col[0]}: {col[1]} {'NULL' if col[2] == 'YES' else 'NOT NULL'}")
                
                # Verificar se precisa recriar a tabela
                current_columns = [col[0] for col in columns]
                required_columns = [
                    'id', 'placa', 'texto_relato', 'classificacao_usuario', 
                    'classificacao_modelo', 'confianca_modelo', 'feedback_usuario', 
                    'observacoes', 'usuario', 'contexto', 'criado_em'
                ]
                
                missing_columns = [col for col in required_columns if col not in current_columns]
                
                if missing_columns:
                    print(f"\n⚠️ Colunas faltando: {missing_columns}")
                    print("🔄 Recriando tabela com estrutura correta...")
                    
                    # Fazer backup dos dados existentes
                    cur.execute("SELECT COUNT(*) FROM feedback;")
                    count = cur.fetchone()[0]
                    print(f"📊 Registros existentes: {count}")
                    
                    if count > 0:
                        print("💾 Fazendo backup dos dados existentes...")
                        cur.execute("CREATE TABLE feedback_backup AS SELECT * FROM feedback;")
                        conn.commit()
                    
                    # Recriar tabela com estrutura correta
                    cur.execute("DROP TABLE IF EXISTS feedback CASCADE;")
                    
                    cur.execute("""
                        CREATE TABLE feedback (
                            id SERIAL PRIMARY KEY,
                            placa VARCHAR(10),
                            texto_relato TEXT NOT NULL,
                            classificacao_usuario VARCHAR(50) NOT NULL,
                            classificacao_modelo VARCHAR(50),
                            confianca_modelo DECIMAL(5,4),
                            feedback_usuario VARCHAR(50) NOT NULL,
                            observacoes TEXT,
                            usuario VARCHAR(100),
                            contexto VARCHAR(100),
                            criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                        );
                    """)
                    
                    conn.commit()
                    print("✅ Tabela 'feedback' recriada com sucesso!")
                    
                    # Restaurar dados do backup se existirem
                    if count > 0:
                        print("🔄 Tentando restaurar dados do backup...")
                        try:
                            cur.execute("""
                                INSERT INTO feedback (texto_relato, classificacao_usuario, feedback_usuario)
                                SELECT 
                                    COALESCE(feedback, 'Dados migrados'),
                                    'Migrado',
                                    'Migrado'
                                FROM feedback_backup;
                            """)
                            conn.commit()
                            print("✅ Dados restaurados com sucesso!")
                        except Exception as e:
                            print(f"⚠️ Não foi possível restaurar dados: {e}")
                    
                else:
                    print("✅ Tabela 'feedback' já tem a estrutura correta!")
                
                # Verificar estrutura final
                cur.execute("""
                    SELECT column_name, data_type, is_nullable 
                    FROM information_schema.columns 
                    WHERE table_name = 'feedback' 
                    ORDER BY ordinal_position;
                """)
                final_columns = cur.fetchall()
                
                print("\n📋 Estrutura final:")
                for col in final_columns:
                    print(f"  {col[0]}: {col[1]} {'NULL' if col[2] == 'YES' else 'NOT NULL'}")
                
                # Testar inserção
                print("\n🧪 Testando inserção...")
                cur.execute("""
                    INSERT INTO feedback (
                        texto_relato, classificacao_usuario, feedback_usuario, 
                        usuario, contexto
                    ) VALUES (%s, %s, %s, %s, %s)
                """, (
                    'Teste de estrutura',
                    'Suspeito',
                    'Correto',
                    'script_teste',
                    'teste_estrutura'
                ))
                conn.commit()
                
                cur.execute("SELECT COUNT(*) FROM feedback;")
                total = cur.fetchone()[0]
                print(f"✅ Teste bem-sucedido! Total de registros: {total}")
                
    except Exception as e:
        print(f"❌ Erro ao corrigir tabela: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    fix_feedback_table()
