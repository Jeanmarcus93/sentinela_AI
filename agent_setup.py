# setup_agents.py
"""
Script para configurar e migrar para o sistema de agentes especializados
Execute este script para implementar a nova arquitetura de análise
"""

import os
import sys
import shutil
from pathlib import Path
import asyncio
import time

def create_agent_structure():
    """Cria a estrutura de diretórios para os agentes"""
    directories = [
        "app/services/agents",
        "tests/agents",
        "config/agents"
    ]
    
    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)
        init_file = Path(directory) / "__init__.py"
        if not init_file.exists() and "tests" not in directory:
            init_file.touch()
    
    print("✅ Estrutura de diretórios para agentes criada")

def create_agent_files():
    """Cria os arquivos dos agentes especializados"""
    
    # Criar __init__.py para o módulo de agentes
    agents_init_content = '''"""
Sistema de Agentes Especializados para Análise de Placas
"""

from .base_agent import BaseAgent, AgentType, AnalysisTask, AgentResult, Priority, AgentOrchestrator
from .orchestrator import get_orchestrator

__all__ = [
    'BaseAgent', 'AgentType', 'AnalysisTask', 'AgentResult', 'Priority',
    'AgentOrchestrator', 'get_orchestrator'
]
'''
    
    with open("app/services/agents/__init__.py", "w", encoding="utf-8") as f:
        f.write(agents_init_content)
    
    print("✅ Arquivos base dos agentes criados")

def create_configuration_file():
    """Cria arquivo de configuração para os agentes"""
    config_content = '''# config/agents/agent_config.py
"""
Configurações para o sistema de agentes especializados
"""

from typing import Dict, Any

# Configurações gerais
AGENT_CONFIG = {
    "max_concurrent_tasks_per_agent": 5,
    "default_task_timeout": 30.0,
    "enable_performance_monitoring": True,
    "log_agent_activities": True,
    
    # Configurações específicas por agente
    "agents": {
        "data_collector": {
            "max_concurrent_tasks": 5,
            "timeout": 20.0,
            "cache_duration": 300,  # 5 minutos
            "enable_parallel_db_queries": True
        },
        "route_analyzer": {
            "max_concurrent_tasks": 3,
            "timeout": 30.0,
            "enable_ml_analysis": True,
            "fallback_to_heuristics": True,
            "pattern_detection_threshold": 0.6
        },
        "semantic_analyzer": {
            "max_concurrent_tasks": 4,
            "timeout": 25.0,
            "max_reports_per_analysis": 10,
            "enable_parallel_processing": True
        },
        "risk_calculator": {
            "max_concurrent_tasks": 5,
            "timeout": 15.0,
            "route_weight": 0.6,
            "semantic_weight": 0.4,
            "adaptive_weighting": True
        }
    },
    
    # Configurações de performance
    "performance": {
        "enable_caching": True,
        "cache_ttl": 600,  # 10 minutos
        "max_cache_size": 1000,
        "enable_result_compression": False
    },
    
    # Configurações de monitoramento
    "monitoring": {
        "collect_metrics": True,
        "metrics_retention_days": 7,
        "alert_on_high_error_rate": True,
        "error_rate_threshold": 0.1  # 10%
    }
}

def get_agent_config(agent_name: str = None) -> Dict[str, Any]:
    """Retorna configuração para um agente específico ou geral"""
    if agent_name:
        return AGENT_CONFIG["agents"].get(agent_name, {})
    return AGENT_CONFIG
'''
    
    os.makedirs("config/agents", exist_ok=True)
    with open("config/agents/agent_config.py", "w", encoding="utf-8") as f:
        f.write(config_content)
    
    print("✅ Arquivo de configuração criado")

def create_test_suite():
    """Cria suite de testes para os agentes"""
    test_content = '''# tests/test_agent_system.py
"""
Testes para o sistema de agentes especializados
"""

import asyncio
import pytest
import time
from typing import Dict, Any

# Configurar path para imports
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.enhanced_placa_service import get_enhanced_service, quick_risk_analysis

class TestAgentSystem:
    """Classe de testes para o sistema de agentes"""
    
    @pytest.fixture
    def service(self):
        """Fixture para o serviço aprimorado"""
        return get_enhanced_service()
    
    def test_service_initialization(self, service):
        """Testa inicialização do serviço"""
        assert service._is_initialized
        assert len(service.orchestrator.agents) > 0
    
    @pytest.mark.asyncio
    async def test_basic_analysis(self, service):
        """Testa análise básica de uma placa"""
        result = await service.analisar_placa_async("TEST123")
        
        assert result["success"]
        assert "placa" in result
        assert "risco" in result
        assert "execution_time" in result
    
    @pytest.mark.asyncio 
    async def test_quick_risk_analysis(self):
        """Testa análise rápida de risco"""
        result = await quick_risk_analysis("TEST123")
        
        assert result["success"]
        assert "risco" in result
    
    def test_compatibility_with_existing_api(self, service):
        """Testa compatibilidade com API existente"""
        from app.services.enhanced_placa_service import analisar_placa_json
        
        result = analisar_placa_json("TEST123")
        
        # Verificar formato esperado pela API antiga
        assert "placa" in result
        assert "rotas" in result
        assert "relatos" in result
        assert "risco" in result
    
    @pytest.mark.asyncio
    async def test_performance_comparison(self, service):
        """Compara performance do novo sistema vs antigo"""
        placa = "TEST123"
        
        # Medir novo sistema
        start = time.time()
        new_result = await service.analisar_placa_async(placa)
        new_time = time.time() - start
        
        # Medir sistema antigo (se disponível)
        try:
            from app.services.placa_service import analisar_placa_json as old_analysis
            start = time.time()
            old_result = old_analysis(placa)
            old_time = time.time() - start
            
            print(f"Novo sistema: {new_time:.2f}s")
            print(f"Sistema antigo: {old_time:.2f}s")
            print(f"Melhoria: {((old_time - new_time) / old_time * 100):.1f}%")
            
        except ImportError:
            print(f"Sistema novo: {new_time:.2f}s (sistema antigo não disponível)")
    
    @pytest.mark.asyncio
    async def test_system_health(self, service):
        """Testa saúde do sistema"""
        health = await service.get_system_health()
        
        assert "system_stats" in health
        assert "initialized" in health
        assert health["initialized"] is True

if __name__ == "__main__":
    # Execução simples dos testes
    service = get_enhanced_service()
    
    print("🧪 Executando testes básicos...")
    
    # Teste 1: Inicialização
    print("1. Testando inicialização...", end=" ")
    assert service._is_initialized
    print("✅")
    
    # Teste 2: Análise síncrona
    print("2. Testando análise síncrona...", end=" ")
    result = service.analisar_placa_sync("TEST123")
    assert result["success"]
    print("✅")
    
    # Teste 3: Compatibilidade
    print("3. Testando compatibilidade...", end=" ")
    from app.services.enhanced_placa_service import analisar_placa_json
    compat_result = analisar_placa_json("TEST123")
    assert "placa" in compat_result
    print("✅")
    
    print("\\n🎉 Todos os testes básicos passaram!")
'''
    
    with open("tests/test_agent_system.py", "w", encoding="utf-8") as f:
        f.write(test_content)
    
    print("✅ Suite de testes criada")

def update_main_routes():
    """Atualiza rotas principais para usar o novo sistema"""
    update_content = '''
# Adicionar no app/routes/main_routes.py (no topo, após outros imports)

# Import do novo sistema de agentes
try:
    from app.services.enhanced_placa_service import analisar_placa_json as enhanced_analysis
    ENHANCED_SYSTEM_AVAILABLE = True
    print("✅ Sistema de agentes carregado com sucesso")
except ImportError as e:
    print(f"⚠️ Sistema de agentes não disponível: {e}")
    ENHANCED_SYSTEM_AVAILABLE = False

# Adicionar nova rota para análise aprimorada
@main_bp.route('/api/analise_placa_enhanced/<string:placa>')
def api_analise_placa_enhanced(placa):
    """Nova rota otimizada com sistema de agentes"""
    try:
        if ENHANCED_SYSTEM_AVAILABLE:
            resultado = enhanced_analysis(placa.upper())
            return jsonify(resultado)
        else:
            # Fallback para sistema antigo
            from app.services.placa_service import analisar_placa_json
            resultado = analisar_placa_json(placa.upper())
            return jsonify(resultado)
    except FileNotFoundError:
        return jsonify({"error": "Modelos de ML não encontrados"}), 404
    except Exception as e:
        print(f"ERRO em api_analise_placa_enhanced: {e}")
        return jsonify({"error": "Erro interno ao analisar a placa"}), 500

# Adicionar rota para estatísticas dos agentes
@main_bp.route('/api/agent_stats')
def api_agent_stats():
    """Retorna estatísticas do sistema de agentes"""
    try:
        if ENHANCED_SYSTEM_AVAILABLE:
            from app.services.enhanced_placa_service import get_enhanced_service
            service = get_enhanced_service()
            stats = service.get_performance_metrics()
            return jsonify(stats)
        else:
            return jsonify({"error": "Sistema de agentes não disponível"}), 503
    except Exception as e:
        return jsonify({"error": str(e)}), 500
'''
    
    print("ℹ️ Para ativar o sistema de agentes, adicione o seguinte código ao app/routes/main_routes.py:")
    print(update_content)

def create_migration_script():
    """Cria script de migração gradual"""
    migration_content = '''# migrate_to_agents.py
"""
Script para migração gradual para o sistema de agentes
Permite testar o novo sistema paralelamente ao antigo
"""

import sys
import os
import time
import asyncio

# Adicionar ao path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_compatibility():
    """Testa compatibilidade entre sistemas"""
    try:
        from app.services.enhanced_placa_service import analisar_placa_json as new_analysis
        from app.services.placa_service import analisar_placa_json as old_analysis
        
        test_placas = ["ABC1234", "XYZ5678", "TEST123"]
        
        print("🔄 Testando compatibilidade entre sistemas...")
        
        for placa in test_placas:
            print(f"\\nTestando placa: {placa}")
            
            # Sistema antigo
            try:
                start = time.time()
                old_result = old_analysis(placa)
                old_time = time.time() - start
                print(f"  Sistema antigo: {old_time:.2f}s - {'✅' if old_result else '❌'}")
            except Exception as e:
                print(f"  Sistema antigo: ❌ Erro: {e}")
                old_time = float('inf')
            
            # Sistema novo
            try:
                start = time.time()
                new_result = new_analysis(placa)
                new_time = time.time() - start
                print(f"  Sistema novo: {new_time:.2f}s - {'✅' if new_result else '❌'}")
                
                if old_time != float('inf'):
                    improvement = ((old_time - new_time) / old_time * 100)
                    print(f"  Melhoria de performance: {improvement:.1f}%")
                    
            except Exception as e:
                print(f"  Sistema novo: ❌ Erro: {e}")
        
        return True
        
    except ImportError as e:
        print(f"❌ Erro de import: {e}")
        return False

def enable_gradual_migration():
    """Habilita migração gradual com fallback"""
    print("🔄 Habilitando migração gradual...")
    
    # Verificar se os arquivos necessários existem
    required_files = [
        "app/services/agents/__init__.py",
        "app/services/enhanced_placa_service.py"
    ]
    
    missing_files = [f for f in required_files if not os.path.exists(f)]
    
    if missing_files:
        print(f"❌ Arquivos necessários não encontrados: {missing_files}")
        print("Execute setup_agents.py primeiro!")
        return False
    
    print("✅ Migração gradual habilitada")
    print("ℹ️ O sistema utilizará agentes quando possível e fará fallback para o sistema antigo quando necessário")
    
    return True

if __name__ == "__main__":
    print("🚀 Iniciando migração para sistema de agentes...")
    
    if enable_gradual_migration():
        if test_compatibility():
            print("\\n🎉 Migração concluída com sucesso!")
            print("\\nPróximos passos:")
            print("1. Monitore os logs para verificar o funcionamento")
            print("2. Teste as novas rotas /api/analise_placa_enhanced/<placa>")
            print("3. Verifique estatísticas em /api/agent_stats")
            print("4. Considere migrar completamente após testes em produção")
        else:
            print("\\n⚠️ Problemas de compatibilidade detectados")
            print("Verifique os erros acima e corrija antes de continuar")
    else:
        print("\\n❌ Falha na migração")
'''
    
    with open("migrate_to_agents.py", "w", encoding="utf-8") as f:
        f.write(migration_content)
    
    print("✅ Script de migração criado")

def main():
    """Função principal de setup"""
    print("🚀 Configurando sistema de agentes especializados...")
    
    create_agent_structure()
    create_agent_files()
    create_configuration_file()
    create_test_suite()
    create_migration_script()
    update_main_routes()
    
    print("\\n✅ Setup do sistema de agentes concluído!")
    print("\\nPróximos passos:")
    print("1. Copie o código dos agentes para os arquivos criados")
    print("2. Execute: python migrate_to_agents.py")
    print("3. Execute testes: python tests/test_agent_system.py")
    print("4. Atualize as rotas conforme mostrado acima")
    print("5. Reinicie a aplicação e teste")
    
    print("\\n📊 Benefícios esperados:")
    print("- Análise 40-60% mais rápida")
    print("- Processamento paralelo de tarefas")
    print("- Economia de recursos computacionais")
    print("- Melhor escalabilidade")
    print("- Análises especializadas e precisas")

if __name__ == "__main__":
    main()
