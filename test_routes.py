import os
import sys
import joblib
import psycopg
import numpy as np
import pandas as pd
from psycopg.rows import dict_row

# garante acesso ao database.py
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database import DB_CONFIG
from train_routes import CLF_PATH, LBL_PATH, _segment_trips, _short_trip, _is_night, _build_trip


def fetch_route_by_placa(placa: str):
    """
    Busca todas passagens de uma placa específica.
    """
    sql = """
    SELECT p.id, v.placa, p.datahora, p.municipio, p.rodovia,
           p.ilicito_ida, p.ilicito_volta
    FROM passagens p
    JOIN veiculos v ON v.id = p.veiculo_id
    WHERE v.placa = %s
    ORDER BY p.datahora;
    """
    with psycopg.connect(**DB_CONFIG) as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(sql, (placa,))
            return cur.fetchall()


def build_features(rows):
    """
    Constrói features para uma única placa.
    Mesmo formato usado em train_routes.py
    """
    if not rows:
        return None, None

    df = pd.DataFrame(rows).sort_values("datahora")
    df["datahora"] = pd.to_datetime(df["datahora"])
    df["municipio"] = df["municipio"].astype(str)
    df["rodovia"] = df["rodovia"].astype(str)
    for col in ("ilicito_ida", "ilicito_volta"):
        if col not in df.columns:
            df[col] = False
        df[col] = df[col].fillna(False).astype(bool)

    # features clássicas
    n_passagens = len(df)
    n_municipios = df["municipio"].nunique()
    n_rodovias = df["rodovia"].nunique()
    duracao_periodo_h = (df["datahora"].max() - df["datahora"].min()).total_seconds() / 3600.0
    hora_inicio = df["datahora"].min().hour

    # trips
    trips = _segment_trips(df)
    total_trips = len(trips)
    short_trip_count = sum(_short_trip(t) for t in trips) if total_trips > 0 else 0
    short_trip_ratio = (short_trip_count / total_trips) if total_trips > 0 else 0.0
    avg_trip_duration_h = float(np.mean([t.duration_h for t in trips])) if total_trips > 0 else 0.0

    if total_trips > 1:
        starts = [t.start_time for t in trips]
        gaps_h = []
        for i in range(1, total_trips):
            gap = (starts[i] - trips[i - 1].end_time).total_seconds() / 3600.0
            gaps_h.append(gap)
        median_inter_gap_h = float(np.median(gaps_h)) if gaps_h else 0.0
    else:
        median_inter_gap_h = 0.0

    days_span = max((df["datahora"].max().date() - df["datahora"].min().date()).days + 1, 1)
    trips_per_day = total_trips / days_span if days_span > 0 else 0.0
    night_trip_ratio = (sum(_is_night(t.start_time) for t in trips) / total_trips) if total_trips > 0 else 0.0

    if total_trips > 0:
        od_pairs = [(t.start_mun, t.end_mun) for t in trips]
        od_series = pd.Series(od_pairs)
        counts = od_series.value_counts()
        repeated_set = set(counts[counts >= 2].index)
        repeated_od = sum(1 for od in od_pairs if od in repeated_set)
        repeated_od_ratio = repeated_od / total_trips
    else:
        repeated_od_ratio = 0.0

    X = np.array([[n_passagens, n_municipios, n_rodovias,
                   duracao_periodo_h, hora_inicio,
                   total_trips, short_trip_count, short_trip_ratio,
                   avg_trip_duration_h, median_inter_gap_h,
                   trips_per_day, night_trip_ratio, repeated_od_ratio]])

    features_dict = {
        "n_passagens": n_passagens,
        "n_municipios": n_municipios,
        "n_rodovias": n_rodovias,
        "duracao_periodo_h": round(duracao_periodo_h, 2),
        "hora_inicio": hora_inicio,
        "total_trips": total_trips,
        "short_trip_count": short_trip_count,
        "short_trip_ratio": round(short_trip_ratio, 2),
        "avg_trip_duration_h": round(avg_trip_duration_h, 2),
        "median_inter_gap_h": round(median_inter_gap_h, 2),
        "trips_per_day": round(trips_per_day, 2),
        "night_trip_ratio": round(night_trip_ratio, 2),
        "repeated_od_ratio": round(repeated_od_ratio, 2),
    }

    return X, features_dict


def carregar_modelo():
    if not os.path.exists(CLF_PATH) or not os.path.exists(LBL_PATH):
        raise FileNotFoundError("⚠️ Modelo não encontrado. Rode primeiro train_routes.py")

    clf = joblib.load(CLF_PATH)
    labels = joblib.load(LBL_PATH)
    return clf, labels


def analisar_placa(placa: str):
    rows = fetch_route_by_placa(placa)
    if not rows:
        print(f"⚠️ Nenhuma passagem encontrada para a placa {placa}")
        return

    X, feats = build_features(rows)
    clf, labels = carregar_modelo()
    probs = clf.predict_proba(X)[0]

    print("=" * 80)
    print(f"Placa: {placa}")
    print(f"Total de passagens: {len(rows)}")
    print(f"Primeira data: {rows[0]['datahora']} | Última data: {rows[-1]['datahora']}")

    print("\n📊 Features extraídas:")
    for k, v in feats.items():
        print(f"  {k}: {v}")

    print("\n📊 Predição da rota:")
    for lbl, prob in zip(labels, probs):
        print(f"  {lbl}: {prob:.2f}")

    print(f"\n✅ Classe escolhida: {labels[np.argmax(probs)]}")


if __name__ == "__main__":
    while True:
        placa = input("\nDigite a placa para análise (ou 'sair' para encerrar): ").strip().upper()
        if placa == "SAIR":
            break
        analisar_placa(placa)
