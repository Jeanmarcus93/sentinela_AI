#!/usr/bin/env python3
# train_configurable.py - Treinamento com configuração externa

import os
import json
import sys
import numpy as np
import joblib
import psycopg
from psycopg.rows import dict_row
from sklearn.linear_model import LogisticRegression
from sklearn.multiclass import OneVsRestClassifier
from sklearn.calibration import CalibratedClassifierCV
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database import DB_CONFIG
from semantic_local import embed, CLF_PATH, LBL_PATH

def carregar_configuracao():
    """Carrega palavras e configurações dos arquivos externos"""
    config_dir = "config"
    
    # Cria diretório se não existir
    os.makedirs(config_dir, exist_ok=True)
    
    # Carrega configuração principal
    config_path = os.path.join(config_dir, "config.json")
    if os.path.exists(config_path):
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
    else:
        config = {"training_config": {"min_suspicious_indicators": 2}}
    
    # Carrega palavras suspeitas
    suspeitas_path = os.path.join(config_dir, "palavras_suspeitas.txt")
    palavras_suspeitas = []
    if os.path.exists(suspeitas_path):
        with open(suspeitas_path, 'r', encoding='utf-8') as f:
            palavras_suspeitas = [linha.strip() for linha in f 
                                if linha.strip() and not linha.startswith('#')]
    
    # Carrega palavras normais
    normais_path = os.path.join(config_dir, "palavras_normais.txt")
    palavras_normais = []
    if os.path.exists(normais_path):
        with open(normais_path, 'r', encoding='utf-8') as f:
            palavras_normais = [linha.strip() for linha in f 
                              if linha.strip() and not linha.startswith('#')]
    
    return config, palavras_suspeitas, palavras_normais

def calcular_score_texto(texto, config, palavras_suspeitas, palavras_normais):
    """Calcula score de suspeição baseado nas configurações"""
    texto_lower = texto.lower()
    
    # Pesos das configurações
    pesos = config.get("pesos", {
        "palavra_critica": 3,
        "palavra_suspeita": 1, 
        "palavra_normal": -2,
        "palavra_protegida": -5
    })
    
    score = 0
    indicadores_criticos = config.get("palavras_criticas", [])
    palavras_protegidas = config.get("palavras_protegidas", [])
    
    # Palavras críticas (peso alto)
    for palavra in indicadores_criticos:
        if palavra.lower() in texto_lower:
            score += pesos["palavra_critica"]
    
    # Palavras suspeitas normais
    for palavra in palavras_suspeitas:
        if palavra.lower() in texto_lower:
            score += pesos["palavra_suspeita"]
    
    # Palavras protegidas (peso muito negativo)
    for palavra in palavras_protegidas:
        if palavra.lower() in texto_lower:
            score += pesos["palavra_protegida"]
    
    # Palavras normais
    for palavra in palavras_normais:
        if palavra.lower() in texto_lower:
            score += pesos["palavra_normal"]
    
    return score

def auto_label_configuravel(row, config, palavras_suspeitas, palavras_normais):
    """Classificação baseada em configuração externa"""
    relato = (row.get("relato") or "").lower()
    
    # Verifica apreensões
    if row.get("apreensoes"):
        if any(a["tipo"] in ("Maconha", "Skunk", "Cocaina", "Crack", "Sintéticos", "Arma") 
               for a in row["apreensoes"]):
            return "SUSPEITO"
    
    # Calcula score baseado nas listas de palavras
    score = calcular_score_texto(relato, config, palavras_suspeitas, palavras_normais)
    
    # Limiar de decisão
    min_indicators = config.get("training_config", {}).get("min_suspicious_indicators", 2)
    
    # Se score >= limiar, é suspeito
    return "SUSPEITO" if score >= min_indicators else "SEM_ALTERACAO"

def fetch_training_data(limit=None):
    """Busca dados de treinamento"""
    qlimit = f"LIMIT {int(limit)}" if limit else ""
    sql = f"""
    SELECT o.id, o.relato, o.tipo,
           COALESCE(
             (
               SELECT json_agg(json_build_object('tipo', a.tipo::text))
               FROM apreensoes a WHERE a.ocorrencia_id = o.id
             ), '[]'::json
           ) AS apreensoes
    FROM ocorrencias o
    WHERE o.relato IS NOT NULL AND o.relato <> ''
    ORDER BY o.datahora DESC
    {qlimit};
    """
    
    with psycopg.connect(**DB_CONFIG) as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(sql)
            return cur.fetchall()

def criar_arquivos_exemplo():
    """Cria arquivos de exemplo se não existirem"""
    config_dir = "config"
    os.makedirs(config_dir, exist_ok=True)
    
    # Se não existir config.json, cria um básico
    config_path = os.path.join(config_dir, "config.json")
    if not os.path.exists(config_path):
        config_exemplo = {
            "training_config": {"min_suspicious_indicators": 2},
            "palavras_criticas": ["traficante", "maconha", "cocaina", "crack"],
            "palavras_protegidas": ["família", "férias", "trabalho"],
            "pesos": {"palavra_critica": 3, "palavra_suspeita": 1, "palavra_normal": -2, "palavra_protegida": -5}
        }
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config_exemplo, f, indent=2, ensure_ascii=False)
    
    print(f"Configurações carregadas de: {config_dir}/")

def main():
    print("Carregando configurações externas...")
    criar_arquivos_exemplo()
    config, palavras_suspeitas, palavras_normais = carregar_configuracao()
    
    print(f"Palavras suspeitas: {len(palavras_suspeitas)}")
    print(f"Palavras normais: {len(palavras_normais)}")
    
    # Busca dados
    rows = fetch_training_data()
    print(f"Carregados {len(rows)} relatos do banco")
    
    if not rows:
        print("Nenhum dado encontrado")
        return
    
    # Classifica usando configuração
    print("Classificando relatos com base na configuração...")
    X_text = [(r["relato"] or "").strip() for r in rows]
    y_labels = [auto_label_configuravel(r, config, palavras_suspeitas, palavras_normais) 
                for r in rows]
    
    # Estatísticas
    suspeitos = sum(1 for y in y_labels if y == "SUSPEITO")
    normais = len(y_labels) - suspeitos
    print(f"SUSPEITO: {suspeitos} ({suspeitos/len(y_labels)*100:.1f}%)")
    print(f"SEM_ALTERACAO: {normais} ({normais/len(y_labels)*100:.1f}%)")
    
    if suspeitos < 100:
        print("AVISO: Poucos casos suspeitos. Ajuste as configurações.")
    
    # Gera embeddings
    print("Gerando embeddings...")
    X = embed(X_text)
    
    # Prepara dados para treinamento multilabel
    classes = sorted(list(set(y_labels)))
    print("Classes detectadas:", classes)
    
    if len(classes) < 2:
        print("Erro: Precisa de pelo menos 2 classes")
        return
    
    class_to_idx = {c: i for i, c in enumerate(classes)}
    Y = np.zeros((len(y_labels), len(classes)), dtype=int)
    for i, y in enumerate(y_labels):
        if y in class_to_idx:
            Y[i, class_to_idx[y]] = 1
    
    # Treina modelo
    Xtr, Xte, Ytr, Yte = train_test_split(X, Y, test_size=0.2, random_state=42, stratify=Y)
    
    # Usa configurações do arquivo para o modelo
    model_params = config.get("training_config", {}).get("model_params", {})
    base = LogisticRegression(
        max_iter=model_params.get("max_iter", 200),
        class_weight=model_params.get("class_weight", "balanced")
    )
    
    ovr = OneVsRestClassifier(CalibratedClassifierCV(base, cv=3, method="sigmoid"))
    ovr.fit(Xtr, Ytr)
    
    # Avalia
    Yp = (ovr.predict_proba(Xte) > 0.5).astype(int)
    print(classification_report(Yte, Yp, target_names=classes, zero_division=0))
    
    # Salva modelo
    joblib.dump(ovr, CLF_PATH)
    joblib.dump(classes, LBL_PATH)
    print("Modelo salvo em:", CLF_PATH)
    print("Labels salvos em:", LBL_PATH)
    
    # Salva estatísticas do treinamento
    stats_path = os.path.join("config", "training_stats.json")
    stats = {
        "total_samples": len(rows),
        "suspeitos": suspeitos,
        "normais": normais,
        "suspeitos_percent": suspeitos/len(y_labels)*100,
        "palavras_suspeitas_count": len(palavras_suspeitas),
        "palavras_normais_count": len(palavras_normais)
    }
    
    with open(stats_path, 'w', encoding='utf-8') as f:
        json.dump(stats, f, indent=2, ensure_ascii=False)
    
    print(f"Estatísticas salvas em: {stats_path}")

if __name__ == "__main__":
    main()