# semantic_local.py
from __future__ import annotations
import re, json, os
from dataclasses import dataclass
from typing import List, Dict, Any, Optional, Tuple

import numpy as np
import joblib
import yake
import spacy
from sentence_transformers import SentenceTransformer
from sklearn.linear_model import LogisticRegression
from sklearn.multiclass import OneVsRestClassifier
from sklearn.calibration import CalibratedClassifierCV

# =========================
# Config e caminhos
# =========================
MODELS_DIR = os.path.join(os.path.dirname(__file__), "models")
os.makedirs(MODELS_DIR, exist_ok=True)

SPACY_MODEL = os.environ.get("SPACY_PT_MODEL", "pt_core_news_sm")
EMB_MODEL_NAME = os.environ.get("SENTENCE_EMB_MODEL", "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")

CLF_PATH = os.path.join(MODELS_DIR, "semantic_clf.joblib")
LBL_PATH = os.path.join(MODELS_DIR, "semantic_labels.joblib")

SUPPORTED_CLASSES = ["TRAFICO", "PORTE_ARMA", "RECEPTACAO", "OUTROS"]

# =========================
# Carregamento de pipelines
# =========================
_nlp = None
_emb = None
_yake = None
_clf = None
_lbl = None

def load_spacy():
    global _nlp
    if _nlp is None:
        try:
            _nlp = spacy.load(SPACY_MODEL, disable=["tagger"])
        except OSError:
            raise RuntimeError(
                f"Modelo spaCy '{SPACY_MODEL}' não encontrado. Rode: python -m spacy download {SPACY_MODEL}"
            )
    return _nlp


def load_embeddings():
    global _emb
    if _emb is None:
        _emb = SentenceTransformer(EMB_MODEL_NAME, trust_remote_code=True)
    return _emb

def load_yake():
    global _yake
    if _yake is None:
        _yake = yake.KeywordExtractor(lan="pt", n=1, top=15, windowsSize=2, dedupLim=0.9)
    return _yake

def load_classifier():
    global _clf, _lbl
    if _clf is None and os.path.exists(CLF_PATH) and os.path.exists(LBL_PATH):
        _clf = joblib.load(CLF_PATH)
        _lbl = joblib.load(LBL_PATH)
    return _clf, _lbl

# =========================
# Utilidades de features
# =========================
# ATUALIZAÇÃO: Inclusão das novas palavras-chave
DRUG_TERMS = r"\b(maconha|skunk|coca[ií]na|p[oó]|crack|sint[eé]tico[s]?|mdma|lsd|droga[s]?|tr[aá]fico)\b"
WEAPON_TERMS = r"\b(arma[s]?|rev[oó]lver|pistola|muni[cç][aã]o|fuzil)\b"
THEFT_TERMS = r"\b(roubou|furtou|recepta[cç][aã]o|recupera[cç][aã]o|clonado|adulterado)\b"
SUSPICIOUS_TERMS = r"\b(mentiu|batedor|fronteira|ec ruim|estado de conserva[cç][aã]o ruim|homic[ií]dio)\b"
DELIVERY_TERMS = r"\b(entrega|entregue|local de entrega|drop|desova|repasse)\b"

QUANT_PATTERN = r"(\d+[.,]?\d*)\s?(kg|g|un)\b"

def simple_norm(s: str) -> str:
    return re.sub(r"\s+", " ", s.strip().lower())

def rule_based_indicators(text: str) -> Dict[str, Any]:
    t = simple_norm(text)
    # ATUALIZAÇÃO: Contagem dos novos termos
    drugs = len(re.findall(DRUG_TERMS, t, flags=re.IGNORECASE))
    weapons = len(re.findall(WEAPON_TERMS, t, flags=re.IGNORECASE))
    theft = len(re.findall(THEFT_TERMS, t, flags=re.IGNORECASE))
    suspicious = len(re.findall(SUSPICIOUS_TERMS, t, flags=re.IGNORECASE))
    delivery = len(re.findall(DELIVERY_TERMS, t, flags=re.IGNORECASE))
    quants = re.findall(QUANT_PATTERN, t, flags=re.IGNORECASE)

    total_kg = 0.0
    total_un = 0
    for q, unit in quants:
        try:
            val = float(q.replace(",", "."))
        except:
            val = 0.0
        if unit.lower() == "kg":
            total_kg += val
        elif unit.lower() == "g":
            total_kg += val / 1000.0
        else:
            total_un += int(val)

    # ATUALIZAÇÃO: Score heurístico ajustado para incluir novos indicadores
    score = (drugs * 25) + (weapons * 25) + (theft * 20) + (suspicious * 15) + (delivery * 15) + min(total_kg * 10, 40) + min(total_un * 0.5, 20)
    score = max(0, min(100, score))

    return {
        "drugs_hits": drugs,
        "weapons_hits": weapons,
        "theft_hits": theft,
        "suspicious_hits": suspicious,
        "delivery_hits": delivery,
        "total_kg": round(total_kg, 3),
        "total_un": total_un,
        "rule_score": score
    }

def extract_keywords(text: str, topk: int = 10) -> List[Tuple[str, float]]:
    kw = load_yake()
    return kw.extract_keywords(text)[:topk]

def embed(texts: List[str]) -> np.ndarray:
    model = load_embeddings()
    return model.encode(texts, normalize_embeddings=True)

def spacy_entities(text: str) -> List[Dict[str, Any]]:
    nlp = load_spacy()
    doc = nlp(text)
    ents = []
    for e in doc.ents:
        ents.append({"text": e.text, "label": e.label_})
    return ents

# =========================
# Predição / fallback
# =========================
def predict_class(text: str) -> Tuple[str, float, Dict[str, Any]]:
    indicators = rule_based_indicators(text)
    clf, lbl = load_classifier()

    if clf is not None and lbl is not None:
        X = embed([text])
        proba = clf.predict_proba(X)[0]
        idx = int(np.argmax(proba))
        classe = lbl[idx]
        p = float(np.max(proba))
        model_score = int(round(100 * p))
        final = int(round(0.6 * model_score + 0.4 * indicators["rule_score"]))
        return classe, final, {"probas": {lbl[i]: float(proba[i]) for i in range(len(lbl))}, "indicators": indicators}

    # Fallback puramente por regras se não tiver modelo treinado
    c = "OUTROS"
    if indicators["drugs_hits"] > 0 or indicators["total_kg"] > 0:
        c = "TRAFICO"
    elif indicators["weapons_hits"] > 0:
        c = "PORTE_ARMA"
    elif indicators["theft_hits"] > 0:
        c = "RECEPTACAO"
    return c, indicators["rule_score"], {"probas": {}, "indicators": indicators}

# =========================
# API de alto nível
# =========================
def analyze_text(relato: str) -> Dict[str, Any]:
    relato = relato or ""
    classe, score, extra = predict_class(relato)
    kws = extract_keywords(relato, topk=10)
    ents = spacy_entities(relato)

    return {
        "classe": classe,
        "pontuacao": score,  # 0..100
        "keywords": [{"term": k, "score": float(v)} for k, v in kws],
        "entidades": ents,
        "indicadores": extra["indicators"],
        "probs": extra.get("probas", {})
    }
