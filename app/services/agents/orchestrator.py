# app/services/agents/orchestrator.py
"""
Implementação completa do AgentOrchestrator
"""

import asyncio
import time
from typing import Dict, List, Any, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import defaultdict

from .base_agent import BaseAgent, AgentType, AnalysisTask, AgentResult, Priority

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
        print(f"Agente {agent.agent_type.value} registrado com sucesso")
    
    def get_agent(self, agent_type: AgentType) -> Optional[BaseAgent]:
        """Retorna um agente específico"""
        return self.agents.get(agent_type)
    
    async def execute_task(self, task: AnalysisTask) -> AgentResult:
        """Executa uma única tarefa"""
        agent = self.agents.get(task.agent_type)
        if not agent:
            return AgentResult(
                agent_type=task.agent_type,
                task_id=task.task_id,
                success=False,
                data={},
                execution_time=0.0,
                error=f"Agente {task.agent_type.value} não encontrado"
            )
        
        # Verificar se o agente pode processar
        if not agent.can_process():
            return AgentResult(
                agent_type=task.agent_type,
                task_id=task.task_id,
                success=False,
                data={},
                execution_time=0.0,
                error="Agente sobrecarregado"
            )
        
        # Executar tarefa
        try:
            result = await asyncio.wait_for(agent.process(task), timeout=task.timeout)
            self.completed_tasks[task.task_id] = result
            return result
        except asyncio.TimeoutError:
            return AgentResult(
                agent_type=task.agent_type,
                task_id=task.task_id,
                success=False,
                data={},
                execution_time=task.timeout,
                error="Timeout na execução da tarefa"
            )
        except Exception as e:
            return AgentResult(
                agent_type=task.agent_type,
                task_id=task.task_id,
                success=False,
                data={},
                execution_time=0.0,
                error=str(e)
            )
    
    async def execute_pipeline(self, tasks: List[AnalysisTask]) -> Dict[str, AgentResult]:
        """
        Executa um pipeline de tarefas respeitando dependências
        """
        if not tasks:
            return {}
        
        # Criar mapeamento de tarefas
        task_map = {task.task_id: task for task in tasks}
        completed_results = {}
        pending_tasks = set(task.task_id for task in tasks)
        
        # Executar em rounds até completar todas as tarefas
        max_rounds = 10  # Evitar loops infinitos
        round_count = 0
        
        while pending_tasks and round_count < max_rounds:
            round_count += 1
            current_round_tasks = []
            
            # Identificar tarefas que podem ser executadas neste round
            for task_id in list(pending_tasks):
                task = task_map[task_id]
                
                # Verificar se todas as dependências foram resolvidas
                dependencies_met = all(
                    dep_id in completed_results 
                    for dep_id in task.dependencies
                )
                
                if dependencies_met:
                    # Adicionar resultados das dependências aos dados da tarefa
                    if task.dependencies:
                        dependency_results = {
                            dep_id: completed_results[dep_id].data 
                            for dep_id in task.dependencies
                            if dep_id in completed_results and completed_results[dep_id].success
                        }
                        task.data["dependency_results"] = dependency_results
                    
                    current_round_tasks.append(task)
                    pending_tasks.remove(task_id)
            
            if not current_round_tasks:
                # Nenhuma tarefa pode ser executada - possível ciclo ou dependência não resolvida
                print(f"Aviso: {len(pending_tasks)} tarefas não puderam ser executadas devido a dependências não resolvidas")
                break
            
            # Executar tarefas do round atual em paralelo
            round_results = await self._execute_parallel_tasks(current_round_tasks)
            completed_results.update(round_results)
        
        return completed_results
    
    async def _execute_parallel_tasks(self, tasks: List[AnalysisTask]) -> Dict[str, AgentResult]:
        """Executa múltiplas tarefas em paralelo"""
        if not tasks:
            return {}
        
        # Criar tarefas assíncronas
        async_tasks = []
        for task in tasks:
            async_task = asyncio.create_task(self.execute_task(task))
            async_tasks.append((task.task_id, async_task))
        
        # Aguardar conclusão de todas as tarefas
        results = {}
        for task_id, async_task in async_tasks:
            try:
                result = await async_task
                results[task_id] = result
            except Exception as e:
                results[task_id] = AgentResult(
                    agent_type=AgentType.DATA_COLLECTOR,  # Fallback
                    task_id=task_id,
                    success=False,
                    data={},
                    execution_time=0.0,
                    error=f"Erro na execução paralela: {str(e)}"
                )
        
        return results
    
    def add_task(self, task: AnalysisTask):
        """Adiciona uma tarefa à fila"""
        self.task_queue.append(task)
    
    def get_queue_size(self) -> int:
        """Retorna o tamanho atual da fila"""
        return len(self.task_queue)
    
    def get_stats(self) -> Dict[str, Any]:
        """Retorna estatísticas do orquestrador"""
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
            "agent_stats": agent_stats,
            "timestamp": time.time()
        }
    
    async def clear_completed_tasks(self, older_than_seconds: int = 3600):
        """Remove tarefas completadas antigas para liberar memória"""
        current_time = time.time()
        tasks_to_remove = []
        
        for task_id, result in self.completed_tasks.items():
            # Assumir que tarefas sem timestamp são antigas
            task_age = current_time - result.metadata.get("timestamp", 0)
            if task_age > older_than_seconds:
                tasks_to_remove.append(task_id)
        
        for task_id in tasks_to_remove:
            del self.completed_tasks[task_id]
        
        print(f"Removidas {len(tasks_to_remove)} tarefas antigas do cache")
    
    def get_agent_load_balancing_info(self) -> Dict[str, Any]:
        """Retorna informações para balanceamento de carga"""
        load_info = {}
        
        for agent_type, agent in self.agents.items():
            load_info[agent_type.value] = {
                "current_load": agent.get_load(),
                "can_process": agent.can_process(),
                "active_tasks": agent.active_tasks,
                "max_concurrent": agent.max_concurrent_tasks
            }
        
        return load_info
    
    async def shutdown(self):
        """Finaliza o orquestrador de forma segura"""
        # Cancelar tarefas em execução
        for task_id, task in self._running_tasks.items():
            if not task.done():
                task.cancel()
        
        # Aguardar finalização das tarefas canceladas
        if self._running_tasks:
            await asyncio.gather(*self._running_tasks.values(), return_exceptions=True)
        
        # Finalizar executor
        self.executor.shutdown(wait=True)
        
        print("Orquestrador finalizado com sucesso")


# Instância global do orquestrador
_orchestrator_instance = None

def get_orchestrator() -> AgentOrchestrator:
    """Retorna instância singleton do orquestrador"""
    global _orchestrator_instance
    if _orchestrator_instance is None:
        _orchestrator_instance = AgentOrchestrator()
    return _orchestrator_instance