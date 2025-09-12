# app/utils/helpers.py
"""
Helpers específicos para o sistema de análise de placas
Funções auxiliares para regras de negócio, análise de dados e processamento
"""

import re
import json
import hashlib
from datetime import datetime, timedelta, time as datetime_time
from typing import Dict, List, Any, Optional, Tuple, Union
from collections import defaultdict, Counter
import numpy as np
from dataclasses import dataclass
from enum import Enum

# =============================================================================
# ENUMS E CLASSES AUXILIARES
# =============================================================================

class RiskLevel(Enum):
    BAIXO = "BAIXO"
    MEDIO = "MEDIO"
    ALTO = "ALTO"
    CRITICO = "CRITICO"

class OcorrenciaType(Enum):
    ABORDAGEM = "Abordagem"
    BOP = "BOP"
    LOCAL_ENTREGA = "Local de Entrega"

@dataclass
class PlacaInfo:
    """Informações consolidadas de uma placa"""
    placa: str
    veiculo_info: Dict[str, Any]
    total_passagens: int
    total_ocorrencias: int
    primeira_passagem: Optional[datetime]
    ultima_passagem: Optional[datetime]
    municipios_visitados: List[str]
    rodovias_utilizadas: List[str]
    risk_score: float = 0.0
    risk_level: RiskLevel = RiskLevel.BAIXO

@dataclass
class RoutePattern:
    """Padrão de rota identificado"""
    origem: str
    destino: str
    frequencia: int
    ultima_ocorrencia: datetime
    risco_associado: float
    horarios_comuns: List[int]  # Horas do dia

# =============================================================================
# HELPERS PARA ANÁLISE DE VEÍCULOS
# =============================================================================

def extract_veiculo_info(veiculo_data: Dict) -> Dict[str, Any]:
    """Extrai e padroniza informações do veículo"""
    if not veiculo_data:
        return {}
    
    return {
        "id": veiculo_data.get("id"),
        "placa": veiculo_data.get("placa", "").upper(),
        "marca_modelo": veiculo_data.get("marca_modelo", "N/I"),
        "cor": veiculo_data.get("cor", "N/I"),
        "tipo": veiculo_data.get("tipo", "N/I"),
        "ano_modelo": veiculo_data.get("ano_modelo"),
        "local_emplacamento": veiculo_data.get("local_emplacamento", "N/I"),
        "criado_em": veiculo_data.get("criado_em")
    }

def is_veiculo_suspeito_profile(veiculo_info: Dict) -> Tuple[bool, List[str]]:
    """Analisa se o perfil do veículo é suspeito"""
    indicators = []
    score = 0
    
    # Cor do veículo
    cor = (veiculo_info.get("cor", "") or "").lower()
    cores_suspeitas = ["preto", "prata", "cinza", "branco"]
    if cor in cores_suspeitas:
        score += 1
        indicators.append(f"Cor comum em atividades ilícitas: {cor}")
    
    # Tipo de veículo
    tipo = (veiculo_info.get("tipo", "") or "").lower()
    if "suv" in tipo or "pickup" in tipo or "van" in tipo:
        score += 1
        indicators.append(f"Tipo de veículo comumente usado: {tipo}")
    
    # Idade do veículo (se disponível)
    ano = veiculo_info.get("ano_modelo")
    if ano and isinstance(ano, int):
        idade = datetime.now().year - ano
        if idade > 15:  # Veículos muito antigos
            score += 1
            indicators.append(f"Veículo antigo ({idade} anos)")
        elif idade < 2:  # Veículos muito novos
            score += 1
            indicators.append(f"Veículo muito novo ({idade} anos)")
    
    return score >= 2, indicators

def get_vehicle_risk_factors(passagens: List[Dict], ocorrencias: List[Dict]) -> Dict[str, Any]:
    """Calcula fatores de risco baseado no histórico do veículo"""
    factors = {
        "night_activity": 0.0,
        "border_proximity": 0.0,
        "route_repetition": 0.0,
        "suspicious_locations": 0.0,
        "frequency_anomaly": 0.0
    }
    
    if not passagens:
        return factors
    
    # Análise de atividade noturna
    night_count = sum(1 for p in passagens if is_night_time(p.get("datahora")))
    factors["night_activity"] = min(1.0, night_count / len(passagens))
    
    # Análise de locais suspeitos
    suspicious_cities = get_suspicious_cities()
    suspicious_count = sum(1 for p in passagens 
                          if p.get("municipio", "").lower() in suspicious_cities)
    factors["suspicious_locations"] = min(1.0, suspicious_count / len(passagens))
    
    # Análise de repetição de rotas
    routes = [(p.get("municipio"), p.get("rodovia")) for p in passagens]
    route_counts = Counter(routes)
    max_repetition = max(route_counts.values()) if route_counts else 0
    factors["route_repetition"] = min(1.0, max_repetition / len(passagens))
    
    return factors

# =============================================================================
# HELPERS PARA ANÁLISE DE PADRÕES TEMPORAIS
# =============================================================================

def is_night_time(datahora: Union[str, datetime]) -> bool:
    """Verifica se o horário é considerado noturno (22h-6h)"""
    if not datahora:
        return False
    
    try:
        if isinstance(datahora, str):
            dt = datetime.fromisoformat(datahora.replace('Z', '+00:00'))
        else:
            dt = datahora
        
        hour = dt.hour
        return hour >= 22 or hour <= 6
    except:
        return False

def is_weekend(datahora: Union[str, datetime]) -> bool:
    """Verifica se a data é fim de semana"""
    if not datahora:
        return False
    
    try:
        if isinstance(datahora, str):
            dt = datetime.fromisoformat(datahora.replace('Z', '+00:00'))
        else:
            dt = datahora
        
        return dt.weekday() >= 5  # 5=sábado, 6=domingo
    except:
        return False

def get_time_period(datahora: Union[str, datetime]) -> str:
    """Retorna período do dia: madrugada, manhã, tarde, noite"""
    if not datahora:
        return "indefinido"
    
    try:
        if isinstance(datahora, str):
            dt = datetime.fromisoformat(datahora.replace('Z', '+00:00'))
        else:
            dt = datahora
        
        hour = dt.hour
        if 0 <= hour < 6:
            return "madrugada"
        elif 6 <= hour < 12:
            return "manha"
        elif 12 <= hour < 18:
            return "tarde"
        else:
            return "noite"
    except:
        return "indefinido"

def analyze_temporal_patterns(passagens: List[Dict]) -> Dict[str, Any]:
    """Analisa padrões temporais nas passagens"""
    if not passagens:
        return {}
    
    patterns = {
        "hour_distribution": defaultdict(int),
        "day_of_week_distribution": defaultdict(int),
        "period_distribution": defaultdict(int),
        "night_percentage": 0.0,
        "weekend_percentage": 0.0,
        "most_active_hour": None,
        "most_active_day": None
    }
    
    night_count = 0
    weekend_count = 0
    
    for passagem in passagens:
        datahora = passagem.get("datahora")
        if not datahora:
            continue
        
        try:
            if isinstance(datahora, str):
                dt = datetime.fromisoformat(datahora.replace('Z', '+00:00'))
            else:
                dt = datahora
            
            # Distribuições
            patterns["hour_distribution"][dt.hour] += 1
            patterns["day_of_week_distribution"][dt.weekday()] += 1
            patterns["period_distribution"][get_time_period(dt)] += 1
            
            # Contadores especiais
            if is_night_time(dt):
                night_count += 1
            if is_weekend(dt):
                weekend_count += 1
                
        except:
            continue
    
    total = len(passagens)
    patterns["night_percentage"] = (night_count / total) * 100 if total > 0 else 0
    patterns["weekend_percentage"] = (weekend_count / total) * 100 if total > 0 else 0
    
    # Hora mais ativa
    if patterns["hour_distribution"]:
        patterns["most_active_hour"] = max(patterns["hour_distribution"], 
                                         key=patterns["hour_distribution"].get)
    
    # Dia mais ativo
    if patterns["day_of_week_distribution"]:
        patterns["most_active_day"] = max(patterns["day_of_week_distribution"], 
                                        key=patterns["day_of_week_distribution"].get)
    
    return patterns

# =============================================================================
# HELPERS PARA ANÁLISE GEOGRÁFICA
# =============================================================================

def get_suspicious_cities() -> List[str]:
    """Lista de cidades consideradas suspeitas (fronteiras, etc.)"""
    return [
        "foz do iguacu", "cidade del este", "pedro juan caballero",
        "ponta pora", "corumba", "uruguaiana", "santana do livramento",
        "jaguarao", "acegua", "barra do quarai", "itaqui"
    ]

def get_border_cities() -> List[str]:
    """Lista de cidades de fronteira"""
    return [
        "foz do iguacu", "ponta pora", "corumba", "uruguaiana",
        "santana do livramento", "jaguarao", "acegua", "barra do quarai"
    ]

def is_border_route(origem: str, destino: str) -> bool:
    """Verifica se a rota envolve cidades de fronteira"""
    border_cities = [city.lower() for city in get_border_cities()]
    origem_lower = origem.lower() if origem else ""
    destino_lower = destino.lower() if destino else ""
    
    return origem_lower in border_cities or destino_lower in border_cities

def calculate_route_risk(origem: str, destino: str, frequencia: int) -> float:
    """Calcula risco de uma rota específica"""
    risk = 0.0
    
    # Risco por fronteira
    if is_border_route(origem, destino):
        risk += 0.4
    
    # Risco por cidades suspeitas
    suspicious = [city.lower() for city in get_suspicious_cities()]
    if origem.lower() in suspicious or destino.lower() in suspicious:
        risk += 0.3
    
    # Risco por frequência alta
    if frequencia > 10:
        risk += 0.2
    elif frequencia > 5:
        risk += 0.1
    
    return min(1.0, risk)

def detect_route_patterns(passagens: List[Dict], min_frequency: int = 3) -> List[RoutePattern]:
    """Detecta padrões de rotas frequentes"""
    if not passagens:
        return []
    
    # Agrupar passagens por rota (origem->destino)
    routes = defaultdict(list)
    
    for i, passagem in enumerate(passagens[:-1]):  # Excluir última para ter destino
        if i + 1 < len(passagens):
            origem = passagem.get("municipio", "N/I")
            destino = passagens[i + 1].get("municipio", "N/I")
            route_key = f"{origem}->{destino}"
            routes[route_key].append(passagem)
    
    patterns = []
    
    for route_key, route_passagens in routes.items():
        if len(route_passagens) >= min_frequency:
            origem, destino = route_key.split("->")
            
            # Extrair horários comuns
            horarios = []
            for p in route_passagens:
                try:
                    if isinstance(p.get("datahora"), str):
                        dt = datetime.fromisoformat(p["datahora"].replace('Z', '+00:00'))
                        horarios.append(dt.hour)
                except:
                    continue
            
            pattern = RoutePattern(
                origem=origem,
                destino=destino,
                frequencia=len(route_passagens),
                ultima_ocorrencia=max(p.get("datahora") for p in route_passagens 
                                    if p.get("datahora")),
                risco_associado=calculate_route_risk(origem, destino, len(route_passagens)),
                horarios_comuns=list(set(horarios))
            )
            
            patterns.append(pattern)
    
    # Ordenar por frequência
    return sorted(patterns, key=lambda p: p.frequencia, reverse=True)

# =============================================================================
# HELPERS PARA ANÁLISE DE OCORRÊNCIAS
# =============================================================================

def categorize_ocorrencia(ocorrencia: Dict) -> Dict[str, Any]:
    """Categoriza uma ocorrência e extrai informações relevantes"""
    tipo = ocorrencia.get("tipo", "")
    relato = ocorrencia.get("relato", "")
    
    categoria = {
        "tipo_original": tipo,
        "categoria": "indefinida",
        "gravidade": 1,  # 1-5
        "indicadores_suspeitos": [],
        "substancias_encontradas": [],
        "armas_encontradas": [],
        "valor_estimado": 0.0
    }
    
    # Categorizar por tipo
    if tipo == "BOP":
        categoria["categoria"] = "apreensao"
        categoria["gravidade"] = 4
    elif tipo == "Abordagem":
        categoria["categoria"] = "fiscalizacao"
        categoria["gravidade"] = 2
    elif tipo == "Local de Entrega":
        categoria["categoria"] = "entrega_drogas"
        categoria["gravidade"] = 5
    
    # Analisar relato
    if relato:
        relato_lower = relato.lower()
        
        # Substâncias
        substancias = {
            "maconha": ["maconha", "marijuana", "erva"],
            "cocaina": ["cocaina", "pó", "coca"],
            "crack": ["crack", "pedra"],
            "skunk": ["skunk"],
            "sinteticos": ["mdma", "ecstasy", "lsd", "sintetico"]
        }
        
        for substancia, palavras in substancias.items():
            if any(palavra in relato_lower for palavra in palavras):
                categoria["substancias_encontradas"].append(substancia)
        
        # Armas
        armas_palavras = ["arma", "revolver", "pistola", "fuzil", "espingarda"]
        for palavra in armas_palavras:
            if palavra in relato_lower:
                categoria["armas_encontradas"].append(palavra)
        
        # Indicadores suspeitos
        indicadores = [
            "nervoso", "agressivo", "mentiu", "contradicao", "nao soube explicar",
            "comportamento suspeito", "tentou fugir", "resistiu", "fronteira"
        ]
        
        for indicador in indicadores:
            if indicador in relato_lower:
                categoria["indicadores_suspeitos"].append(indicador)
    
    # Ajustar gravidade baseada nos achados
    if categoria["armas_encontradas"]:
        categoria["gravidade"] = min(5, categoria["gravidade"] + 2)
    if categoria["substancias_encontradas"]:
        categoria["gravidade"] = min(5, categoria["gravidade"] + 1)
    if len(categoria["indicadores_suspeitos"]) > 2:
        categoria["gravidade"] = min(5, categoria["gravidade"] + 1)
    
    return categoria

def aggregate_ocorrencias_stats(ocorrencias: List[Dict]) -> Dict[str, Any]:
    """Agrega estatísticas das ocorrências"""
    if not ocorrencias:
        return {}
    
    stats = {
        "total": len(ocorrencias),
        "por_tipo": defaultdict(int),
        "por_categoria": defaultdict(int),
        "gravidade_media": 0.0,
        "substancias_total": defaultdict(int),
        "armas_total": defaultdict(int),
        "indicadores_total": defaultdict(int),
        "primeira_ocorrencia": None,
        "ultima_ocorrencia": None
    }
    
    gravidades = []
    datas = []
    
    for ocorrencia in ocorrencias:
        categoria = categorize_ocorrencia(ocorrencia)
        
        stats["por_tipo"][categoria["tipo_original"]] += 1
        stats["por_categoria"][categoria["categoria"]] += 1
        gravidades.append(categoria["gravidade"])
        
        # Agregações
        for substancia in categoria["substancias_encontradas"]:
            stats["substancias_total"][substancia] += 1
        
        for arma in categoria["armas_encontradas"]:
            stats["armas_total"][arma] += 1
        
        for indicador in categoria["indicadores_suspeitos"]:
            stats["indicadores_total"][indicador] += 1
        
        # Datas
        if ocorrencia.get("datahora"):
            try:
                if isinstance(ocorrencia["datahora"], str):
                    dt = datetime.fromisoformat(ocorrencia["datahora"].replace('Z', '+00:00'))
                else:
                    dt = ocorrencia["datahora"]
                datas.append(dt)
            except:
                pass
    
    if gravidades:
        stats["gravidade_media"] = sum(gravidades) / len(gravidades)
    
    if datas:
        stats["primeira_ocorrencia"] = min(datas)
        stats["ultima_ocorrencia"] = max(datas)
    
    return stats

# =============================================================================
# HELPERS PARA CÁLCULO DE RISCO
# =============================================================================

def calculate_comprehensive_risk(veiculo_info: Dict, passagens: List[Dict], 
                               ocorrencias: List[Dict]) -> Dict[str, Any]:
    """Calcula risco abrangente baseado em todos os dados"""
    
    risk_components = {
        "vehicle_profile": 0.0,
        "route_patterns": 0.0,
        "temporal_patterns": 0.0,
        "occurrence_history": 0.0,
        "geographic_risk": 0.0
    }
    
    weights = {
        "vehicle_profile": 0.1,
        "route_patterns": 0.3,
        "temporal_patterns": 0.2,
        "occurrence_history": 0.3,
        "geographic_risk": 0.1
    }
    
    # 1. Perfil do veículo
    is_suspicious_vehicle, _ = is_veiculo_suspeito_profile(veiculo_info)
    risk_components["vehicle_profile"] = 0.6 if is_suspicious_vehicle else 0.2
    
    # 2. Padrões de rota
    vehicle_factors = get_vehicle_risk_factors(passagens, ocorrencias)
    risk_components["route_patterns"] = (
        vehicle_factors.get("route_repetition", 0) * 0.4 +
        vehicle_factors.get("suspicious_locations", 0) * 0.6
    )
    
    # 3. Padrões temporais
    temporal = analyze_temporal_patterns(passagens)
    night_risk = min(1.0, temporal.get("night_percentage", 0) / 100 * 2)  # >50% noite = alto risco
    weekend_risk = min(1.0, temporal.get("weekend_percentage", 0) / 100 * 1.5)
    risk_components["temporal_patterns"] = (night_risk + weekend_risk) / 2
    
    # 4. Histórico de ocorrências
    if ocorrencias:
        occ_stats = aggregate_ocorrencias_stats(ocorrencias)
        occurrence_risk = min(1.0, occ_stats.get("gravidade_media", 0) / 5)
        # Bonus por substâncias e armas
        if occ_stats.get("substancias_total"):
            occurrence_risk = min(1.0, occurrence_risk + 0.3)
        if occ_stats.get("armas_total"):
            occurrence_risk = min(1.0, occurrence_risk + 0.4)
        risk_components["occurrence_history"] = occurrence_risk
    
    # 5. Risco geográfico
    border_count = sum(1 for p in passagens 
                      if p.get("municipio", "").lower() in [c.lower() for c in get_border_cities()])
    if passagens:
        risk_components["geographic_risk"] = min(1.0, border_count / len(passagens) * 2)
    
    # Cálculo final
    final_risk = sum(risk_components[comp] * weights[comp] 
                    for comp in risk_components)
    
    # Determinar nível
    if final_risk >= 0.8:
        risk_level = RiskLevel.CRITICO
    elif final_risk >= 0.6:
        risk_level = RiskLevel.ALTO
    elif final_risk >= 0.4:
        risk_level = RiskLevel.MEDIO
    else:
        risk_level = RiskLevel.BAIXO
    
    return {
        "final_risk": final_risk,
        "risk_level": risk_level.value,
        "components": risk_components,
        "weights_used": weights,
        "risk_factors": {
            "high_risk_factors": [k for k, v in risk_components.items() if v > 0.7],
            "medium_risk_factors": [k for k, v in risk_components.items() if 0.4 <= v <= 0.7],
            "low_risk_factors": [k for k, v in risk_components.items() if v < 0.4]
        }
    }

# =============================================================================
# HELPERS PARA CACHE E PERFORMANCE
# =============================================================================

def generate_cache_key(*args, **kwargs) -> str:
    """Gera chave de cache baseada nos argumentos"""
    key_parts = []
    
    for arg in args:
        if isinstance(arg, (str, int, float)):
            key_parts.append(str(arg))
        else:
            key_parts.append(str(hash(str(arg))))
    
    for k, v in sorted(kwargs.items()):
        key_parts.append(f"{k}:{v}")
    
    key_string = ":".join(key_parts)
    return hashlib.md5(key_string.encode()).hexdigest()[:16]

def should_recalculate_risk(last_calculation: datetime, 
                          new_data_since: Optional[datetime] = None) -> bool:
    """Determina se o risco deve ser recalculado"""
    if not last_calculation:
        return True
    
    # Recalcular se dados muito antigos (>24h)
    if datetime.now() - last_calculation > timedelta(hours=24):
        return True
    
    # Recalcular se há dados novos desde a última análise
    if new_data_since and new_data_since > last_calculation:
        return True
    
    return False

# =============================================================================
# EXPORTS
# =============================================================================

__all__ = [
    'RiskLevel', 'OcorrenciaType', 'PlacaInfo', 'RoutePattern',
    'extract_veiculo_info', 'is_veiculo_suspeito_profile', 'get_vehicle_risk_factors',
    'is_night_time', 'is_weekend', 'get_time_period', 'analyze_temporal_patterns',
    'get_suspicious_cities', 'get_border_cities', 'is_border_route', 'calculate_route_risk',
    'detect_route_patterns', 'categorize_ocorrencia', 'aggregate_ocorrencias_stats',
    'calculate_comprehensive_risk', 'generate_cache_key', 'should_recalculate_risk'
]