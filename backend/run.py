import sys

from app import create_app
from config.settings import criar_tabelas

# Importe o novo blueprint de feedback (se disponível)
try:
    from app.routes.analise_routes import feedback_bp
    FEEDBACK_BP_AVAILABLE = True
except ImportError:
    feedback_bp = None
    FEEDBACK_BP_AVAILABLE = False

app = create_app()

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
        
        app = create_app()

        # Registre o novo blueprint (se disponível)
        if FEEDBACK_BP_AVAILABLE:
            app.register_blueprint(feedback_bp)
            print("✅ Blueprint de feedback registrado")
        
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
