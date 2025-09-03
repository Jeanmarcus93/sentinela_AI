from __future__ import annotations
import os, json, re
import sys
import numpy as np
import joblib
import psycopg
from psycopg.rows import dict_row
from sklearn.linear_model import LogisticRegression
from sklearn.multiclass import OneVsRestClassifier
from sklearn.calibration import CalibratedClassifierCV
from sklearn.pipeline import Pipeline
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report

# garante que a raiz está no sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import DB_CONFIG
from semantic_local import MODELS_DIR, EMB_MODEL_NAME, embed, SUPPORTED_CLASSES, CLF_PATH, LBL_PATH


RE_RECEPT = re.compile(r"\b(recepta[cç][aã]o|recupera[cç][aã]o|clonado|roubado|adulterado)\b", re.I)

def auto_label(row) -> str:
    # regra por apreensões
    if row.get("apreensoes"):
        for a in row["apreensoes"]:
            if a["tipo"] in ("Maconha", "Skunk", "Cocaina", "Crack", "Sintéticos"):
                return "TRAFICO"
            if a["tipo"] == "Arma":
                return "PORTE_ARMA"
    # regra por texto
    relato = (row.get("relato") or "").lower()
    if RE_RECEPT.search(relato):
        return "RECEPTACAO"
    return "OUTROS"

def fetch_training_data(limit: int | None = None):
    """
    Busca relatos de Abordagem e BOP com possíveis apreensões
    """
    qlimit = f"LIMIT {int(limit)}" if limit else ""
    sql = f"""
    SELECT o.id, o.relato, o.tipo,
           COALESCE(
             (
               SELECT json_agg(json_build_object('tipo', a.tipo::text, 'quantidade', a.quantidade, 'unidade', a.unidade))
               FROM apreensoes a WHERE a.ocorrencia_id = o.id
             ), '[]'::json
           ) AS apreensoes
    FROM ocorrencias o
    WHERE o.relato IS NOT NULL AND o.relato <> '' AND o.tipo IN ('Abordagem','BOP')
    ORDER BY o.datahora DESC
    {qlimit};
    """
    with psycopg.connect(**DB_CONFIG) as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(sql)
            rows = cur.fetchall()
    return rows

def main():
    rows = fetch_training_data()
    if not rows:
        print("Sem dados de treino.")
        return

    X_text = [(r["relato"] or "").strip() for r in rows]
    y_labels = [auto_label(r) for r in rows]

    # Filtra classes suportadas
    mask = [y in SUPPORTED_CLASSES for y in y_labels]
    X_text = [x for x, m in zip(X_text, mask) if m]
    y_labels = [y for y in y_labels if y in SUPPORTED_CLASSES]

    X = embed(X_text)  # 768-dim aprox para este modelo
    classes = sorted(list(set(y_labels)))
    print("Classes detectadas:", classes)

    # binariza manualmente
    class_to_idx = {c: i for i, c in enumerate(classes)}
    Y = np.zeros((len(y_labels), len(classes)), dtype=int)
    for i, y in enumerate(y_labels):
        Y[i, class_to_idx[y]] = 1

    Xtr, Xte, Ytr, Yte = train_test_split(X, Y, test_size=0.2, random_state=42, stratify=Y)

    base = LogisticRegression(max_iter=200, class_weight="balanced")
    ovr = OneVsRestClassifier(CalibratedClassifierCV(base, cv=3, method="sigmoid"))
    ovr.fit(Xtr, Ytr)

    # avaliação simples
    Yp = (ovr.predict_proba(Xte) > 0.5).astype(int)
    print(classification_report(Yte, Yp, target_names=classes, zero_division=0))

    # salva
    joblib.dump(ovr, CLF_PATH)
    joblib.dump(classes, LBL_PATH)
    print("Modelo salvo em:", CLF_PATH)
    print("Labels salvos em:", LBL_PATH)

if __name__ == "__main__":
    main()
