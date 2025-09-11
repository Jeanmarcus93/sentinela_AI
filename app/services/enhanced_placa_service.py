# app/services/enhanced_placa_service.py
"""
Serviço Aprimorado de Análise de Placas usando Sistema de Agentes
"""

import asyncio
import time
import uuid
from typing import Dict, Any, Optional
from dataclasses import asdict

from app.services.agents import get_orchestrator, AnalysisTask, AgentType, Priority
from app.services.agents.specialized_agents import (
    DataCollectorAgent, RouteAnalyzerAgent, 
    SemanticAnalyzerAgent, RiskCalculatorAgent
)

class EnhancedPlacaService:
    """Serviço aprimorado de análise de placas usando agentes especializados"""
    
    def __init__(self):
        self.orchestrator = get_orchestrator()
        self._initialize_agents()
    
    def _initialize_agents(self):
        """Inicializa e registra todos os agentes especializados"""
        agents = [
            DataCollectorAgent(),
            RouteAnalyzerAgent(),
            SemanticAnalyzerAgent(),
            RiskCalculatorAgent()
        ]
        
        for agent in agents:
            self.orchestrator.register_agent(agent)
    
    async def analyze_placa_comprehensive(self, placa: str, priority: Priority = Priority.MEDIUM) -> Dict[str, Any]:
        """
        Análise completa de uma placa usando todos os agentes disponíveis
        
        Args:
            placa: Placa do veículo
            priority: Prioridade da análise
            
        Returns:
            Dict com análise completa
        """
        analysis_id = str(uuid.uuid4())
        start_time = time.time()
        
        try:
            # 1. Criar tarefa de coleta de dados (sem dependências)
            data_task = AnalysisTask(
                task_id=f"{analysis_id}_data",
                agent_type=AgentType.DATA_COLLECTOR,
                data={"placa": placa},
                priority=priority,
                timeout=30.0
            )
            
            # 2. Criar tarefas de análise (dependem da coleta de dados)
            route_task = AnalysisTask(
                task_id=f"{analysis_id}_route",
                agent_type=AgentType.ROUTE_ANALYZER,
                data={"placa": placa},
                priority=priority,
                dependencies=[data_task.task_id]
            )
            
            semantic_task = AnalysisTask(
                task_id=f"{analysis_id}_semantic",
                agent_type=AgentType.SEMANTIC_ANALYZER,
                data={"placa": placa},
                priority=priority,
                dependencies=[data_task.task_id]
            )
            
            # 3. Criar tarefa de cálculo final (depende das análises)
            risk_task = AnalysisTask(
                task_id=f"{analysis_id}_risk",
                agent_type=AgentType.RISK_CALCULATOR,
                data={"placa": placa},
                priority=priority,
                dependencies=[route_task.task_id, semantic_task.task_id]
            )
            
            # 4. Executar pipeline
            tasks = [data_task, route_task, semantic_task, risk_task]
            results = await self.orchestrator.execute_pipeline(tasks)
            
            # 5. Consolidar resultados
            return self._consolidate_results(placa, results, start_time)
            
        except Exception as e:
            return {
                "placa": placa,
                "success": False,
                "error": str(e),
                "execution_time": time.time() - start_time,
                "timestamp": time.time()
            }
    
    async def analyze_placa_fast(self, placa: str) -> Dict[str, Any]:
        """
        Análise rápida usando apenas coleta de dados e análise de risco básica
        """
        analysis_id = str(uuid.uuid4())
        start_time = time.time()
        
        try:
            # Coleta rápida de dados
            data_task = AnalysisTask(
                task_id=f"{analysis_id}_data_fast",
                agent_type=AgentType.DATA_COLLECTOR,
                data={"placa": placa},
                priority=Priority.HIGH,
                timeout=15.0
            )
            
            # Análise básica de risco
            risk_task = AnalysisTask(
                task_id=f"{analysis_id}_risk_fast",
                agent_type=AgentType.RISK_CALCULATOR,
                data={"placa": placa},
                priority=Priority.HIGH,
                dependencies=[data_task.task_id]
            )
            
            results = await self.orchestrator.execute_pipeline([data_task, risk_task])
            return self._consolidate_results(placa, results, start_time, mode="fast")
            
        except Exception as e:
            return {
                "placa": placa,
                "success": False,
                "error": str(e),
                "execution_time": time.time() - start_time,
                "analysis_mode": "fast"
            }
    
    async def analyze_batch(self, placas: list, priority: Priority = Priority.MEDIUM) -> Dict[str, Any]:
        """
        Análise em lote de múltiplas placas
        """
        start_time = time.time()
        batch_id = str(uuid.uuid4())
        
        # Criar tasks para todas as placas
        all_tasks = []
        for i, placa in enumerate(placas):
            # Task de coleta para cada placa
            data_task = AnalysisTask(
                task_id=f"{batch_id}_data_{i}",
                agent_type=AgentType.DATA_COLLECTOR,
                data={"placa": placa},
                priority=priority
            )
            
            # Task de risco para cada placa (depende da coleta)
            risk_task = AnalysisTask(
                task_id=f"{batch_id}_risk_{i}",
                agent_type=AgentType.RISK_CALCULATOR,
                data={"placa": placa, "batch_mode": True},
                priority=priority,
                dependencies=[data_task.task_id]
            )
            
            all_tasks.extend([data_task, risk_task])
        
        try:
            results = await self.orchestrator.execute_pipeline(all_tasks)
            
            # Agrupar resultados por placa
            placa_results = {}
            for i, placa in enumerate(placas):
                data_result = results.get(f"{batch_id}_data_{i}")
                risk_result = results.get(f"{batch_id}_risk_{i}")
                
                placa_results[placa] = {
                    "placa": placa,
                    "data_collected": data_result.success if data_result else False,
                    "risk_calculated": risk_result.success if risk_result else False,
                    "risk_score": risk_result.data.get("final_risk_score", 0.0) if risk_result and risk_result.success else 0.0,
                    "risk_level": risk_result.data.get("risk_level", "BAIXO") if risk_result and risk_result.success else "BAIXO"
                }
            
            return {
                "batch_id": batch_id,
                "success": True,
                "placas_processed": len(placas),
                "results": placa_results,
                "execution_time": time.time() - start_time,
                "timestamp": time.time()
            }
            
        except Exception as e:
            return {
                "batch_id": batch_id,
                "success": False,
                "error": str(e),
                "placas_requested": len(placas),
                "execution_time": time.time() - start_time
            }
    
    def _consolidate_results(self, placa: str, results: Dict, start_time: float, mode: str = "complete") -> Dict[str, Any]:
        """Consolida resultados de múltiplos agentes"""
        
        # Extrair resultados específicos
        data_result = None
        route_result = None
        semantic_result = None
        risk_result = None
        
        for task_id, result in results.items():
            if not result.success:
                continue
                
            if result.agent_type == AgentType.DATA_COLLECTOR:
                data_result = result
            elif result.agent_type == AgentType.ROUTE_ANALYZER:
                route_result = result
            elif result.agent_type == AgentType.SEMANTIC_ANALYZER:
                semantic_result = result
            elif result.agent_type == AgentType.RISK_CALCULATOR:
                risk_result = result
        
        # Montar resposta consolidada
        response = {
            "placa": placa,
            "success": True,
            "analysis_mode": mode,
            "execution_time": time.time() - start_time,
            "timestamp": time.time()
        }
        
        # Dados básicos
        if data_result:
            response["vehicle_info"] = data_result.data.get("veiculo_info", {})
            response["data_quality"] = data_result.data.get("data_quality", {})
            response["passagens_count"] = len(data_result.data.get("passagens", []))
            response["ocorrencias_count"] = len(data_result.data.get("ocorrencias", []))
        
        # Análise de rotas
        if route_result:
            response["route_analysis"] = {
                "risk_score": route_result.data.get("risk_score", 0.0),
                "classification": route_result.data.get("classification", "NORMAL"),
                "patterns": route_result.data.get("patterns", {}),
                "confidence": route_result.data.get("confidence", 0.0)
            }
        
        # Análise semântica
        if semantic_result:
            response["semantic_analysis"] = {
                "overall_risk": semantic_result.data.get("overall_risk", 0.0),
                "reports_analyzed": len(semantic_result.data.get("analyzed_reports", [])),
                "summary": semantic_result.data.get("summary", "")
            }
        
        # Risco final
        if risk_result:
            response["final_assessment"] = {
                "risk_score": risk_result.data.get("final_risk_score", 0.0),
                "risk_level": risk_result.data.get("risk_level", "BAIXO"),
                "component_scores": risk_result.data.get("component_scores", {}),
                "confidence": risk_result.data.get("confidence", 0.0)
            }
        else:
            # Fallback se não há análise de risco
            response["final_assessment"] = {
                "risk_score": 0.0,
                "risk_level": "INDETERMINADO",
                "component_scores": {},
                "confidence": 0.0
            }
        
        # Performance metrics
        response["performance"] = {
            "agents_executed": len([r for r in results.values() if r.success]),
            "total_agents": len(results),
            "success_rate": len([r for r in results.values() if r.success]) / max(len(results), 1),
            "avg_agent_time": sum(r.execution_time for r in results.values()) / max(len(results), 1)
        }
        
        return response
    
    def get_orchestrator_stats(self) -> Dict[str, Any]:
        """Retorna estatísticas do orquestrador e agentes"""
        return self.orchestrator.get_stats()
    
    async def health_check(self) -> Dict[str, Any]:
        """Verifica saúde do sistema de agentes"""
        stats = self.get_orchestrator_stats()
        
        # Teste rápido com placa fictícia
        test_start = time.time()
        try:
            test_result = await self.analyze_placa_fast("TEST123")
            test_success = test_result.get("success", False)
            test_time = time.time() - test_start
        except:
            test_success = False
            test_time = time.time() - test_start
        
        return {
            "system_healthy": test_success and test_time < 10.0,
            "test_execution_time": test_time,
            "test_success": test_success,
            "orchestrator_stats": stats,
            "timestamp": time.time()
        }


# Instância global do serviço
_enhanced_service = None

def get_enhanced_placa_service() -> EnhancedPlacaService:
    """Retorna instância singleton do serviço aprimorado"""
    global _enhanced_service
    if _enhanced_service is None:
        _enhanced_service = EnhancedPlacaService()
    return _enhanced_service