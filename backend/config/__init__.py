# config/__init__.py
"""
Configurações centralizadas do Sistema de Análise de Placas
Consolida todas as configurações em um ponto único de acesso
"""

import os
import json
from typing import Dict, Any, Optional
from pathlib import Path
import logging
import logging.config

# =============================================================================
# CONFIGURAÇÕES DE AMBIENTE
# =============================================================================

def load_env_config() -> Dict[str, Any]:
    """Carrega configurações do ambiente (.env)"""
    config = {}
    
    # Banco de dados principal
    config['DATABASE'] = {
        'HOST': os.getenv('DB_HOST', 'localhost'),
        'PORT': int(os.getenv('DB_PORT', '5432')),
        'NAME': os.getenv('DB_NAME', 'sentinela_teste'),
        'USER': os.getenv('DB_USER', 'postgres'),
        'PASSWORD': os.getenv('DB_PASSWORD', 'Jmkjmk.00')
    }
    
    # Banco de veículos
    config['VEICULOS_DATABASE'] = {
        'HOST': os.getenv('VEICULOS_DB_HOST', 'localhost'),
        'PORT': int(os.getenv('VEICULOS_DB_PORT', '5432')),
        'NAME': os.getenv('VEICULOS_DB_NAME', 'veiculos_db'),
        'USER': os.getenv('VEICULOS_DB_USER', 'postgres'),
        'PASSWORD': os.getenv('VEICULOS_DB_PASSWORD', 'Jmkjmk.00')
    }
    
    # Flask
    config['FLASK'] = {
        'ENV': os.getenv('FLASK_ENV', 'development'),
        'DEBUG': os.getenv('FLASK_DEBUG', 'True').lower() == 'true',
        'SECRET_KEY': os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production'),
        'PORT': int(os.getenv('FLASK_PORT', '5000')),
        'HOST': os.getenv('FLASK_HOST', '0.0.0.0')
    }
    
    # Modelos de ML
    config['ML_MODELS'] = {
        'SPACY_MODEL': os.getenv('SPACY_PT_MODEL', 'pt_core_news_sm'),
        'SENTENCE_TRANSFORMER': os.getenv('SENTENCE_EMB_MODEL', 'sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2'),
        'MODELS_DIR': os.getenv('MODELS_DIR', 'ml_models/trained')
    }
    
    return config

# =============================================================================
# CONFIGURAÇÕES DO SISTEMA
# =============================================================================

class SystemConfig:
    """Configurações centralizadas do sistema"""
    
    def __init__(self):
        self._env_config = load_env_config()
        self._config_dir = Path(__file__).parent
        
    @property
    def database(self) -> Dict[str, Any]:
        """Configurações do banco de dados principal"""
        return self._env_config['DATABASE']
    
    @property
    def veiculos_database(self) -> Dict[str, Any]:
        """Configurações do banco de veículos"""
        return self._env_config['VEICULOS_DATABASE']
    
    @property
    def flask(self) -> Dict[str, Any]:
        """Configurações do Flask"""
        return self._env_config['FLASK']
    
    @property
    def ml_models(self) -> Dict[str, Any]:
        """Configurações dos modelos de ML"""
        return self._env_config['ML_MODELS']
    
    @property
    def agents(self) -> Dict[str, Any]:
        """Configurações dos agentes especializados"""
        try:
            from config.agents.agent_config import get_agent_config
            return get_agent_config()
        except ImportError:
            # Configuração padrão se não encontrar o arquivo
            return {
                "max_concurrent_tasks_per_agent": 5,
                "default_task_timeout": 30.0,
                "enable_performance_monitoring": True,
                "log_agent_activities": True
            }
    
    def get_database_url(self, database_type: str = 'main') -> str:
        """Retorna URL de conexão do banco"""
        if database_type == 'veiculos':
            db_config = self.veiculos_database
        else:
            db_config = self.database
            
        return (f"postgresql://{db_config['USER']}:{db_config['PASSWORD']}"
                f"@{db_config['HOST']}:{db_config['PORT']}/{db_config['NAME']}")
    
    def get_psycopg_config(self, database_type: str = 'main') -> Dict[str, Any]:
        """Retorna configuração para psycopg"""
        if database_type == 'veiculos':
            return {
                "host": self.veiculos_database['HOST'],
                "port": self.veiculos_database['PORT'],
                "dbname": self.veiculos_database['NAME'],
                "user": self.veiculos_database['USER'],
                "password": self.veiculos_database['PASSWORD']
            }
        else:
            return {
                "host": self.database['HOST'],
                "port": self.database['PORT'],
                "dbname": self.database['NAME'],
                "user": self.database['USER'],
                "password": self.database['PASSWORD']
            }

# =============================================================================
# CONFIGURAÇÕES ESPECÍFICAS DO DOMÍNIO
# =============================================================================

class AnalysisConfig:
    """Configurações específicas para análise de placas"""
    
    # Configurações de risco
    RISK_THRESHOLDS = {
        'LOW': 0.0,
        'MEDIUM': 0.4,
        'HIGH': 0.6,
        'CRITICAL': 0.8
    }
    
    # Configurações temporais
    TEMPORAL_ANALYSIS = {
        'NIGHT_START_HOUR': 22,
        'NIGHT_END_HOUR': 6,
        'SUSPICIOUS_NIGHT_PERCENTAGE': 60,  # % de atividade noturna considerada suspeita
        'MIN_ROUTE_FREQUENCY': 3,  # Frequência mínima para detectar padrão
        'ANALYSIS_CACHE_TTL': 3600  # TTL do cache em segundos
    }
    
    # Configurações geográficas
    GEOGRAPHIC_ANALYSIS = {
        'BORDER_CITIES': [
            'Foz do Iguaçu', 'Ponta Porã', 'Corumbá', 'Uruguaiana',
            'Santana do Livramento', 'Jaguarão', 'Aceguá', 'Barra do Quaraí'
        ],
        'SUSPICIOUS_REGIONS': [
            'Fronteira', 'Tríplice Fronteira', 'Região de Fronteira'
        ]
    }
    
    # Configurações de ML
    ML_ANALYSIS = {
        'MIN_TRAINING_SAMPLES': 100,
        'TEST_SIZE': 0.2,
        'CROSS_VALIDATION_FOLDS': 5,
        'EMBEDDING_CACHE_SIZE': 10000
    }

class LoggingConfig:
    """Configurações de logging"""
    
    def __init__(self, system_config: SystemConfig):
        self.config = {
            'version': 1,
            'disable_existing_loggers': False,
            'formatters': {
                'standard': {
                    'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
                },
                'detailed': {
                    'format': '%(asctime)s - %(name)s - %(levelname)s - %(module)s - %(funcName)s - %(message)s'
                }
            },
            'handlers': {
                'console': {
                    'class': 'logging.StreamHandler',
                    'level': 'INFO' if not system_config.flask['DEBUG'] else 'DEBUG',
                    'formatter': 'standard',
                    'stream': 'ext://sys.stdout'
                },
                'file': {
                    'class': 'logging.FileHandler',
                    'level': 'INFO',
                    'formatter': 'detailed',
                    'filename': 'logs/sentinela.log',
                    'mode': 'a'
                }
            },
            'loggers': {
                'sentinela': {
                    'handlers': ['console', 'file'],
                    'level': 'DEBUG',
                    'propagate': False
                },
                'sentinela.agents': {
                    'handlers': ['console', 'file'],
                    'level': 'DEBUG',
                    'propagate': False
                },
                'sentinela.analysis': {
                    'handlers': ['console', 'file'],
                    'level': 'INFO',
                    'propagate': False
                }
            },
            'root': {
                'level': 'WARNING',
                'handlers': ['console']
            }
        }
    
    def setup_logging(self):
        """Configura o sistema de logging"""
        # Criar diretório de logs se não existir
        os.makedirs('logs', exist_ok=True)
        
        logging.config.dictConfig(self.config)
        return logging.getLogger('sentinela')

# =============================================================================
# FUNÇÕES DE INICIALIZAÇÃO
# =============================================================================

def initialize_system() -> SystemConfig:
    """Inicializa as configurações do sistema"""
    config = SystemConfig()
    
    # Configurar logging
    logging_config = LoggingConfig(config)
    logger = logging_config.setup_logging()
    
    logger.info("Iniciando Sistema de Análise de Placas")
    logger.info(f"Ambiente: {config.flask['ENV']}")
    logger.info(f"Debug: {config.flask['DEBUG']}")
    logger.info(f"Banco principal: {config.database['NAME']}@{config.database['HOST']}")
    logger.info(f"Banco veículos: {config.veiculos_database['NAME']}@{config.veiculos_database['HOST']}")
    
    return config

def validate_configuration(config: SystemConfig) -> bool:
    """Valida se todas as configurações necessárias estão presentes"""
    validation_errors = []
    
    # Validar configurações de banco
    for db_name, db_config in [('main', config.database), ('veiculos', config.veiculos_database)]:
        required_fields = ['HOST', 'PORT', 'NAME', 'USER', 'PASSWORD']
        for field in required_fields:
            if not db_config.get(field):
                validation_errors.append(f"Campo obrigatório ausente: {db_name}.{field}")
    
    # Validar Flask
    if not config.flask.get('SECRET_KEY') or config.flask['SECRET_KEY'] == 'dev-secret-key-change-in-production':
        if config.flask['ENV'] == 'production':
            validation_errors.append("SECRET_KEY deve ser alterada em produção")
    
    # Validar diretórios
    models_dir = Path(config.ml_models['MODELS_DIR'])
    if not models_dir.exists():
        models_dir.mkdir(parents=True, exist_ok=True)
    
    if validation_errors:
        print("❌ Erros de configuração encontrados:")
        for error in validation_errors:
            print(f"   - {error}")
        return False
    
    print("✅ Configurações validadas com sucesso")
    return True

def load_training_stats() -> Optional[Dict[str, Any]]:
    """Carrega estatísticas de treinamento se disponíveis"""
    stats_file = Path("config/training_stats.json")
    
    if stats_file.exists():
        try:
            with open(stats_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"⚠️ Erro ao carregar estatísticas de treinamento: {e}")
    
    return None

def save_training_stats(stats: Dict[str, Any]) -> bool:
    """Salva estatísticas de treinamento"""
    stats_file = Path("config/training_stats.json")
    
    try:
        with open(stats_file, 'w', encoding='utf-8') as f:
            json.dump(stats, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"❌ Erro ao salvar estatísticas: {e}")
        return False

# =============================================================================
# INSTÂNCIA GLOBAL DE CONFIGURAÇÃO
# =============================================================================

# Configuração global do sistema (lazy loading)
_system_config = None

def get_config() -> SystemConfig:
    """Retorna a instância global de configuração"""
    global _system_config
    if _system_config is None:
        _system_config = initialize_system()
        validate_configuration(_system_config)
    return _system_config

# =============================================================================
# EXPORTS
# =============================================================================

# Configurações principais
from .settings import Config as FlaskConfig

# Análise e domínio
ANALYSIS_CONFIG = AnalysisConfig()

# Funções utilitárias
__all__ = [
    # Classes principais
    'SystemConfig', 'AnalysisConfig', 'LoggingConfig',
    
    # Configurações específicas  
    'FlaskConfig', 'ANALYSIS_CONFIG',
    
    # Funções
    'get_config', 'initialize_system', 'validate_configuration',
    'load_training_stats', 'save_training_stats',
    
    # Configurações de ambiente
    'load_env_config'
]

# Informações do sistema
__version__ = "2.0.0"
__description__ = "Sistema de Análise de Placas com Agentes Especializados"
__author__ = "Equipe de Desenvolvimento"

print("Settings module loaded successfully")
print(f"Config module loaded - v{__version__}")
print(f"Sistema de Análise de Placas com Agentes Especializados")

# Inicialização automática em modo de desenvolvimento
if os.getenv('FLASK_ENV', 'development') == 'development':
    print("Modo de desenvolvimento detectado - configuração carregada automaticamente")
    config = get_config()
