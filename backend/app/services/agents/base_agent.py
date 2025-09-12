# app/services/agents/base_agent.py
"""
Sistema de Agentes Especializados para Análise de Placas
Cada agente é responsável por uma tarefa específica, permitindo:
- Processamento paralelo
- Economia de recursos
- Especialização de análise
- Escalabilidade
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, List, Any, Optional, Union
from concurrent.futures import ThreadPoolExecutor, as_completed
import asyncio
import time
from enum import Enum

class AgentType(Enum):
    """Tipos de agentes especializados disponíveis"""
    DATA_COLLECTOR = "data_collector"
    ROUTE_ANALYZER = "route_analyzer"
    SEMANTIC_ANALYZER = "semantic_analyzer"  
    RISK_CALCULATOR = "risk_calculator"
    REPORT_GENERATOR = "report_generator"

class Priority(Enum):
    """Níveis de prioridade para tarefas"""
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4

@dataclass
class AnalysisTask:
    """Representa uma tarefa de análise para ser processada por um agente"""
    task_id: str
    agent_type: AgentType
    data: Dict[str, Any]
    priority: Priority = Priority.MEDIUM
    timeout: float = 30.0
    dependencies: List[str] = None
    
    def __post_init__(self):
        if self.dependencies is None:
            self.dependencies = []

@dataclass
class AgentResult:
    """Resultado produzido por um agente"""
    agent_type: AgentType
    task_id: str
    success: bool
    data: Dict[str, Any]
    execution_time: float
    error: Optional[str] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}

class BaseAgent(ABC):
    """Classe base para todos os agentes especializados"""
    
    def __init__(self, agent_type: AgentType, max_concurrent_tasks: int = 3):
        self.agent_type = agent_type
        self.max_concurrent_tasks = max_concurrent_tasks
        self.active_tasks = 0
        self.total_processed = 0
        self.total_errors = 0
        self.start_time = time.time()
        
    @abstractmethod
    async def process(self, task: AnalysisTask) -> AgentResult:
        """
        Processa uma tarefa específica do agente
        
        Args:
            task: Tarefa a ser processada
            
        Returns:
            AgentResult com o resultado da análise
        """
        pass
    
    def can_process(self) -> bool:
        """Verifica se o agente pode processar mais tarefas"""
        return self.active_tasks < self.max_concurrent_tasks
    
    def get_load(self) -> float:
        """Retorna a carga atual do agente (0.0 a 1.0)"""
        return self.active_tasks / self.max_concurrent_tasks
    
    def get_stats(self) -> Dict[str, Any]:
        """Retorna estatísticas do agente"""
        uptime = time.time() - self.start_time
        return {
            "agent_type": self.agent_type.value,
            "active_tasks": self.active_tasks,
            "max_concurrent_tasks": self.max_concurrent_tasks,
            "total_processed": self.total_processed,
            "total_errors": self.total_errors,
            "success_rate": (self.total_processed - self.total_errors) / max(self.total_processed, 1),
            "current_load": self.get_load(),
            "uptime_seconds": uptime,
            "avg_tasks_per_hour": (self.total_processed / max(uptime / 3600, 0.01))
        }
    
    async def _execute_with_timeout(self, task: AnalysisTask) -> AgentResult:
        """Executa uma tarefa com timeout"""
        try:
            result = await asyncio.wait_for(self.process(task), timeout=task.timeout)
            return result
        except asyncio.TimeoutError:
            self.total_errors += 1
            return AgentResult(
                agent_type=self.agent_type,
                task_id=task.task_id,
                success=False,
                data={},
                execution_time=task.timeout,
                error=f"Timeout após {task.timeout}s"
            )
        except Exception as e:
            self.total_errors += 1
            return AgentResult(
                agent_type=self.agent_type,
                task_id=task.task_id,
                success=False,
                data={},
                execution_time=0.0,
                error=str(e)
            )

class AgentOrchestrator:
    """Coordena a execução de múltiplos agentes especializados"""
    
    def __init__(self):
        self.agents: Dict[AgentType, BaseAgent] = {}
        self.task_queue: List[AnalysisTask] = []
        self.completed_tasks: Dict[str, AgentResult] = {}
        self.executor = ThreadPoolExecutor(max_workers=10)
        self._running_tasks: Dict[str, asyncio.Task] = {}
        
    def register_agent(self, agent: BaseAgent):
        """Registra um agente no orquestrador"""
        self.agents[agent.agent_type] = agent
        print(f"✅ Agente {agent.agent_type.value} registrado")
        
    def get_agent(self, agent_type: AgentType) -> Optional[BaseAgent]:
        """Retorna um agente específico"""
        return self.agents.get(agent_type)
        
    async def submit_task(self, task: AnalysisTask) -> str:
        """Submete uma tarefa para processamento"""
        self.task_queue.append(task)
        return task.task_id
    
    async def execute_analysis(self, placa: str, analysis_types: Optional[List[AgentType]] = None) -> Dict[str, AgentResult]:
        """Executa análise completa de uma placa usando agentes especializados"""
        if analysis_types is None:
            analysis_types = [AgentType.DATA_COLLECTOR, AgentType.ROUTE_ANALYZER, 
                            AgentType.SEMANTIC_ANALYZER, AgentType.RISK_CALCULATOR]
        
        # Criar tarefas
        tasks = []
        task_id_base = f"{placa}_{int(time.time())}"
        
        # 1. Coleta de dados (deve ser primeira)
        if AgentType.DATA_COLLECTOR in analysis_types:
            data_task = AnalysisTask(
                task_id=f"{task_id_base}_data",
                agent_type=AgentType.DATA_COLLECTOR,
                data={"placa": placa},
                priority=Priority.HIGH
            )
            tasks.append(data_task)
        
        # 2. Análises especializadas (dependem dos dados)
        data_task_id = f"{task_id_base}_data"
        
        if AgentType.ROUTE_ANALYZER in analysis_types:
            route_task = AnalysisTask(
                task_id=f"{task_id_base}_route",
                agent_type=AgentType.ROUTE_ANALYZER,
                data={"placa": placa},
                dependencies=[data_task_id] if AgentType.DATA_COLLECTOR in analysis_types else []
            )
            tasks.append(route_task)
            
        if AgentType.SEMANTIC_ANALYZER in analysis_types:
            semantic_task = AnalysisTask(
                task_id=f"{task_id_base}_semantic",
                agent_type=AgentType.SEMANTIC_ANALYZER,
                data={"placa": placa},
                dependencies=[data_task_id] if AgentType.DATA_COLLECTOR in analysis_types else []
            )
            tasks.append(semantic_task)
        
        # 3. Cálculo de risco (depende das análises anteriores)
        if AgentType.RISK_CALCULATOR in analysis_types:
            risk_deps = []
            if AgentType.DATA_COLLECTOR in analysis_types:
                risk_deps.append(data_task_id)
            
            # Adicionar dependências de análises específicas
            for task in tasks:
                if task.agent_type in [AgentType.ROUTE_ANALYZER, AgentType.SEMANTIC_ANALYZER]:
                    risk_deps.append(task.task_id)
            
            risk_task = AnalysisTask(
                task_id=f"{task_id_base}_risk",
                agent_type=AgentType.RISK_CALCULATOR,
                data={"placa": placa},
                dependencies=risk_deps
            )
            tasks.append(risk_task)
        
        # Executar tarefas respeitando dependências
        results = await self._execute_tasks_with_dependencies(tasks)
        
        return results
    
    async def _execute_tasks_with_dependencies(self, tasks: List[AnalysisTask]) -> Dict[str, AgentResult]:
        """Executa tarefas respeitando suas dependências"""
        completed = {}
        remaining_tasks = tasks.copy()
        max_rounds = 10  # Evitar loops infinitos
        round_count = 0
        
        while remaining_tasks and round_count < max_rounds:
            round_count += 1
            
            # Encontrar tarefas que podem ser executadas agora
            ready_tasks = []
            for task in remaining_tasks:
                dependencies_met = all(dep_id in completed for dep_id in task.dependencies)
                if dependencies_met:
                    ready_tasks.append(task)
            
            if not ready_tasks:
                # Possível deadlock ou dependências não resolvidas
                print(f"⚠️ Nenhuma tarefa pronta no round {round_count}")
                break
            
            # Executar tarefas prontas em paralelo
            futures = []
            for task in ready_tasks:
                if task.agent_type in self.agents:
                    agent = self.agents[task.agent_type]
                    
                    # Verificar se agente pode processar
                    if not agent.can_process():
                        continue
                    
                    # Adicionar dados de dependências ao contexto da tarefa
                    if task.dependencies:
                        dependency_results = {}
                        for dep_id in task.dependencies:
                            if dep_id in completed and completed[dep_id].success:
                                dependency_results[dep_id] = completed[dep_id].data
                        task.data["dependency_results"] = dependency_results
                    
                    future = asyncio.create_task(agent._execute_with_timeout(task))
                    futures.append((task, future))
                else:
                    # Agente não encontrado
                    error_result = AgentResult(
                        agent_type=task.agent_type,
                        task_id=task.task_id,
                        success=False,
                        data={},
                        execution_time=0.0,
                        error=f"Agente {task.agent_type.value} não encontrado"
                    )
                    completed[task.task_id] = error_result
                    remaining_tasks.remove(task)
            
            # Aguardar conclusão das tarefas executadas
            for task, future in futures:
                try:
                    result = await future
                    completed[task.task_id] = result
                    remaining_tasks.remove(task)
                    
                    if result.success:
                        task.agent_type
                    
                except Exception as e:
                    error_result = AgentResult(
                        agent_type=task.agent_type,
                        task_id=task.task_id,
                        success=False,
                        data={},
                        execution_time=0.0,
                        error=f"Erro na execução: {str(e)}"
                    )
                    completed[task.task_id] = error_result
                    remaining_tasks.remove(task)
        
        # Verificar tarefas não completadas
        if remaining_tasks:
            print(f"⚠️ {len(remaining_tasks)} tarefas não foram completadas")
            for task in remaining_tasks:
                if task.task_id not in completed:
                    completed[task.task_id] = AgentResult(
                        agent_type=task.agent_type,
                        task_id=task.task_id,
                        success=False,
                        data={},
                        execution_time=0.0,
                        error="Tarefa não completada (dependências não resolvidas)"
                    )
        
        return completed
    
    def get_system_stats(self) -> Dict[str, Any]:
        """Retorna estatísticas do sistema de agentes"""
        agent_stats = {}
        total_processed = 0
        total_errors = 0
        
        for agent_type, agent in self.agents.items():
            stats = agent.get_stats()
            agent_stats[agent_type.value] = stats
            total_processed += stats["total_processed"]
            total_errors += stats["total_errors"]
        
        return {
            "registered_agents": len(self.agents),
            "queue_size": len(self.task_queue),
            "completed_tasks": len(self.completed_tasks),
            "total_processed": total_processed,
            "total_errors": total_errors,
            "overall_success_rate": (total_processed - total_errors) / max(total_processed, 1),
            "system_load": sum(agent.get_load() for agent in self.agents.values()) / max(len(self.agents), 1),
            "agent_stats": agent_stats,
            "timestamp": time.time()
        }
    
    def get_agent_load_balancing_info(self) -> Dict[str, Any]:
        """Retorna informações para balanceamento de carga"""
        load_info = {}
        
        for agent_type, agent in self.agents.items():
            load_info[agent_type.value] = {
                "current_load": agent.get_load(),
                "can_process": agent.can_process(),
                "active_tasks": agent.active_tasks,
                "max_concurrent": agent.max_concurrent_tasks,
                "total_processed": agent.total_processed,
                "success_rate": agent.get_stats()["success_rate"]
            }
        
        return load_info
    
    async def shutdown(self):
        """Finaliza o orquestrador de forma segura"""
        print("🔄 Finalizando orquestrador...")
        
        # Cancelar tarefas em execução
        for task_id, task in self._running_tasks.items():
            if not task.done():
                task.cancel()
        
        # Aguardar finalização das tarefas canceladas
        if self._running_tasks:
            await asyncio.gather(*self._running_tasks.values(), return_exceptions=True)
        
        # Finalizar executor
        self.executor.shutdown(wait=True)
        
        print("✅ Orquestrador finalizado")

# Singleton para o orquestrador
_orchestrator = None

def get_orchestrator() -> AgentOrchestrator:
    """Retorna a instância singleton do orquestrador"""
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = AgentOrchestrator()
    return _orchestrator