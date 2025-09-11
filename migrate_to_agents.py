# migrate_to_agents.py
"""
Script para testar e migrar para o sistema de agentes especializados
"""

import asyncio
import time
import sys
import os

# Adicionar o diretório raiz ao path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.services.placa_service import get_enhanced_placa_service
from app.services.agents import Priority

async def test_single_plate_analysis():
    """Testa análise de uma única placa"""
    print("🔍 Testando análise de placa única...")
    
    service = get_enhanced_placa_service()
    
    # Teste com placa de exemplo
    test_placa = "ABC1234"
    
    start_time = time.time()
    result = await service.analyze_placa_comprehensive(test_placa, Priority.HIGH)
    execution_time = time.time() - start_time
    
    print(f"✅ Análise completa executada em {execution_time:.2f}s")
    print(f"   Placa: {result['placa']}")
    print(f"   Sucesso: {result['success']}")
    
    if result['success']:
        assessment = result.get('final_assessment', {})
        print(f"   Risco: {assessment.get('risk_level', 'N/A')} ({assessment.get('risk_score', 0):.2f})")
        print(f"   Passagens: {result.get('passagens_count', 0)}")
        print(f"   Ocorrências: {result.get('ocorrencias_count', 0)}")
        
        performance = result.get('performance', {})
        print(f"   Agentes executados: {performance.get('agents_executed', 0)}/{performance.get('total_agents', 0)}")
        print(f"   Taxa de sucesso: {performance.get('success_rate', 0):.2%}")
    else:
        print(f"   Erro: {result.get('error', 'Erro desconhecido')}")
    
    return result

async def test_fast_analysis():
    """Testa análise rápida"""
    print("\n⚡ Testando análise rápida...")
    
    service = get_enhanced_placa_service()
    test_placa = "XYZ5678"
    
    start_time = time.time()
    result = await service.analyze_placa_fast(test_placa)
    execution_time = time.time() - start_time
    
    print(f"✅ Análise rápida executada em {execution_time:.2f}s")
    print(f"   Modo: {result.get('analysis_mode', 'N/A')}")
    print(f"   Sucesso: {result['success']}")
    
    if result['success']:
        assessment = result.get('final_assessment', {})
        print(f"   Risco: {assessment.get('risk_level', 'N/A')}")
    
    return result

async def test_batch_analysis():
    """Testa análise em lote"""
    print("\n📦 Testando análise em lote...")
    
    service = get_enhanced_placa_service()
    test_placas = ["DEF1111", "GHI2222", "JKL3333"]
    
    start_time = time.time()
    result = await service.analyze_batch(test_placas, Priority.MEDIUM)
    execution_time = time.time() - start_time
    
    print(f"✅ Análise em lote executada em {execution_time:.2f}s")
    print(f"   Placas processadas: {result.get('placas_processed', 0)}")
    print(f"   Sucesso: {result['success']}")
    
    if result['success']:
        for placa, placa_result in result.get('results', {}).items():
            print(f"   {placa}: {placa_result['risk_level']} ({placa_result['risk_score']:.2f})")
    
    return result

async def test_system_health():
    """Testa saúde do sistema"""
    print("\n🏥 Testando saúde do sistema...")
    
    service = get_enhanced_placa_service()
    
    health = await service.health_check()
    
    print(f"✅ Sistema saudável: {health['system_healthy']}")
    print(f"   Tempo de teste: {health['test_execution_time']:.2f}s")
    print(f"   Teste passou: {health['test_success']}")
    
    # Estatísticas do orquestrador
    stats = health.get('orchestrator_stats', {})
    print(f"   Agentes registrados: {stats.get('registered_agents', 0)}")
    print(f"   Taxa geral de sucesso: {stats.get('overall_success_rate', 0):.2%}")
    
    return health

def display_orchestrator_stats():
    """Exibe estatísticas detalhadas do orquestrador"""
    print("\n📊 Estatísticas do Sistema de Agentes:")
    
    service = get_enhanced_placa_service()
    stats = service.get_orchestrator_stats()
    
    print(f"   Agentes registrados: {stats['registered_agents']}")
    print(f"   Tarefas na fila: {stats['queue_size']}")
    print(f"   Tarefas completadas: {stats['completed_tasks']}")
    print(f"   Total processado: {stats['total_processed']}")
    print(f"   Total de erros: {stats['total_errors']}")
    print(f"   Taxa de sucesso geral: {stats['overall_success_rate']:.2%}")
    
    print("\n   📈 Estatísticas por Agente:")
    for agent_name, agent_stats in stats.get('agent_stats', {}).items():
        print(f"      {agent_name}:")
        print(f"         Processados: {agent_stats['total_processed']}")
        print(f"         Erros: {agent_stats['total_errors']}")
        print(f"         Taxa de sucesso: {agent_stats['success_rate']:.2%}")
        print(f"         Carga atual: {agent_stats['current_load']:.2%}")

async def performance_benchmark():
    """Executa benchmark de performance"""
    print("\n🚀 Executando benchmark de performance...")
    
    service = get_enhanced_placa_service()
    
    # Teste de múltiplas análises simultâneas
    test_placas = [f"TEST{i:03d}" for i in range(5)]
    
    start_time = time.time()
    
    # Executar análises em paralelo
    tasks = [
        service.analyze_placa_fast(placa) 
        for placa in test_placas
    ]
    
    results = await asyncio.gather(*tasks, return_exceptions=True)
    total_time = time.time() - start_time
    
    # Analisar resultados
    successful = sum(1 for r in results if isinstance(r, dict) and r.get('success', False))
    avg_time = total_time / len(test_placas)
    
    print(f"✅ Benchmark concluído:")
    print(f"   Placas testadas: {len(test_placas)}")
    print(f"   Sucessos: {successful}/{len(test_placas)}")
    print(f"   Tempo total: {total_time:.2f}s")
    print(f"   Tempo médio por placa: {avg_time:.2f}s")
    print(f"   Throughput: {len(test_placas)/total_time:.2f} placas/segundo")

async def main():
    """Função principal do teste"""
    print("🎯 Sistema de Agentes Especializados - Teste de Migração")
    print("=" * 60)
    
    try:
        # Executar testes em sequência
        await test_single_plate_analysis()
        await test_fast_analysis()
        await test_batch_analysis()
        await test_system_health()
        
        # Exibir estatísticas
        display_orchestrator_stats()
        
        # Benchmark de performance
        await performance_benchmark()
        
        print("\n✅ Todos os testes concluídos com sucesso!")
        print("💡 O sistema de agentes está funcionando corretamente.")
        print("🔄 Você pode agora atualizar suas rotas para usar o EnhancedPlacaService.")
        
    except Exception as e:
        print(f"\n❌ Erro durante os testes: {str(e)}")
        print("🔧 Verifique a configuração do banco de dados e dependências.")
        return False
    
    return True

if __name__ == "__main__":
    # Executar testes
    success = asyncio.run(main())
    
    if success:
        print(f"\n🎉 Migração para sistema de agentes concluída!")
        print("📝 Próximos passos:")
        print("   1. Atualizar rotas para usar EnhancedPlacaService")
        print("   2. Monitorar performance em produção")
        print("   3. Ajustar configurações de agentes conforme necessário")
        exit(0)
    else:
        print(f"\n💥 Migração falhou - corrija os erros antes de prosseguir")
        exit(1)