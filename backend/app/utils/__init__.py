# app/utils/__init__.py
"""
Utilitários comuns para o Sistema de Análise de Placas
"""

import re
import asyncio
import time
import functools
from datetime import datetime, date
from decimal import Decimal
from typing import Dict, Any, Optional, List, Union, Callable
from flask import request
import logging

# =============================================================================
# FORMATAÇÃO E SERIALIZAÇÃO
# =============================================================================

def serialize_dates(obj):
    """Converte objetos de data/hora para formato ISO para serialização JSON"""
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    elif isinstance(obj, Decimal):
        return str(obj)
    return obj

def safe_format_date(input_date) -> str:
    """Formata data de forma segura"""
    if not input_date:
        return 'N/D'
    
    try:
        # Se já é objeto datetime
        if isinstance(input_date, datetime):
            return input_date.strftime('%d/%m/%Y %H:%M')
        elif isinstance(input_date, date):
            return input_date.strftime('%d/%m/%Y')
        
        # Se é string, tentar converter
        if isinstance(input_date, str):
            # Formato ISO com T
            if 'T' in input_date:
                dt = datetime.fromisoformat(input_date.replace('Z', '+00:00'))
                return dt.strftime('%d/%m/%Y %H:%M')
            
            # Outros formatos
            dt = datetime.fromisoformat(input_date)
            return dt.strftime('%d/%m/%Y %H:%M')
        
        return str(input_date)
        
    except Exception:
        return str(input_date) if input_date else 'N/D'

def format_cpf_cnpj(documento: Union[str, int]) -> str:
    """Formata CPF/CNPJ de forma padronizada"""
    if not documento:
        return 'N/D'
    
    cleaned = re.sub(r'\D', '', str(documento))
    
    if len(cleaned) == 11:  # CPF
        return re.sub(r'(\d{3})(\d{3})(\d{3})(\d{2})', r'\1.\2.\3-\4', cleaned)
    elif len(cleaned) == 14:  # CNPJ
        return re.sub(r'(\d{2})(\d{3})(\d{3})(\d{4})(\d{2})', r'\1.\2.\3/\4-\5', cleaned)
    
    return cleaned

def normalize_placa(placa: str) -> str:
    """Normaliza placa para formato padrão"""
    if not placa:
        return ""
    
    # Remove espaços e caracteres especiais
    cleaned = re.sub(r'[^A-Z0-9]', '', placa.upper().strip())
    
    # Valida formato básico
    if len(cleaned) >= 7:
        return cleaned
    
    return placa.upper().strip()

# =============================================================================
# VALIDAÇÕES
# =============================================================================

def validate_placa(placa: str) -> bool:
    """Valida se uma placa está em formato válido"""
    if not placa:
        return False
    
    normalized = normalize_placa(placa)
    
    # Formato brasileiro: 3 letras + 4 números OU formato Mercosul
    pattern_old = r'^[A-Z]{3}\d{4}$'
    pattern_mercosul = r'^[A-Z]{3}\d[A-Z]\d{2}$'
    
    return bool(re.match(pattern_old, normalized) or re.match(pattern_mercosul, normalized))

def validate_cpf(cpf: str) -> bool:
    """Valida CPF usando algoritmo oficial"""
    if not cpf:
        return False
    
    # Remove caracteres não numéricos
    cpf = re.sub(r'\D', '', cpf)
    
    # Verifica se tem 11 dígitos
    if len(cpf) != 11:
        return False
    
    # Verifica se não é uma sequência de números iguais
    if cpf == cpf[0] * 11:
        return False
    
    # Calcula primeiro dígito verificador
    soma = sum(int(cpf[i]) * (10 - i) for i in range(9))
    resto = soma % 11
    dv1 = 0 if resto < 2 else 11 - resto
    
    # Calcula segundo dígito verificador
    soma = sum(int(cpf[i]) * (11 - i) for i in range(10))
    resto = soma % 11
    dv2 = 0 if resto < 2 else 11 - resto
    
    # Verifica se os dígitos calculados conferem
    return cpf[-2:] == f"{dv1}{dv2}"

def validate_cnpj(cnpj: str) -> bool:
    """Valida CNPJ usando algoritmo oficial"""
    if not cnpj:
        return False
    
    # Remove caracteres não numéricos
    cnpj = re.sub(r'\D', '', cnpj)
    
    # Verifica se tem 14 dígitos
    if len(cnpj) != 14:
        return False
    
    # Verifica se não é uma sequência de números iguais
    if cnpj == cnpj[0] * 14:
        return False
    
    # Primeiro dígito verificador
    peso1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    soma1 = sum(int(cnpj[i]) * peso1[i] for i in range(12))
    resto1 = soma1 % 11
    dv1 = 0 if resto1 < 2 else 11 - resto1
    
    # Segundo dígito verificador
    peso2 = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    soma2 = sum(int(cnpj[i]) * peso2[i] for i in range(13))
    resto2 = soma2 % 11
    dv2 = 0 if resto2 < 2 else 11 - resto2
    
    return cnpj[-2:] == f"{dv1}{dv2}"

def is_valid_document(documento: str) -> tuple[bool, str]:
    """Valida documento e retorna tipo"""
    if not documento:
        return False, "empty"
    
    cleaned = re.sub(r'\D', '', documento)
    
    if len(cleaned) == 11:
        return validate_cpf(cleaned), "cpf"
    elif len(cleaned) == 14:
        return validate_cnpj(cleaned), "cnpj"
    else:
        return False, "invalid_length"

# =============================================================================
# HELPERS PARA REQUEST
# =============================================================================

def get_request_info() -> Dict[str, Any]:
    """Coleta informações úteis da requisição atual"""
    if not request:
        return {}
    
    return {
        "method": request.method,
        "endpoint": request.endpoint,
        "url": request.url,
        "remote_addr": request.remote_addr,
        "user_agent": request.headers.get('User-Agent', ''),
        "timestamp": datetime.now().isoformat(),
        "args": dict(request.args),
        "content_type": request.content_type
    }

def extract_filters_from_args() -> Dict[str, Any]:
    """Extrai filtros comuns dos argumentos da requisição"""
    return {
        "placa": request.args.get('placa', '').upper().strip() if request.args.get('placa') else None,
        "data_inicio": request.args.get('data_inicio'),
        "data_fim": request.args.get('data_fim'),
        "limite": request.args.get('limit', type=int, default=100),
        "offset": request.args.get('offset', type=int, default=0),
        "ordenar_por": request.args.get('sort', 'datahora'),
        "ordem": request.args.get('order', 'desc')
    }

# =============================================================================
# ASYNC/SYNC UTILITIES
# =============================================================================

def async_to_sync(async_func: Callable) -> Callable:
    """Converte função assíncrona para síncrona"""
    @functools.wraps(async_func)
    def wrapper(*args, **kwargs):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(async_func(*args, **kwargs))
        finally:
            loop.close()
    return wrapper

def run_in_thread_pool(func: Callable, *args, **kwargs):
    """Executa função CPU-intensiva em thread pool"""
    import concurrent.futures
    
    with concurrent.futures.ThreadPoolExecutor() as executor:
        future = executor.submit(func, *args, **kwargs)
        return future.result()

# =============================================================================
# PERFORMANCE E MONITORAMENTO
# =============================================================================

class Timer:
    """Context manager para medir tempo de execução"""
    
    def __init__(self, description: str = "Operation"):
        self.description = description
        self.start_time = None
        self.end_time = None
        
    def __enter__(self):
        self.start_time = time.time()
        return self
        
    def __exit__(self, *args):
        self.end_time = time.time()
        
    @property
    def elapsed(self) -> float:
        if self.end_time and self.start_time:
            return self.end_time - self.start_time
        return 0.0
    
    def __str__(self):
        return f"{self.description}: {self.elapsed:.3f}s"

def measure_time(func: Callable) -> Callable:
    """Decorator para medir tempo de execução de função"""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start = time.time()
        try:
            result = func(*args, **kwargs)
            return result
        finally:
            end = time.time()
            print(f"⏱️ {func.__name__}: {end - start:.3f}s")
    return wrapper

def rate_limit(calls: int, period: int):
    """Decorator simples para rate limiting"""
    call_times = []
    
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            now = time.time()
            
            # Remove chamadas antigas
            call_times[:] = [t for t in call_times if now - t < period]
            
            if len(call_times) >= calls:
                raise Exception(f"Rate limit exceeded: {calls} calls per {period}s")
            
            call_times.append(now)
            return func(*args, **kwargs)
        return wrapper
    return decorator

# =============================================================================
# LOGGING UTILITIES
# =============================================================================

def setup_logger(name: str, level: int = logging.INFO) -> logging.Logger:
    """Configura logger padrão para o sistema"""
    logger = logging.getLogger(name)
    
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(level)
    
    return logger

def log_request(logger: logging.Logger):
    """Decorator para log automático de requisições"""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            req_info = get_request_info()
            logger.info(f"📥 {req_info['method']} {req_info['endpoint']} from {req_info['remote_addr']}")
            
            start = time.time()
            try:
                result = func(*args, **kwargs)
                duration = time.time() - start
                logger.info(f"✅ Request completed in {duration:.3f}s")
                return result
            except Exception as e:
                duration = time.time() - start
                logger.error(f"❌ Request failed after {duration:.3f}s: {str(e)}")
                raise
        return wrapper
    return decorator

# =============================================================================
# DATA PROCESSING UTILITIES
# =============================================================================

def safe_get_nested(data: Dict, path: str, default=None):
    """Acessa dados aninhados de forma segura"""
    keys = path.split('.')
    current = data
    
    for key in keys:
        if isinstance(current, dict) and key in current:
            current = current[key]
        else:
            return default
    
    return current

def chunk_list(lst: List, chunk_size: int) -> List[List]:
    """Divide lista em chunks menores"""
    return [lst[i:i + chunk_size] for i in range(0, len(lst), chunk_size)]

def flatten_dict(data: Dict, separator: str = '.', prefix: str = '') -> Dict:
    """Achata dicionário aninhado"""
    flattened = {}
    
    for key, value in data.items():
        new_key = f"{prefix}{separator}{key}" if prefix else key
        
        if isinstance(value, dict):
            flattened.update(flatten_dict(value, separator, new_key))
        else:
            flattened[new_key] = value
    
    return flattened

def calculate_percentage(part: Union[int, float], total: Union[int, float]) -> float:
    """Calcula porcentagem de forma segura"""
    if not total or total == 0:
        return 0.0
    return (part / total) * 100

# =============================================================================
# EXPORTS
# =============================================================================

__all__ = [
    # Formatação
    'serialize_dates', 'safe_format_date', 'format_cpf_cnpj', 'normalize_placa',
    
    # Validações
    'validate_placa', 'validate_cpf', 'validate_cnpj', 'is_valid_document',
    
    # Request helpers
    'get_request_info', 'extract_filters_from_args',
    
    # Async/Sync
    'async_to_sync', 'run_in_thread_pool',
    
    # Performance
    'Timer', 'measure_time', 'rate_limit',
    
    # Logging
    'setup_logger', 'log_request',
    
    # Data processing
    'safe_get_nested', 'chunk_list', 'flatten_dict', 'calculate_percentage'
]