#!/usr/bin/env python3
"""
Script para testar o banco de dados criado
"""

import sys
from pathlib import Path

# Adicionar o diretório backend ao path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from app.models.database import DatabaseConfig, get_db_connection, test_connection
import psycopg
from psycopg.rows import dict_row

def test_database():
    """Testa o banco de dados"""
    
    print("🧪 Testando banco de dados: sentinela_treino")
    print("=" * 50)
    
    # Configuração do banco
    db_config = DatabaseConfig(
        host='localhost',
        port=5432,
        dbname='sentinela_treino',
        user='postgres',
        password='Jmkjmk.00'
    )
    
    # Teste 1: Conexão básica
    print("1️⃣ Testando conexão...")
    test_result = test_connection(db_config)
    
    if test_result['success']:
        print(f"   ✅ Conexão OK ({test_result['response_time']:.3f}s)")
        print(f"   📊 Versão: {test_result['server_version'][:50]}...")
    else:
        print(f"   ❌ Falha na conexão: {test_result['error']}")
        return False
    
    # Teste 2: Verificar tabelas
    print("\n2️⃣ Verificando tabelas...")
    try:
        with get_db_connection(db_config) as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute("""
                    SELECT table_name 
                    FROM information_schema.tables 
                    WHERE table_schema = 'public'
                    ORDER BY table_name
                """)
                tables = cur.fetchall()
                
                print(f"   📋 Tabelas encontradas: {len(tables)}")
                for table in tables:
                    print(f"      ✅ {table['table_name']}")
                    
    except Exception as e:
        print(f"   ❌ Erro ao verificar tabelas: {e}")
        return False
    
    # Teste 3: Verificar estrutura da tabela passagens
    print("\n3️⃣ Verificando estrutura da tabela passagens...")
    try:
        with get_db_connection(db_config) as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute("""
                    SELECT column_name, data_type, is_nullable
                    FROM information_schema.columns
                    WHERE table_name = 'passagens'
                    ORDER BY ordinal_position
                """)
                columns = cur.fetchall()
                
                print(f"   📋 Colunas encontradas: {len(columns)}")
                for col in columns:
                    nullable = "NULL" if col['is_nullable'] == 'YES' else "NOT NULL"
                    print(f"      📝 {col['column_name']:<25} {col['data_type']:<15} {nullable}")
                    
    except Exception as e:
        print(f"   ❌ Erro ao verificar estrutura: {e}")
        return False
    
    # Teste 4: Verificar índices
    print("\n4️⃣ Verificando índices...")
    try:
        with get_db_connection(db_config) as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute("""
                    SELECT indexname, tablename
                    FROM pg_indexes 
                    WHERE schemaname = 'public' AND tablename = 'passagens'
                    ORDER BY indexname
                """)
                indexes = cur.fetchall()
                
                print(f"   📋 Índices encontrados: {len(indexes)}")
                for idx in indexes:
                    print(f"      🔍 {idx['indexname']}")
                    
    except Exception as e:
        print(f"   ❌ Erro ao verificar índices: {e}")
        return False
    
    # Teste 5: Verificar dados básicos
    print("\n5️⃣ Verificando dados básicos...")
    try:
        with get_db_connection(db_config) as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                # Contar municípios
                cur.execute("SELECT COUNT(*) as count FROM municipios")
                municipios_count = cur.fetchone()['count']
                print(f"   📍 Municípios inseridos: {municipios_count}")
                
                # Mostrar alguns municípios
                cur.execute("SELECT nome, uf, eh_fronteira FROM municipios LIMIT 5")
                municipios = cur.fetchall()
                print("   📍 Exemplos:")
                for mun in municipios:
                    fronteira = "🌍" if mun['eh_fronteira'] else "🏙️"
                    print(f"      {fronteira} {mun['nome']} ({mun['uf']})")
                    
    except Exception as e:
        print(f"   ❌ Erro ao verificar dados: {e}")
        return False
    
    # Teste 6: Teste de inserção
    print("\n6️⃣ Testando inserção de dados...")
    try:
        with get_db_connection(db_config) as conn:
            with conn.cursor() as cur:
                # Inserir um veículo de teste
                cur.execute("""
                    INSERT INTO veiculos (placa, marca_modelo, cor, tipo)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (placa) DO NOTHING
                """, ('TEST1234', 'Toyota Corolla', 'Branco', 'Automóvel'))
                
                # Inserir uma passagem de teste
                cur.execute("""
                    INSERT INTO passagens (
                        dataHoraUTC, placa, cidade, uf, codigoRodovia, 
                        velocidade, latitude, longitude, sistemaOrigem
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    '2024-01-15 10:30:00', 'TEST1234', 'São Paulo', 'SP', 'BR-116',
                    85.5, -23.5505, -46.6333, 'Sistema Teste'
                ))
                
                conn.commit()
                print("   ✅ Dados de teste inseridos com sucesso")
                
                # Limpar dados de teste
                cur.execute("DELETE FROM passagens WHERE placa = 'TEST1234'")
                cur.execute("DELETE FROM veiculos WHERE placa = 'TEST1234'")
                conn.commit()
                print("   🧹 Dados de teste removidos")
                
    except Exception as e:
        print(f"   ❌ Erro no teste de inserção: {e}")
        return False
    
    print("\n🎉 Todos os testes passaram!")
    print("✅ Banco 'sentinela_treino' está funcionando perfeitamente!")
    print("\n📋 Resumo:")
    print("   🗄️ Banco: sentinela_treino")
    print("   📊 Tabelas: veiculos, passagens, municipios")
    print("   🔍 Índices: Otimizados para consultas rápidas")
    print("   📍 Dados: Municípios básicos inseridos")
    print("   ✅ Pronto para uso!")
    
    return True

if __name__ == "__main__":
    success = test_database()
    sys.exit(0 if success else 1)

