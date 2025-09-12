from __future__ import annotations
import os
import sys
import joblib
import psycopg
import numpy as np
import pandas as pd
from dataclasses import dataclass
from psycopg.rows import dict_row
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split, StratifiedKFold, cross_val_score
from sklearn.metrics import classification_report

# ========= Configurações de segmentação/curta duração =========
GAP_HOURS_NEW_TRIP = 4.0             # gap >= 4h separa viagens
SHORT_TRIP_MAX_HOURS = 3.0           # viagem curta: duração <= 3h
SHORT_TRIP_MAX_STOPS = 2             # viagem curta: <= 2 municípios distintos
NIGHT_START = 22                     # noite: 20:00
NIGHT_END = 6                        # até 06:00

# ========= Caminhos/DB =========
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.models.database import DB_CONFIG  # noqa: E402

MODELS_DIR = os.path.join(os.path.dirname(__file__), "models")
os.makedirs(MODELS_DIR, exist_ok=True)
CLF_PATH = os.path.join(MODELS_DIR, "routes_clf.joblib")
LBL_PATH = os.path.join(MODELS_DIR, "routes_labels.joblib")


def fetch_routes(limit: int | None = None):
    """
    Busca passagens do banco agrupadas por veículo (placa),
    incluindo flags de ilícito para rotulagem supervisionada.
    """
    qlimit = f"LIMIT {int(limit)}" if limit else ""
    sql = f"""
    SELECT p.id, v.placa, p.datahora, p.municipio, p.rodovia,
           p.ilicito_ida, p.ilicito_volta
    FROM passagens p
    JOIN veiculos v ON v.id = p.veiculo_id
    ORDER BY v.placa, p.datahora
    {qlimit};
    """
    with psycopg.connect(**DB_CONFIG) as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(sql)
            rows = cur.fetchall()
    return rows


@dataclass
class Trip:
    start_time: pd.Timestamp
    end_time: pd.Timestamp
    start_mun: str
    end_mun: str
    duration_h: float
    unique_muns: int

def _is_night(ts: pd.Timestamp) -> bool:
    h = ts.hour
    # noite se entre 22:00-23:59 ou 00:00-05:59
    return (h >= NIGHT_START) or (h < NIGHT_END)

def _segment_trips(df: pd.DataFrame) -> list[Trip]:
    """
    Segmentar passagens de uma placa em viagens, usando GAP_HOURS_NEW_TRIP.
    df deve estar ordenado por datahora.
    """
    trips: list[Trip] = []
    if df.empty:
        return trips

    curr_start_idx = 0
    for i in range(1, len(df)):
        gap_h = (df.iloc[i]["datahora"] - df.iloc[i - 1]["datahora"]).total_seconds() / 3600.0
        if gap_h >= GAP_HOURS_NEW_TRIP:
            # fecha viagem atual [curr_start_idx, i-1]
            seg = df.iloc[curr_start_idx:i]
            trips.append(_build_trip(seg))
            curr_start_idx = i

    # fecha última viagem
    seg = df.iloc[curr_start_idx:]
    trips.append(_build_trip(seg))
    return trips

def _build_trip(seg: pd.DataFrame) -> Trip:
    start_time = seg["datahora"].min()
    end_time = seg["datahora"].max()
    duration_h = (end_time - start_time).total_seconds() / 3600.0
    start_mun = str(seg.iloc[0]["municipio"] or "")
    end_mun = str(seg.iloc[-1]["municipio"] or "")
    unique_muns = int(seg["municipio"].nunique())
    return Trip(
        start_time=start_time,
        end_time=end_time,
        start_mun=start_mun,
        end_mun=end_mun,
        duration_h=duration_h,
        unique_muns=unique_muns,
    )

def _short_trip(trip: Trip) -> bool:
    return (trip.duration_h <= SHORT_TRIP_MAX_HOURS) and (trip.unique_muns <= SHORT_TRIP_MAX_STOPS)


def build_features(rows):
    """
    Constrói features por placa, incluindo repetição de viagens curtas
    e métricas temporais/locacionais.
    """
    df = pd.DataFrame(rows)
    if df.empty:
        return None, None

    # Normaliza tipos
    df["datahora"] = pd.to_datetime(df["datahora"])
    df["municipio"] = df["municipio"].astype(str)
    df["rodovia"] = df["rodovia"].astype(str)
    # booleanos podem vir como None -> preenche com False
    for col in ("ilicito_ida", "ilicito_volta"):
        if col not in df.columns:
            df[col] = False
        df[col] = df[col].fillna(False).astype(bool)

    features, labels = [], []

    for placa, grupo in df.groupby("placa"):
        grupo = grupo.sort_values("datahora")

        # ===== Features clássicas (janela global do histórico) =====
        n_passagens = len(grupo)
        n_municipios = grupo["municipio"].nunique()
        n_rodovias = grupo["rodovia"].nunique()
        duracao_periodo_h = (grupo["datahora"].max() - grupo["datahora"].min()).total_seconds() / 3600.0
        hora_inicio = int(grupo["datahora"].min().hour)

        # ===== Segmentação em viagens =====
        trips = _segment_trips(grupo)
        total_trips = len(trips)

        short_trip_count = sum(_short_trip(t) for t in trips) if total_trips > 0 else 0
        short_trip_ratio = (short_trip_count / total_trips) if total_trips > 0 else 0.0
        avg_trip_duration_h = float(np.mean([t.duration_h for t in trips])) if total_trips > 0 else 0.0

        # gaps entre viagens
        if total_trips > 1:
            starts = [t.start_time for t in trips]
            gaps_h = []
            for i in range(1, total_trips):
                gap = (starts[i] - trips[i - 1].end_time).total_seconds() / 3600.0
                gaps_h.append(gap)
            median_inter_gap_h = float(np.median(gaps_h)) if gaps_h else 0.0
        else:
            median_inter_gap_h = 0.0

        # viagens por dia
        days_span = max((grupo["datahora"].max().date() - grupo["datahora"].min().date()).days + 1, 1)
        trips_per_day = total_trips / days_span if days_span > 0 else 0.0

        # viagens iniciadas à noite
        night_trip_ratio = (sum(_is_night(t.start_time) for t in trips) / total_trips) if total_trips > 0 else 0.0

        # repetição de OD (origem-destino)
        if total_trips > 0:
            od_pairs = [(t.start_mun, t.end_mun) for t in trips]
            od_series = pd.Series(od_pairs)
            # viagens que repetem um OD que já ocorreu ao menos 2x
            counts = od_series.value_counts()
            repeated_set = set(counts[counts >= 2].index)
            repeated_od = sum(1 for od in od_pairs if od in repeated_set)
            repeated_od_ratio = repeated_od / total_trips
        else:
            repeated_od_ratio = 0.0

        # ===== Rótulo supervisionado =====
        ilicito_label = bool(grupo["ilicito_ida"].any() or grupo["ilicito_volta"].any())

        # ===== Monta vetor de features =====
        feat_vec = [
            # clássicas
            n_passagens,
            n_municipios,
            n_rodovias,
            duracao_periodo_h,
            hora_inicio,
            # de viagens
            total_trips,
            short_trip_count,
            short_trip_ratio,
            avg_trip_duration_h,
            median_inter_gap_h,
            trips_per_day,
            night_trip_ratio,
            repeated_od_ratio,
        ]

        features.append(feat_vec)
        labels.append("ILICITO" if ilicito_label else "NORMAL")

    X = np.array(features, dtype=float)
    y = np.array(labels)
    return X, y


def main():
    rows = fetch_routes()
    if not rows:
        print("⚠️ Nenhuma passagem encontrada no banco.")
        return

    X, y = build_features(rows)
    if X is None or len(X) == 0:
        print("⚠️ Sem features para treinar.")
        return

    print("Shape dos dados:", X.shape)
    print("Distribuição das classes:", pd.Series(y).value_counts())

    # ===== Treino/teste + Cross-Validation (melhor em datasets pequenos) =====
    Xtr, Xte, Ytr, Yte = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    clf = RandomForestClassifier(
        n_estimators=400,
        max_depth=None,
        min_samples_leaf=2,
        random_state=42,
        class_weight="balanced",
        n_jobs=-1,
    )
    clf.fit(Xtr, Ytr)

    yp = clf.predict(Xte)
    print("\n📊 Relatório de classificação (holdout 20%):")
    print(classification_report(Yte, yp, zero_division=0))

    # k-fold para estabilizar métrica em bases pequenas
    if len(np.unique(y)) > 1 and len(y) >= 6:
        cv = StratifiedKFold(n_splits=min(5, np.unique(y, return_counts=True)[1].min()))
        scores = cross_val_score(clf, X, y, cv=cv, scoring="f1_macro")
        print(f"\n🔁 CV F1-macro ({cv.get_n_splits()} folds): média={scores.mean():.3f} ± {scores.std():.3f}")

    # Salvar
    joblib.dump(clf, CLF_PATH)
    joblib.dump(sorted(set(y)), LBL_PATH)
    print("\n✅ Modelo salvo em:", CLF_PATH)
    print("✅ Labels salvos em:", LBL_PATH)


if __name__ == "__main__":
    main()