# backend/config/agents/semantic_binary_config.py
"""
Configuração especializada para Agente Semântico com Classificação Binária
Sistema otimizado para detectar apenas SUSPEITO vs SEM_ALTERACAO
"""

from dataclasses import dataclass, field
from typing import Dict, List, Set, Optional, Any
import os
import json
from pathlib import Path

@dataclass
class BinarySemanticConfig:
    """Configuração para classificação binária semântica"""
    
    # =================================================================
    # CONFIGURAÇÕES PRINCIPAIS
    # =================================================================
    
    # Classificação binária
    classification_mode: str = "binary"  # Sempre binário
    positive_class: str = "SUSPEITO"
    negative_class: str = "SEM_ALTERACAO"
    
    # Thresholds críticos
    suspicion_threshold: float = 0.5      # Limite para considerar suspeito
    confidence_threshold: float = 0.7     # Confiança mínima na classificação
    high_risk_threshold: float = 0.8      # Threshold para casos de alto risco
    
    # =================================================================
    # SISTEMA DE PONTUAÇÃO PONDERADA
    # =================================================================
    
    # Pesos para diferentes indicadores (devem somar ~1.0)
    indicator_weights: Dict[str, float] = field(default_factory=lambda: {
        'palavras_criticas': 0.25,        # Palavras de alto impacto
        'padroes_cobertura': 0.20,        # Histórias de cobertura
        'contexto_criminal': 0.20,        # Contextos criminais
        'inconsistencias_narrativas': 0.15, # Contradições/evasões
        'palavras_suspeitas_gerais': 0.10,  # Vocabulário geral suspeito
        'indicadores_comportamentais': 0.10  # Padrões comportamentais
    })
    
    # =================================================================
    # LISTAS DE PALAVRAS E PADRÕES CRÍTICOS
    # =================================================================
    
    # Palavras críticas (maior peso)
    critical_keywords: Set[str] = field(default_factory=lambda: {
        'droga', 'cocaína', 'maconha', 'crack', 'tráfico', 'traficante',
        'arma', 'revolver', 'pistola', 'munição', 'disparo',
        'roubo', 'assalto', 'furto', 'receptação',
        'foragido', 'procurado', 'mandado',
        'boca de fumo', 'ponto de droga', 'contenção',
        'flagrante', 'apreensão', 'entorpecente', 'pó', 'pedra',
        'rifle', 'escopeta', 'calibre', 'cartucho',
        'latrocínio', 'homicídio', 'lesão corporal'
    })
    
    # Padrões típicos de histórias de cobertura
    coverage_patterns: List[str] = field(default_factory=lambda: [
        'estava passando e vi',
        'não sabia de nada',
        'só estava dando uma volta',
        'estava indo para casa',
        'não conhecia ninguém',
        'estava esperando alguém',
        'estava perdido',
        'peguei carona',
        'estava indo trabalhar',
        'estava voltando do trabalho',
        'não tinha conhecimento',
        'nunca vi isso antes',
        'apareceu do nada',
        'não é meu',
        'alguém deve ter colocado',
        'não sei como chegou aqui',
        'estava guardando para alguém',
        'achei na rua'
    ])
    
    # Indicadores de evasão narrativa
    evasion_indicators: List[str] = field(default_factory=lambda: [
        'não lembro', 'não sei', 'talvez', 'acho que', 'pode ser',
        'não tenho certeza', 'mais ou menos', 'não reparei',
        'não prestei atenção', 'não percebi', 'estava distraído',
        'não me lembro bem', 'meio que', 'tipo assim',
        'não faço ideia', 'sei lá', 'vai saber',
        'pode ter sido', 'acho que sim', 'acho que não'
    ])
    
    # Contextos criminais específicos
    criminal_contexts: Set[str] = field(default_factory=lambda: {
        'zona de tráfico', 'área controlada', 'território',
        'ponto conhecido', 'local suspeito', 'região perigosa',
        'horário suspeito', 'madrugada', 'local ermo',
        'sem documento', 'sem identificação', 'nervoso',
        'atitude suspeita', 'comportamento estranho',
        'olhar desconfiado', 'tentou fugir', 'resistiu',
        'agiu de forma estranha', 'demonstrou nervosismo',
        'local conhecido pelo tráfico', 'área de conflito',
        'ponto de venda', 'boca de fumo ativa'
    })
    
    # Palavras que indicam normalidade (reduzem score)
    normal_indicators: Set[str] = field(default_factory=lambda: {
        'trabalho', 'emprego', 'família', 'filhos', 'esposa',
        'casa', 'igreja', 'escola', 'hospital', 'médico',
        'documentos', 'carteira', 'identidade', 'cpf',
        'colaborou', 'ajudou', 'explicou', 'esclareceu',
        'honesto', 'trabalhador', 'responsável', 'pai de família'
    })
    
    # =================================================================
    # CONFIGURAÇÕES DE PERFORMANCE
    # =================================================================
    
    # Performance do agente
    max_concurrent_analyses: int = 5
    analysis_timeout: float = 30.0
    cache_results: bool = True
    cache_ttl_minutes: int = 60
    
    # Configurações de ML
    model_confidence_required: float = 0.6
    enable_ensemble_voting: bool = True
    use_calibrated_probabilities: bool = True
    
    # =================================================================
    # CONFIGURAÇÕES DE CONTEXTO EXPANDIDO
    # =================================================================
    
    # Análise contextual avançada
    analyze_temporal_context: bool = True      # Análise de horários suspeitos
    analyze_location_context: bool = True      # Análise de locais suspeitos
    analyze_behavioral_context: bool = True    # Análise comportamental
    
    # Horários considerados suspeitos (24h format)
    suspicious_hours: List[int] = field(default_factory=lambda: [22, 23, 0, 1, 2, 3, 4, 5])
    
    # Multiplicadores de risco por contexto
    context_multipliers: Dict[str, float] = field(default_factory=lambda: {
        'horario_suspeito': 1.2,
        'local_conhecido_crime': 1.5,
        'comportamento_evasivo': 1.3,
        'sem_documentacao': 1.2,
        'grupo_suspeito': 1.4,
        'reincidencia': 2.0,
        'area_fronteira': 1.6,
        'local_ermo': 1.3,
        'tentativa_fuga': 1.8
    })
    
    # =================================================================
    # CONFIGURAÇÕES DE VALIDAÇÃO E QUALIDADE
    # =================================================================
    
    # Validação de entrada
    min_text_length: int = 20              # Mínimo de caracteres
    max_text_length: int = 5000            # Máximo de caracteres
    require_meaningful_content: bool = True # Rejeitar textos vazios/inúteis
    
    # Controle de qualidade
    flag_low_confidence: bool = True        # Sinalizar baixa confiança
    require_human_review_threshold: float = 0.4  # Casos que precisam revisão humana
    
    # =================================================================
    # CONFIGURAÇÕES DE LOGGING E AUDITORIA
    # =================================================================
    
    # Logging detalhado
    log_all_classifications: bool = True
    log_confidence_scores: bool = True
    log_decision_factors: bool = True
    log_processing_time: bool = True
    
    # Auditoria
    track_false_positives: bool = True
    track_false_negatives: bool = True
    enable_feedback_loop: bool = True
    save_difficult_cases: bool = True
    
    # =================================================================
    # CONFIGURAÇÕES AVANÇADAS DE ANÁLISE
    # =================================================================
    
    # Análise de padrões textuais
    detect_repetitive_patterns: bool = True
    analyze_sentence_structure: bool = True
    check_vocabulary_diversity: bool = True
    
    # Limites para detecção de padrões suspeitos
    max_repetitive_phrases: int = 3  # Máximo de frases repetitivas antes de sinalizar
    min_vocabulary_ratio: float = 0.4  # Razão mínima palavras únicas/total
    max_evasion_indicators: int = 5  # Máximo de indicadores de evasão
    
    # Análise de consistência temporal
    check_temporal_consistency: bool = True
    flag_multiple_timeframes: bool = True
    
    # =================================================================
    # MÉTODOS DE CONFIGURAÇÃO DINÂMICA
    # =================================================================
    
    def adjust_threshold_for_context(self, context: str) -> float:
        """Ajusta threshold baseado no contexto específico"""
        base_threshold = self.suspicion_threshold
        
        if context in self.context_multipliers:
            multiplier = self.context_multipliers[context]
            # Reduz threshold para contextos de maior risco
            adjusted = base_threshold / multiplier
            return max(0.1, min(0.9, adjusted))
        
        return base_threshold
    
    def get_weighted_indicators(self) -> Dict[str, float]:
        """Retorna indicadores com pesos normalizados"""
        total_weight = sum(self.indicator_weights.values())
        if total_weight == 0:
            return self.indicator_weights
        return {
            key: weight / total_weight 
            for key, weight in self.indicator_weights.items()
        }
    
    def calculate_dynamic_threshold(self, context_factors: List[str]) -> float:
        """Calcula threshold dinâmico baseado em múltiplos fatores contextuais"""
        base_threshold = self.suspicion_threshold
        
        # Aplicar multiplicadores sequencialmente
        for factor in context_factors:
            if factor in self.context_multipliers:
                multiplier = self.context_multipliers[factor]
                base_threshold = base_threshold / multiplier
        
        # Garantir que o threshold permaneça dentro de limites razoáveis
        return max(0.05, min(0.95, base_threshold))
    
    def get_risk_level(self, confidence: float) -> str:
        """Determina nível de risco baseado na confiança"""
        if confidence >= self.high_risk_threshold:
            return "ALTO"
        elif confidence >= self.confidence_threshold:
            return "MEDIO"
        elif confidence >= self.suspicion_threshold:
            return "BAIXO"
        else:
            return "MINIMO"
    
    def should_require_human_review(self, confidence: float, context_factors: List[str] = None) -> bool:
        """Determina se caso requer revisão humana"""
        # Baixa confiança sempre requer revisão
        if confidence < self.require_human_review_threshold:
            return True
        
        # Casos limítrofes próximos ao threshold
        if abs(confidence - self.suspicion_threshold) < 0.1:
            return True
        
        # Contextos específicos que sempre requerem revisão
        high_stakes_contexts = ['reincidencia', 'area_fronteira', 'tentativa_fuga']
        if context_factors:
            for context in context_factors:
                if context in high_stakes_contexts:
                    return True
        
        return False
    
    def validate_configuration(self) -> List[str]:
        """Valida configuração e retorna lista de problemas"""
        issues = []
        
        # Verificar pesos
        total_weight = sum(self.indicator_weights.values())
        if abs(total_weight - 1.0) > 0.15:  # Tolerância de 15%
            issues.append(f"Pesos dos indicadores não somam ~1.0: {total_weight:.3f}")
        
        # Verificar thresholds
        thresholds_to_check = [
            ('suspicion_threshold', self.suspicion_threshold),
            ('confidence_threshold', self.confidence_threshold),
            ('high_risk_threshold', self.high_risk_threshold),
            ('require_human_review_threshold', self.require_human_review_threshold)
        ]
        
        for name, value in thresholds_to_check:
            if not 0.0 <= value <= 1.0:
                issues.append(f"{name} deve estar entre 0.0 e 1.0: {value}")
        
        # Verificar ordem dos thresholds
        if self.suspicion_threshold >= self.confidence_threshold:
            issues.append("suspicion_threshold deve ser menor que confidence_threshold")
        
        if self.confidence_threshold >= self.high_risk_threshold:
            issues.append("confidence_threshold deve ser menor que high_risk_threshold")
        
        # Verificar listas não vazias
        required_lists = [
            ('critical_keywords', self.critical_keywords),
            ('coverage_patterns', self.coverage_patterns),
            ('evasion_indicators', self.evasion_indicators),
            ('criminal_contexts', self.criminal_contexts)
        ]
        
        for name, collection in required_lists:
            if not collection:
                issues.append(f"Lista {name} está vazia")
        
        # Verificar configurações de performance
        if self.max_concurrent_analyses <= 0:
            issues.append("max_concurrent_analyses deve ser maior que 0")
        
        if self.analysis_timeout <= 0:
            issues.append("analysis_timeout deve ser maior que 0")
        
        # Verificar limites de texto
        if self.min_text_length >= self.max_text_length:
            issues.append("min_text_length deve ser menor que max_text_length")
        
        return issues
    
    def optimize_for_precision(self):
        """Otimiza configuração para maior precisão (menos falsos positivos)"""
        self.suspicion_threshold = 0.7
        self.confidence_threshold = 0.8
        self.high_risk_threshold = 0.9
        self.require_human_review_threshold = 0.5
        
        # Aumenta peso de indicadores mais confiáveis
        self.indicator_weights.update({
            'palavras_criticas': 0.35,
            'padroes_cobertura': 0.25,
            'contexto_criminal': 0.20,
            'inconsistencias_narrativas': 0.10,
            'palavras_suspeitas_gerais': 0.05,
            'indicadores_comportamentais': 0.05
        })
        
        # Configurações mais conservadoras
        self.max_evasion_indicators = 3
        self.max_repetitive_phrases = 2
    
    def optimize_for_recall(self):
        """Otimiza configuração para maior recall (menos falsos negativos)"""
        self.suspicion_threshold = 0.3
        self.confidence_threshold = 0.5
        self.high_risk_threshold = 0.6
        self.require_human_review_threshold = 0.2
        
        # Distribui pesos de forma mais equilibrada
        self.indicator_weights.update({
            'palavras_criticas': 0.20,
            'padroes_cobertura': 0.18,
            'contexto_criminal': 0.18,
            'inconsistencias_narrativas': 0.16,
            'palavras_suspeitas_gerais': 0.14,
            'indicadores_comportamentais': 0.14
        })
        
        # Configurações mais sensíveis
        self.max_evasion_indicators = 8
        self.max_repetitive_phrases = 5
    
    def optimize_for_balanced(self):
        """Otimiza configuração para performance balanceada"""
        self.suspicion_threshold = 0.5
        self.confidence_threshold = 0.7
        self.high_risk_threshold = 0.8
        self.require_human_review_threshold = 0.4
        
        # Pesos balanceados (valores padrão)
        self.indicator_weights.update({
            'palavras_criticas': 0.25,
            'padroes_cobertura': 0.20,
            'contexto_criminal': 0.20,
            'inconsistencias_narrativas': 0.15,
            'palavras_suspeitas_gerais': 0.10,
            'indicadores_comportamentais': 0.10
        })
    
    # =================================================================
    # CONFIGURAÇÕES DE INTEGRAÇÃO COM AGENTES
    # =================================================================
    
    # Comunicação entre agentes
    share_context_with_other_agents: bool = True
    receive_context_from_route_agent: bool = True
    receive_context_from_profile_agent: bool = True
    
    # Escalação para agentes especializados
    escalate_high_risk_cases: bool = True
    escalation_threshold: float = 0.85
    
    # Cache compartilhado entre agentes
    use_shared_cache: bool = True
    shared_cache_prefix: str = "semantic_binary"
    
    # Integração com sistema de feedback
    enable_model_feedback: bool = True
    feedback_confidence_threshold: float = 0.9
    
    def to_dict(self) -> Dict[str, Any]:
        """Converte configuração para dicionário"""
        return {
            'classification_mode': self.classification_mode,
            'classes': {
                'positive': self.positive_class,
                'negative': self.negative_class
            },
            'thresholds': {
                'suspicion': self.suspicion_threshold,
                'confidence': self.confidence_threshold,
                'high_risk': self.high_risk_threshold,
                'human_review': self.require_human_review_threshold
            },
            'weights': self.get_weighted_indicators(),
            'performance': {
                'max_concurrent': self.max_concurrent_analyses,
                'timeout': self.analysis_timeout,
                'cache_ttl': self.cache_ttl_minutes
            },
            'validation': {
                'min_length': self.min_text_length,
                'max_length': self.max_text_length,
                'require_content': self.require_meaningful_content
            },
            'collections_size': {
                'critical_keywords': len(self.critical_keywords),
                'coverage_patterns': len(self.coverage_patterns),
                'evasion_indicators': len(self.evasion_indicators),
                'criminal_contexts': len(self.criminal_contexts),
                'normal_indicators': len(self.normal_indicators)
            },
            'features': {
                'temporal_analysis': self.analyze_temporal_context,
                'location_analysis': self.analyze_location_context,
                'behavioral_analysis': self.analyze_behavioral_context,
                'pattern_detection': self.detect_repetitive_patterns
            }
        }
    
    def save_to_file(self, filepath: Path):
        """Salva configuração em arquivo JSON"""
        config_dict = self.to_dict()
        config_dict['_metadata'] = {
            'version': '2.0_binary',
            'created_at': __import__('time').time(),
            'description': 'Configuração para classificação semântica binária'
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(config_dict, f, indent=2, ensure_ascii=False)

# =================================================================
# CONFIGURAÇÕES PRÉ-DEFINIDAS
# =================================================================

class PresetConfigurations:
    """Configurações pré-definidas para diferentes cenários"""
    
    @staticmethod
    def balanced() -> BinarySemanticConfig:
        """Configuração balanceada (padrão)"""
        config = BinarySemanticConfig()
        config.optimize_for_balanced()
        return config
    
    @staticmethod
    def high_precision() -> BinarySemanticConfig:
        """Configuração para alta precisão (poucos falsos positivos)"""
        config = BinarySemanticConfig()
        config.optimize_for_precision()
        return config
    
    @staticmethod
    def high_recall() -> BinarySemanticConfig:
        """Configuração para alto recall (poucos falsos negativos)"""
        config = BinarySemanticConfig()
        config.optimize_for_recall()
        return config
    
    @staticmethod
    def conservative() -> BinarySemanticConfig:
        """Configuração conservadora (somente casos muito claros)"""
        config = BinarySemanticConfig()
        config.suspicion_threshold = 0.8
        config.confidence_threshold = 0.9
        config.high_risk_threshold = 0.95
        config.require_human_review_threshold = 0.6
        
        # Pesos mais concentrados em indicadores críticos
        config.indicator_weights.update({
            'palavras_criticas': 0.40,
            'contexto_criminal': 0.30,
            'padroes_cobertura': 0.20,
            'inconsistencias_narrativas': 0.05,
            'palavras_suspeitas_gerais': 0.03,
            'indicadores_comportamentais': 0.02
        })
        
        return config
    
    @staticmethod
    def aggressive() -> BinarySemanticConfig:
        """Configuração agressiva (detecta mais casos suspeitos)"""
        config = BinarySemanticConfig()
        config.suspicion_threshold = 0.25
        config.confidence_threshold = 0.4
        config.high_risk_threshold = 0.6
        config.require_human_review_threshold = 0.15
        
        # Pesos mais distribuídos
        config.indicator_weights.update({
            'palavras_criticas': 0.18,
            'padroes_cobertura': 0.18,
            'contexto_criminal': 0.16,
            'inconsistencias_narrativas': 0.16,
            'palavras_suspeitas_gerais': 0.16,
            'indicadores_comportamentais': 0.16
        })
        
        return config
    
    @staticmethod
    def forensic() -> BinarySemanticConfig:
        """Configuração para análise forense (máxima precisão)"""
        config = BinarySemanticConfig()
        config.suspicion_threshold = 0.9
        config.confidence_threshold = 0.95
        config.high_risk_threshold = 0.98
        config.require_human_review_threshold = 0.8
        
        # Focar apenas em indicadores mais confiáveis
        config.indicator_weights.update({
            'palavras_criticas': 0.50,
            'contexto_criminal': 0.35,
            'padroes_cobertura': 0.10,
            'inconsistencias_narrativas': 0.03,
            'palavras_suspeitas_gerais': 0.01,
            'indicadores_comportamentais': 0.01
        })
        
        return config

# =================================================================
# FUNÇÃO DE FACTORY
# =================================================================

def create_semantic_config(preset: str = "balanced", **overrides) -> BinarySemanticConfig:
    """
    Cria configuração semântica com preset e overrides personalizados
    
    Args:
        preset: Nome do preset ('balanced', 'high_precision', 'high_recall', 'conservative', 'aggressive', 'forensic')
        **overrides: Parâmetros específicos para sobrescrever
    
    Returns:
        Configuração personalizada
    """
    preset_map = {
        'balanced': PresetConfigurations.balanced,
        'high_precision': PresetConfigurations.high_precision,
        'high_recall': PresetConfigurations.high_recall,
        'conservative': PresetConfigurations.conservative,
        'aggressive': PresetConfigurations.aggressive,
        'forensic': PresetConfigurations.forensic
    }
    
    if preset not in preset_map:
        available_presets = list(preset_map.keys())
        raise ValueError(f"Preset desconhecido: {preset}. Opções: {available_presets}")
    
    config = preset_map[preset]()
    
    # Aplicar overrides
    for key, value in overrides.items():
        if hasattr(config, key):
            setattr(config, key, value)
        else:
            print(f"⚠️ Atributo desconhecido ignorado: {key}")
    
    # Validar configuração final
    issues = config.validate_configuration()
    if issues:
        print("⚠️ Problemas na configuração:")
        for issue in issues:
            print(f"   - {issue}")
    
    return config

# =================================================================
# CONFIGURAÇÃO PADRÃO PARA O SISTEMA
# =================================================================

# Instância padrão para uso no sistema
DEFAULT_SEMANTIC_CONFIG = create_semantic_config("balanced")

def get_default_config() -> BinarySemanticConfig:
    """Retorna configuração padrão do sistema"""
    return DEFAULT_SEMANTIC_CONFIG

def load_config_from_env() -> BinarySemanticConfig:
    """Carrega configuração a partir de variáveis de ambiente"""
    preset = os.getenv('SEMANTIC_PRESET', 'balanced')
    
    overrides = {}
    
    # Thresholds via env vars
    env_mappings = {
        'SEMANTIC_SUSPICION_THRESHOLD': 'suspicion_threshold',
        'SEMANTIC_CONFIDENCE_THRESHOLD': 'confidence_threshold',
        'SEMANTIC_HIGH_RISK_THRESHOLD': 'high_risk_threshold',
        'SEMANTIC_MAX_CONCURRENT': 'max_concurrent_analyses',
        'SEMANTIC_TIMEOUT': 'analysis_timeout',
        'SEMANTIC_CACHE_TTL': 'cache_ttl_minutes'
    }
    
    for env_var, config_attr in env_mappings.items():
        value = os.getenv(env_var)
        if value:
            try:
                # Tentar converter para float primeiro, depois int
                if '.' in value:
                    overrides[config_attr] = float(value)
                else:
                    overrides[config_attr] = int(value)
            except ValueError:
                print(f"⚠️ Valor inválido para {env_var}: {value}")
    
    return create_semantic_config(preset, **overrides)

def load_config_from_file(filepath: Path) -> BinarySemanticConfig:
    """Carrega configuração a partir de arquivo JSON"""
    if not filepath.exists():
        raise FileNotFoundError(f"Arquivo de configuração não encontrado: {filepath}")
    
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Extrair preset se especificado, senão usar balanced
    preset = data.get('preset', 'balanced')
    
    # Extrair overrides
    overrides = data.get('overrides', {})
    
    return create_semantic_config(preset, **overrides)

# =================================================================
# UTILITÁRIOS PARA CONFIGURAÇÃO
# =================================================================

def compare_configs(config1: BinarySemanticConfig, config2: BinarySemanticConfig) -> Dict[str, Any]:
    """Compara duas configurações e retorna diferenças"""
    dict1 = config1.to_dict()
    dict2 = config2.to_dict()
    
    differences = {}
    
    def compare_recursive(d1, d2, path=""):
        for key in set(d1.keys()) | set(d2.keys()):
            current_path = f"{path}.{key}" if path else key
            
            if key not in d1:
                differences[current_path] = {"status": "added", "value": d2[key]}
            elif key not in d2:
                differences[current_path] = {"status": "removed", "value": d1[key]}
            elif isinstance(d1[key], dict) and isinstance(d2[key], dict):
                compare_recursive(d1[key], d2[key], current_path)
            elif d1[key] != d2[key]:
                differences[current_path] = {
                    "status": "changed",
                    "old_value": d1[key],
                    "new_value": d2[key]
                }
    
    compare_recursive(dict1, dict2)
    return differences

def print_config_summary(config: BinarySemanticConfig):
    """Imprime resumo da configuração"""
    print("📊 RESUMO DA CONFIGURAÇÃO SEMÂNTICA")
    print("=" * 45)
    
    print(f"🎯 Modo: {config.classification_mode.upper()}")
    print(f"   Classes: {config.negative_class} ↔ {config.positive_class}")
    
    print(f"\n⚙️ Thresholds:")
    print(f"   Suspeição: {config.suspicion_threshold:.2f}")
    print(f"   Confiança: {config.confidence_threshold:.2f}")
    print(f"   Alto risco: {config.high_risk_threshold:.2f}")
    print(f"   Revisão humana: {config.require_human_review_threshold:.2f}")
    
    print(f"\n📈 Pesos dos Indicadores:")
    for indicator, weight in config.get_weighted_indicators().items():
        print(f"   {indicator}: {weight:.3f}")
    
    print(f"\n🔍 Recursos:")
    print(f"   Palavras críticas: {len(config.critical_keywords)}")
    print(f"   Padrões cobertura: {len(config.coverage_patterns)}")
    print(f"   Contextos criminais: {len(config.criminal_contexts)}")
    print(f"   Indicadores evasão: {len(config.evasion_indicators)}")
    
    print(f"\n⚡ Performance:")
    print(f"   Análises simultâneas: {config.max_concurrent_analyses}")
    print(f"   Timeout: {config.analysis_timeout}s")
    print(f"   Cache: {'✅' if config.cache_results else '❌'} ({config.cache_ttl_minutes}min)")
    
    print(f"\n🔧 Análise Avançada:")
    print(f"   Temporal: {'✅' if config.analyze_temporal_context else '❌'}")
    print(f"   Localização: {'✅' if config.analyze_location_context else '❌'}")
    print(f"   Comportamental: {'✅' if config.analyze_behavioral_context else '❌'}")
    print(f"   Padrões repetitivos: {'✅' if config.detect_repetitive_patterns else '❌'}")
    
    # Validação
    issues = config.validate_configuration()
    if issues:
        print(f"\n⚠️ Problemas ({len(issues)}):")
        for issue in issues[:3]:  # Mostrar apenas os 3 primeiros
            print(f"   - {issue}")
        if len(issues) > 3:
            print(f"   ... e mais {len(issues) - 3} problemas")
    else:
        print(f"\n✅ Configuração válida!")

# =================================================================
# EXEMPLO DE USO E TESTES
# =================================================================

def create_test_scenarios() -> Dict[str, BinarySemanticConfig]:
    """Cria cenários de teste para diferentes situações"""
    scenarios = {}
    
    # Cenário 1: Delegacia urbana (casos variados)
    urban_config = create_semantic_config("balanced")
    urban_config.suspicion_threshold = 0.45
    scenarios["delegacia_urbana"] = urban_config
    
    # Cenário 2: Fronteira (alta sensibilidade)
    border_config = create_semantic_config("high_recall")
    border_config.context_multipliers['area_fronteira'] = 2.0
    scenarios["posto_fronteira"] = border_config
    
    # Cenário 3: Análise forense (máxima precisão)
    forensic_config = create_semantic_config("forensic")
    scenarios["laboratorio_forense"] = forensic_config
    
    # Cenário 4: Patrulhamento (detecção rápida)
    patrol_config = create_semantic_config("aggressive")
    patrol_config.analysis_timeout = 15.0  # Mais rápido
    patrol_config.max_concurrent_analyses = 10
    scenarios["patrulhamento"] = patrol_config
    
    return scenarios

def benchmark_config_performance():
    """Benchmarks de performance para diferentes configurações"""
    import time
    
    configs = {
        "balanced": create_semantic_config("balanced"),
        "high_precision": create_semantic_config("high_precision"),
        "high_recall": create_semantic_config("high_recall"),
        "conservative": create_semantic_config("conservative"),
        "aggressive": create_semantic_config("aggressive")
    }
    
    # Textos de teste
    test_texts = [
        "Foi encontrado com drogas na cintura durante abordagem",
        "Estava passando na rua quando vi a ocorrência policial",
        "Confessou estar traficando há meses na região",
        "Apresentou documentos e colaborou com a investigação",
        "Não sabia de nada sobre o material encontrado no local"
    ]
    
    print("⏱️ BENCHMARK DE CONFIGURAÇÕES")
    print("=" * 50)
    
    for name, config in configs.items():
        start_time = time.time()
        
        # Simular processamento
        total_issues = len(config.validate_configuration())
        dict_size = len(str(config.to_dict()))
        
        processing_time = time.time() - start_time
        
        print(f"\n📊 {name.upper()}:")
        print(f"   Tempo de inicialização: {processing_time*1000:.1f}ms")
        print(f"   Tamanho da configuração: {dict_size:,} chars")
        print(f"   Problemas de validação: {total_issues}")
        print(f"   Threshold suspeição: {config.suspicion_threshold:.2f}")
        print(f"   Palavras críticas: {len(config.critical_keywords)}")

if __name__ == "__main__":
    print("🧪 TESTANDO CONFIGURAÇÕES SEMÂNTICAS BINÁRIAS")
    print("=" * 55)
    
    # Testar todos os presets
    presets = ['balanced', 'high_precision', 'high_recall', 'conservative', 'aggressive', 'forensic']
    
    print("\n📋 TESTANDO PRESETS:")
    for preset_name in presets:
        try:
            config = create_semantic_config(preset_name)
            issues = config.validate_configuration()
            status = "✅" if not issues else f"⚠️ ({len(issues)} problemas)"
            
            print(f"   {preset_name:15s}: {status}")
            print(f"      Threshold: {config.suspicion_threshold:.2f} | "
                  f"Confiança: {config.confidence_threshold:.2f} | "
                  f"Palavras: {len(config.critical_keywords)}")
            
        except Exception as e:
            print(f"   {preset_name:15s}: ❌ Erro - {e}")
    
    # Testar configuração padrão
    print(f"\n🔧 CONFIGURAÇÃO PADRÃO:")
    default_config = get_default_config()
    print_config_summary(default_config)
    
    # Testar carregamento do ambiente
    print(f"\n🌍 TESTE DE VARIÁVEIS DE AMBIENTE:")
    try:
        env_config = load_config_from_env()
        print("   ✅ Configuração carregada do ambiente")
        print(f"   Preset usado: {os.getenv('SEMANTIC_PRESET', 'balanced')}")
    except Exception as e:
        print(f"   ❌ Erro ao carregar do ambiente: {e}")
    
    # Testar cenários
    print(f"\n🎭 CENÁRIOS DE TESTE:")
    scenarios = create_test_scenarios()
    for scenario_name, scenario_config in scenarios.items():
        issues = scenario_config.validate_configuration()
        status = "✅" if not issues else f"⚠️"
        print(f"   {scenario_name:20s}: {status} (Threshold: {scenario_config.suspicion_threshold:.2f})")
    
    # Benchmark
    print(f"\n⏱️ EXECUTANDO BENCHMARK:")
    benchmark_config_performance()
    
    print(f"\n🎉 TODOS OS TESTES CONCLUÍDOS!")
    print("=" * 55)