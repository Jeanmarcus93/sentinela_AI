# semantic_local.py - Versão com correções críticas
from __future__ import annotations
import re, json, os
from typing import List, Dict, Any, Optional, Tuple

import numpy as np
import joblib
from sentence_transformers import SentenceTransformer

# =========================
# Config e caminhos
# =========================
MODELS_DIR = os.path.join(os.path.dirname(__file__), "models")
os.makedirs(MODELS_DIR, exist_ok=True)

EMB_MODEL_NAME = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"

CLF_PATH = os.path.join(MODELS_DIR, "semantic_clf.joblib")
LBL_PATH = os.path.join(MODELS_DIR, "semantic_labels.joblib")

# CLASSES ALINHADAS COM O TREINAMENTO HÍBRIDO
SUPPORTED_CLASSES = ["SEM_ALTERACAO", "SUSPEITO"]

# =========================
# Carregamento
# =========================
_emb = None
_clf = None
_lbl = None

def load_embeddings():
    global _emb
    if _emb is None:
        _emb = SentenceTransformer(EMB_MODEL_NAME, trust_remote_code=True)
    return _emb

def load_classifier():
    global _clf, _lbl
    if _clf is None and os.path.exists(CLF_PATH) and os.path.exists(LBL_PATH):
        try:
            _clf = joblib.load(CLF_PATH)
            _lbl = joblib.load(LBL_PATH)
        except Exception as e:
            print(f"Erro ao carregar classificador: {e}")
            _clf = None
            _lbl = None
    return _clf, _lbl

# =========================
# CLASSE HÍBRIDA CORRIGIDA
# =========================
class HybridClassifier:
    """Classificador híbrido com lógica corrigida"""
    def __init__(self, ml_model, always_suspeito, always_sem_alteracao, indicadores):
        self.ml_model = ml_model
        self.always_suspeito = always_suspeito
        self.always_sem_alteracao = always_sem_alteracao
        self.indicadores = indicadores
        self.classes_ = ml_model.classes_
    
    def classify_by_rules_enhanced(self, texto: str) -> Optional[str]:
        """Classificação por regras MELHORADAS"""
        texto_lower = texto.lower()
        
        # CORREÇÃO 1: APREENSÕES REAIS (qualquer quantidade + droga/arma)
        apreensao_patterns = [
            r'\d+\s*kg\s*de\s*(crack|cocaina|maconha|skunk)',  # "8 kg de crack"
            r'encontrad[oa]s?\s*\d+\s*kg',  # "encontrados 8 kg"
            r'apreendid[oa]s?\s*\d+\s*kg',  # "apreendidos 5 kg"
            r'(crack|cocaina|maconha)\s+escondid[oa]',  # "crack escondido"
            r'(crack|cocaina|maconha)\s+encontrad[oa]',  # "maconha encontrada"
            r'\d+\s*kg.*?(crack|cocaina|maconha)',  # qualquer variação
        ]
        
        for pattern in apreensao_patterns:
            if re.search(pattern, texto_lower):
                return "SUSPEITO"
        
        # CORREÇÃO 2: Passagens criminais específicas
        criminal_patterns = [
            r'passagem.*?por.*?trafico',
            r'ficha.*?criminal.*(trafico|homicidio|roubo)',
            r'antecedentes.*(trafico|homicidio|porte.*arma)',
            r'organizacao criminosa',
            r'faccao.*?(bala|manos|cv|pcc)',
        ]
        
        for pattern in criminal_patterns:
            if re.search(pattern, texto_lower):
                return "SUSPEITO"
        
        # Regras originais SEMPRE_SUSPEITO (mantidas)
        for regra in self.always_suspeito:
            if regra in texto_lower:
                return "SUSPEITO"
        
        # Regras SEMPRE_SEM_ALTERACAO (mais específicas)
        specific_normal_patterns = [
            r'fiscalizacao\s+de\s+rotina.*documentos.*ordem',
            r'nada.*encontrado.*liberado',
            r'verificacao.*rotina.*sem.*alteracao',
        ]
        
        for pattern in specific_normal_patterns:
            if re.search(pattern, texto_lower):
                return "SEM_ALTERACAO"
        
        # Regras originais (apenas se muito específicas)
        specific_normal = [
            "fiscalizacao de rotina", "verificacao de rotina", 
            "abordagem normal", "tudo normal", "sem irregularidade"
        ]
        for regra in specific_normal:
            if regra in texto_lower and "nada encontrado" in texto_lower:
                return "SEM_ALTERACAO"
        
        return None  # Caso ambíguo - usar ML
    
    def predict(self, X_text_or_embeddings):
        """Predição híbrida CORRIGIDA"""
        if isinstance(X_text_or_embeddings, list) and isinstance(X_text_or_embeddings[0], str):
            predictions = []
            for texto in X_text_or_embeddings:
                rule_pred = self.classify_by_rules_enhanced(texto)
                if rule_pred:
                    predictions.append(rule_pred)
                else:
                    # ML com threshold ajustado
                    X_embed = embed([texto])
                    ml_proba = self.ml_model.predict_proba(X_embed)[0]
                    
                    # CORREÇÃO 3: Usar score manual para casos ambíguos
                    manual_score = calculate_enhanced_score(texto)
                    
                    # Lógica híbrida melhorada
                    if manual_score >= 10:  # Score alto = SUSPEITO
                        predictions.append("SUSPEITO")
                    elif manual_score <= -5:  # Score muito negativo = SEM_ALTERACAO
                        predictions.append("SEM_ALTERACAO")
                    else:
                        # Usar ML com threshold mais conservador
                        prob_suspeito = ml_proba[1] if len(ml_proba) > 1 else ml_proba[0]
                        if prob_suspeito > 0.4:  # Threshold mais baixo para capturar suspeitos
                            predictions.append("SUSPEITO")
                        else:
                            predictions.append("SEM_ALTERACAO")
            return np.array(predictions)
        else:
            return self.ml_model.predict(X_text_or_embeddings)
    
    def predict_proba(self, X_text_or_embeddings):
        """Probabilidades híbridas CORRIGIDAS"""
        if isinstance(X_text_or_embeddings, list) and isinstance(X_text_or_embeddings[0], str):
            probabilities = []
            for texto in X_text_or_embeddings:
                rule_pred = self.classify_by_rules_enhanced(texto)
                if rule_pred == "SUSPEITO":
                    probabilities.append([0.05, 0.95])  # Alta confiança SUSPEITO
                elif rule_pred == "SEM_ALTERACAO":
                    probabilities.append([0.95, 0.05])  # Alta confiança SEM_ALTERACAO
                else:
                    # ML com ajuste baseado em score manual
                    X_embed = embed([texto])
                    ml_proba = self.ml_model.predict_proba(X_embed)[0]
                    manual_score = calculate_enhanced_score(texto)
                    
                    # Ajustar probabilidades baseado no score manual
                    if manual_score >= 10:
                        # Forçar para suspeito se score alto
                        probabilities.append([0.2, 0.8])
                    elif manual_score <= -5:
                        # Forçar para sem alteração se score muito negativo
                        probabilities.append([0.8, 0.2])
                    else:
                        # Usar ML puro
                        probabilities.append(ml_proba)
            return np.array(probabilities)
        else:
            return self.ml_model.predict_proba(X_text_or_embeddings)

    # Adicionar método para compatibilidade
    def classify_by_rules(self, texto: str) -> Optional[str]:
        """Método para compatibilidade - usa versão melhorada"""
        return self.classify_by_rules_enhanced(texto)

# =========================
# Funcionalidades essenciais CORRIGIDAS
# =========================
def embed(texts: List[str]) -> np.ndarray:
    """Função principal de embedding - ESSENCIAL"""
    model = load_embeddings()
    return model.encode(texts, normalize_embeddings=True)

def calculate_enhanced_score(text: str) -> float:
    """Score manual CORRIGIDO com melhor detecção"""
    t = text.lower()
    score = 0
    
    # CORREÇÃO 1: Apreensões reais têm peso máximo
    apreensao_patterns = [
        (r'\d+\s*kg\s*de\s*(crack|cocaina|maconha)', 50),  # Apreensão específica
        (r'encontrad[oa].*?(crack|cocaina|maconha)', 40),   # Droga encontrada
        (r'apreendid[oa].*?(droga|crack|cocaina)', 45),     # Droga apreendida
        (r'escondid[oa].*?(crack|cocaina|maconha)', 35),    # Droga escondida
    ]
    
    for pattern, peso in apreensao_patterns:
        if re.search(pattern, t):
            score += peso
    
    # CORREÇÃO 2: Passagens criminais contextualizadas
    criminal_patterns = [
        (r'passagem.*?trafico', 25),
        (r'ficha.*criminal.*(trafico|homicidio)', 20),
        (r'antecedentes.*(trafico|porte.*arma)', 20),
        (r'organizacao criminosa', 30),
        (r'faccao.*?(bala|manos)', 35),
    ]
    
    for pattern, peso in criminal_patterns:
        if re.search(pattern, t):
            score += peso
    
    # CORREÇÃO 3: Indicadores contextuais (não palavras soltas)
    contexto_suspeito = [
        (r'bate.*volta.*fronteira', 15),  # Bate volta real na fronteira
        (r'historia.*estranha.*mentiu', 12),  # Combinação de indicadores
        (r'nervoso.*contradição', 10),
        (r'nao.*soube.*explicar.*viagem', 8),
        (r'madrugada.*sem.*motivo', 8),
    ]
    
    for pattern, peso in contexto_suspeito:
        if re.search(pattern, t):
            score += peso
    
    # CORREÇÃO 4: Indicadores de normalidade mais específicos
    normal_patterns = [
        (r'fiscalizacao.*rotina.*nada.*encontrado', -20),
        (r'documentos.*ordem.*liberado', -15),
        (r'consulta.*medica.*hospital', -10),
        (r'trabalho.*comprovado', -8),
    ]
    
    for pattern, peso in normal_patterns:
        if re.search(pattern, t):
            score += peso
    
    # Indicadores básicos (peso menor)
    if re.search(r'\b(nervoso|inquieto|agitado)\b', t):
        score += 3
    if re.search(r'\b(mentiu|contradicao)\b', t):
        score += 5
    if re.search(r'\b(antecedentes|denuncia)\b', t):
        score += 4
    
    # Redutores básicos
    if re.search(r'\bnada.*encontrado\b', t):
        score -= 8
    if re.search(r'\bliberado\b', t):
        score -= 5
    
    return score

def rule_based_indicators(text: str) -> Dict[str, Any]:
    """Indicadores baseados em regras CORRIGIDAS"""
    t = text.lower()
    
    # Contadores específicos e contextuais
    apreensoes = len(re.findall(r'\d+\s*kg\s*de\s*(crack|cocaina|maconha)', t))
    drogas_encontradas = len(re.findall(r'encontrad[oa].*?(crack|cocaina|maconha|droga)', t))
    armas = len(re.findall(r'\b(arma|revolver|pistola|municao)\b', t))
    criminal_history = len(re.findall(r'(passagem.*trafico|ficha.*criminal|antecedentes.*trafico)', t))
    
    # Comportamento contextual
    comportamento_suspeito = len(re.findall(r'(nervoso.*mentiu|historia.*estranha|nao.*soube.*explicar)', t))
    
    # Contexto geográfico/temporal real
    padrao_geografico = len(re.findall(r'(bate.*volta.*fronteira|madrugada.*sem.*motivo)', t))
    
    # Normalidade específica
    indicadores_normais = len(re.findall(r'(fiscalizacao.*rotina|documentos.*ordem|nada.*encontrado)', t))
    
    # Score total corrigido
    score = calculate_enhanced_score(text)

    return {
        "apreensoes_reais": apreensoes,
        "drogas_encontradas": drogas_encontradas,
        "armas_hits": armas,
        "criminal_history": criminal_history,
        "comportamento_suspeito": comportamento_suspeito,
        "padrao_geografico": padrao_geografico,
        "indicadores_normais": indicadores_normais,
        "rule_score": score
    }

def predict_class_hybrid(text: str) -> Tuple[str, float, Dict[str, Any]]:
    """Predição usando modelo híbrido CORRIGIDO"""
    indicators = rule_based_indicators(text)
    clf, lbl = load_classifier()

    if clf is not None and lbl is not None:
        try:
            if hasattr(clf, 'classify_by_rules_enhanced'):
                # Modelo híbrido corrigido
                predictions = clf.predict([text])
                probabilities = clf.predict_proba([text])[0]
                
                classe = predictions[0]
                
                # Calcular confiança
                if len(lbl) == 2:
                    prob_sem_alt = probabilities[0] if lbl[0] == "SEM_ALTERACAO" else probabilities[1]
                    prob_suspeito = probabilities[1] if lbl[1] == "SUSPEITO" else probabilities[0]
                    confianca = max(prob_sem_alt, prob_suspeito)
                else:
                    confianca = float(np.max(probabilities))
                
                final_score = int(round(100 * confianca))
                
                return classe, final_score, {
                    "probas": {lbl[i]: float(probabilities[i]) for i in range(len(lbl))}, 
                    "indicators": indicators,
                    "method": "hybrid_enhanced"
                }
        except Exception as e:
            print(f"Erro na predição: {e}")

    # Fallback com lógica corrigida
    score = indicators["rule_score"]
    
    # CORREÇÃO FINAL: Thresholds baseados em análise real
    if score >= 25:  # Casos claros de suspeita
        classe = "SUSPEITO"
        confianca = min(0.95, (score / 50) + 0.5)
    elif score <= -10:  # Casos claramente normais
        classe = "SEM_ALTERACAO"  
        confianca = min(0.95, (-score / 20) + 0.5)
    elif score >= 10:  # Suspeita moderada
        classe = "SUSPEITO"
        confianca = 0.7
    else:  # Casos neutros
        classe = "SEM_ALTERACAO"
        confianca = 0.6
    
    final_score = int(confianca * 100)
    
    return classe, final_score, {
        "probas": {"SEM_ALTERACAO": 1-confianca, "SUSPEITO": confianca}, 
        "indicators": indicators,
        "method": "rules_enhanced"
    }

def analyze_text(relato: str) -> Dict[str, Any]:
    """Análise completa de texto CORRIGIDA"""
    relato = relato or ""
    classe, score, extra = predict_class_hybrid(relato)

    return {
        "classe": classe,
        "pontuacao": score,  # 0..100
        "keywords": [],  # Simplificado por ora
        "entidades": [],  # Vazio sem spaCy
        "indicadores": extra["indicators"],
        "probs": extra.get("probas", {}),
        "method": extra.get("method", "unknown")
    }

# Manter compatibilidade
def predict_class(text: str) -> Tuple[str, float, Dict[str, Any]]:
    """Alias para compatibilidade"""
    return predict_class_hybrid(text)