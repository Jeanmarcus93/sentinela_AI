# app/services/enhanced_placa_service.py
"""
Serviço de Análise de Placas v2.0 com Agentes Especializados
Orquestra múltiplos agentes para realizar uma análise completa e detalhada.
"""

import asyncio
import time
from typing import Dict, Any, List, Optional
from dataclasses import asdict

from .agents.orchestrator import get_orchestrator, AgentOrchestrator
from .agents.specialized_agents import (
    DataCollectorAgent,
    RouteAnalyzerAgent,
    SemanticAnalyzerAgent,
    RiskCalculatorAgent
)
from .agents.base_agent import AgentType, AnalysisTask, Priority

class EnhancedPlacaService:
    """Serviço que orquestra agentes para análise de placas."""
    
    def __init__(self):
        self.orchestrator = get_orchestrator()
        self._is_initialized = False
        self._initialize_agents()
        
    def _initialize_agents(self):
        """Registra todos os agentes especializados no orquestrador."""
        if self._is_initialized:
            return
            
        print("🤖 Registrando agentes especializados...")
        self.orchestrator.register_agent(DataCollectorAgent())
        self.orchestrator.register_agent(RouteAnalyzerAgent())
        self.orchestrator.register_agent(SemanticAnalyzerAgent())
        self.orchestrator.register_agent(RiskCalculatorAgent())
        
        self._is_initialized = True
        print(f"✅ {len(self.orchestrator.agents)} agentes registrados.")

    async def analisar_placa_async(self, placa: str, priority: Priority = Priority.MEDIUM) -> Dict[str, Any]:
        """
        Executa uma análise completa de forma assíncrona.
        """
        start_time = time.time()
        
        try:
            results = await self.orchestrator.execute_analysis(placa, analysis_types=None)
            
            # Consolidar resultados
            final_assessment = self._consolidate_results(results)
            
            return {
                "placa": placa,
                "success": True,
                "execution_time": time.time() - start_time,
                "final_assessment": final_assessment,
                "detailed_results": {k: asdict(v) for k, v in results.items()}
            }
            
        except Exception as e:
            return {
                "placa": placa,
                "success": False,
                "error": f"Erro na orquestração: {str(e)}",
                "execution_time": time.time() - start_time
            }

    def analisar_placa_sync(self, placa: str, priority: Priority = Priority.MEDIUM) -> Dict[str, Any]:
        """Wrapper síncrono para a análise assíncrona."""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(self.analisar_placa_async(placa, priority))
        finally:
            loop.close()

    def get_orchestrator_stats(self) -> Dict[str, Any]:
        """Retorna estatísticas do orquestrador."""
        return self.orchestrator.get_stats()

    def get_performance_metrics(self) -> Dict[str, Any]:
        """Retorna métricas de performance."""
        # Esta função pode ser expandida no futuro
        return self.orchestrator.get_stats()

    async def health_check(self) -> Dict[str, Any]:
        """Verifica a saúde do sistema de agentes."""
        return self.orchestrator.get_system_health()

    def _consolidate_results(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Consolida os resultados dos agentes em um único objeto."""
        consolidated = {
            "risk_level": "INDETERMINADO",
            "risk_score": 0,
            "summary": "Análise incompleta",
            "recommendations": []
        }
        
        # Extrair resultado do agente de risco, que é o final
        risk_result = next((v for k, v in results.items() if v.agent_type == AgentType.RISK_CALCULATOR), None)
        
        if risk_result and risk_result.success:
            risk_data = risk_result.data
            consolidated["risk_level"] = risk_data.get("risk_level", "INDETERMINADO")
            consolidated["risk_score"] = round(risk_data.get("final_risk_score", 0) * 100)
            consolidated["recommendations"] = risk_data.get("recommendations", [])
            
            # Criar um sumário
            summary_parts = [f"Risco {consolidated['risk_level']} ({consolidated['risk_score']}%)."]
            
            route_analysis = next((v.data for k, v in results.items() if v.agent_type == AgentType.ROUTE_ANALYZER and v.success), None)
            if route_analysis:
                summary_parts.append(f"Análise de rotas: {route_analysis.get('classification', 'N/A')}.")
                
            semantic_analysis = next((v.data for k, v in results.items() if v.agent_type == AgentType.SEMANTIC_ANALYZER and v.success), None)
            if semantic_analysis:
                summary_parts.append(f"{semantic_analysis.get('high_risk_reports', 0)} relato(s) de alto risco.")

            consolidated["summary"] = " ".join(summary_parts)

        return consolidated

# Singleton para o serviço
_enhanced_service_instance = None

def get_enhanced_placa_service() -> EnhancedPlacaService:
    """Retorna a instância singleton do serviço."""
    global _enhanced_service_instance
    if _enhanced_service_instance is None:
        _enhanced_service_instance = EnhancedPlacaService()
    return _enhanced_service_instance

# Funções de conveniência para rotas
async def quick_risk_analysis(placa: str) -> Dict[str, Any]:
    """Análise rápida focada em risco."""
    service = get_enhanced_placa_service()
    analysis_types = [
        AgentType.DATA_COLLECTOR,
        AgentType.ROUTE_ANALYZER,
        AgentType.RISK_CALCULATOR,
    ]
    return await service.orchestrator.execute_analysis(placa, analysis_types)

async def route_analysis_only(placa: str) -> Dict[str, Any]:
    """Análise focada apenas em rotas."""
    service = get_enhanced_placa_service()
    analysis_types = [
        AgentType.DATA_COLLECTOR,
        AgentType.ROUTE_ANALYZER,
    ]
    return await service.orchestrator.execute_analysis(placa, analysis_types)

async def semantic_analysis_only(placa: str) -> Dict[str, Any]:
    """Análise focada apenas em relatos."""
    service = get_enhanced_placa_service()
    analysis_types = [
        AgentType.DATA_COLLECTOR,
        AgentType.SEMANTIC_ANALYZER,
    ]
    return await service.orchestrator.execute_analysis(placa, analysis_types)
