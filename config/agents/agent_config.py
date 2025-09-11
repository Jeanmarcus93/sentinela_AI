# config/agents/agent_config.py
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
