#!/usr/bin/env python3
"""
Script para iniciar o servidor Sentinela IA com suporte ao banco sentinela_treino
"""

import sys
import os
from pathlib import Path

# Adicionar o diretório backend ao path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

def check_dependencies():
    """Verifica se todas as dependências estão instaladas"""
    print("🔍 Verificando dependências...")
    
    required_packages = [
        'flask',
        'flask_cors',
        'psycopg',
        'sqlalchemy',
        'pandas',
        'requests'
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package)
            print(f"✅ {package}")
        except ImportError:
            print(f"❌ {package} não encontrado")
            missing_packages.append(package)
    
    if missing_packages:
        print(f"\n⚠️ Pacotes ausentes: {missing_packages}")
        print("   Execute: pip install " + " ".join(missing_packages))
        return False
    
    print("✅ Todas as dependências estão instaladas")
    return True

def check_database_connection():
    """Verifica conexão com o banco sentinela_treino"""
    print("\n🔍 Verificando conexão com banco sentinela_treino...")
    
    try:
        from config.sentinela_treino_config import validate_sentinela_treino_connection
        
        if validate_sentinela_treino_connection():
            print("✅ Conexão com banco sentinela_treino OK")
            return True
        else:
            print("❌ Erro de conexão com banco sentinela_treino")
            return False
            
    except Exception as e:
        print(f"❌ Erro ao verificar banco: {e}")
        return False

def check_database_data():
    """Verifica se há dados no banco"""
    print("\n🔍 Verificando dados no banco...")
    
    try:
        from config.sentinela_treino_config import get_sentinela_treino_connection
        
        with get_sentinela_treino_connection() as conn:
            with conn.cursor() as cur:
                # Verificar veículos
                cur.execute("SELECT COUNT(*) FROM veiculos")
                veiculos_count = cur.fetchone()[0]
                
                # Verificar passagens
                cur.execute("SELECT COUNT(*) FROM passagens")
                passagens_count = cur.fetchone()[0]
                
                print(f"📊 Veículos: {veiculos_count:,}")
                print(f"📊 Passagens: {passagens_count:,}")
                
                if veiculos_count > 0 and passagens_count > 0:
                    print("✅ Banco possui dados")
                    return True
                else:
                    print("⚠️ Banco está vazio")
                    return False
                    
    except Exception as e:
        print(f"❌ Erro ao verificar dados: {e}")
        return False

def start_server():
    """Inicia o servidor Flask"""
    print("\n🚀 Iniciando servidor Sentinela IA...")
    
    try:
        from app import create_app
        
        # Criar aplicação
        app = create_app()
        
        # Configurar para desenvolvimento
        app.config['DEBUG'] = True
        app.config['ENV'] = 'development'
        
        print("✅ Aplicação criada com sucesso")
        print("📌 APIs disponíveis:")
        print("   - Legacy: http://localhost:5000/api/consulta_placa/<placa>")
        print("   - Sentinela Treino: http://localhost:5000/api/treino/")
        print("   - Sistema: http://localhost:5000/api/info")
        print("   - Health: http://localhost:5000/api/health")
        print("\n🌐 Servidor rodando em: http://localhost:5000")
        print("🛑 Para parar: Ctrl+C")
        print("=" * 60)
        
        # Iniciar servidor
        app.run(
            host='0.0.0.0',
            port=5000,
            debug=True,
            use_reloader=True
        )
        
    except Exception as e:
        print(f"❌ Erro ao iniciar servidor: {e}")
        return False

def main():
    """Função principal"""
    
    print("🚀 Sentinela IA - Iniciando Servidor com Sentinela Treino")
    print("=" * 60)
    
    # Verificações prévias
    if not check_dependencies():
        return False
    
    if not check_database_connection():
        print("\n⚠️ Problema de conexão com banco. Verifique:")
        print("   - PostgreSQL está rodando?")
        print("   - Banco 'sentinela_treino' existe?")
        print("   - Credenciais estão corretas?")
        return False
    
    if not check_database_data():
        print("\n⚠️ Banco está vazio. Execute:")
        print("   python scripts/import_normalized_fixed.py \"C:\\Users\\jeanm\\Downloads\\export.csv\"")
        return False
    
    # Iniciar servidor
    start_server()
    return True

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n🛑 Servidor interrompido pelo usuário")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Erro fatal: {e}")
        sys.exit(1)

