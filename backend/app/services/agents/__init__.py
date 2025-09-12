"""
Sistema de Agentes Especializados para Análise de Placas
"""

from .base_agent import BaseAgent, AgentType, AnalysisTask, AgentResult, Priority, AgentOrchestrator
from .orchestrator import get_orchestrator

__all__ = [
    'BaseAgent', 'AgentType', 'AnalysisTask', 'AgentResult', 'Priority',
    'AgentOrchestrator', 'get_orchestrator'
]