from __future__ import annotations
import os, json, re, random
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

# garante que a raiz está no sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import DB_CONFIG
from semantic_local import embed, CLF_PATH, LBL_PATH

# ATUALIZADO: Novas classes focadas na classificação binária de suspeita
SUPPORTED_CLASSES = ["SUSPEITO", "SEM_ALTERACAO"]

# Agrupamos todas as palavras e expressões de indício em uma única lista
INDICIOS_SUSPEITA = [
    # Tráfico
    "maconha", "skunk", "coca", "crack", "droga", "pó", "erva",
    "fronteira", "bate volta", "provavelmente entregando", "entregar",
    "suspeito de tráfico", "viagem sem justificativa",
    "corre", "buscar droga", "voltando de entrega", "entorpecentes", "ilícitos",
    # Arma
    "arma", "revólver", "pistola", "munição", "fuzil",
    "mão na cintura", "comportamento agressivo",
    "pode estar armado", "suspeito de arma",
    # Geral
    "história estranha", "ficou nervoso", "mentiu", "inquieto",
    "sem motivo aparente", "madrugada", "agitado",
    "entrevista ruim", "não soube explicar", "contradição",
    "denúncia anônima", "dinheiro em espécie", "hostil", "antecedentes"
]

def humanizar_texto(texto: str) -> str:
    """Função para introduzir pequenas variações nos textos. (Pode ser expandida)"""
    # Esta função pode ser mantida para adicionar ruído aos dados se desejado.
    return texto

def auto_label(row) -> str:
    """
    Classificação mais rigorosa: só é SUSPEITO se houver múltiplos indicadores.
    """
    relato = (row.get("relato") or "").lower()

    # Verifica apreensões (indício forte)
    if row.get("apreensoes"):
        if any(a["tipo"] in ("Maconha", "Skunk", "Cocaina", "Crack", "Sintéticos", "Arma") for a in row["apreensoes"]):
            return "SUSPEITO"

    # Lista de indicadores FORTES - precisam de pelo menos 2 para ser suspeito
    indicadores_fortes = [
        "maconha", "skunk", "cocaina", "crack", "droga", "traficante",
        "arma", "revólver", "pistola", "munição", "fronteira",
        "mentiu", "contradição", "nervoso", "agressivo", "entrevista ruim"
    ]
    
    # Conta quantos indicadores fortes existem
    count = sum(1 for ind in indicadores_fortes if ind in relato)
    
    # Palavras que NUNCA devem ser suspeitas
    palavras_normais = [
        "família", "férias", "trabalho", "visitar", "parentes", 
        "documentação em ordem", "sem irregularidade", "liberado"
    ]
    
    # Se tem palavras claramente normais, não é suspeito
    if any(palavra in relato for palavra in palavras_normais):
        return "SEM_ALTERACAO"
    
    # Só é suspeito se tem 2+ indicadores fortes OU 1 indicador muito específico
    if count >= 2 or any(palavra in relato for palavra in ["traficante", "maconha", "cocaina", "crack"]):
        return "SUSPEITO"

    return "SEM_ALTERACAO"
    
    # Só é suspeito se tem 2+ indicadores fortes OU 1 indicador muito específico
    if count >= 2 or any(palavra in relato for palavra in ["traficante", "maconha", "cocaina", "crack"]):
        return "SUSPEITO"

    return "SEM_ALTERACAO"

def fetch_training_data(limit: int | None = None):
    """Busca todos os relatos relevantes do banco de dados para o treinamento."""
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
            rows = cur.fetchall()
    return rows

def main():
    """Orquestra o processo de treinamento."""
    rows = fetch_training_data()
    print(f"Carregados {len(rows)} relatos do banco")
    print("Iniciando geração de embeddings...")
    if not rows:
        print("Nenhum dado encontrado para treinamento.")
        return

    X_text = [humanizar_texto((r["relato"] or "").strip()) for r in rows]
    y_labels = [auto_label(r) for r in rows]

    mask = [y in SUPPORTED_CLASSES for y in y_labels]
    X_text = [x for x, m in zip(X_text, mask) if m]
    y_labels = [y for y in y_labels if y in SUPPORTED_CLASSES]

    X = embed(X_text)
    classes = sorted(list(set(y_labels)))
    print("Classes detectadas:", classes)

    if len(classes) < 2:
        print("Erro: É necessário ter pelo menos 2 classes nos dados para treinar o modelo.")
        return

    class_to_idx = {c: i for i, c in enumerate(classes)}
    Y = np.zeros((len(y_labels), len(classes)), dtype=int)
    for i, y in enumerate(y_labels):
        if y in class_to_idx:
            Y[i, class_to_idx[y]] = 1

    Xtr, Xte, Ytr, Yte = train_test_split(X, Y, test_size=0.2, random_state=42, stratify=Y)

    # O classificador OneVsRestClassifier funciona bem para o caso binário também.
    base = LogisticRegression(max_iter=200, class_weight="balanced")
    ovr = OneVsRestClassifier(CalibratedClassifierCV(base, cv=3, method="sigmoid"))
    ovr.fit(Xtr, Ytr)

    Yp = (ovr.predict_proba(Xte) > 0.5).astype(int)
    print(classification_report(Yte, Yp, target_names=classes, zero_division=0))

    joblib.dump(ovr, CLF_PATH)
    joblib.dump(classes, LBL_PATH)
    print("Modelo salvo em:", CLF_PATH)
    print("Labels salvos em:", LBL_PATH)

if __name__ == "__main__":
    main()

