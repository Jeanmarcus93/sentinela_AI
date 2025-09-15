#!/usr/bin/env python3
"""
Script para conectar ao banco sentinela_treino e mostrar informações
"""

import sys
from pathlib import Path

# Adicionar o diretório backend ao path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from app.models.database import DatabaseConfig, get_db_connection
import psycopg
from psycopg.rows import dict_row

def connect_and_show_info():
    """Conecta ao banco e mostra informações"""
    
    print("🔗 Conectando ao banco: sentinela_treino")
    print("=" * 50)
    
    # Configuração do banco
    db_config = DatabaseConfig(
        host='localhost',
        port=5432,
        dbname='sentinela_treino',
        user='postgres',
        password='Jmkjmk.00'
    )
    
    try:
        with get_db_connection(db_config) as conn:
            print("✅ Conectado com sucesso!")
            print(f"🏠 Host: {db_config.host}:{db_config.port}")
            print(f"🗄️ Banco: {db_config.dbname}")
            print(f"👤 Usuário: {db_config.user}")
            
            with conn.cursor(row_factory=dict_row) as cur:
                # Informações do servidor
                cur.execute("SELECT version(), current_database(), current_user")
                version, database, user = cur.fetchone()
                
                print(f"\n📊 Informações do Servidor:")
                print(f"   Versão: {version}")
                print(f"   Banco atual: {database}")
                print(f"   Usuário atual: {user}")
                
                # Listar tabelas
                print(f"\n📋 Tabelas disponíveis:")
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
                
                # Detalhes da tabela passagens
                print(f"\n🔍 Estrutura da tabela 'passagens':")
                cur.execute("""
                    SELECT column_name, data_type, is_nullable, column_default
                    FROM information_schema.columns
                    WHERE table_name = 'passagens'
                    ORDER BY ordinal_position
                """)
                columns = cur.fetchall()
                
                for col in columns:
                    nullable = "NULL" if col['is_nullable'] == 'YES' else "NOT NULL"
                    default = f" DEFAULT {col['column_default']}" if col['column_default'] else ""
                    print(f"   📝 {col['column_name']:<25} {col['data_type']:<20} {nullable}{default}")
                
                # Contar registros
                print(f"\n📊 Contagem de registros:")
                for table_name in ['veiculos', 'passagens', 'municipios']:
                    try:
                        cur.execute(f"SELECT COUNT(*) as count FROM {table_name}")
                        count = cur.fetchone()['count']
                        print(f"   📍 {table_name}: {count} registros")
                    except Exception as e:
                        print(f"   ❌ {table_name}: Erro ao contar - {e}")
                
                # Mostrar alguns municípios
                print(f"\n📍 Municípios cadastrados (primeiros 10):")
                cur.execute("SELECT nome, uf, eh_fronteira FROM municipios ORDER BY nome LIMIT 10")
                municipios = cur.fetchall()
                
                for mun in municipios:
                    fronteira = "🌍 Fronteira" if mun['eh_fronteira'] else "🏙️ Interior"
                    print(f"   {fronteira}: {mun['nome']} ({mun['uf']})")
                
                print(f"\n✅ Conexão estabelecida com sucesso!")
                print(f"💡 Você pode usar este banco para:")
                print(f"   - Importar dados de passagens")
                print(f"   - Executar análises")
                print(f"   - Desenvolver aplicações")
                
    except Exception as e:
        print(f"❌ Erro ao conectar: {e}")
        print("💡 Verifique se:")
        print("   - O PostgreSQL está rodando")
        print("   - As credenciais estão corretas")
        print("   - O banco 'sentinela_treino' existe")
        return False
    
    return True

def interactive_mode():
    """Modo interativo para executar comandos SQL"""
    
    print("\n🔧 Modo Interativo")
    print("=" * 30)
    print("Digite comandos SQL (ou 'sair' para encerrar):")
    
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
                while True:
                    try:
                        comando = input("\nsentinela_treino> ").strip()
                        
                        if comando.lower() in ['sair', 'exit', 'quit']:
                            print("👋 Até logo!")
                            break
                        
                        if not comando:
                            continue
                        
                        if comando.startswith('\\'):
                            # Comandos especiais
                            if comando == '\\dt':
                                cur.execute("""
                                    SELECT table_name FROM information_schema.tables 
                                    WHERE table_schema = 'public' ORDER BY table_name
                                """)
                                tables = cur.fetchall()
                                for table in tables:
                                    print(f"   📝 {table['table_name']}")
                            elif comando == '\\d passagens':
                                cur.execute("""
                                    SELECT column_name, data_type, is_nullable
                                    FROM information_schema.columns
                                    WHERE table_name = 'passagens'
                                    ORDER BY ordinal_position
                                """)
                                columns = cur.fetchall()
                                for col in columns:
                                    print(f"   📝 {col['column_name']:<25} {col['data_type']}")
                            else:
                                print("Comando não reconhecido")
                        else:
                            # Comando SQL
                            cur.execute(comando)
                            
                            if cur.description:
                                # SELECT - mostrar resultados
                                results = cur.fetchall()
                                if results:
                                    # Mostrar cabeçalhos
                                    headers = [desc[0] for desc in cur.description]
                                    print(" | ".join(f"{h:<15}" for h in headers))
                                    print("-" * (len(" | ".join(headers))))
                                    
                                    # Mostrar dados
                                    for row in results:
                                        values = [str(v)[:15] if v is not None else "NULL" for v in row]
                                        print(" | ".join(f"{v:<15}" for v in values))
                                else:
                                    print("Nenhum resultado encontrado")
                            else:
                                # Comando que não retorna dados
                                print("Comando executado com sucesso")
                                
                    except Exception as e:
                        print(f"❌ Erro: {e}")
                        
    except Exception as e:
        print(f"❌ Erro de conexão: {e}")

def main():
    """Função principal"""
    print("🎯 Conector do Banco Sentinela Treino")
    print("=" * 40)
    
    if connect_and_show_info():
        resposta = input("\nDeseja entrar no modo interativo? (s/n): ").lower().strip()
        if resposta in ['s', 'sim', 'y', 'yes']:
            interactive_mode()

if __name__ == "__main__":
    main()

