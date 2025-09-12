#!/usr/bin/env python3
"""
Sistema de Análise de Placas v2.0 - Integração com Sistema de Agentes
"""

from app import create_app
from config.settings import criar_tabelas
import asyncio
import sys

app = create_app()

# Função de migração (mantida do app.py original)
def migrar_apreensoes_para_tabela_normalizada():
    """
    Migra dados da coluna JSON 'apreensoes' para a nova tabela normalizada 'apreensoes'.
    """
    print("Iniciando migração de apreensões para tabela normalizada...")
    try:
        from app.models.database import get_db_connection
        import json
        
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                # Verifica se a migração já foi executada
                cur.execute("SELECT COUNT(*) FROM apreensoes;")
                if cur.fetchone()[0] > 0:
                    print("A tabela 'apreensoes' já contém dados. A migração não será executada novamente.")
                    return

                # Busca todas as ocorrências que possuem dados de apreensões
                cur.execute("SELECT id, apreensoes FROM ocorrencias WHERE apreensoes IS NOT NULL AND apreensoes::text != '[]';")
                ocorrencias = cur.fetchall()

                if not ocorrencias:
                    print("Nenhum dado de apreensão para migrar.")
                    return

                print(f"Encontrados {len(ocorrencias)} ocorrências com dados de apreensões para migrar.")
                
                for occ_id, apreensoes_data in ocorrencias:
                    apreensoes_list = []
                    if isinstance(apreensoes_data, str):
                        try:
                            apreensoes_list = json.loads(apreensoes_data)
                        except json.JSONDecodeError:
                            print(f"AVISO: Não foi possível decodificar o JSON para a ocorrência ID {occ_id}.")
                            continue
                    elif isinstance(apreensoes_data, list):
                        apreensoes_list = apreensoes_data

                    for item in apreensoes_list:
                        tipo = item.get('tipo')
                        if tipo == 'Armas':
                            tipo = 'Arma'
                        
                        quantidade = item.get('quantidade')
                        unidade = item.get('unidade')
                        
                        if not all([tipo, quantidade, unidade]):
                            print(f"AVISO: Item de apreensão incompleto para ocorrência ID {occ_id}.")
                            continue
                        
                        cur.execute(
                            "INSERT INTO apreensoes (ocorrencia_id, tipo, quantidade, unidade) VALUES (%s, %s, %s, %s)",
                            (occ_id, tipo, quantidade, unidade)
                        )
                conn.commit()
                print("Migração de apreensões concluída com sucesso.")

    except Exception as e:
        print(f"Erro durante a migração de apreensões: {e}")

def inicializar_sistema_agentes():
    """
    Inicializa e testa o sistema de agentes especializados
    """
    print("🤖 Inicializando Sistema de Agentes Especializados...")
    
    try:
        # Testar se o sistema de agentes está funcionando
        from app.services.enhanced_placa_service import get_enhanced_placa_service
        
        # Executar teste rápido
        service = get_enhanced_placa_service()
        
        # Como estamos em Flask (síncrono), vamos testar de forma síncrona
        print("✅ Sistema de agentes carregado com sucesso!")
        
        # Mostrar agentes registrados
        stats = service.get_orchestrator_stats()
        print(f"   📊 Agentes registrados: {stats.get('registered_agents', 0)}")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro ao inicializar sistema de agentes: {e}")
        print("   O sistema continuará funcionando sem os agentes especializados")
        return False

def testar_sistema_agentes():
    """
    Executa teste completo do sistema de agentes (opcional)
    """
    print("\n🧪 Executando teste do sistema de agentes...")
    
    try:
        # Executar script de teste
        import subprocess
        result = subprocess.run([sys.executable, "migrate_to_agents.py"], 
                              capture_output=True, text=True, timeout=60)
        
        if result.returncode == 0:
            print("✅ Testes do sistema de agentes passaram!")
            return True
        else:
            print("⚠️  Testes do sistema de agentes com problemas:")
            print(result.stderr)
            return False
            
    except subprocess.TimeoutExpired:
        print("⏱️  Teste do sistema de agentes demorou muito (timeout)")
        return False
    except Exception as e:
        print(f"❌ Erro ao executar testes: {e}")
        return False

if __name__ == '__main__':
    print("🚀 Iniciando Sistema de Análise de Placas v2.0")
    print("=" * 50)
    
    try:
        # 1. Criar tabelas (mantendo funcionalidade original)
        print("📋 Criando/verificando tabelas do banco de dados...")
        criar_tabelas()
        print("✅ Tabelas verificadas/criadas com sucesso!")
        
        # 2. Migrar apreensões (mantendo funcionalidade original)  
        # migrar_apreensoes_para_tabela_normalizada()
        
        # 3. Inicializar sistema de agentes (nova funcionalidade)
        sistema_agentes_ok = inicializar_sistema_agentes()
        
        # 4. Executar teste completo (opcional - descomente se quiser)
        # if sistema_agentes_ok:
        #     testar_sistema_agentes()
        
        print("\n🌟 Sistema inicializado com sucesso!")
        print("📚 Acesse: http://localhost:5000 para usar a aplicação")
        
        if sistema_agentes_ok:
            print("🤖 Recursos de agentes especializados disponíveis!")
            print("   - Análise completa com múltiplos agentes")
            print("   - Análise rápida otimizada")
            print("   - Processamento em lote")
            print("   - Monitoramento de performance")
        
        print("\n" + "=" * 50)
        
    except Exception as e:
        print(f"❌ Erro ao inicializar: {e}")
        print("🔧 Verifique a configuração do banco de dados")
        sys.exit(1)
    
    # Executar aplicação Flask
    app.run(debug=True, use_reloader=False, host='0.0.0.0', port=5000)
