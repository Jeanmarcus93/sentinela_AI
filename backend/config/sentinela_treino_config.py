#!/usr/bin/env python3
"""
Configuração específica para o banco sentinela_treino
Adaptação das APIs para trabalhar com a estrutura normalizada
"""

import os
from pathlib import Path
from sqlalchemy import create_engine, text
from typing import Dict, Any, Optional
from psycopg import connect
from psycopg.rows import dict_row

# =============================================================================
# CONFIGURAÇÕES DO BANCO SENTINELA_TREINO
# =============================================================================

# Configuração do banco sentinela_treino
SENTINELA_TREINO_CONFIG = {
    "host": os.getenv("SENTINELA_TREINO_HOST", "localhost"),
    "port": int(os.getenv("SENTINELA_TREINO_PORT", "5432")),
    "dbname": os.getenv("SENTINELA_TREINO_DB", "sentinela_treino"),
    "user": os.getenv("SENTINELA_TREINO_USER", "postgres"),
    "password": os.getenv("SENTINELA_TREINO_PASSWORD", "Jmkjmk.00")
}

def get_sentinela_treino_engine():
    """Retorna engine SQLAlchemy para o banco sentinela_treino"""
    config = SENTINELA_TREINO_CONFIG
    conn_str = f"postgresql+psycopg://{config['user']}:{config['password']}@{config['host']}:{config['port']}/{config['dbname']}"
    
    return create_engine(
        conn_str, 
        echo=False, 
        future=True,
        pool_pre_ping=True,
        pool_recycle=3600,
        pool_size=10,
        max_overflow=20
    )

def get_sentinela_treino_connection():
    """Retorna conexão psycopg para o banco sentinela_treino"""
    config = SENTINELA_TREINO_CONFIG
    return connect(
        host=config['host'],
        port=config['port'],
        dbname=config['dbname'],
        user=config['user'],
        password=config['password']
    )

def validate_sentinela_treino_connection() -> bool:
    """Valida conectividade com o banco sentinela_treino"""
    try:
        with get_sentinela_treino_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
        return True
    except Exception as e:
        print(f"❌ Erro de conexão com sentinela_treino: {e}")
        return False

# =============================================================================
# FUNÇÕES AUXILIARES PARA APIS
# =============================================================================

def serialize_dates(obj):
    """Converte objetos de data/hora para o formato ISO para serialização JSON"""
    from datetime import datetime, date
    from decimal import Decimal
    
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    if isinstance(obj, Decimal):
        return str(obj)
    if isinstance(obj, list):
        return [serialize_dates(item) for item in obj]
    if isinstance(obj, dict):
        return {k: serialize_dates(v) for k, v in obj.items()}
    return obj

def get_vehicle_stats(veiculo_id: int) -> Dict[str, Any]:
    """Retorna estatísticas de um veículo"""
    try:
        with get_sentinela_treino_connection() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                # Buscar dados do veículo
                cur.execute("SELECT * FROM veiculos WHERE id = %s", (veiculo_id,))
                veiculo = cur.fetchone()
                
                if not veiculo:
                    return None
                
                # Buscar estatísticas das passagens
                cur.execute("""
                    SELECT 
                        COUNT(*) as total_passagens,
                        MIN(dataHoraUTC) as primeira_passagem,
                        MAX(dataHoraUTC) as ultima_passagem,
                        COUNT(DISTINCT cidade) as cidades_unicas,
                        COUNT(DISTINCT uf) as ufs_unicas,
                        COUNT(DISTINCT codigoRodovia) as rodovias_unicas,
                        COUNT(DISTINCT sistemaOrigem) as sistemas_unicos
                    FROM passagens 
                    WHERE veiculo_id = %s
                """, (veiculo_id,))
                
                stats = cur.fetchone()
                
                # Buscar distribuição por cidade
                cur.execute("""
                    SELECT cidade, uf, COUNT(*) as passagens
                    FROM passagens 
                    WHERE veiculo_id = %s AND cidade IS NOT NULL
                    GROUP BY cidade, uf
                    ORDER BY passagens DESC
                    LIMIT 10
                """, (veiculo_id,))
                
                top_cidades = cur.fetchall()
                
                # Buscar distribuição por rodovia
                cur.execute("""
                    SELECT codigoRodovia, COUNT(*) as passagens
                    FROM passagens 
                    WHERE veiculo_id = %s AND codigoRodovia IS NOT NULL
                    GROUP BY codigoRodovia
                    ORDER BY passagens DESC
                    LIMIT 10
                """, (veiculo_id,))
                
                top_rodovias = cur.fetchall()
                
                return {
                    'veiculo': serialize_dates(veiculo),
                    'estatisticas': serialize_dates(stats),
                    'top_cidades': serialize_dates(top_cidades),
                    'top_rodovias': serialize_dates(top_rodovias)
                }
                
    except Exception as e:
        print(f"❌ Erro ao buscar estatísticas do veículo {veiculo_id}: {e}")
        return None

def get_passages_by_vehicle(veiculo_id: int, limit: int = 100, offset: int = 0) -> Dict[str, Any]:
    """Retorna passagens de um veículo com paginação"""
    try:
        with get_sentinela_treino_connection() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                # Buscar passagens
                cur.execute("""
                    SELECT 
                        id, dataHoraUTC, pontoCaptura, cidade, uf,
                        codigoEquipamento, codigoRodovia, km, faixa, sentido,
                        velocidade, latitude, longitude, refImagem1, refImagem2,
                        sistemaOrigem, ehEquipamentoMovel, ehLeituraHumana,
                        tipoInferidoIA, marcaModeloInferidoIA, criado_em
                    FROM passagens 
                    WHERE veiculo_id = %s
                    ORDER BY dataHoraUTC DESC
                    LIMIT %s OFFSET %s
                """, (veiculo_id, limit, offset))
                
                passagens = cur.fetchall()
                
                # Contar total
                cur.execute("SELECT COUNT(*) FROM passagens WHERE veiculo_id = %s", (veiculo_id,))
                total = cur.fetchone()['count']
                
                return {
                    'passagens': serialize_dates(passagens),
                    'total': total,
                    'limit': limit,
                    'offset': offset,
                    'has_more': (offset + limit) < total
                }
                
    except Exception as e:
        print(f"❌ Erro ao buscar passagens do veículo {veiculo_id}: {e}")
        return None

def search_vehicles(search_term: str, limit: int = 50) -> Dict[str, Any]:
    """Busca veículos por placa ou outros critérios"""
    try:
        with get_sentinela_treino_connection() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                # Buscar por placa (exata ou parcial)
                cur.execute("""
                    SELECT 
                        id, placa, marca_modelo, tipo, total_passagens,
                        primeira_passagem, ultima_passagem,
                        array_length(cidades_visitadas, 1) as total_cidades,
                        array_length(ufs_visitadas, 1) as total_ufs
                    FROM veiculos 
                    WHERE placa ILIKE %s
                    ORDER BY total_passagens DESC, placa
                    LIMIT %s
                """, (f"%{search_term}%", limit))
                
                veiculos = cur.fetchall()
                
                return {
                    'veiculos': serialize_dates(veiculos),
                    'total': len(veiculos),
                    'search_term': search_term
                }
                
    except Exception as e:
        print(f"❌ Erro ao buscar veículos: {e}")
        return None

def get_analytics_data() -> Dict[str, Any]:
    """Retorna dados analíticos gerais do sistema"""
    try:
        with get_sentinela_treino_connection() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                # Estatísticas gerais
                cur.execute("""
                    SELECT 
                        COUNT(*) as total_veiculos,
                        SUM(total_passagens) as total_passagens,
                        AVG(total_passagens) as media_passagens_por_veiculo,
                        MAX(total_passagens) as max_passagens,
                        COUNT(DISTINCT unnest(cidades_visitadas)) as cidades_unicas,
                        COUNT(DISTINCT unnest(ufs_visitadas)) as ufs_unicas
                    FROM veiculos
                """)
                
                stats_gerais = cur.fetchone()
                
                # Top veículos com mais passagens
                cur.execute("""
                    SELECT 
                        placa, total_passagens, 
                        primeira_passagem, ultima_passagem,
                        array_length(cidades_visitadas, 1) as total_cidades,
                        array_length(ufs_visitadas, 1) as total_ufs
                    FROM veiculos 
                    ORDER BY total_passagens DESC
                    LIMIT 20
                """)
                
                top_veiculos = cur.fetchall()
                
                # Distribuição por UF
                cur.execute("""
                    SELECT 
                        unnest(ufs_visitadas) as uf,
                        COUNT(*) as veiculos
                    FROM veiculos 
                    WHERE ufs_visitadas IS NOT NULL
                    GROUP BY unnest(ufs_visitadas)
                    ORDER BY veiculos DESC
                    LIMIT 10
                """)
                
                distribuicao_uf = cur.fetchall()
                
                # Distribuição por sistema origem
                cur.execute("""
                    SELECT 
                        unnest(sistemas_origem) as sistema,
                        COUNT(*) as veiculos
                    FROM veiculos 
                    WHERE sistemas_origem IS NOT NULL
                    GROUP BY unnest(sistemas_origem)
                    ORDER BY veiculos DESC
                    LIMIT 10
                """)
                
                distribuicao_sistema = cur.fetchall()
                
                return {
                    'estatisticas_gerais': serialize_dates(stats_gerais),
                    'top_veiculos': serialize_dates(top_veiculos),
                    'distribuicao_uf': serialize_dates(distribuicao_uf),
                    'distribuicao_sistema': serialize_dates(distribuicao_sistema)
                }
                
    except Exception as e:
        print(f"❌ Erro ao buscar dados analíticos: {e}")
        return None

def get_passages_analytics(filters: Dict[str, Any] = None) -> Dict[str, Any]:
    """Retorna análises das passagens com filtros"""
    try:
        with get_sentinela_treino_connection() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                # Construir filtros WHERE
                where_conditions = ["1=1"]
                params = []
                
                if filters:
                    if filters.get('cidade'):
                        where_conditions.append("cidade ILIKE %s")
                        params.append(f"%{filters['cidade']}%")
                    
                    if filters.get('uf'):
                        where_conditions.append("uf = %s")
                        params.append(filters['uf'])
                    
                    if filters.get('data_inicio'):
                        where_conditions.append("dataHoraUTC >= %s")
                        params.append(filters['data_inicio'])
                    
                    if filters.get('data_fim'):
                        where_conditions.append("dataHoraUTC <= %s")
                        params.append(filters['data_fim'])
                
                where_clause = " AND ".join(where_conditions)
                
                # Distribuição por cidade
                cur.execute(f"""
                    SELECT cidade, uf, COUNT(*) as passagens
                    FROM passagens 
                    WHERE {where_clause} AND cidade IS NOT NULL
                    GROUP BY cidade, uf
                    ORDER BY passagens DESC
                    LIMIT 20
                """, params)
                
                distribuicao_cidade = cur.fetchall()
                
                # Distribuição por rodovia
                cur.execute(f"""
                    SELECT codigoRodovia, COUNT(*) as passagens
                    FROM passagens 
                    WHERE {where_clause} AND codigoRodovia IS NOT NULL
                    GROUP BY codigoRodovia
                    ORDER BY passagens DESC
                    LIMIT 20
                """, params)
                
                distribuicao_rodovia = cur.fetchall()
                
                # Distribuição por hora do dia
                cur.execute(f"""
                    SELECT 
                        EXTRACT(HOUR FROM dataHoraUTC) as hora,
                        COUNT(*) as passagens
                    FROM passagens 
                    WHERE {where_clause}
                    GROUP BY EXTRACT(HOUR FROM dataHoraUTC)
                    ORDER BY hora
                """, params)
                
                distribuicao_hora = cur.fetchall()
                
                # Distribuição por dia da semana
                cur.execute(f"""
                    SELECT 
                        EXTRACT(DOW FROM dataHoraUTC) as dia_semana,
                        COUNT(*) as passagens
                    FROM passagens 
                    WHERE {where_clause}
                    GROUP BY EXTRACT(DOW FROM dataHoraUTC)
                    ORDER BY dia_semana
                """, params)
                
                distribuicao_dia_semana = cur.fetchall()
                
                return {
                    'distribuicao_cidade': serialize_dates(distribuicao_cidade),
                    'distribuicao_rodovia': serialize_dates(distribuicao_rodovia),
                    'distribuicao_hora': serialize_dates(distribuicao_hora),
                    'distribuicao_dia_semana': serialize_dates(distribuicao_dia_semana),
                    'filtros_aplicados': filters or {}
                }
                
    except Exception as e:
        print(f"❌ Erro ao buscar análises de passagens: {e}")
        return None

# =============================================================================
# EXPORTS
# =============================================================================

__all__ = [
    'SENTINELA_TREINO_CONFIG',
    'get_sentinela_treino_engine',
    'get_sentinela_treino_connection',
    'validate_sentinela_treino_connection',
    'serialize_dates',
    'get_vehicle_stats',
    'get_passages_by_vehicle',
    'search_vehicles',
    'get_analytics_data',
    'get_passages_analytics'
]

print("⚙️ Sentinela Treino config module loaded successfully")

