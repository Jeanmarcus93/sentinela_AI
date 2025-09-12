# backend/app/models/__init__.py
"""
Módulo de Modelos de Dados - Sentinela IA v2.0

Este módulo centraliza:
- Conexões com banco de dados
- Configurações de database
- Utilitários para modelos
- Validações de dados
- Schema helpers

Usage:
    from app.models import get_db_connection, get_engine
    from app.models import validate_placa, normalize_cpf
"""

import re
import logging
from typing import Optional, Dict, Any, List, Union
from datetime import datetime, date
from decimal import Decimal

# ==========================================
# IMPORTS DO DATABASE CORE
# ==========================================

try:
    from .database import (
        get_db_connection,
        get_engine, 
        DB_CONFIG,
        validate_db_config
    )
    
    # Status da conexão
    DATABASE_AVAILABLE = True
    
except ImportError as e:
    logging.error(f"Erro ao importar database core: {e}")
    DATABASE_AVAILABLE = False
    
    # Fallbacks para evitar erros
    def get_db_connection():
        raise RuntimeError("Database não disponível")
    
    def get_engine():
        raise RuntimeError("Database engine não disponível")
    
    DB_CONFIG = {}


# ==========================================
# UTILITÁRIOS DE VALIDAÇÃO
# ==========================================

def validate_placa(placa: str) -> bool:
    """
    Valida formato de placa brasileira (antigo e Mercosul)
    
    Args:
        placa: String da placa (ex: "ABC1234" ou "ABC1D23")
        
    Returns:
        bool: True se válida
        
    Examples:
        >>> validate_placa("ABC1234")
        True
        >>> validate_placa("ABC1D23") 
        True
        >>> validate_placa("INVALID")
        False
    """
    if not placa or not isinstance(placa, str):
        return False
    
    placa_clean = placa.strip().upper().replace('-', '').replace(' ', '')
    
    if len(placa_clean) != 7:
        return False
    
    # Padrão antigo: AAA9999
    old_pattern = re.match(r'^[A-Z]{3}[0-9]{4}$', placa_clean)
    
    # Padrão Mercosul: AAA9A99  
    mercosul_pattern = re.match(r'^[A-Z]{3}[0-9][A-Z][0-9]{2}$', placa_clean)
    
    return bool(old_pattern or mercosul_pattern)


def normalize_placa(placa: str) -> Optional[str]:
    """
    Normaliza placa para formato padrão (uppercase, sem símbolos)
    
    Args:
        placa: Placa em qualquer formato
        
    Returns:
        str: Placa normalizada ou None se inválida
        
    Examples:
        >>> normalize_placa("abc-1234")
        "ABC1234"
        >>> normalize_placa("abc 1d23")
        "ABC1D23" 
    """
    if not placa:
        return None
    
    normalized = placa.strip().upper().replace('-', '').replace(' ', '')
    
    return normalized if validate_placa(normalized) else None


def validate_cpf(cpf: str) -> bool:
    """
    Valida CPF brasileiro
    
    Args:
        cpf: String do CPF
        
    Returns:
        bool: True se válido
    """
    if not cpf or not isinstance(cpf, str):
        return False
    
    # Remove caracteres não numéricos
    numbers = re.sub(r'\D', '', cpf)
    
    if len(numbers) != 11:
        return False
    
    # Verifica se todos os dígitos são iguais
    if numbers == numbers[0] * 11:
        return False
    
    # Validação dos dígitos verificadores
    def calc_digit(cpf_partial):
        sum_val = sum(int(digit) * weight for digit, weight in zip(cpf_partial, range(len(cpf_partial) + 1, 1, -1)))
        remainder = sum_val % 11
        return 0 if remainder < 2 else 11 - remainder
    
    first_digit = calc_digit(numbers[:9])
    second_digit = calc_digit(numbers[:10])
    
    return numbers[9] == str(first_digit) and numbers[10] == str(second_digit)


def validate_cnpj(cnpj: str) -> bool:
    """
    Valida CNPJ brasileiro
    
    Args:
        cnpj: String do CNPJ
        
    Returns:
        bool: True se válido
    """
    if not cnpj or not isinstance(cnpj, str):
        return False
    
    numbers = re.sub(r'\D', '', cnpj)
    
    if len(numbers) != 14:
        return False
    
    # Verifica se todos os dígitos são iguais
    if numbers == numbers[0] * 14:
        return False
    
    # Pesos para validação
    weights1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    weights2 = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    
    def calc_digit(cnpj_partial, weights):
        sum_val = sum(int(digit) * weight for digit, weight in zip(cnpj_partial, weights))
        remainder = sum_val % 11
        return 0 if remainder < 2 else 11 - remainder
    
    first_digit = calc_digit(numbers[:12], weights1)
    second_digit = calc_digit(numbers[:13], weights2)
    
    return numbers[12] == str(first_digit) and numbers[13] == str(second_digit)


def normalize_cpf_cnpj(document: str) -> Optional[str]:
    """
    Normaliza CPF ou CNPJ (remove formatação)
    
    Args:
        document: CPF ou CNPJ com ou sem formatação
        
    Returns:
        str: Documento normalizado ou None se inválido
        
    Examples:
        >>> normalize_cpf_cnpj("123.456.789-01")
        "12345678901"
        >>> normalize_cpf_cnpj("12.345.678/0001-95")
        "12345678000195"
    """
    if not document:
        return None
    
    numbers = re.sub(r'\D', '', document)
    
    # Verificar se é CPF (11 dígitos) ou CNPJ (14 dígitos)
    if len(numbers) == 11 and validate_cpf(numbers):
        return numbers
    elif len(numbers) == 14 and validate_cnpj(numbers):
        return numbers
    
    return None


# ==========================================
# FORMATADORES
# ==========================================

def format_cpf(cpf: str) -> str:
    """
    Formata CPF com pontuação
    
    Args:
        cpf: CPF em string numérica
        
    Returns:
        str: CPF formatado (123.456.789-01)
    """
    if not cpf or len(cpf) != 11:
        return cpf
    
    return f"{cpf[:3]}.{cpf[3:6]}.{cpf[6:9]}-{cpf[9:]}"


def format_cnpj(cnpj: str) -> str:
    """
    Formata CNPJ com pontuação
    
    Args:
        cnpj: CNPJ em string numérica
        
    Returns:
        str: CNPJ formatado (12.345.678/0001-95)
    """
    if not cnpj or len(cnpj) != 14:
        return cnpj
    
    return f"{cnpj[:2]}.{cnpj[2:5]}.{cnpj[5:8]}/{cnpj[8:12]}-{cnpj[12:]}"


def format_placa(placa: str) -> str:
    """
    Formata placa com hífen
    
    Args:
        placa: Placa normalizada
        
    Returns:
        str: Placa formatada (ABC-1234)
    """
    if not placa or len(placa) != 7:
        return placa
    
    return f"{placa[:3]}-{placa[3:]}"


# ==========================================
# SERIALIZADORES DE DADOS
# ==========================================

def serialize_datetime(obj: Any) -> Any:
    """
    Serializa objetos datetime para JSON
    
    Args:
        obj: Objeto a ser serializado
        
    Returns:
        str: Data/hora em formato ISO ou objeto original
    """
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    elif isinstance(obj, Decimal):
        return float(obj)
    return obj


def serialize_record(record: Dict[str, Any]) -> Dict[str, Any]:
    """
    Serializa um registro do banco para JSON
    
    Args:
        record: Dicionário com dados do banco
        
    Returns:
        Dict: Registro serializado
    """
    if not record:
        return {}
    
    return {key: serialize_datetime(value) for key, value in record.items()}


def serialize_records(records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Serializa lista de registros
    
    Args:
        records: Lista de registros do banco
        
    Returns:
        List: Lista de registros serializados
    """
    return [serialize_record(record) for record in records] if records else []


# ==========================================
# QUERY HELPERS
# ==========================================

def build_where_clause(filters: Dict[str, Any]) -> tuple[str, Dict[str, Any]]:
    """
    Constrói cláusula WHERE dinâmica a partir de filtros
    
    Args:
        filters: Dicionário de filtros {campo: valor}
        
    Returns:
        tuple: (WHERE clause, parameters dict)
        
    Example:
        >>> build_where_clause({'placa': 'ABC1234', 'data_inicio': '2024-01-01'})
        ("WHERE placa = %(placa)s AND datahora >= %(data_inicio)s", {...})
    """
    if not filters:
        return "", {}
    
    conditions = []
    params = {}
    
    for key, value in filters.items():
        if value is not None:
            if key == 'placa':
                conditions.append("placa = %(placa)s")
                params['placa'] = normalize_placa(value) or value
            elif key == 'cpf_cnpj':
                conditions.append("cpf_cnpj = %(cpf_cnpj)s") 
                params['cpf_cnpj'] = normalize_cpf_cnpj(value) or value
            elif key == 'data_inicio':
                conditions.append("datahora >= %(data_inicio)s")
                params['data_inicio'] = value
            elif key == 'data_fim':
                conditions.append("datahora <= %(data_fim)s")
                params['data_fim'] = f"{value} 23:59:59" if len(str(value)) == 10 else value
            else:
                conditions.append(f"{key} = %({key})s")
                params[key] = value
    
    where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""
    
    return where_clause, params


# ==========================================
# HEALTH CHECKS
# ==========================================

def check_database_health() -> Dict[str, Any]:
    """
    Verifica saúde do banco de dados
    
    Returns:
        Dict: Status da conexão e métricas
    """
    health_info = {
        "status": "unknown",
        "connection": False,
        "tables": [],
        "error": None
    }
    
    if not DATABASE_AVAILABLE:
        health_info.update({
            "status": "unavailable",
            "error": "Database module not available"
        })
        return health_info
    
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                # Test connection
                cur.execute("SELECT 1")
                cur.fetchone()
                health_info["connection"] = True
                
                # List tables
                cur.execute("""
                    SELECT table_name 
                    FROM information_schema.tables 
                    WHERE table_schema = 'public'
                    ORDER BY table_name
                """)
                
                health_info["tables"] = [row[0] for row in cur.fetchall()]
                health_info["status"] = "healthy"
                
    except Exception as e:
        health_info.update({
            "status": "error",
            "error": str(e)
        })
        logging.error(f"Database health check failed: {e}")
    
    return health_info


def get_table_stats() -> Dict[str, int]:
    """
    Retorna estatísticas básicas das tabelas principais
    
    Returns:
        Dict: Contagem de registros por tabela
    """
    stats = {}
    
    if not DATABASE_AVAILABLE:
        return stats
    
    tables = ['veiculos', 'passagens', 'ocorrencias', 'pessoas', 'apreensoes']
    
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                for table in tables:
                    try:
                        cur.execute(f"SELECT COUNT(*) FROM {table}")
                        count = cur.fetchone()[0]
                        stats[table] = count
                    except Exception as e:
                        stats[table] = f"error: {str(e)}"
                        logging.warning(f"Could not get stats for table {table}: {e}")
    
    except Exception as e:
        logging.error(f"Could not get table stats: {e}")
    
    return stats


# ==========================================
# EXPORTS
# ==========================================

__all__ = [
    # Database core
    'get_db_connection',
    'get_engine',
    'DB_CONFIG',
    'DATABASE_AVAILABLE',
    'validate_db_config',
    
    # Validators
    'validate_placa',
    'validate_cpf', 
    'validate_cnpj',
    'normalize_placa',
    'normalize_cpf_cnpj',
    
    # Formatters
    'format_cpf',
    'format_cnpj', 
    'format_placa',
    
    # Serializers
    'serialize_datetime',
    'serialize_record',
    'serialize_records',
    
    # Query helpers
    'build_where_clause',
    
    # Health checks
    'check_database_health',
    'get_table_stats'
]


# ==========================================
# INICIALIZAÇÃO DO MÓDULO
# ==========================================

# Log status do módulo
if DATABASE_AVAILABLE:
    logging.info("✅ Models module loaded successfully")
    try:
        health = check_database_health()
        if health["status"] == "healthy":
            logging.info(f"✅ Database connected - {len(health['tables'])} tables found")
        else:
            logging.warning(f"⚠️ Database status: {health['status']}")
    except Exception:
        logging.warning("⚠️ Could not perform initial health check")
else:
    logging.error("❌ Models module loaded with database unavailable")


# Compatibilidade com imports antigos
try:
    from .database import *
except ImportError:
    pass