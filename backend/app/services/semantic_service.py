# app/services/semantic_service.py
"""
Serviço de Análise Semântica Inteligente
Sistema aprimorado para análise contextual de relatos com detecção de padrões de cobertura criminal
"""

from __future__ import annotations
import re
import json
import os
import time
from dataclasses import dataclass
from typing import List, Dict, Any, Optional, Tuple, Set
from pathlib import Path

import numpy as np
import joblib
import yake
import spacy
from sentence_transformers import SentenceTransformer
from sklearn.linear_model import LogisticRegression
from sklearn.multiclass import OneVsRestClassifier
from sklearn.calibration import CalibratedClassifierCV

# =========================
# CONFIGURAÇÕES E CAMINHOS
# =========================

# Diretórios
MODELS_DIR = Path(__file__).parent.parent.parent / "ml_models" / "trained"
CONFIG_DIR = Path(__file__).parent.parent.parent / "config"
MODELS_DIR.mkdir(parents=True, exist_ok=True)

# Modelos
SPACY_MODEL = os.environ.get("SPACY_PT_MODEL", "pt_core_news_sm")
EMB_MODEL_NAME = os.environ.get("SENTENCE_EMB_MODEL", "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")

# Arquivos de modelo
CLF_PATH = MODELS_DIR / "semantic_clf.joblib"
LBL_PATH = MODELS_DIR / "semantic_labels.joblib"
METADATA_PATH = MODELS_DIR / "semantic_metadata.json"

# Classes suportadas
SUPPORTED_CLASSES = ["TRAFICO", "PORTE_ARMA", "RECEPTACAO", "OUTROS", "SEM_ALTERACAO", "SUSPEITO"]

# =========================
# CACHE E INSTÂNCIAS GLOBAIS
# =========================

_nlp = None
_emb = None
_yake = None
_clf = None
_lbl = None
_contexts = None

@dataclass
class SemanticContext:
    """Contexto carregado dos arquivos de configuração"""
    palavras_suspeitas: Set[str]
    palavras_normais: Set[str]
    historias_cobertura: Set[str]
    contextos_suspeitos: List[str]
    palavras_criticas: Set[str]

# =========================
# CARREGAMENTO DE PIPELINES
# =========================

def load_spacy():
    """Carrega modelo spaCy com cache"""
    global _nlp
    if _nlp is None:
        try:
            _nlp = spacy.load(SPACY_MODEL, disable=["tagger", "parser", "lemmatizer"])
            print(f"✅ SpaCy modelo '{SPACY_MODEL}' carregado")
        except OSError:
            print(f"⚠️ Modelo spaCy '{SPACY_MODEL}' não encontrado")
            print(f"   Execute: python -m spacy download {SPACY_MODEL}")
            # Fallback para modelo básico
            try:
                _nlp = spacy.load("pt_core_news_sm", disable=["tagger", "parser", "lemmatizer"])
                print("✅ Usando modelo spaCy básico como fallback")
            except OSError:
                raise RuntimeError("Nenhum modelo spaCy português encontrado!")
    return _nlp

def load_embeddings():
    """Carrega modelo de embeddings com cache"""
    global _emb
    if _emb is None:
        print(f"🔄 Carregando modelo de embeddings: {EMB_MODEL_NAME}")
        _emb = SentenceTransformer(EMB_MODEL_NAME, trust_remote_code=True)
        print("✅ Modelo de embeddings carregado")
    return _emb

def load_yake():
    """Carrega extrator de palavras-chave YAKE"""
    global _yake
    if _yake is None:
        _yake = yake.KeywordExtractor(
            lan="pt", 
            n=3,  # até 3-gramas
            top=20, 
            windowsSize=3, 
            dedupLim=0.7,
            features=["tf", "upfreq", "dist", "position"]
        )
    return _yake

def load_classifier():
    """Carrega modelo de classificação treinado"""
    global _clf, _lbl
    if _clf is None and CLF_PATH.exists() and LBL_PATH.exists():
        try:
            _clf = joblib.load(CLF_PATH)
            _lbl = joblib.load(LBL_PATH)
            print("✅ Modelo de classificação carregado")
        except Exception as e:
            print(f"⚠️ Erro ao carregar modelo: {e}")
            _clf, _lbl = None, None
    return _clf, _lbl

def load_contexts():
    """Carrega contextos de análise dos arquivos de configuração"""
    global _contexts
    if _contexts is None:
        _contexts = _load_context_files()
    return _contexts

def _load_context_files() -> SemanticContext:
    """Carrega arquivos de contexto"""
    def load_file(filename: str) -> Set[str]:
        filepath = CONFIG_DIR / filename
        if filepath.exists():
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    return {
                        line.strip().lower() 
                        for line in f 
                        if line.strip() and not line.startswith('#')
                    }
            except Exception as e:
                print(f"⚠️ Erro ao carregar {filename}: {e}")
        return set()

    def load_list_file(filename: str) -> List[str]:
        filepath = CONFIG_DIR / filename
        if filepath.exists():
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    return [
                        line.strip() 
                        for line in f 
                        if line.strip() and not line.startswith('#')
                    ]
            except Exception as e:
                print(f"⚠️ Erro ao carregar {filename}: {e}")
        return []

    # Carregar arquivos
    palavras_suspeitas = load_file("palavras_suspeitas.txt")
    palavras_normais = load_file("palavras_normais.txt")
    historias_cobertura = load_file("historias_cobertura.txt")
    contextos_suspeitos = load_list_file("contextos_suspeitos.txt")
    
    # Palavras críticas (sempre suspeitas)
    palavras_criticas = {
        "traficante", "traficantes", "maconha", "skunk", "cocaina", "crack", 
        "arma", "revolver", "pistola", "munição", "fuzil", "droga", "drogas",
        "tráfico", "trafico", "homicidio", "homicídio"
    }
    
    print(f"📚 Contextos carregados:")
    print(f"   - Palavras suspeitas: {len(palavras_suspeitas)}")
    print(f"   - Palavras normais: {len(palavras_normais)}")
    print(f"   - Histórias de cobertura: {len(historias_cobertura)}")
    print(f"   - Contextos suspeitos: {len(contextos_suspeitos)}")
    print(f"   - Palavras críticas: {len(palavras_criticas)}")
    
    return SemanticContext(
        palavras_suspeitas=palavras_suspeitas,
        palavras_normais=palavras_normais,
        historias_cobertura=historias_cobertura,
        contextos_suspeitos=contextos_suspeitos,
        palavras_criticas=palavras_criticas
    )

# =========================
# ANÁLISE DE FEATURES
# =========================

# Padrões regex otimizados
DRUG_TERMS = re.compile(r'\b(maconha|skunk|coca[ií]na|p[oó]|crack|sint[eé]tico[s]?|mdma|lsd|droga[s]?|tr[aá]fico|traficante[s]?)\b', re.IGNORECASE)
WEAPON_TERMS = re.compile(r'\b(arma[s]?|rev[oó]lver|pistola|muni[cç][aã]o|fuzil|porte)\b', re.IGNORECASE)
THEFT_TERMS = re.compile(r'\b(roubou|furtou|recepta[cç][aã]o|recupera[cç][aã]o|clonado|adulterado|receptacao)\b', re.IGNORECASE)
SUSPICIOUS_TERMS = re.compile(r'\b(mentiu|batedor|fronteira|ec ruim|estado de conserva[cç][aã]o ruim|homic[ií]dio|nervos[oa]|contradicao|contradição)\b', re.IGNORECASE)
DELIVERY_TERMS = re.compile(r'\b(entrega|entregue|local de entrega|drop|desova|repasse|bate[- ]?volta)\b', re.IGNORECASE)
QUANT_PATTERN = re.compile(r'(\d+[.,]?\d*)\s?(kg|g|un|unidades?|gramas?)\b', re.IGNORECASE)

def simple_norm(s: str) -> str:
    """Normalização simples de texto"""
    return re.sub(r'\s+', ' ', s.strip().lower())

def rule_based_indicators(text: str) -> Dict[str, Any]:
    """Análise baseada em regras com detecção avançada"""
    if not text:
        return {"rule_score": 0, "indicators": {}}
    
    text_norm = simple_norm(text)
    
    # Contadores básicos
    drugs = len(DRUG_TERMS.findall(text_norm))
    weapons = len(WEAPON_TERMS.findall(text_norm))
    theft = len(THEFT_TERMS.findall(text_norm))
    suspicious = len(SUSPICIOUS_TERMS.findall(text_norm))
    delivery = len(DELIVERY_TERMS.findall(text_norm))
    
    # Análise de quantidades
    quants = QUANT_PATTERN.findall(text_norm)
    total_kg = 0.0
    total_un = 0
    
    for qty_str, unit in quants:
        try:
            val = float(qty_str.replace(",", "."))
        except:
            val = 0.0
        
        unit_lower = unit.lower()
        if unit_lower == "kg":
            total_kg += val
        elif unit_lower in ["g", "gramas", "grama"]:
            total_kg += val / 1000.0
        else:
            total_un += int(val)
    
    # Score heurístico otimizado
    score = 0
    score += drugs * 25          # Drogas: peso alto
    score += weapons * 25        # Armas: peso alto
    score += theft * 20          # Receptação: peso médio-alto
    score += suspicious * 15     # Comportamento suspeito
    score += delivery * 15       # Entrega/logística
    score += min(total_kg * 10, 50)  # Quantidade em kg (cap 50)
    score += min(total_un * 0.5, 20) # Quantidade em unidades (cap 20)
    
    # Bonificações por combinações
    if drugs > 0 and delivery > 0:
        score += 15  # Droga + entrega
    if weapons > 0 and suspicious > 0:
        score += 10  # Arma + comportamento suspeito
    
    score = max(0, min(100, score))
    
    return {
        "drugs_hits": drugs,
        "weapons_hits": weapons,
        "theft_hits": theft,
        "suspicious_hits": suspicious,
        "delivery_hits": delivery,
        "total_kg": round(total_kg, 3),
        "total_un": total_un,
        "rule_score": score,
        "combinations": {
            "drugs_delivery": drugs > 0 and delivery > 0,
            "weapons_suspicious": weapons > 0 and suspicious > 0
        }
    }

def contextual_analysis(text: str, contexts: SemanticContext) -> Tuple[str, int, List[str]]:
    """Análise contextual inteligente para detecção de padrões de cobertura"""
    if not text:
        return "SEM_ALTERACAO", 0, []
    
    text_lower = text.lower()
    score = 0
    motivos = []
    
    # 1. HISTÓRIAS DE COBERTURA (peso máximo)
    for cobertura in contexts.historias_cobertura:
        if cobertura in text_lower:
            score += 40
            motivos.append(f"História de cobertura detectada: '{cobertura}'")
    
    # 2. PALAVRAS CRÍTICAS (automático suspeito)
    for critica in contexts.palavras_criticas:
        if critica in text_lower:
            score += 35
            motivos.append(f"Palavra crítica: '{critica}'")
    
    # 3. CONTEXTOS SUSPEITOS (combinações)
    for contexto in contexts.contextos_suspeitos:
        if '|' in contexto:  # Operador E (todas devem estar)
            palavras = [p.strip().lower() for p in contexto.split('|')]
            if all(palavra in text_lower for palavra in palavras):
                score += 25
                motivos.append(f"Contexto suspeito (E): {' + '.join(palavras)}")
        elif ',' in contexto:  # Operador OU (qualquer uma)
            palavras = [p.strip().lower() for p in contexto.split(',')]
            matches = [p for p in palavras if p in text_lower]
            if matches:
                score += 15
                motivos.append(f"Contexto suspeito (OU): {', '.join(matches)}")
    
    # 4. PADRÕES ESPECÍFICOS CONHECIDOS
    # "Visitando parente" em local estratégico
    if any(x in text_lower for x in ["visita", "tia", "parente", "primo"]):
        if any(y in text_lower for y in ["rodoviária", "posto", "fronteira", "divisa"]):
            score += 20
            motivos.append("Padrão: visita familiar em local estratégico")
    
    # Inconsistências sobre viagem
    if any(x in text_lower for x in ["mentiu", "contradicao", "contradição", "mudou versão"]):
        if any(y in text_lower for y in ["viagem", "destino", "motivo", "origem"]):
            score += 25
            motivos.append("Inconsistência sobre propósito/destino")
    
    # EC/Entrevista problemática
    if any(x in text_lower for x in ["ec ruim", "entrevista ruim", "não soube explicar", "evasiva"]):
        score += 20
        motivos.append("Entrevista de campo inconsistente")
    
    # Horário/local suspeito
    if any(x in text_lower for x in ["madrugada", "noite", "2h", "3h", "4h", "5h"]):
        if any(y in text_lower for y in ["viajando", "estrada", "rodovia"]):
            score += 10
            motivos.append("Horário suspeito para viagem")
    
    # 5. PALAVRAS SUSPEITAS NORMAIS
    for palavra in contexts.palavras_suspeitas:
        if palavra in text_lower:
            score += 8
            motivos.append(f"Indicador suspeito: '{palavra}'")
    
    # 6. PALAVRAS PROTETIVAS (reduzem score)
    for normal in contexts.palavras_normais:
        if normal in text_lower:
            score -= 12
            motivos.append(f"Contexto normal: '{normal}' (reduz suspeita)")
    
    # Classificação final
    if score >= 30:
        return "SUSPEITO", score, motivos
    elif score <= -15:
        return "SEM_ALTERACAO", score, motivos
    elif score >= 15:
        return "SUSPEITO", score, motivos
    else:
        return "SEM_ALTERACAO", score, motivos

def extract_keywords(text: str, topk: int = 15) -> List[Tuple[str, float]]:
    """Extração de palavras-chave com YAKE"""
    if not text or len(text.strip()) < 20: # Adicione essa validação
        return []
    
    try:
        kw = load_yake()
        if kw is None:
            return []
            
        keywords = kw.extract_keywords(text)
        return keywords[:topk]
    except Exception as e:
        print(f"Erro na extração de keywords: {e}")
        return []
    
def embed(texts: List[str]) -> np.ndarray:
    """Gera embeddings para lista de textos"""
    if not texts:
        return np.array([])
    
    try:
        model = load_embeddings()
        embeddings = model.encode(texts, normalize_embeddings=True, batch_size=32)
        return embeddings
    except Exception as e:
        print(f"Erro ao gerar embeddings: {e}")
        # Fallback: retornar zeros
        return np.zeros((len(texts), 384))

def spacy_entities(text: str) -> List[Dict[str, Any]]:
    """Extração de entidades nomeadas com spaCy"""
    if not text:
        return []
    
    try:
        nlp = load_spacy()
        doc = nlp(text)
        entities = []
        
        for ent in doc.ents:
            entities.append({
                "text": ent.text,
                "label": ent.label_,
                "start": ent.start_char,
                "end": ent.end_char,
                "confidence": 0.8  # spaCy não fornece confiança
            })
        
        return entities
    except Exception as e:
        print(f"Erro na extração de entidades: {e}")
        return []

# =========================
# PREDIÇÃO E CLASSIFICAÇÃO
# =========================

def predict_class(text: str) -> Tuple[str, float, Dict[str, Any]]:
    """Predição de classe usando modelo treinado + análise contextual"""
    if not text:
        return "OUTROS", 0.0, {}
    
    # Análise por regras
    indicators = rule_based_indicators(text)
    
    # Análise contextual
    contexts = load_contexts()
    contextual_class, contextual_score, motivos = contextual_analysis(text, contexts)
    
    # Tentar usar modelo treinado
    clf, lbl = load_classifier()
    
    if clf is not None and lbl is not None:
        try:
            X = embed([text])
            if X.size > 0:
                proba = clf.predict_proba(X)[0]
                idx = int(np.argmax(proba))
                ml_class = lbl[idx]
                ml_confidence = float(np.max(proba))
                
                # Combinar predições (ML + contextual + regras)
                final_score = (
                    ml_confidence * 0.4 +           # Modelo ML: 40%
                    (contextual_score / 100) * 0.35 + # Contextual: 35%
                    (indicators["rule_score"] / 100) * 0.25  # Regras: 25%
                )
                
                final_score = min(100, max(0, final_score * 100))
                
                # Decisão final inteligente
                if contextual_class == "SUSPEITO" and contextual_score >= 25:
                    final_class = "SUSPEITO"
                elif ml_class in ["TRAFICO", "PORTE_ARMA", "RECEPTACAO"] and ml_confidence > 0.6:
                    final_class = ml_class
                elif indicators["rule_score"] >= 50:
                    final_class = "SUSPEITO"
                else:
                    final_class = ml_class if ml_confidence > 0.5 else contextual_class
                
                return final_class, final_score, {
                    "ml_prediction": {
                        "class": ml_class,
                        "confidence": ml_confidence,
                        "probas": {lbl[i]: float(proba[i]) for i in range(len(lbl))}
                    },
                    "contextual_analysis": {
                        "class": contextual_class,
                        "score": contextual_score,
                        "motivos": motivos
                    },
                    "indicators": indicators,
                    "method": "hybrid"
                }
        except Exception as e:
            print(f"Erro na predição com ML: {e}")
    
    # Fallback para análise contextual + regras
    if contextual_class == "SUSPEITO" or indicators["rule_score"] >= 40:
        final_class = "SUSPEITO"
    elif contextual_class == "SEM_ALTERACAO" and indicators["rule_score"] < 20:
        final_class = "SEM_ALTERACAO" 
    else:
        # Classificação por padrões específicos
        if indicators["drugs_hits"] > 0 or indicators["total_kg"] > 0:
            final_class = "TRAFICO"
        elif indicators["weapons_hits"] > 0:
            final_class = "PORTE_ARMA"
        elif indicators["theft_hits"] > 0:
            final_class = "RECEPTACAO"
        else:
            final_class = contextual_class
    
    combined_score = max(contextual_score, indicators["rule_score"])
    
    return final_class, combined_score, {
        "contextual_analysis": {
            "class": contextual_class,
            "score": contextual_score,
            "motivos": motivos
        },
        "indicators": indicators,
        "method": "rule_based_contextual"
    }

# =========================
# API PRINCIPAL
# =========================

def analyze_text(relato: str) -> Dict[str, Any]:
    """
    Análise completa de texto - API principal
    
    Args:
        relato: Texto do relato a ser analisado
        
    Returns:
        Dicionário com análise completa
    """
    start_time = time.time()
    
    if not relato or not relato.strip():
        return {
            "classe": "OUTROS",
            "pontuacao": 0,
            "confianca": 0.0,
            "keywords": [],
            "entidades": [],
            "indicadores": {},
            "contexto": {},
            "metodo": "empty_input",
            "tempo_execucao": 0.0
        }
    
    relato = relato.strip()
    
    try:
        # Análise principal
        classe, score, extra = predict_class(relato)
        
        # Análises complementares
        keywords = extract_keywords(relato, topk=12)
        entities = spacy_entities(relato)
        
        # Confiança baseada no método usado
        if extra.get("method") == "hybrid":
            confianca = extra["ml_prediction"]["confidence"]
        else:
            confianca = min(1.0, score / 100.0)
        
        # Resultado final
        resultado = {
            "classe": classe,
            "pontuacao": int(score),
            "confianca": float(confianca),
            "keywords": [{"termo": k, "score": float(v)} for k, v in keywords],
            "entidades": entities,
            "indicadores": extra.get("indicators", {}),
            "contexto": extra.get("contextual_analysis", {}),
            "metodo": extra.get("method", "unknown"),
            "tempo_execucao": time.time() - start_time
        }
        
        # Adicionar predição ML se disponível
        if "ml_prediction" in extra:
            resultado["ml_prediction"] = extra["ml_prediction"]
        
        return resultado
        
    except Exception as e:
        print(f"Erro na análise de texto: {e}")
        return {
            "classe": "ERRO",
            "pontuacao": 0,
            "confianca": 0.0,
            "keywords": [],
            "entidades": [],
            "indicadores": {},
            "contexto": {},
            "erro": str(e),
            "metodo": "error",
            "tempo_execucao": time.time() - start_time
        }

def analyze_batch(relatos: List[str], batch_size: int = 32) -> List[Dict[str, Any]]:
    """Análise em lote de múltiplos relatos"""
    if not relatos:
        return []
    
    print(f"🔄 Analisando {len(relatos)} relatos em lotes de {batch_size}")
    
    results = []
    for i in range(0, len(relatos), batch_size):
        batch = relatos[i:i+batch_size]
        batch_results = []
        
        for relato in batch:
            result = analyze_text(relato)
            batch_results.append(result)
        
        results.extend(batch_results)
        
        if len(results) % 100 == 0:
            print(f"   Processados: {len(results)}/{len(relatos)}")
    
    print(f"✅ Análise em lote concluída: {len(results)} relatos")
    return results

# =========================
# UTILITÁRIOS E INFORMAÇÕES
# =========================

def get_model_info() -> Dict[str, Any]:
    """Informações sobre o modelo carregado"""
    clf, lbl = load_classifier()
    contexts = load_contexts()
    
    info = {
        "model_loaded": clf is not None,
        "model_path": str(CLF_PATH),
        "labels_path": str(LBL_PATH),
        "supported_classes": SUPPORTED_CLASSES,
        "contexts_loaded": {
            "palavras_suspeitas": len(contexts.palavras_suspeitas),
            "palavras_normais": len(contexts.palavras_normais),
            "historias_cobertura": len(contexts.historias_cobertura),
            "contextos_suspeitos": len(contexts.contextos_suspeitos),
            "palavras_criticas": len(contexts.palavras_criticas)
        }
    }
    
    if METADATA_PATH.exists():
        try:
            with open(METADATA_PATH, 'r', encoding='utf-8') as f:
                metadata = json.load(f)
                info["model_metadata"] = metadata
        except:
            pass
    
    return info

def health_check() -> Dict[str, Any]:
    """Verificação de saúde do serviço semântico"""
    health = {
        "service_healthy": True,
        "components": {},
        "test_results": {},
        "timestamp": time.time()
    }
    
    # Testar componentes
    try:
        nlp = load_spacy()
        health["components"]["spacy"] = {"status": "ok", "model": SPACY_MODEL}
    except Exception as e:
        health["components"]["spacy"] = {"status": "error", "error": str(e)}
        health["service_healthy"] = False
    
    try:
        emb = load_embeddings()
        health["components"]["embeddings"] = {"status": "ok", "model": EMB_MODEL_NAME}
    except Exception as e:
        health["components"]["embeddings"] = {"status": "error", "error": str(e)}
        health["service_healthy"] = False
    
    try:
        contexts = load_contexts()
        health["components"]["contexts"] = {"status": "ok", "loaded": True}
    except Exception as e:
        health["components"]["contexts"] = {"status": "error", "error": str(e)}
    
    clf, lbl = load_classifier()
    if clf is not None:
        health["components"]["ml_model"] = {"status": "ok", "classes": len(lbl) if lbl else 0}
    else:
        health["components"]["ml_model"] = {"status": "warning", "message": "Modelo não treinado"}
    
    # Teste de análise
    try:
        test_result = analyze_text("Teste de análise semântica")
        health["test_results"]["analysis"] = {
            "status": "ok", 
            "execution_time": test_result.get("tempo_execucao", 0)
        }
    except Exception as e:
        health["test_results"]["analysis"] = {"status": "error", "error": str(e)}
        health["service_healthy"] = False
    
    return health

def get_service_stats() -> Dict[str, Any]:
    """Estatísticas do serviço"""
    return {
        "version": "2.0",
        "model_info": get_model_info(),
        "health": health_check(),
        "capabilities": [
            "Análise contextual inteligente",
            "Detecção de padrões de cobertura", 
            "Classificação multi-classe",
            "Extração de palavras-chave",
            "Reconhecimento de entidades",
            "Análise baseada em regras",
            "Processamento em lote"
        ]
    }

# =========================
# COMPATIBILIDADE E MIGRAÇÃO
# =========================

# Manter compatibilidade com versões antigas
def classify_text(text: str) -> str:
    """Compatibilidade: classificação simples"""
    result = analyze_text(text)
    return result["classe"]

def get_risk_score(text: str) -> int:
    """Compatibilidade: apenas score de risco"""
    result = analyze_text(text)
    return result["pontuacao"]

if __name__ == "__main__":
    # Teste do sistema
    print("🧪 Testando Sistema de Análise Semântica")
    print("=" * 45)
    
    # Health check
    health = health_check()
    print(f"🏥 Sistema saudável: {'✅' if health['service_healthy'] else '❌'}")
    
    # Informações do modelo
    info = get_model_info()
    print(f"🤖 Modelo carregado: {'✅' if info['model_loaded'] else '❌'}")
    
    # Teste de análises
    print("\n🔍 Testes de análise:")
    
    casos_teste = [
        "Abordagem de rotina, família voltando de férias, sem irregularidades",
        "Motorista nervoso, mentiu sobre destino, encontrada maconha no veículo", 
        "Visitando a tia que mora próximo à rodoviária, comportamento evasivo",
        "EC ruim, não soube explicar origem do dinheiro em espécie",
        "Viagem de trabalho, documentação em ordem, liberado após verificação"
    ]
    
    for i, caso in enumerate(casos_teste, 1):
        try:
            resultado = analyze_text(caso)
            classe = resultado["classe"]
            score = resultado["pontuacao"]
            metodo = resultado["metodo"]
            tempo = resultado["tempo_execucao"]
            
            print(f"\n{i}. \"{caso[:50]}...\"")
            print(f"   → {classe} ({score}%) | Método: {metodo} | {tempo:.3f}s")
            
            if resultado.get("contexto", {}).get("motivos"):
                print(f"   Motivos: {resultado['contexto']['motivos'][0]}")
                
        except Exception as e:
            print(f"\n{i}. ERRO: {e}")
    
    print(f"\n🎉 Sistema de Análise Semântica pronto!")
    print(f"📊 Use analyze_text(relato) para análise completa")

def load_yake():
    """Carrega extrator de palavras-chave YAKE com proteção contra erros"""
    global _yake
    if _yake is None:
        try:
            _yake = yake.KeywordExtractor(
                lan="pt", 
                n=3,  # até 3-gramas
                top=20, 
                windowsSize=3, 
                dedupLim=0.7,
                features=["tf", "upfreq", "dist", "position"]
            )
            print("✅ YAKE extractor carregado")
        except Exception as e:
            print(f"⚠️ Erro ao inicializar YAKE: {e}")
            _yake = None
    return _yake

def extract_keywords_safe(text):
    """Extrai palavras-chave com proteção contra erros"""
    if not text or len(text.strip()) < 10:
        return []
    
    try:
        yake_extractor = load_yake()
        if yake_extractor is None:
            return []
        
        keywords = yake_extractor.extract_keywords(text)
        return [kw[1] for kw in keywords[:10]]  # Top 10 keywords
    except ZeroDivisionError:
        print("⚠️ YAKE erro de divisão por zero - texto muito curto")
        return []
    except Exception as e:
        print(f"⚠️ Erro na extração de keywords: {e}")
        return []
    
# Adicione esta função no semantic_service.py

def safe_extract_keywords(text):
    """Extrai palavras-chave com proteção total contra erros"""
    # Validação de entrada
    if not text or not isinstance(text, str):
        return []
    
    # Limpar e validar texto
    text = text.strip()
    if len(text) < 20:  # Texto muito curto
        return []
    
    # Verificar se tem conteúdo significativo
    words = text.split()
    if len(words) < 5:  # Muito poucas palavras
        return []
    
    try:
        yake_extractor = load_yake()
        if yake_extractor is None:
            return []
        
        # Tentar extrair keywords
        keywords = yake_extractor.extract_keywords(text)
        return [kw[1] for kw in keywords[:10] if kw[0] > 0]  # Filtrar scores inválidos
        
    except (ZeroDivisionError, ValueError, AttributeError) as e:
        print(f"⚠️ YAKE erro protegido: {type(e).__name__}")
        return []
    except Exception as e:
        print(f"⚠️ Erro inesperado no YAKE: {e}")
        return []
