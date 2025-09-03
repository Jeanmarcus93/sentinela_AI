# test_batch.py
import psycopg
from psycopg.rows import dict_row

from database import DB_CONFIG
from semantic_local import analyze_text

def fetch_sample(limit: int = 10):
    sql = f"""
    SELECT id, tipo, relato
    FROM ocorrencias
    WHERE relato IS NOT NULL AND relato <> ''
    ORDER BY datahora DESC
    LIMIT {limit};
    """
    with psycopg.connect(**DB_CONFIG) as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(sql)
            return cur.fetchall()

def main():
    rows = fetch_sample(10)
    if not rows:
        print("⚠️ Nenhum relato encontrado no banco.")
        return
    
    for r in rows:
        print("=" * 80)
        print(f"ID: {r['id']} | Tipo: {r['tipo']}")
        print(f"Relato: {r['relato']}")
        res = analyze_text(r['relato'])
        print("\n📊 Análise semântica:")
        print(f"  Classe: {res['classe']} | Risco: {res['pontuacao']}")
        print(f"  Indicadores: {res['indicadores']}")
        print(f"  Keywords: {[k['term'] for k in res['keywords'][:5]]}")
        print(f"  Probs: {res['probs']}")
        print()

if __name__ == "__main__":
    main()
