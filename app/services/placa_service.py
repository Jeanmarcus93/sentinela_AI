# app/services/enhanced_placa_service.py
"""
Serviço de análise de placas aprimorado com agentes especializados
Mantém compatibilidade com a API existente enquanto oferece análise otimizada
"""

import asyncio
import time
from typing import Dict, Any, List, Optional
import json

from app.services.agents import AgentType, get_orchestrator
from app.services.agents.specialized_agents import (
    DataCollectorAgent, 
    RouteAnalyzerAgent, 
    SemanticAnalyzerAgent, 
    RiskCalculatorAgent
)

class EnhancedPlacaService:
    """Serviço aprimorado de análise de placas usando arquitetura de agentes"""
    
    def __init__(self):
        self.orchestrator = get_orchestrator()
        self._initialize_agents()
        self._is_initialized = False
    
    def _initialize_agents(self):
        """Inicializa e registra todos os agentes especializados"""
        if not self._is_initialized:
            # Registrar agentes especializados
            self.orchestrator.register_agent(DataCollectorAgent())
            self.orchestrator.register_agent(RouteAnalyzerAgent())
            self.orchestrator.register_agent(SemanticAnalyzerAgent())
            self.orchestrator.register_agent(RiskCalculatorAgent())
            
            self._is_initialized = True
            print("✅ Agentes especializados inicializados com sucesso")
    
    async def analisar_placa_async(self, placa: str, analysis_types: Optional[List[AgentType]] = None) -> Dict[str, Any]:
        """
        Análise assíncrona completa de uma placa usando agentes especializados
        
        Args:
            placa: Placa do veículo a ser analisada
            analysis_types: Lista de tipos de análise a executar (opcional)
        
        Returns:
            Resultado consolidado da análise
        """
        try:
            start_time = time.time()
            
            # Executar análise distribuída
            results = await self.orchestrator.execute_analysis(placa, analysis_types)
            
            # Consolidar resultados
            consolidated_result = self._consolidate_results(placa, results, time.time() - start_time)
            
            return consolidated_result
            
        except Exception as e:
            return {
                "placa": placa,
                "success": False,
                "error": str(e),
                "execution_time": time.time() - start_time if 'start_time' in locals() else 0
            }
    
    def analisar_placa_sync(self, placa: str, analysis_types: Optional[List[AgentType]] = None) -> Dict[str, Any]:
        """
        Versão síncrona para compatibilidade com código existente
        """
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(self.analisar_placa_async(placa, analysis_types))
        finally:
            loop.close()
    
    def _consolidate_results(self, placa: str, results: Dict[str, Any], execution_time: float) -> Dict[str, Any]:
        """Consolida os resultados de múltiplos agentes em formato compatível"""
        
        # Extrair resultados por tipo de agente
        data_result = self._find_result_by_type(results, AgentType.DATA_COLLECTOR)
        route_result = self._find_result_by_type(results, AgentType.ROUTE_ANALYZER)
        semantic_result = self._find_result_by_type(results, AgentType.SEMANTIC_ANALYZER)
        risk_result = self._find_result_by_type(results, AgentType.RISK_CALCULATOR)
        
        # Construir resultado no formato esperado pela API existente
        consolidated = {
            "placa": placa,
            "success": True,
            "execution_time": execution_time,
            "analysis_timestamp": time.time(),
            
            # Dados coletados
            "data_quality": data_result.get("data_quality", {}) if data_result else {},
            
            # Análise de rotas (formato compatível)
            "rotas": self._format_route_analysis(route_result),
            
            # Análise de relatos (formato compatível) 
            "relatos": self._format_semantic_analysis(semantic_result),
            
            # Cálculo de risco final
            "risco": self._format_risk_analysis(risk_result),
            
            # Metadados dos agentes
            "agent_stats": {
                "total_agents_used": len([r for r in results.values() if r.success]),
                "failed_agents": len([r for r in results.values() if not r.success]),
                "parallel_execution_time": execution_time
            }
        }
        
        return consolidated
    
    def _find_result_by_type(self, results: Dict[str, Any], agent_type: AgentType) -> Optional[Dict]:
        """Encontra resultado de um tipo específico de agente"""
        for result in results.values():
            if hasattr(result, 'agent_type') and result.agent_type == agent_type:
                return result.data if result.success else None
        return None
    
    def _format_route_analysis(self, route_result: Optional[Dict]) -> Dict[str, Any]:
        """Formata resultado de análise de rotas para compatibilidade"""
        if not route_result:
            return {
                "labels": ["NORMAL"],
                "probs": [1.0],
                "classe": "NORMAL"
            }
        
        # Converter para formato esperado
        classification = route_result.get("classification", "NORMAL")
        confidence = route_result.get("confidence", 0.8)
        
        if classification == "SUSPEITO":
            return {
                "labels": ["NORMAL", "ILICITO"],
                "probs": [1 - confidence, confidence],
                "classe": "ILICITO"
            }
        else:
            return {
                "labels": ["NORMAL", "ILICITO"], 
                "probs": [confidence, 1 - confidence],
                "classe": "NORMAL"
            }
    
    def _format_semantic_analysis(self, semantic_result: Optional[Dict]) -> List[Dict[str, Any]]:
        """Formata resultado de análise semântica para compatibilidade"""
        if not semantic_result or not semantic_result.get("analyzed_reports"):
            return []
        
        formatted_reports = []
        for report in semantic_result["analyzed_reports"]:
            analysis = report.get("analysis", {})
            
            # Simular formato de probabilidades para compatibilidade
            classe = analysis.get("classe", "OUTROS")
            pontuacao = analysis.get("pontuacao", 50)
            
            # Distribuição de probabilidades baseada na classe
            if classe == "TRAFICO":
                probs = [0.1, 0.1, 0.7, 0.1]  # [OUTROS, PORTE_ARMA, TRAFICO, RECEPTACAO]
                labels = ["OUTROS", "PORTE_ARMA", "TRAFICO", "RECEPTACAO"]
            elif classe == "PORTE_ARMA":
                probs = [0.1, 0.7, 0.1, 0.1]
                labels = ["OUTROS", "PORTE_ARMA", "TRAFICO", "RECEPTACAO"]
            elif classe == "RECEPTACAO":
                probs = [0.1, 0.1, 0.1, 0.7]
                labels = ["OUTROS", "PORTE_ARMA", "TRAFICO", "RECEPTACAO"]
            else:
                probs = [0.7, 0.1, 0.1, 0.1]
                labels = ["OUTROS", "PORTE_ARMA", "TRAFICO", "RECEPTACAO"]
            
            formatted_reports.append({
                "id": report.get("ocorrencia_id"),
                "tipo": report.get("tipo"),
                "datahora": report.get("datahora"),
                "texto": report.get("relato"),
                "labels": labels,
                "probs": probs,
                "classe": classe
            })
        
        return formatted_reports
    
    def _format_risk_analysis(self, risk_result: Optional[Dict]) -> Dict[str, Any]:
        """Formata resultado de cálculo de risco para compatibilidade"""
        if not risk_result:
            return {
                "rotas": 0.0,
                "relatos": 0.0, 
                "final": 0.0
            }
        
        component_scores = risk_result.get("component_scores", {})
        
        return {
            "rotas": component_scores.get("route_risk", 0.0),
            "relatos": component_scores.get("semantic_risk", 0.0),
            "final": risk_result.get("final_risk_score", 0.0),
            "level": risk_result.get("risk_level", "BAIXO"),
            "confidence": risk_result.get("confidence", 0.5),
            "recommendations": risk_result.get("recommendations", [])
        }
    
    async def get_system_health(self) -> Dict[str, Any]:
        """Retorna informações sobre a saúde do sistema de agentes"""
        return {
            "system_stats": self.orchestrator.get_system_stats(),
            "initialized": self._is_initialized,
            "available_agents": list(self.orchestrator.agents.keys()),
            "timestamp": time.time()
        }
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Retorna métricas de performance dos agentes"""
        metrics = {}
        for agent_type, agent in self.orchestrator.agents.items():
            metrics[agent_type.value] = agent.get_stats()
        return metrics

# Instância global para compatibilidade
_enhanced_service = None

def get_enhanced_service() -> EnhancedPlacaService:
    """Retorna instância singleton do serviço aprimorado"""
    global _enhanced_service
    if _enhanced_service is None:
        _enhanced_service = EnhancedPlacaService()
    return _enhanced_service

# Função de compatibilidade com a API existente
def analisar_placa_json(placa: str) -> Dict[str, Any]:
    """
    Função de compatibilidade que mantém a mesma assinatura da API original
    mas utiliza o sistema de agentes internamente
    """
    service = get_enhanced_service()
    return service.analisar_placa_sync(placa)

# Funções de análise específicas para uso direto
async def quick_risk_analysis(placa: str) -> Dict[str, Any]:
    """Análise rápida focada apenas em risco"""
    service = get_enhanced_service()
    return await service.analisar_placa_async(
        placa, 
        [AgentType.DATA_COLLECTOR, AgentType.RISK_CALCULATOR]
    )

async def route_analysis_only(placa: str) -> Dict[str, Any]:
    """Análise focada apenas em padrões de rotas"""
    service = get_enhanced_service()
    return await service.analisar_placa_async(
        placa,
        [AgentType.DATA_COLLECTOR, AgentType.ROUTE_ANALYZER]
    )

async def semantic_analysis_only(placa: str) -> Dict[str, Any]:
    """Análise focada apenas em relatos"""
    service = get_enhanced_service()
    return await service.analisar_placa_async(
        placa,
        [AgentType.DATA_COLLECTOR, AgentType.SEMANTIC_ANALYZER]
    )