# analise.py
from flask import Blueprint, jsonify, request
import pandas as pd
from sqlalchemy import text
import json

from database import get_engine, get_db_connection

# Cria um Blueprint para as rotas de análise
analise_bp = Blueprint('analise_bp', __name__)

@analise_bp.route('/api/analise/filtros')
def api_analise_filtros():
    """Fornece a lista de locais de entrega para preencher os filtros da UI."""
    try:
        engine = get_engine()
        with engine.connect() as conn:
            query = text("SELECT DISTINCT relato FROM ocorrencias WHERE tipo = 'Local de Entrega' AND relato IS NOT NULL ORDER BY 1;")
            df_locais = pd.read_sql(query, conn)
            return jsonify(locais=df_locais['relato'].tolist())
    except Exception as e:
        print(f"ERRO em api_analise_filtros: {e}")
        return jsonify({"error": "Não foi possível carregar os filtros."}), 500

@analise_bp.route('/api/analise')
def api_analise_dados():
    """Endpoint principal que gera todos os dados de análise e inteligência."""
    locais_selecionados = request.args.getlist('locais')
    placa = request.args.get('placa', None)
    engine = get_engine()
    
    try:
        params = {}
        where_clauses = ["1=1"]

        if locais_selecionados:
            where_clauses.append("veiculo_id IN (SELECT DISTINCT veiculo_id FROM ocorrencias WHERE tipo = 'Local de Entrega' AND relato = ANY(:locais))")
            params['locais'] = locais_selecionados

        if placa:
            with get_db_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT id FROM veiculos WHERE placa = %s;", (placa.upper(),))
                    veiculo_result = cur.fetchone()
                    if veiculo_result:
                        where_clauses.append("veiculo_id = :placa_veiculo_id")
                        params['placa_veiculo_id'] = veiculo_result[0]
                    else:
                        where_clauses.append("1=0")

        base_where_sql = " AND ".join(where_clauses)

        # --- Análise de Padrões de Passagens (Ida e Volta) ---
        def get_chart_data(table_name, extra_condition=""):
            query = f"""
                SELECT municipio, rodovia, EXTRACT(HOUR FROM datahora) AS hora, EXTRACT(DOW FROM datahora) AS dow 
                FROM {table_name} WHERE {base_where_sql} {extra_condition}
            """
            df = pd.read_sql(text(query), engine, params=params)
            if df.empty:
                return {"municipio": {}, "rodovia": {}, "hora": {}, "dia_semana": {}}
            
            df_mun = df['municipio'].value_counts().head(10)
            df_rodo = df['rodovia'].value_counts().head(10)
            df_hora = df['hora'].astype(int).value_counts().sort_index()
            
            dias_map = {0: "Dom", 1: "Seg", 2: "Ter", 3: "Qua", 4: "Qui", 5: "Sex", 6: "Sáb"}
            df['dia_semana'] = df['dow'].map(dias_map)
            df_dow = df['dia_semana'].value_counts().reindex(dias_map.values()).dropna()

            return {
                "municipio": {"labels": df_mun.index.tolist(), "data": df_mun.values.tolist()},
                "rodovia": {"labels": df_rodo.index.tolist(), "data": df_rodo.values.tolist()},
                "hora": {"labels": df_hora.index.tolist(), "data": df_hora.values.tolist()},
                "dia_semana": {"labels": df_dow.index.tolist(), "data": df_dow.values.tolist()}
            }

        dados_ida = get_chart_data("passagens", "AND ilicito_ida IS TRUE")
        dados_volta = get_chart_data("passagens", "AND ilicito_volta IS TRUE")
        
        # --- Análise Logística (Tempo Médio de Permanência) ---
        logistica_data = {}
        query_lead_time = f"SELECT datahora, datahora_fim FROM ocorrencias WHERE tipo = 'Local de Entrega' AND datahora_fim IS NOT NULL AND {base_where_sql}"
        df_lead_time = pd.read_sql(text(query_lead_time), engine, params=params)
        tempo_medio_horas = 0
        if not df_lead_time.empty:
            df_lead_time['permanencia_horas'] = (df_lead_time['datahora_fim'] - df_lead_time['datahora']).dt.total_seconds() / 3600
            tempo_medio_horas = df_lead_time['permanencia_horas'].mean()
        logistica_data["tempo_medio"] = f"{tempo_medio_horas:.2f}"

        # ================== SEÇÃO DE INTELIGÊNCIA ==================
        passagens_where_sql = base_where_sql.replace('veiculo_id', 'p.veiculo_id')
        ocorrencias_where_sql = base_where_sql.replace('veiculo_id', 'o.veiculo_id')
        veiculos_join_where = base_where_sql.replace('veiculo_id', 'p.veiculo_id')

        # --- Inteligência de Rotas Comuns ---
        query_rotas = text(f"""
            WITH partida AS (
                SELECT DISTINCT ON (p.veiculo_id) p.veiculo_id, p.municipio AS municipio_partida
                FROM passagens p WHERE p.ilicito_ida IS TRUE AND {passagens_where_sql} ORDER BY p.veiculo_id, p.datahora ASC
            ),
            chegada AS (
                SELECT o.veiculo_id, o.relato AS municipio_chegada FROM ocorrencias o 
                WHERE o.tipo = 'Local de Entrega' AND {ocorrencias_where_sql}
            )
            SELECT p.municipio_partida || ' -> ' || c.municipio_chegada AS rota, COUNT(*) AS total
            FROM partida p JOIN chegada c ON p.veiculo_id = c.veiculo_id GROUP BY rota ORDER BY total DESC LIMIT 10;
        """)
        df_rotas = pd.read_sql(query_rotas, engine, params=params)
        rotas_chart = {"labels": df_rotas['rota'].tolist(), "data": df_rotas['total'].tolist()} if not df_rotas.empty else {}
        
        # --- Inteligência de Perfil de Veículos ---
        query_veiculos = text(f"""
            SELECT v.marca_modelo, v.cor FROM veiculos v JOIN passagens p ON v.id = p.veiculo_id
            WHERE p.ilicito_ida IS TRUE AND {veiculos_join_where}
        """)
        df_veiculos = pd.read_sql(query_veiculos, engine, params=params).drop_duplicates()
        modelos_chart, cores_chart = {}, {}
        if not df_veiculos.empty:
            df_modelos = df_veiculos['marca_modelo'].value_counts().head(10)
            df_cores = df_veiculos['cor'].value_counts().head(10)
            modelos_chart = {"labels": df_modelos.index.tolist(), "data": df_modelos.values.tolist()}
            cores_chart = {"labels": df_cores.index.tolist(), "data": df_cores.values.tolist()}
            
        # --- Inteligência de Apreensões (BOP) ---
        query_bop = text(f"SELECT apreensoes FROM ocorrencias WHERE tipo = 'BOP' AND apreensoes IS NOT NULL AND {base_where_sql};")
        df_bop = pd.read_sql(query_bop, engine, params=params)
        apreensoes_chart = {}
        if not df_bop.empty and not df_bop['apreensoes'].dropna().empty:
            try:
                s_apreensoes = df_bop['apreensoes'].dropna().apply(json.loads).explode()
                df_apreensoes = s_apreensoes.value_counts().head(10)
                apreensoes_chart = {"labels": df_apreensoes.index.tolist(), "data": df_apreensoes.values.tolist()}
            except Exception as e:
                print(f"AVISO: Erro ao processar JSON de apreensões: {e}")

        inteligencia_data = {
            "rotas": rotas_chart, "veiculos_modelos": modelos_chart,
            "veiculos_cores": cores_chart, "apreensoes": apreensoes_chart
        }
        
        return jsonify(ida=dados_ida, volta=dados_volta, logistica=logistica_data, inteligencia=inteligencia_data)

    except Exception as e:
        print(f"ERRO em api_analise_dados: {e}")
        return jsonify({"error": "Não foi possível gerar os dados de análise."}), 500