# tests/test_agent_system.py
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
    
    print("\n🎉 Todos os testes básicos passaram!")
