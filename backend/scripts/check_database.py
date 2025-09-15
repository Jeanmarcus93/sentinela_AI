#!/usr/bin/env python3
"""
Script para verificar o que está no banco de dados
"""

import sys
from pathlib import Path

# Adicionar o diretório backend ao path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from app.models.database import DatabaseConfig, get_db_connection
import psycopg
from psycopg.rows import dict_row

def check_database():
    """Verifica o conteúdo do banco"""
    
    print("🔍 Verificando banco de dados: sentinela_treino")
    print("=" * 50)
    
    db_config = DatabaseConfig(
        host='localhost',
        port=5432,
        dbname='sentinela_treino',
        user='postgres',
        password='Jmkjmk.00'
    )
    
    try:
        with get_db_connection(db_config) as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                # Verificar tabelas
                print("📋 Tabelas no banco:")
                cur.execute("""
                    SELECT table_name, 
                           (SELECT COUNT(*) FROM information_schema.columns 
                            WHERE table_name = t.table_name) as colunas
                    FROM information_schema.tables t
                    WHERE table_schema = 'public'
                    ORDER BY table_name
                """)
                tables = cur.fetchall()
                
                for table in tables:
                    print(f"   📝 {table['table_name']} ({table['colunas']} colunas)")
                
                # Verificar dados em cada tabela
                print(f"\n📊 Dados nas tabelas:")
                for table in tables:
                    table_name = table['table_name']
                    try:
                        cur.execute(f"SELECT COUNT(*) as count FROM {table_name}")
                        count = cur.fetchone()['count']
                        print(f"   📍 {table_name}: {count:,} registros")
                    except Exception as e:
                        print(f"   ❌ {table_name}: Erro - {e}")
                
                # Verificar estrutura da tabela passagens
                print(f"\n🔍 Estrutura da tabela 'passagens':")
                cur.execute("""
                    SELECT column_name, data_type, character_maximum_length, is_nullable
                    FROM information_schema.columns
                    WHERE table_name = 'passagens'
                    ORDER BY ordinal_position
                """)
                columns = cur.fetchall()
                
                for col in columns:
                    nullable = "NULL" if col['is_nullable'] == 'YES' else "NOT NULL"
                    length = f"({col['character_maximum_length']})" if col['character_maximum_length'] else ""
                    print(f"   📝 {col['column_name']:<25} {col['data_type']}{length:<15} {nullable}")
                
                # Se houver dados na tabela passagens, mostrar alguns exemplos
                cur.execute("SELECT COUNT(*) as count FROM passagens")
                passagens_count = cur.fetchone()['count']
                
                if passagens_count > 0:
                    print(f"\n📋 Exemplos de dados na tabela passagens:")
                    cur.execute("""
                        SELECT placa, cidade, uf, dataHoraUTC, latitude, longitude
                        FROM passagens 
                        ORDER BY dataHoraUTC DESC 
                        LIMIT 5
                    """)
                    samples = cur.fetchall()
                    
                    for i, sample in enumerate(samples, 1):
                        print(f"   {i}. Placa: {sample['placa']} | Cidade: {sample['cidade']}/{sample['uf']} | Data: {sample['dataHoraUTC']}")
                        print(f"      Coordenadas: {sample['latitude']}, {sample['longitude']}")
                else:
                    print(f"\n⚠️ Tabela passagens está vazia!")
                
                # Verificar se há problemas com coordenadas
                if passagens_count > 0:
                    print(f"\n🔍 Verificando coordenadas:")
                    cur.execute("""
                        SELECT 
                            COUNT(*) as total,
                            COUNT(latitude) as com_latitude,
                            COUNT(longitude) as com_longitude,
                            COUNT(CASE WHEN latitude IS NOT NULL AND longitude IS NOT NULL THEN 1 END) as com_ambas
                        FROM passagens
                    """)
                    coord_stats = cur.fetchone()
                    
                    print(f"   📊 Total de registros: {coord_stats['total']:,}")
                    print(f"   📍 Com latitude: {coord_stats['com_latitude']:,}")
                    print(f"   📍 Com longitude: {coord_stats['com_longitude']:,}")
                    print(f"   📍 Com ambas: {coord_stats['com_ambas']:,}")
                
    except Exception as e:
        print(f"❌ Erro ao verificar banco: {e}")

if __name__ == "__main__":
    check_database()

