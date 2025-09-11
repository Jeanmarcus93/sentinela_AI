#!/usr/bin/env python3
# train_inteligente.py - Sistema inteligente que reconhece padrões de cobertura

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
from app.models.database import DB_CONFIG
from app.services.semantic_service import embed, CLF_PATH, LBL_PATH

def carregar_contextos():
    """Carrega todas as configurações de contexto"""
    config_dir = "config"
    
    # Palavras suspeitas básicas
    suspeitas = []
    if os.path.exists(f"{config_dir}/palavras_suspeitas.txt"):
        with open(f"{config_dir}/palavras_suspeitas.txt", 'r', encoding='utf-8') as f:
            suspeitas = [linha.strip() for linha in f if linha.strip() and not linha.startswith('#')]
    
    # Palavras normais básicas
    normais = []
    if os.path.exists(f"{config_dir}/palavras_normais.txt"):
        with open(f"{config_dir}/palavras_normais.txt", 'r', encoding='utf-8') as f:
            normais = [linha.strip() for linha in f if linha.strip() and not linha.startswith('#')]
    
    # Histórias de cobertura (SEMPRE suspeitas)
    coberturas = []
    if os.path.exists(f"{config_dir}/historias_cobertura.txt"):
        with open(f"{config_dir}/historias_cobertura.txt", 'r', encoding='utf-8') as f:
            coberturas = [linha.strip() for linha in f if linha.strip() and not linha.startswith('#')]
    
    # Contextos suspeitos (combinações)
    contextos = []
    if os.path.exists(f"{config_dir}/contextos_suspeitos.txt"):
        with open(f"{config_dir}/contextos_suspeitos.txt", 'r', encoding='utf-8') as f:
            contextos = [linha.strip() for linha in f if linha.strip() and not linha.startswith('#')]
    
    return suspeitas, normais, coberturas, contextos

def analise_contextual(texto, suspeitas, normais, coberturas, contextos):
    """Análise inteligente considerando contextos e padrões de cobertura"""
    texto_lower = texto.lower()
    score = 0
    motivos = []
    
    # 1. HISTÓRIAS DE COBERTURA (peso alto)
    for cobertura in coberturas:
        if cobertura.lower() in texto_lower:
            score += 8  # Peso muito alto
            motivos.append(f"História de cobertura: '{cobertura}'")
    
    # 2. CONTEXTOS SUSPEITOS (combinações)
    for contexto in contextos:
        if '|' in contexto:  # Combinação E (todas devem estar presentes)
            palavras = [p.strip() for p in contexto.split('|')]
            if all(palavra.lower() in texto_lower for palavra in palavras):
                score += 6
                motivos.append(f"Contexto suspeito: {' + '.join(palavras)}")
        elif ',' in contexto:  # Combinação OU (qualquer uma presente)
            palavras = [p.strip() for p in contexto.split(',')]
            if any(palavra.lower() in texto_lower for palavra in palavras):
                score += 3
                motivos.append(f"Indicador suspeito: {contexto}")
    
    # 3. PALAVRAS CRÍTICAS (automático)
    criticas = ["traficante", "traficantes", "maconha", "cocaina", "crack", "arma", "revolver", "pistola"]
    for critica in criticas:
        if critica in texto_lower:
            score += 10  # Peso máximo
            motivos.append(f"Palavra crítica: '{critica}'")
    
    # 4. PADRÕES ESPECÍFICOS CONHECIDOS
    # "Visitando tia" próximo a locais estratégicos
    if ("visita" in texto_lower or "tia" in texto_lower) and ("rodoviária" in texto_lower or "posto" in texto_lower):
        score += 7
        motivos.append("Padrão de cobertura: visita familiar em local estratégico")
    
    # Mentiras sobre viagem
    if ("mentiu" in texto_lower or "contradicao" in texto_lower) and ("viagem" in texto_lower or "motivo" in texto_lower):
        score += 8
        motivos.append("Inconsistência sobre propósito da viagem")
    
    # EC ruim (entrevista de campo ruim)
    if "ec ruim" in texto_lower or "entrevista ruim" in texto_lower:
        score += 6
        motivos.append("Entrevista de campo inconsistente")
    
    # 5. PALAVRAS SUSPEITAS NORMAIS
    for palavra in suspeitas:
        if palavra.lower() in texto_lower:
            score += 2
            motivos.append(f"Indicador: '{palavra}'")
    
    # 6. PALAVRAS PROTETIVAS (reduzem score)
    for normal in normais:
        if normal.lower() in texto_lower:
            score -= 3
            motivos.append(f"Contexto normal: '{normal}' (reduz suspeita)")
    
    return score, motivos

def classificar_inteligente(texto, suspeitas, normais, coberturas, contextos):
    """Classificação final baseada em análise contextual"""
    score, motivos = analise_contextual(texto, suspeitas, normais, coberturas, contextos)
    
    # Limites mais refinados
    if score >= 6:  # Score alto = suspeito
        return "SUSPEITO", score, motivos
    elif score <= -3:  # Score muito negativo = normal
        return "SEM_ALTERACAO", score, motivos
    elif score >= 3:  # Score médio mas positivo = suspeito
        return "SUSPEITO", score, motivos
    else:
        return "SEM_ALTERACAO", score, motivos

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

def main():
    print("SISTEMA INTELIGENTE - Reconhece padrões de cobertura criminal")
    
    # Carrega contextos
    suspeitas, normais, coberturas, contextos = carregar_contextos()
    print(f"Palavras suspeitas: {len(suspeitas)}")
    print(f"Palavras normais: {len(normais)}")
    print(f"Histórias de cobertura: {len(coberturas)}")
    print(f"Contextos suspeitos: {len(contextos)}")
    
    # Testa exemplos
    exemplos = [
        "Passeando com amigos",
        "Visitando a tia que mora próximo à rodoviária", 
        "Traficante viajando com amigos",
        "EC ruim, mentiu o motivo da viagem",
        "Emergência familiar na fronteira"
    ]
    
    print("\nTeste dos exemplos:")
    for exemplo in exemplos:
        classe, score, motivos = classificar_inteligente(exemplo, suspeitas, normais, coberturas, contextos)
        print(f"\n'{exemplo}'")
        print(f"→ {classe} (score: {score})")
        for motivo in motivos:
            print(f"  • {motivo}")
    
    # Busca dados reais
    rows = fetch_training_data()
    print(f"\nCarregados {len(rows)} relatos do banco")
    
    # Classifica usando sistema inteligente
    print("Classificando com sistema inteligente...")
    X_text = [(r["relato"] or "").strip() for r in rows]
    labels = []
    
    for row in rows:
        relato = (row.get("relato") or "").strip()
        
        # Verifica apreensões primeiro
        if row.get("apreensoes"):
            if any(a["tipo"] in ("Maconha", "Skunk", "Cocaina", "Crack", "Sintéticos", "Arma") 
                   for a in row["apreensoes"]):
                labels.append("SUSPEITO")
                continue
        
        # Usa classificação inteligente
        classe, _, _ = classificar_inteligente(relato, suspeitas, normais, coberturas, contextos)
        labels.append(classe)
    
    # Estatísticas
    suspeitos = sum(1 for l in labels if l == "SUSPEITO")
    print(f"SUSPEITO: {suspeitos} ({suspeitos/len(labels)*100:.1f}%)")
    print(f"SEM_ALTERACAO: {len(labels) - suspeitos} ({(len(labels) - suspeitos)/len(labels)*100:.1f}%)")
    
    # Gera embeddings
    print("Gerando embeddings...")
    X = embed(X_text)
    
    # Treina modelo
    classes = sorted(list(set(labels)))
    print("Classes detectadas:", classes)
    
    if len(classes) < 2:
        print("Erro: Precisa de pelo menos 2 classes")
        return
    
    class_to_idx = {c: i for i, c in enumerate(classes)}
    Y = np.zeros((len(labels), len(classes)), dtype=int)
    for i, y in enumerate(labels):
        if y in class_to_idx:
            Y[i, class_to_idx[y]] = 1
    
    Xtr, Xte, Ytr, Yte = train_test_split(X, Y, test_size=0.2, random_state=42, stratify=Y)
    
    base = LogisticRegression(max_iter=200, class_weight="balanced")
    ovr = OneVsRestClassifier(CalibratedClassifierCV(base, cv=3, method="sigmoid"))
    ovr.fit(Xtr, Ytr)
    
    # Avalia
    Yp = (ovr.predict_proba(Xte) > 0.5).astype(int)
    print(classification_report(Yte, Yp, target_names=classes, zero_division=0))
    
    # Salva modelo
    joblib.dump(ovr, CLF_PATH)
    joblib.dump(classes, LBL_PATH)
    print("Modelo salvo em:", CLF_PATH)

if __name__ == "__main__":
    main()
