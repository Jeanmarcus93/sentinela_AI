import os
import sys
import joblib
import psycopg
import numpy as np
import pandas as pd
from psycopg.rows import dict_row

# garante acesso ao database.py
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database import DB_CONFIG, DB_CONFIG_TESTE
from train_routes import CLF_PATH as ROUTE_CLF, LBL_PATH as ROUTE_LBL, build_features
from semantic_local import embed, CLF_PATH as SEM_CLF, LBL_PATH as SEM_LBL


# ================== Funções de apoio ==================

def fetch_passagens_duplo(placa: str):
    """
    Consulta passagens da placa em ambos os bancos (produção e teste).
    """
    sql = """
    SELECT p.id, v.placa, p.datahora, p.municipio, p.rodovia,
           p.ilicito_ida, p.ilicito_volta
    FROM passagens p
    JOIN veiculos v ON v.id = p.veiculo_id
    WHERE v.placa = %s
    ORDER BY p.datahora;
    """
    resultados = []
    for cfg in (DB_CONFIG, DB_CONFIG_TESTE):
        try:
            with psycopg.connect(**cfg) as conn:
                with conn.cursor(row_factory=dict_row) as cur:
                    cur.execute(sql, (placa,))
                    resultados.extend(cur.fetchall())
        except Exception as e:
            print(f"⚠️ Erro ao consultar banco {cfg['dbname']}: {e}")
    return resultados


def fetch_ocorrencias_duplo(placa: str, limit: int = 5):
    """
    Consulta ocorrências da placa em ambos os bancos (produção e teste).
    """
    sql = """
    SELECT o.id, o.tipo, o.relato, o.datahora
    FROM ocorrencias o
    JOIN veiculos v ON v.id = o.veiculo_id
    WHERE v.placa = %s AND o.relato IS NOT NULL AND o.relato <> ''
    ORDER BY o.datahora DESC
    LIMIT %s;
    """
    resultados = []
    for cfg in (DB_CONFIG, DB_CONFIG_TESTE):
        try:
            with psycopg.connect(**cfg) as conn:
                with conn.cursor(row_factory=dict_row) as cur:
                    cur.execute(sql, (placa, limit))
                    resultados.extend(cur.fetchall())
        except Exception as e:
            print(f"⚠️ Erro ao consultar banco {cfg['dbname']}: {e}")
    return resultados


def carregar_modelos():
    route_clf = joblib.load(ROUTE_CLF)
    route_labels = joblib.load(ROUTE_LBL)
    sem_clf = joblib.load(SEM_CLF)
    sem_labels = joblib.load(SEM_LBL)
    return route_clf, route_labels, sem_clf, sem_labels


# ================== Análise combinada ==================

def analisar_placa(placa: str):
    route_clf, route_labels, sem_clf, sem_labels = carregar_modelos()

    risco_rota = 0.0
    risco_sem = 0.0

    # ---------- Rotas ----------
    passagens = fetch_passagens_duplo(placa)
    if passagens:
        X, _ = build_features(passagens)
        if X is not None:
            probs_route = route_clf.predict_proba(X)[0]
            risco_rota = probs_route[route_labels.index("ILICITO")] if "ILICITO" in route_labels else 0.0
            print("=" * 80)
            print(f"📍 Análise de Rotas para {placa}")
            for lbl, prob in zip(route_labels, probs_route):
                print(f"  {lbl}: {prob:.2f}")
            print(f"✅ Classe escolhida: {route_labels[np.argmax(probs_route)]}")
    else:
        print("⚠️ Nenhuma passagem encontrada para essa placa.")

    # ---------- Relatos ----------
    ocorrencias = fetch_ocorrencias_duplo(placa)
    if ocorrencias:
        riscos_relatos = []
        print("\n📝 Análise de Relatos (últimos):")
        for oc in ocorrencias:
            texto = (oc["relato"] or "").strip()
            if not texto:
                continue
            X_text = embed([texto])
            probs_sem = sem_clf.predict_proba(X_text)[0]
            # risco = soma de classes ilícitas
            risco = 0.0
            for lbl, prob in zip(sem_labels, probs_sem):
                if lbl in ("TRAFICO", "PORTE_ARMA", "RECEPTACAO"):
                    risco += prob
            riscos_relatos.append(risco)

            print(f"\nRelato ID {oc['id']} ({oc['tipo']} - {oc['datahora']}):")
            for lbl, prob in zip(sem_labels, probs_sem):
                print(f"  {lbl}: {prob:.2f}")
            print(f"✅ Classe escolhida: {sem_labels[np.argmax(probs_sem)]}")

        if riscos_relatos:
            risco_sem = float(np.mean(riscos_relatos))
    else:
        print("\n⚠️ Nenhum relato encontrado para essa placa.")

    # ---------- Índice de risco global ----------
    indice_risco = 0.6 * risco_rota + 0.4 * risco_sem
    print("\n🔥 Índice de Risco Global:")
    print(f"  Rotas: {risco_rota:.2f} | Relatos: {risco_sem:.2f}")
    print(f"  => Risco final: {indice_risco:.2f}")


if __name__ == "__main__":
    while True:
        placa = input("\nDigite a placa para análise (ou 'sair' para encerrar): ").strip().upper()
        if placa == "SAIR":
            break
        analisar_placa(placa)
def analisar_placa_json(placa: str):
    route_clf, route_labels, sem_clf, sem_labels = carregar_modelos()

    resultado = {"placa": placa, "rotas": {}, "relatos": [], "risco": {}}
    risco_rota = 0.0
    risco_sem = 0.0

    # Rotas
    passagens = fetch_passagens_duplo(placa)
    if passagens:
        X, _ = build_features(passagens)
        if X is not None:
            probs_route = route_clf.predict_proba(X)[0]
            risco_rota = probs_route[route_labels.index("ILICITO")] if "ILICITO" in route_labels else 0.0
            resultado["rotas"] = {
                "labels": route_labels,
                "probs": probs_route.tolist(),
                "classe": route_labels[np.argmax(probs_route)]
            }

    # Relatos
    ocorrencias = fetch_ocorrencias_duplo(placa)
    for oc in ocorrencias:
        texto = (oc["relato"] or "").strip()
        if texto:
            X_text = embed([texto])
            probs_sem = sem_clf.predict_proba(X_text)[0]
            risco = sum(prob for lbl, prob in zip(sem_labels, probs_sem)
                        if lbl in ("TRAFICO", "PORTE_ARMA", "RECEPTACAO"))
            risco_sem += risco
            resultado["relatos"].append({
                "id": oc["id"],
                "tipo": oc["tipo"],
                "datahora": str(oc["datahora"]),
                "texto": texto,
                "labels": sem_labels,
                "probs": probs_sem.tolist(),
                "classe": sem_labels[np.argmax(probs_sem)]
            })
    if resultado["relatos"]:
        risco_sem /= len(resultado["relatos"])

    # Índice global
    indice_risco = 0.6 * risco_rota + 0.4 * risco_sem
    resultado["risco"] = {
        "rotas": risco_rota,
        "relatos": risco_sem,
        "final": indice_risco
    }
    return resultado
