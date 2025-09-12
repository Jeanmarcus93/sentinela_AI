# backend/app/services/__init__.py
"""
Services Module - Sentinela IA v2.0

Centraliza todos os serviços de negócio:
- Análise de placas (legacy + agentes v2)
- Análise semântica de relatos
- Sistema de agentes especializados
- Utilitários comuns para serviços
- Cache e performance

Usage:
    from app.services import analisar_placa_json, analyze_text
    from app.services import get_enhanced_service, quick_risk_analysis
"""

import logging
import time
import functools
from typing import Dict, Any, List, Optional, Callable, Union
from datetime import datetime, timedelta
import asyncio
import threading

# ==========================================
# CORE SERVICES IMPORTS
# ==========================================

# Serviço de análise semântica
try:
    from .semantic_service import (
        analyze_text,
        embed,
        extract_keywords,
        predict_class,
        rule_based_indicators,
        load_classifier,
        load_embeddings
    )
    SEMANTIC_SERVICE_AVAILABLE = True
    print("✅ Semantic service loaded")
except ImportError as e:
    logging.warning(f"Semantic service não disponível: {e}")
    SEMANTIC_SERVICE_AVAILABLE = False
    
    # Fallbacks
    def analyze_text(text): return {"erro": "Serviço não disponível"}
    def embed(texts): return []
    def extract_keywords(text): return []

# Serviço de análise de placas (legacy)
try:
    from .placa_service import analisar_placa_json
    PLACA_SERVICE_AVAILABLE = True
    print("✅ Legacy placa service loaded")
except ImportError as e:
    logging.warning(f"Legacy placa service não disponível: {e}")
    PLACA_SERVICE_AVAILABLE = False
    
    # Fallback
    def analisar_placa_json(placa): return {"erro": "Serviço não disponível"}

# Sistema de agentes especializados (v2)
try:
    from .enhanced_placa_service import (
        get_enhanced_placa_service,
        quick_risk_analysis,
        route_analysis_only,
        semantic_analysis_only
    )
    ENHANCED_SERVICE_AVAILABLE = True
    print("✅ Enhanced service (agents v2) loaded")
except ImportError as e:
    logging.warning(f"Enhanced service não disponível: {e}")
    ENHANCED_SERVICE_AVAILABLE = False
    
    # Fallbacks
    def get_enhanced_placa_service(): return None
    async def quick_risk_analysis(placa): return {"erro": "Serviço não disponível"}
    async def route_analysis_only(placa): return {"erro": "Serviço não disponível"}
    async def semantic_analysis_only(placa): return {"erro": "Serviço não disponível"}


# ==========================================
# SERVICE REGISTRY & DISCOVERY
# ==========================================

class ServiceRegistry:
    """Registry centralizado de serviços disponíveis"""
    
    def __init__(self):
        self.services = {}
        self.health_cache = {}
        self.cache_ttl = 300  # 5 minutos
        self._register_core_services()
    
    def _register_core_services(self):
        """Registra serviços core do sistema"""
        self.services.update({
            'semantic_service': {
                'available': SEMANTIC_SERVICE_AVAILABLE,
                'functions': ['analyze_text', 'embed', 'extract_keywords'] if SEMANTIC_SERVICE_AVAILABLE else [],
                'description': 'Análise semântica de relatos'
            },
            'placa_service': {
                'available': PLACA_SERVICE_AVAILABLE, 
                'functions': ['analisar_placa_json'] if PLACA_SERVICE_AVAILABLE else [],
                'description': 'Análise de placas (legacy)'
            },
            'enhanced_service': {
                'available': ENHANCED_SERVICE_AVAILABLE,
                'functions': ['get_enhanced_placa_service', 'quick_risk_analysis'] if ENHANCED_SERVICE_AVAILABLE else [],
                'description': 'Sistema de agentes especializados v2'
            }
        })
    
    def is_service_available(self, service_name: str) -> bool:
        """Verifica se um serviço está disponível"""
        return self.services.get(service_name, {}).get('available', False)
    
    def get_available_services(self) -> List[str]:
        """Retorna lista de serviços disponíveis"""
        return [name for name, info in self.services.items() if info['available']]
    
    def get_service_info(self, service_name: str = None) -> Dict[str, Any]:
        """Retorna informações sobre serviços"""
        if service_name:
            return self.services.get(service_name, {})
        return self.services
    
    def health_check_all(self) -> Dict[str, Any]:
        """Executa health check em todos os serviços"""
        now = time.time()
        
        # Verificar cache
        if 'last_check' in self.health_cache:
            if now - self.health_cache['last_check'] < self.cache_ttl:
                return self.health_cache
        
        health_status = {
            'timestamp': now,
            'last_check': now,
            'services': {}
        }
        
        # Check semantic service
        if SEMANTIC_SERVICE_AVAILABLE:
            try:
                start = time.time()
                result = analyze_text("teste")
                duration = time.time() - start
                health_status['services']['semantic_service'] = {
                    'status': 'healthy',
                    'response_time': duration,
                    'result_keys': list(result.keys()) if isinstance(result, dict) else []
                }
            except Exception as e:
                health_status['services']['semantic_service'] = {
                    'status': 'error',
                    'error': str(e)
                }
        
        # Check placa service
        if PLACA_SERVICE_AVAILABLE:
            try:
                start = time.time()
                result = analisar_placa_json("TEST123")
                duration = time.time() - start
                health_status['services']['placa_service'] = {
                    'status': 'healthy',
                    'response_time': duration,
                    'has_result': bool(result)
                }
            except Exception as e:
                health_status['services']['placa_service'] = {
                    'status': 'error',
                    'error': str(e)
                }
        
        # Check enhanced service
        if ENHANCED_SERVICE_AVAILABLE:
            try:
                service = get_enhanced_placa_service()
                health_status['services']['enhanced_service'] = {
                    'status': 'healthy',
                    'initialized': service._is_initialized if service else False,
                    'agents_count': len(service.orchestrator.agents) if service else 0
                }
            except Exception as e:
                health_status['services']['enhanced_service'] = {
                    'status': 'error',
                    'error': str(e)
                }
        
        # Calcular saúde geral
        healthy_services = sum(1 for svc in health_status['services'].values() if svc.get('status') == 'healthy')
        total_services = len(health_status['services'])
        health_status['overall'] = {
            'healthy_services': healthy_services,
            'total_services': total_services,
            'health_percentage': (healthy_services / total_services * 100) if total_services > 0 else 0,
            'status': 'healthy' if healthy_services == total_services else 'degraded' if healthy_services > 0 else 'unhealthy'
        }
        
        # Atualizar cache
        self.health_cache = health_status
        return health_status


# Instância global do registry
service_registry = ServiceRegistry()


# ==========================================
# CACHE & PERFORMANCE UTILITIES
# ==========================================

class ServiceCache:
    """Cache simples para resultados de serviços"""
    
    def __init__(self, default_ttl: int = 300):
        self.cache = {}
        self.default_ttl = default_ttl
        self._lock = threading.RLock()
    
    def get(self, key: str) -> Optional[Any]:
        """Busca item no cache"""
        with self._lock:
            if key in self.cache:
                item = self.cache[key]
                if time.time() < item['expires_at']:
                    return item['data']
                else:
                    del self.cache[key]
            return None
    
    def set(self, key: str, data: Any, ttl: int = None) -> None:
        """Armazena item no cache"""
        if ttl is None:
            ttl = self.default_ttl
        
        with self._lock:
            self.cache[key] = {
                'data': data,
                'expires_at': time.time() + ttl,
                'created_at': time.time()
            }
    
    def clear(self) -> None:
        """Limpa todo o cache"""
        with self._lock:
            self.cache.clear()
    
    def cleanup_expired(self) -> int:
        """Remove itens expirados do cache"""
        now = time.time()
        expired_keys = []
        
        with self._lock:
            for key, item in self.cache.items():
                if now >= item['expires_at']:
                    expired_keys.append(key)
            
            for key in expired_keys:
                del self.cache[key]
        
        return len(expired_keys)
    
    def get_stats(self) -> Dict[str, Any]:
        """Retorna estatísticas do cache"""
        with self._lock:
            return {
                'total_items': len(self.cache),
                'size_bytes': sum(len(str(item)) for item in self.cache.values()),
                'oldest_item': min((item['created_at'] for item in self.cache.values()), default=None),
                'newest_item': max((item['created_at'] for item in self.cache.values()), default=None)
            }


# Instância global do cache
service_cache = ServiceCache(default_ttl=600)  # 10 minutos


def cached_service_call(cache_key_func: Callable = None, ttl: int = 300):
    """
    Decorator para cache automático de chamadas de serviço
    
    Args:
        cache_key_func: Função para gerar chave do cache
        ttl: Time to live em segundos
        
    Usage:
        @cached_service_call(ttl=600)
        def minha_funcao(placa):
            return resultado_complexo(placa)
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Gerar chave do cache
            if cache_key_func:
                cache_key = cache_key_func(*args, **kwargs)
            else:
                cache_key = f"{func.__name__}:{str(args)}:{str(sorted(kwargs.items()))}"
            
            # Tentar buscar no cache
            cached_result = service_cache.get(cache_key)
            if cached_result is not None:
                logging.debug(f"Cache hit for {func.__name__}")
                return cached_result
            
            # Executar função e cachear resultado
            result = func(*args, **kwargs)
            service_cache.set(cache_key, result, ttl)
            logging.debug(f"Cached result for {func.__name__}")
            return result
        
        return wrapper
    return decorator


# ==========================================
# PERFORMANCE MONITORING
# ==========================================

class PerformanceMonitor:
    """Monitor de performance para serviços"""
    
    def __init__(self):
        self.metrics = {}
        self._lock = threading.RLock()
    
    def record_call(self, service_name: str, function_name: str, duration: float, success: bool):
        """Registra uma chamada de serviço"""
        with self._lock:
            key = f"{service_name}.{function_name}"
            
            if key not in self.metrics:
                self.metrics[key] = {
                    'total_calls': 0,
                    'total_time': 0.0,
                    'success_calls': 0,
                    'error_calls': 0,
                    'min_time': float('inf'),
                    'max_time': 0.0,
                    'last_call': None
                }
            
            metric = self.metrics[key]
            metric['total_calls'] += 1
            metric['total_time'] += duration
            metric['min_time'] = min(metric['min_time'], duration)
            metric['max_time'] = max(metric['max_time'], duration)
            metric['last_call'] = time.time()
            
            if success:
                metric['success_calls'] += 1
            else:
                metric['error_calls'] += 1
    
    def get_stats(self, service_name: str = None) -> Dict[str, Any]:
        """Retorna estatísticas de performance"""
        with self._lock:
            if service_name:
                return {k: v for k, v in self.metrics.items() if k.startswith(service_name)}
            
            # Calcular médias e estatísticas agregadas
            stats = {}
            for key, metric in self.metrics.items():
                avg_time = metric['total_time'] / metric['total_calls'] if metric['total_calls'] > 0 else 0
                success_rate = metric['success_calls'] / metric['total_calls'] if metric['total_calls'] > 0 else 0
                
                stats[key] = {
                    **metric,
                    'avg_time': avg_time,
                    'success_rate': success_rate
                }
            
            return stats
    
    def reset_stats(self):
        """Reseta todas as estatísticas"""
        with self._lock:
            self.metrics.clear()


# Instância global do monitor
performance_monitor = PerformanceMonitor()


def monitor_performance(service_name: str, function_name: str = None):
    """
    Decorator para monitoramento automático de performance
    
    Usage:
        @monitor_performance('semantic_service')
        def analyze_text(text):
            return resultado
    """
    def decorator(func):
        nonlocal function_name
        if function_name is None:
            function_name = func.__name__
        
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            success = False
            
            try:
                result = func(*args, **kwargs)
                success = True
                return result
            except Exception as e:
                logging.error(f"Error in {service_name}.{function_name}: {e}")
                raise
            finally:
                duration = time.time() - start_time
                performance_monitor.record_call(service_name, function_name, duration, success)
        
        return wrapper
    return decorator


# ==========================================
# HIGH-LEVEL SERVICE FUNCTIONS
# ==========================================

def get_service_status() -> Dict[str, Any]:
    """
    Retorna status completo de todos os serviços
    
    Returns:
        Dict: Status dos serviços, cache, performance, etc.
    """
    return {
        'services': service_registry.get_service_info(),
        'health': service_registry.health_check_all(),
        'cache': service_cache.get_stats(),
        'performance': performance_monitor.get_stats(),
        'available_services': service_registry.get_available_services()
    }


@cached_service_call(ttl=300)
def analyze_placa_comprehensive(placa: str, use_agents: bool = True) -> Dict[str, Any]:
    """
    Análise completa de placa usando melhor serviço disponível
    
    Args:
        placa: Placa do veículo
        use_agents: Preferir sistema de agentes se disponível
        
    Returns:
        Dict: Resultado da análise
    """
    if not placa:
        return {"error": "Placa não informada"}
    
    # Tentar sistema de agentes primeiro (se solicitado e disponível)
    if use_agents and ENHANCED_SERVICE_AVAILABLE:
        try:
            service = get_enhanced_placa_service()
            if service:
                result = service.analisar_placa_sync(placa)
                if result.get("success"):
                    result["service_used"] = "enhanced_agents_v2"
                    return result
        except Exception as e:
            logging.warning(f"Enhanced service failed, falling back to legacy: {e}")
    
    # Fallback para serviço legacy
    if PLACA_SERVICE_AVAILABLE:
        try:
            result = analisar_placa_json(placa)
            result["service_used"] = "legacy_placa_service"
            return result
        except Exception as e:
            logging.error(f"Legacy placa service failed: {e}")
            return {"error": f"Análise falhou: {str(e)}"}
    
    return {"error": "Nenhum serviço de análise de placa disponível"}


async def analyze_placa_async(placa: str, mode: str = "comprehensive") -> Dict[str, Any]:
    """
    Análise assíncrona de placa
    
    Args:
        placa: Placa do veículo  
        mode: 'comprehensive', 'fast', 'route_only', 'semantic_only'
        
    Returns:
        Dict: Resultado da análise
    """
    if not ENHANCED_SERVICE_AVAILABLE:
        # Fallback síncrono
        return analyze_placa_comprehensive(placa)
    
    try:
        if mode == "fast":
            return await quick_risk_analysis(placa)
        elif mode == "route_only":
            return await route_analysis_only(placa)  
        elif mode == "semantic_only":
            return await semantic_analysis_only(placa)
        else:  # comprehensive
            service = get_enhanced_placa_service()
            return await service.analisar_placa_async(placa)
            
    except Exception as e:
        logging.error(f"Async analysis failed: {e}")
        return {"error": str(e), "success": False}


def batch_analyze_text(texts: List[str]) -> List[Dict[str, Any]]:
    """
    Análise em lote de textos
    
    Args:
        texts: Lista de textos para analisar
        
    Returns:
        List: Resultados das análises
    """
    if not SEMANTIC_SERVICE_AVAILABLE:
        return [{"error": "Serviço semântico não disponível"} for _ in texts]
    
    results = []
    for text in texts:
        try:
            result = analyze_text(text)
            results.append(result)
        except Exception as e:
            results.append({"error": str(e)})
    
    return results


# ==========================================
# MAINTENANCE & CLEANUP
# ==========================================

def cleanup_services():
    """Limpeza e manutenção dos serviços"""
    try:
        # Limpar cache expirado
        expired_count = service_cache.cleanup_expired()
        
        # Log de limpeza
        if expired_count > 0:
            logging.info(f"Cleaned {expired_count} expired cache entries")
        
        # Resetar métricas antigas (opcional)
        # performance_monitor.reset_stats()
        
        return {
            "cache_cleaned": expired_count,
            "timestamp": time.time()
        }
    except Exception as e:
        logging.error(f"Error during service cleanup: {e}")
        return {"error": str(e)}


# ==========================================
# EXPORTS
# ==========================================

__all__ = [
    # Core services
    'analyze_text',
    'analisar_placa_json', 
    'get_enhanced_placa_service',
    'quick_risk_analysis',
    
    # High-level functions
    'analyze_placa_comprehensive',
    'analyze_placa_async',
    'batch_analyze_text',
    
    # Service management
    'service_registry',
    'get_service_status',
    'cleanup_services',
    
    # Cache & Performance
    'service_cache',
    'performance_monitor',
    'cached_service_call',
    'monitor_performance',
    
    # Status flags
    'SEMANTIC_SERVICE_AVAILABLE',
    'PLACA_SERVICE_AVAILABLE', 
    'ENHANCED_SERVICE_AVAILABLE',
    
    # Utilities from individual services
    'embed',
    'extract_keywords',
    'load_classifier',
    'route_analysis_only',
    'semantic_analysis_only'
]


# ==========================================
# INITIALIZATION
# ==========================================

logging.info("🔧 Services module initialized")
logging.info(f"📊 Available services: {service_registry.get_available_services()}")

# Agendar limpeza automática (se possível)
try:
    import atexit
    atexit.register(cleanup_services)
except:
    pass

# Executar health check inicial em background (não bloquear)
def _initial_health_check():
    try:
        health = service_registry.health_check_all()
        healthy_count = health.get('overall', {}).get('healthy_services', 0)
        total_count = health.get('overall', {}).get('total_services', 0)
        logging.info(f"🏥 Initial health check: {healthy_count}/{total_count} services healthy")
    except Exception as e:
        logging.warning(f"Initial health check failed: {e}")

# Executar em thread para não bloquear inicialização
threading.Thread(target=_initial_health_check, daemon=True).start()
