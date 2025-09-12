# config/agents/__init__.py
"""
Configurações dos Agentes Especializados
Centraliza todas as configurações relacionadas ao sistema de agentes
"""

import os
import json
from typing import Dict, Any, Optional, List
from pathlib import Path
from dataclasses import dataclass, asdict
from enum import Enum

# =============================================================================
# TIPOS E ENUMS
# =============================================================================

class AgentType(Enum):
    """Tipos de agentes disponíveis"""
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

class ExecutionMode(Enum):
    """Modos de execução dos agentes"""
    SEQUENTIAL = "sequential"
    PARALLEL = "parallel"
    PIPELINE = "pipeline"
    ADAPTIVE = "adaptive"

# =============================================================================
# CONFIGURAÇÕES DOS AGENTES
# =============================================================================

@dataclass
class AgentConfig:
    """Configuração individual de um agente"""
    max_concurrent_tasks: int = 5
    timeout_seconds: float = 30.0
    retry_attempts: int = 3
    retry_delay: float = 1.0
    enable_caching: bool = True
    cache_ttl_seconds: int = 600
    memory_limit_mb: Optional[int] = None
    cpu_limit_percent: Optional[float] = None

@dataclass
class OrchestratorConfig:
    """Configuração do orquestrador de agentes"""
    max_total_concurrent_tasks: int = 20
    task_timeout_seconds: float = 120.0
    enable_load_balancing: bool = True
    enable_auto_scaling: bool = False
    health_check_interval: int = 60
    metrics_retention_hours: int = 24
    enable_performance_monitoring: bool = True
    log_agent_activities: bool = True

@dataclass
class SystemConfig:
    """Configuração geral do sistema de agentes"""
    execution_mode: ExecutionMode = ExecutionMode.PIPELINE
    enable_distributed_execution: bool = False
    max_memory_usage_mb: int = 2048
    temp_directory: str = "/tmp/sentinela_agents"
    backup_enabled: bool = True
    backup_interval_hours: int = 6

# =============================================================================
# CONFIGURAÇÕES ESPECÍFICAS POR AGENTE
# =============================================================================

# Data Collector Agent
DATA_COLLECTOR_CONFIG = AgentConfig(
    max_concurrent_tasks=8,
    timeout_seconds=20.0,
    retry_attempts=2,
    enable_caching=True,
    cache_ttl_seconds=300,  # 5 minutos
    memory_limit_mb=512
)

# Route Analyzer Agent  
ROUTE_ANALYZER_CONFIG = AgentConfig(
    max_concurrent_tasks=4,
    timeout_seconds=45.0,
    retry_attempts=3,
    enable_caching=True,
    cache_ttl_seconds=900,  # 15 minutos
    memory_limit_mb=1024
)

# Semantic Analyzer Agent
SEMANTIC_ANALYZER_CONFIG = AgentConfig(
    max_concurrent_tasks=3,
    timeout_seconds=60.0,
    retry_attempts=2,
    enable_caching=True,
    cache_ttl_seconds=1800,  # 30 minutos
    memory_limit_mb=1536
)

# Risk Calculator Agent
RISK_CALCULATOR_CONFIG = AgentConfig(
    max_concurrent_tasks=6,
    timeout_seconds=15.0,
    retry_attempts=1,
    enable_caching=True,
    cache_ttl_seconds=600,  # 10 minutos
    memory_limit_mb=256
)

# Report Generator Agent
REPORT_GENERATOR_CONFIG = AgentConfig(
    max_concurrent_tasks=2,
    timeout_seconds=90.0,
    retry_attempts=2,
    enable_caching=False,  # Relatórios sempre frescos
    memory_limit_mb=512
)

# =============================================================================
# CONFIGURAÇÃO CENTRALIZADA
# =============================================================================

class AgentsConfiguration:
    """Classe principal para configurações dos agentes"""
    
    def __init__(self):
        self.orchestrator = OrchestratorConfig()
        self.system = SystemConfig()
        self.agents = {
            AgentType.DATA_COLLECTOR: DATA_COLLECTOR_CONFIG,
            AgentType.ROUTE_ANALYZER: ROUTE_ANALYZER_CONFIG,
            AgentType.SEMANTIC_ANALYZER: SEMANTIC_ANALYZER_CONFIG,
            AgentType.RISK_CALCULATOR: RISK_CALCULATOR_CONFIG,
            AgentType.REPORT_GENERATOR: REPORT_GENERATOR_CONFIG
        }
        
        # Carregar configurações personalizadas se existirem
        self._load_custom_config()
        
        # Aplicar variáveis de ambiente
        self._apply_env_overrides()
    
    def get_agent_config(self, agent_type: AgentType) -> AgentConfig:
        """Retorna configuração de um agente específico"""
        return self.agents.get(agent_type, AgentConfig())
    
    def set_agent_config(self, agent_type: AgentType, config: AgentConfig):
        """Define configuração para um agente"""
        self.agents[agent_type] = config
    
    def get_all_configs(self) -> Dict[str, Any]:
        """Retorna todas as configurações em formato dict"""
        return {
            "orchestrator": asdict(self.orchestrator),
            "system": asdict(self.system),
            "agents": {
                agent_type.value: asdict(config)
                for agent_type, config in self.agents.items()
            }
        }
    
    def _load_custom_config(self):
        """Carrega configurações personalizadas de arquivo JSON"""
        config_file = Path(__file__).parent / "custom_config.json"
        
        if config_file.exists():
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    custom_config = json.load(f)
                
                # Aplicar configurações do orquestrador
                if "orchestrator" in custom_config:
                    self._update_dataclass(self.orchestrator, custom_config["orchestrator"])
                
                # Aplicar configurações do sistema
                if "system" in custom_config:
                    self._update_dataclass(self.system, custom_config["system"])
                
                # Aplicar configurações dos agentes
                if "agents" in custom_config:
                    for agent_name, agent_config in custom_config["agents"].items():
                        try:
                            agent_type = AgentType(agent_name)
                            if agent_type in self.agents:
                                self._update_dataclass(self.agents[agent_type], agent_config)
                        except ValueError:
                            print(f"⚠️ Tipo de agente desconhecido: {agent_name}")
                
                print("✅ Configurações personalizadas carregadas")
                
            except Exception as e:
                print(f"⚠️ Erro ao carregar configurações personalizadas: {e}")
    
    def _apply_env_overrides(self):
        """Aplica sobrescritas das variáveis de ambiente"""
        # Configurações do orquestrador
        if os.getenv('AGENT_MAX_CONCURRENT'):
            self.orchestrator.max_total_concurrent_tasks = int(os.getenv('AGENT_MAX_CONCURRENT'))
        
        if os.getenv('AGENT_TASK_TIMEOUT'):
            self.orchestrator.task_timeout_seconds = float(os.getenv('AGENT_TASK_TIMEOUT'))
        
        if os.getenv('AGENT_LOAD_BALANCING'):
            self.orchestrator.enable_load_balancing = os.getenv('AGENT_LOAD_BALANCING').lower() == 'true'
        
        # Configurações específicas por agente
        for agent_type in self.agents:
            prefix = f"AGENT_{agent_type.value.upper()}"
            config = self.agents[agent_type]
            
            if os.getenv(f'{prefix}_MAX_TASKS'):
                config.max_concurrent_tasks = int(os.getenv(f'{prefix}_MAX_TASKS'))
            
            if os.getenv(f'{prefix}_TIMEOUT'):
                config.timeout_seconds = float(os.getenv(f'{prefix}_TIMEOUT'))
            
            if os.getenv(f'{prefix}_CACHE_TTL'):
                config.cache_ttl_seconds = int(os.getenv(f'{prefix}_CACHE_TTL'))
    
    def _update_dataclass(self, instance, updates: Dict[str, Any]):
        """Atualiza um dataclass com valores de um dicionário"""
        for key, value in updates.items():
            if hasattr(instance, key):
                # Converter enum se necessário
                field_type = type(getattr(instance, key))
                if hasattr(field_type, '__bases__') and Enum in field_type.__bases__:
                    value = field_type(value)
                
                setattr(instance, key, value)
    
    def save_config(self, filename: Optional[str] = None):
        """Salva configurações atuais em arquivo JSON"""
        if filename is None:
            filename = Path(__file__).parent / "current_config.json"
        else:
            filename = Path(filename)
        
        try:
            config_dict = self.get_all_configs()
            
            # Converter enums para strings para serialização
            def convert_enums(obj):
                if isinstance(obj, dict):
                    return {k: convert_enums(v) for k, v in obj.items()}
                elif isinstance(obj, list):
                    return [convert_enums(item) for item in obj]
                elif isinstance(obj, Enum):
                    return obj.value
                else:
                    return obj
            
            config_dict = convert_enums(config_dict)
            
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(config_dict, f, indent=2, ensure_ascii=False)
            
            print(f"✅ Configurações salvas em: {filename}")
            
        except Exception as e:
            print(f"❌ Erro ao salvar configurações: {e}")
    
    def validate_config(self) -> List[str]:
        """Valida configurações e retorna lista de erros"""
        errors = []
        
        # Validar orquestrador
        if self.orchestrator.max_total_concurrent_tasks <= 0:
            errors.append("max_total_concurrent_tasks deve ser positivo")
        
        if self.orchestrator.task_timeout_seconds <= 0:
            errors.append("task_timeout_seconds deve ser positivo")
        
        # Validar agentes
        for agent_type, config in self.agents.items():
            prefix = f"Agent {agent_type.value}"
            
            if config.max_concurrent_tasks <= 0:
                errors.append(f"{prefix}: max_concurrent_tasks deve ser positivo")
            
            if config.timeout_seconds <= 0:
                errors.append(f"{prefix}: timeout_seconds deve ser positivo")
            
            if config.cache_ttl_seconds < 0:
                errors.append(f"{prefix}: cache_ttl_seconds deve ser não-negativo")
            
            if config.memory_limit_mb and config.memory_limit_mb <= 0:
                errors.append(f"{prefix}: memory_limit_mb deve ser positivo")
        
        # Validar consistência
        total_agent_tasks = sum(config.max_concurrent_tasks for config in self.agents.values())
        if total_agent_tasks > self.orchestrator.max_total_concurrent_tasks:
            errors.append(
                f"Soma das tarefas dos agentes ({total_agent_tasks}) "
                f"excede limite do orquestrador ({self.orchestrator.max_total_concurrent_tasks})"
            )
        
        return errors
    
    def get_performance_profile(self) -> Dict[str, Any]:
        """Retorna perfil de performance baseado nas configurações"""
        total_memory = sum(
            config.memory_limit_mb or 256 
            for config in self.agents.values()
        )
        
        total_tasks = sum(
            config.max_concurrent_tasks 
            for config in self.agents.values()
        )
        
        return {
            "estimated_memory_usage_mb": total_memory,
            "max_concurrent_tasks": total_tasks,
            "bottleneck_agents": [
                agent_type.value for agent_type, config in self.agents.items()
                if config.max_concurrent_tasks <= 2
            ],
            "high_performance_agents": [
                agent_type.value for agent_type, config in self.agents.items()
                if config.max_concurrent_tasks >= 6
            ],
            "cache_enabled_agents": [
                agent_type.value for agent_type, config in self.agents.items()
                if config.enable_caching
            ]
        }

# =============================================================================
# CONFIGURAÇÕES DE DESENVOLVIMENTO/PRODUÇÃO
# =============================================================================

def get_development_config() -> AgentsConfiguration:
    """Configuração otimizada para desenvolvimento"""
    config = AgentsConfiguration()
    
    # Reduzir limites para desenvolvimento
    for agent_config in config.agents.values():
        agent_config.max_concurrent_tasks = min(agent_config.max_concurrent_tasks, 3)
        agent_config.timeout_seconds = min(agent_config.timeout_seconds, 30.0)
        agent_config.cache_ttl_seconds = 60  # Cache mais rápido
    
    config.orchestrator.max_total_concurrent_tasks = 10
    config.orchestrator.enable_performance_monitoring = True
    config.orchestrator.log_agent_activities = True
    
    return config

def get_production_config() -> AgentsConfiguration:
    """Configuração otimizada para produção"""
    config = AgentsConfiguration()
    
    # Aumentar limites para produção
    config.orchestrator.max_total_concurrent_tasks = 50
    config.orchestrator.enable_load_balancing = True
    config.orchestrator.enable_auto_scaling = True
    
    # Configurações mais conservadoras
    for agent_config in config.agents.values():
        agent_config.retry_attempts = max(agent_config.retry_attempts, 2)
        agent_config.cache_ttl_seconds *= 2  # Cache mais duradouro
    
    return config

def get_testing_config() -> AgentsConfiguration:
    """Configuração para testes"""
    config = AgentsConfiguration()
    
    # Configurações mínimas para testes
    for agent_config in config.agents.values():
        agent_config.max_concurrent_tasks = 1
        agent_config.timeout_seconds = 10.0
        agent_config.retry_attempts = 1
        agent_config.enable_caching = False
    
    config.orchestrator.max_total_concurrent_tasks = 3
    config.orchestrator.enable_load_balancing = False
    config.orchestrator.log_agent_activities = False
    
    return config

# =============================================================================
# INSTÂNCIA GLOBAL E FUNÇÕES DE ACESSO
# =============================================================================

# Instância global (lazy loading)
_global_config = None

def get_agents_config(environment: Optional[str] = None) -> AgentsConfiguration:
    """Retorna configuração global dos agentes"""
    global _global_config
    
    if _global_config is None:
        if environment == 'development':
            _global_config = get_development_config()
        elif environment == 'production':
            _global_config = get_production_config()
        elif environment == 'testing':
            _global_config = get_testing_config()
        else:
            # Detectar ambiente automaticamente
            env = os.getenv('FLASK_ENV', 'development')
            if env == 'production':
                _global_config = get_production_config()
            elif env == 'testing':
                _global_config = get_testing_config()
            else:
                _global_config = get_development_config()
        
        # Validar configuração
        errors = _global_config.validate_config()
        if errors:
            print("⚠️ Erros de configuração encontrados:")
            for error in errors:
                print(f"   - {error}")
    
    return _global_config

def reset_config():
    """Reseta configuração global (útil para testes)"""
    global _global_config
    _global_config = None

# =============================================================================
# FUNÇÕES DE CONVENIÊNCIA
# =============================================================================

def get_agent_config(agent_type: AgentType) -> AgentConfig:
    """Função de conveniência para obter configuração de um agente"""
    return get_agents_config().get_agent_config(agent_type)

def get_orchestrator_config() -> OrchestratorConfig:
    """Função de conveniência para obter configuração do orquestrador"""
    return get_agents_config().orchestrator

def get_system_config() -> SystemConfig:
    """Função de conveniência para obter configuração do sistema"""
    return get_agents_config().system

def print_configuration_summary():
    """Imprime resumo das configurações atuais"""
    config = get_agents_config()
    profile = config.get_performance_profile()
    
    print("\n🤖 Configuração dos Agentes Especializados")
    print("=" * 50)
    print(f"📊 Memória estimada: {profile['estimated_memory_usage_mb']} MB")
    print(f"⚡ Tarefas concorrentes: {profile['max_concurrent_tasks']}")
    print(f"🔄 Modo de execução: {config.system.execution_mode.value}")
    print(f"📈 Balanceamento: {'✅' if config.orchestrator.enable_load_balancing else '❌'}")
    print(f"📝 Logs ativos: {'✅' if config.orchestrator.log_agent_activities else '❌'}")
    
    print(f"\n🚀 Agentes de alta performance: {', '.join(profile['high_performance_agents'])}")
    print(f"🐌 Possíveis gargalos: {', '.join(profile['bottleneck_agents'])}")
    print(f"💾 Cache habilitado: {', '.join(profile['cache_enabled_agents'])}")

# =============================================================================
# EXPORTS
# =============================================================================

__all__ = [
    # Enums
    'AgentType', 'Priority', 'ExecutionMode',
    
    # Classes de configuração
    'AgentConfig', 'OrchestratorConfig', 'SystemConfig', 'AgentsConfiguration',
    
    # Configurações específicas
    'DATA_COLLECTOR_CONFIG', 'ROUTE_ANALYZER_CONFIG', 'SEMANTIC_ANALYZER_CONFIG',
    'RISK_CALCULATOR_CONFIG', 'REPORT_GENERATOR_CONFIG',
    
    # Funções principais
    'get_agents_config', 'get_agent_config', 'get_orchestrator_config', 
    'get_system_config', 'reset_config',
    
    # Configurações por ambiente
    'get_development_config', 'get_production_config', 'get_testing_config',
    
    # Utilitários
    'print_configuration_summary'
]

# Inicialização automática
if __name__ == "__main__":
    print_configuration_summary()
else:
    # Log silencioso da inicialização
    config = get_agents_config()
    print(f"🤖 Sistema de Agentes configurado - {len(config.agents)} agentes registrados")