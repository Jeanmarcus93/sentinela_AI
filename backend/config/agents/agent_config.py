# config/agents/agent_config.py
"""
Configurações detalhadas para o sistema de agentes especializados
Define parâmetros específicos, thresholds e configurações operacionais
"""

import os
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from pathlib import Path

# =============================================================================
# CONFIGURAÇÕES GERAIS DO SISTEMA
# =============================================================================

AGENT_CONFIG = {
    "max_concurrent_tasks_per_agent": 5,
    "default_task_timeout": 30.0,
    "enable_performance_monitoring": True,
    "log_agent_activities": True,
    
    # Configurações de retry e recovery
    "max_retry_attempts": 3,
    "retry_backoff_factor": 1.5,
    "circuit_breaker_enabled": True,
    "circuit_breaker_threshold": 5,
    
    # Configurações de memória
    "max_memory_per_agent_mb": 1024,
    "memory_monitoring_enabled": True,
    "garbage_collection_interval": 300,  # 5 minutos
    
    # Configurações de rede
    "connection_timeout": 10.0,
    "read_timeout": 30.0,
    "max_retries_network": 3,
}

# =============================================================================
# CONFIGURAÇÕES ESPECÍFICAS POR AGENTE
# =============================================================================

@dataclass
class DataCollectorConfig:
    """Configuração específica do Data Collector Agent"""
    # Performance
    max_concurrent_tasks: int = 8
    timeout: float = 20.0
    cache_duration: int = 300  # 5 minutos
    enable_parallel_db_queries: bool = True
    
    # Database
    query_batch_size: int = 1000
    max_db_connections: int = 5
    db_connection_timeout: float = 10.0
    enable_query_optimization: bool = True
    
    # Cache
    cache_enabled: bool = True
    cache_size_mb: int = 256
    cache_compression: bool = True
    
    # Data quality
    min_required_fields: List[str] = field(default_factory=lambda: ["placa", "datahora"])
    validate_data_integrity: bool = True
    clean_invalid_records: bool = True
    
    # Specific queries configuration
    passagens_limit: int = 10000  # Máximo de passagens por consulta
    ocorrencias_limit: int = 100   # Máximo de ocorrências por consulta
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "performance": {
                "max_concurrent_tasks": self.max_concurrent_tasks,
                "timeout": self.timeout,
                "cache_duration": self.cache_duration,
                "enable_parallel_db_queries": self.enable_parallel_db_queries
            },
            "database": {
                "query_batch_size": self.query_batch_size,
                "max_db_connections": self.max_db_connections,
                "db_connection_timeout": self.db_connection_timeout,
                "enable_query_optimization": self.enable_query_optimization
            },
            "limits": {
                "passagens_limit": self.passagens_limit,
                "ocorrencias_limit": self.ocorrencias_limit
            }
        }

@dataclass
class RouteAnalyzerConfig:
    """Configuração específica do Route Analyzer Agent"""
    # Performance
    max_concurrent_tasks: int = 4
    timeout: float = 45.0
    enable_ml_analysis: bool = True
    fallback_to_heuristics: bool = True
    
    # Machine Learning
    model_path: Optional[str] = "ml_models/trained/routes_clf.joblib"
    labels_path: Optional[str] = "ml_models/trained/routes_labels.joblib" 
    confidence_threshold: float = 0.6
    enable_model_caching: bool = True
    
    # Pattern detection
    pattern_detection_threshold: float = 0.6
    min_route_frequency: int = 3
    max_analysis_window_days: int = 90
    
    # Temporal analysis
    night_start_hour: int = 22
    night_end_hour: int = 6
    weekend_weight_factor: float = 1.2
    night_weight_factor: float = 1.5
    
    # Risk factors
    border_route_risk_multiplier: float = 2.0
    repeated_route_threshold: int = 5
    suspicious_location_multiplier: float = 1.8
    
    # Cache and optimization
    cache_route_patterns: bool = True
    pattern_cache_ttl: int = 3600  # 1 hora
    
    def get_risk_weights(self) -> Dict[str, float]:
        """Retorna pesos para diferentes fatores de risco"""
        return {
            "night_activity": 0.3,
            "route_repetition": 0.25,
            "border_proximity": 0.2,
            "suspicious_locations": 0.15,
            "frequency_anomaly": 0.1
        }

@dataclass
class SemanticAnalyzerConfig:
    """Configuração específica do Semantic Analyzer Agent"""
    # Performance
    max_concurrent_tasks: int = 3
    timeout: float = 60.0
    max_reports_per_analysis: int = 50
    enable_parallel_processing: bool = True
    
    # NLP Models
    spacy_model: str = "pt_core_news_sm"
    embedding_model: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    classifier_path: Optional[str] = "ml_models/trained/semantic_clf.joblib"
    labels_path: Optional[str] = "ml_models/trained/semantic_labels.joblib"
    
    # Text processing
    min_text_length: int = 10
    max_text_length: int = 5000
    remove_stopwords: bool = True
    normalize_text: bool = True
    
    # Classification thresholds
    confidence_threshold: float = 0.5
    multi_label_threshold: float = 0.3
    
    # Keyword extraction
    max_keywords: int = 15
    keyword_ngram_range: Tuple[int, int] = (1, 2)
    
    # Contextual analysis
    enable_context_analysis: bool = True
    context_window_size: int = 5  # Sentenças antes/depois
    
    # Cache
    cache_embeddings: bool = True
    embedding_cache_size: int = 10000
    results_cache_ttl: int = 1800  # 30 minutos
    
    # Suspicious patterns
    suspicious_keywords: List[str] = field(default_factory=lambda: [
        "traficante", "maconha", "cocaina", "crack", "arma", "droga",
        "suspeito", "nervoso", "mentiu", "fronteira", "entrega"
    ])
    
    normal_keywords: List[str] = field(default_factory=lambda: [
        "familia", "trabalho", "ferias", "turismo", "visita", "emergencia"
    ])
    
    def get_analysis_weights(self) -> Dict[str, float]:
        """Retorna pesos para diferentes tipos de análise"""
        return {
            "keyword_matching": 0.3,
            "ml_classification": 0.4,
            "contextual_analysis": 0.2,
            "entity_recognition": 0.1
        }

@dataclass
class RiskCalculatorConfig:
    """Configuração específica do Risk Calculator Agent"""
    # Performance
    max_concurrent_tasks: int = 6
    timeout: float = 15.0
    
    # Risk calculation weights
    route_weight: float = 0.4
    semantic_weight: float = 0.3
    temporal_weight: float = 0.15
    vehicle_profile_weight: float = 0.1
    historical_weight: float = 0.05
    
    # Risk thresholds
    low_risk_threshold: float = 0.3
    medium_risk_threshold: float = 0.6
    high_risk_threshold: float = 0.8
    
    # Adaptive weighting
    adaptive_weighting: bool = True
    min_data_points_for_adaptive: int = 10
    
    # Historical analysis
    historical_window_days: int = 180
    decay_factor_days: float = 30.0  # Fator de decaimento temporal
    
    # Risk factors configuration
    vehicle_factors: Dict[str, float] = field(default_factory=lambda: {
        "suspicious_profile": 0.2,
        "age_factor": 0.1,
        "type_factor": 0.15,
        "color_factor": 0.05
    })
    
    temporal_factors: Dict[str, float] = field(default_factory=lambda: {
        "night_activity": 0.4,
        "weekend_activity": 0.2,
        "frequency_anomaly": 0.25,
        "pattern_consistency": 0.15
    })
    
    # Cache and optimization
    enable_risk_caching: bool = True
    risk_cache_ttl: int = 600  # 10 minutos
    enable_incremental_calculation: bool = True
    
    def get_risk_level(self, score: float) -> str:
        """Determina nível de risco baseado no score"""
        if score >= self.high_risk_threshold:
            return "CRITICO"
        elif score >= self.medium_risk_threshold:
            return "ALTO"
        elif score >= self.low_risk_threshold:
            return "MEDIO"
        else:
            return "BAIXO"
    
    def calculate_confidence(self, data_quality: float, data_completeness: float) -> float:
        """Calcula confiança do resultado baseado na qualidade dos dados"""
        return min(1.0, (data_quality * 0.6 + data_completeness * 0.4))

@dataclass
class ReportGeneratorConfig:
    """Configuração específica do Report Generator Agent"""
    # Performance
    max_concurrent_tasks: int = 2
    timeout: float = 120.0
    
    # Report formats
    supported_formats: List[str] = field(default_factory=lambda: ["json", "pdf", "excel", "html"])
    default_format: str = "json"
    
    # Templates
    template_directory: str = "templates/reports"
    enable_custom_templates: bool = True
    
    # Content generation
    max_report_size_mb: int = 50
    include_charts: bool = True
    include_raw_data: bool = False
    
    # Localization
    default_language: str = "pt_BR"
    date_format: str = "%d/%m/%Y %H:%M"
    timezone: str = "America/Sao_Paulo"
    
    # Security
    enable_data_sanitization: bool = True
    mask_sensitive_data: bool = True
    
    sensitive_fields: List[str] = field(default_factory=lambda: [
        "cpf_cnpj", "nome_completo", "endereco"
    ])

# =============================================================================
# CONFIGURAÇÕES DE AMBIENTE
# =============================================================================

def get_environment_config() -> Dict[str, Any]:
    """Retorna configurações baseadas no ambiente"""
    env = os.getenv("FLASK_ENV", "development")
    
    base_config = {
        "environment": env,
        "debug_mode": env == "development",
        "enable_detailed_logging": env != "production",
        "enable_performance_profiling": env == "development"
    }
    
    if env == "production":
        base_config.update({
            "max_concurrent_tasks_multiplier": 2.0,
            "timeout_multiplier": 1.5,
            "cache_ttl_multiplier": 2.0,
            "enable_auto_scaling": True,
            "resource_monitoring": True
        })
    elif env == "testing":
        base_config.update({
            "max_concurrent_tasks_multiplier": 0.5,
            "timeout_multiplier": 0.5,
            "cache_ttl_multiplier": 0.1,
            "enable_caching": False,
            "simplified_analysis": True
        })
    else:  # development
        base_config.update({
            "max_concurrent_tasks_multiplier": 1.0,
            "timeout_multiplier": 1.0,
            "cache_ttl_multiplier": 0.5,
            "enable_hot_reload": True,
            "verbose_logging": True
        })
    
    return base_config

# =============================================================================
# CONFIGURAÇÕES POR TIPO DE ANÁLISE
# =============================================================================

ANALYSIS_PROFILES = {
    "quick": {
        "description": "Análise rápida com menor precisão",
        "timeout_multiplier": 0.5,
        "skip_ml_analysis": False,
        "use_cached_results": True,
        "max_data_points": 1000
    },
    
    "standard": {
        "description": "Análise padrão balanceada",
        "timeout_multiplier": 1.0,
        "skip_ml_analysis": False,
        "use_cached_results": True,
        "max_data_points": 10000
    },
    
    "comprehensive": {
        "description": "Análise completa e detalhada",
        "timeout_multiplier": 2.0,
        "skip_ml_analysis": False,
        "use_cached_results": False,
        "max_data_points": 50000,
        "include_historical_analysis": True,
        "deep_pattern_analysis": True
    },
    
    "batch": {
        "description": "Análise otimizada para lotes",
        "timeout_multiplier": 1.5,
        "batch_optimization": True,
        "shared_cache": True,
        "parallel_processing": True
    }
}

# =============================================================================
# CONFIGURAÇÕES DE MONITORAMENTO
# =============================================================================

MONITORING_CONFIG = {
    "collect_metrics": True,
    "metrics_retention_days": 7,
    "alert_on_high_error_rate": True,
    "error_rate_threshold": 0.1,  # 10%
    
    # Performance monitoring
    "track_execution_time": True,
    "track_memory_usage": True,
    "track_cpu_usage": True,
    
    # Health checks
    "health_check_interval": 60,  # segundos
    "health_check_timeout": 10,
    
    # Alertas
    "alert_thresholds": {
        "high_error_rate": 0.1,
        "high_latency_ms": 5000,
        "memory_usage_percent": 85,
        "cpu_usage_percent": 80
    },
    
    # Logs
    "log_level": "INFO",
    "log_format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    "log_rotation": True,
    "max_log_size_mb": 100,
    "backup_count": 5
}

# =============================================================================
# FUNÇÕES PRINCIPAIS
# =============================================================================

def get_agent_config(agent_name: str = None) -> Dict[str, Any]:
    """Retorna configuração para um agente específico ou geral"""
    env_config = get_environment_config()
    
    if agent_name:
        if agent_name == "data_collector":
            config = DataCollectorConfig()
            return {**config.to_dict(), **env_config}
        elif agent_name == "route_analyzer":
            config = RouteAnalyzerConfig()
            return {**config.__dict__, **env_config}
        elif agent_name == "semantic_analyzer":
            config = SemanticAnalyzerConfig()
            return {**config.__dict__, **env_config}
        elif agent_name == "risk_calculator":
            config = RiskCalculatorConfig()
            return {**config.__dict__, **env_config}
        elif agent_name == "report_generator":
            config = ReportGeneratorConfig()
            return {**config.__dict__, **env_config}
    
    return {**AGENT_CONFIG, **env_config}

def get_analysis_profile(profile_name: str) -> Dict[str, Any]:
    """Retorna configuração de um perfil de análise específico"""
    return ANALYSIS_PROFILES.get(profile_name, ANALYSIS_PROFILES["standard"])

def get_monitoring_config() -> Dict[str, Any]:
    """Retorna configuração de monitoramento"""
    return MONITORING_CONFIG

def apply_environment_overrides(config: Dict[str, Any], environment: str) -> Dict[str, Any]:
    """Aplica sobrescritas baseadas no ambiente"""
    env_config = get_environment_config()
    
    # Aplicar multiplicadores
    if "max_concurrent_tasks_multiplier" in env_config:
        if "max_concurrent_tasks" in config:
            config["max_concurrent_tasks"] = int(
                config["max_concurrent_tasks"] * env_config["max_concurrent_tasks_multiplier"]
            )
    
    if "timeout_multiplier" in env_config:
        if "timeout" in config:
            config["timeout"] = config["timeout"] * env_config["timeout_multiplier"]
    
    # Aplicar configurações específicas
    if environment == "production":
        config.update({
            "enable_detailed_logging": False,
            "cache_aggressive": True,
            "optimize_for_throughput": True
        })
    elif environment == "development":
        config.update({
            "enable_debug_mode": True,
            "verbose_errors": True,
            "disable_optimizations": False
        })
    
    return config

def validate_agent_config(config: Dict[str, Any]) -> List[str]:
    """Valida configuração de agente e retorna lista de erros"""
    errors = []
    
    # Validações básicas
    if config.get("max_concurrent_tasks", 0) <= 0:
        errors.append("max_concurrent_tasks deve ser positivo")
    
    if config.get("timeout", 0) <= 0:
        errors.append("timeout deve ser positivo")
    
    # Validações específicas por agente
    if "confidence_threshold" in config:
        threshold = config["confidence_threshold"]
        if not 0.0 <= threshold <= 1.0:
            errors.append("confidence_threshold deve estar entre 0 e 1")
    
    if "cache_ttl" in config:
        if config["cache_ttl"] < 0:
            errors.append("cache_ttl deve ser não-negativo")
    
    return errors

def create_agent_configs() -> Dict[str, Any]:
    """Cria configurações para todos os agentes"""
    return {
        "data_collector": get_agent_config("data_collector"),
        "route_analyzer": get_agent_config("route_analyzer"),
        "semantic_analyzer": get_agent_config("semantic_analyzer"),
        "risk_calculator": get_agent_config("risk_calculator"),
        "report_generator": get_agent_config("report_generator")
    }

def get_optimized_config_for_load(expected_load: str) -> Dict[str, Any]:
    """Retorna configuração otimizada baseada na carga esperada"""
    base_config = get_agent_config()
    
    if expected_load == "low":
        base_config.update({
            "max_concurrent_tasks_per_agent": 2,
            "enable_aggressive_caching": True,
            "reduce_memory_usage": True
        })
    elif expected_load == "high":
        base_config.update({
            "max_concurrent_tasks_per_agent": 10,
            "enable_batch_processing": True,
            "increase_timeouts": True,
            "parallel_optimization": True
        })
    
    return base_config

# =============================================================================
# EXPORTS E CONFIGURAÇÃO PADRÃO
# =============================================================================

# Configurações padrão para compatibilidade
DEFAULT_AGENT_CONFIGS = create_agent_configs()

__all__ = [
    "AGENT_CONFIG",
    "DataCollectorConfig", 
    "RouteAnalyzerConfig",
    "SemanticAnalyzerConfig", 
    "RiskCalculatorConfig",
    "ReportGeneratorConfig",
    "get_agent_config",
    "get_analysis_profile",
    "get_monitoring_config",
    "apply_environment_overrides",
    "validate_agent_config",
    "DEFAULT_AGENT_CONFIGS"
]

# Inicialização e validação
if __name__ == "__main__":
    print("🔧 Validando configurações dos agentes...")
    
    configs = create_agent_configs()
    total_errors = 0
    
    for agent_name, config in configs.items():
        errors = validate_agent_config(config)
        if errors:
            print(f"❌ {agent_name}: {len(errors)} erros encontrados")
            for error in errors:
                print(f"   - {error}")
            total_errors += len(errors)
        else:
            print(f"✅ {agent_name}: configuração válida")
    
    if total_errors == 0:
        print("🎉 Todas as configurações estão válidas!")
    else:
        print(f"⚠️  {total_errors} erro(s) encontrado(s) no total")
else:
    # Log de inicialização
    env = os.getenv("FLASK_ENV", "development")
    print(f"⚙️  Configurações dos agentes carregadas para ambiente: {env}")