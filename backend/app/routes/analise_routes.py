import re
import os
import csv
import json
import pandas as pd
from sqlalchemy import text
from app.services.semantic_service import analyze_text
from app.models.database import get_db_connection
from flask import Blueprint, jsonify, request, render_template
from app.services.placa_service import analisar_placa_json
from app.models.database import get_engine, get_db_connection
from app.services.semantic_service import analyze_text
from app.models.database import get_db_connection

# Cria um Blueprint para as rotas de feedback
feedback_bp = Blueprint('feedback', __name__)

# Cria um Blueprint para as rotas de análise
analise_bp = Blueprint('analise_bp', __name__)

# --- Rota para renderizar a página de Análise ---
@analise_bp.route('/analise')
def analise():
    """Renderiza o template da página de Análise."""
    return render_template('analise.html')

@analise_bp.route('/api/analise/filtros')
def api_analise_filtros():
    """Fornece a lista de locais de entrega e tipos de apreensão para preencher os filtros da UI."""
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                # Busca locais de entrega distintos para o filtro
                cur.execute("SELECT DISTINCT relato FROM ocorrencias WHERE tipo = 'Local de Entrega' AND relato IS NOT NULL ORDER BY 1;")
                locais = [row[0] for row in cur.fetchall()]

                # Busca todos os tipos possíveis do enum de apreensões para o filtro
                cur.execute("SELECT unnest(enum_range(NULL::tipo_apreensao_enum))::text ORDER BY 1;")
                apreensoes = [row[0] for row in cur.fetchall()]

        return jsonify(locais=locais, apreensoes=apreensoes)
    except Exception as e:
        print(f"ERRO em api_analise_filtros: {e}")
        return jsonify({"error": "Não foi possível carregar os filtros."}), 500

@analise_bp.route('/api/analise')
def api_analise_dados():
    """Endpoint principal que gera todos os dados de análise e inteligência com base nos filtros fornecidos."""
    # Coleta os parâmetros da URL
    locais_selecionados = request.args.getlist('locais')
    apreensoes_selecionadas = request.args.getlist('apreensoes')
    placa = request.args.get('placa', None)
    data_inicio = request.args.get('data_inicio', None)
    data_fim = request.args.get('data_fim', None)

    engine = get_engine()

    try:
        # ---- Construção da Cláusula WHERE Dinâmica para filtrar veiculo_id ----
        params = {}
        subqueries = []

        if locais_selecionados:
            subqueries.append("SELECT DISTINCT veiculo_id FROM ocorrencias WHERE tipo = 'Local de Entrega' AND relato = ANY(:locais)")
            params['locais'] = locais_selecionados

        if apreensoes_selecionadas:
            # Converte a coluna enum para texto para permitir a comparação com a lista de strings
            subqueries.append("SELECT DISTINCT o.veiculo_id FROM ocorrencias o JOIN apreensoes a ON o.id = a.ocorrencia_id WHERE a.tipo::text = ANY(:apreensoes)")
            params['apreensoes'] = apreensoes_selecionadas

        veiculo_id_filter = ""
        if subqueries:
            # Usa INTERSECT para encontrar veículos que correspondem a AMBOS os critérios (locais E apreensões)
            veiculo_id_filter = f"veiculo_id IN ({ ' INTERSECT '.join(subqueries) })"

        # Constrói a cláusula WHERE principal para as consultas
        where_clauses = ["1=1"] # Inicia com uma condição sempre verdadeira
        if veiculo_id_filter:
            where_clauses.append(veiculo_id_filter)

        if placa:
            where_clauses.append("veiculo_id = (SELECT id FROM veiculos WHERE placa = :placa)")
            params['placa'] = placa.upper()

        if data_inicio:
            where_clauses.append("datahora >= :data_inicio")
            params['data_inicio'] = data_inicio

        if data_fim:
            # Inclui o dia inteiro na data de fim
            where_clauses.append("datahora <= :data_fim_inclusive")
            params['data_fim_inclusive'] = f"{data_fim} 23:59:59"

        base_where_sql = " AND ".join(where_clauses)

        # --- Análise de Padrões de Passagens ---
        def get_chart_data(table_name, extra_condition=""):
            """Função auxiliar para buscar e agregar dados para os gráficos de padrões."""
            query = text(f"SELECT municipio, rodovia, EXTRACT(HOUR FROM datahora) AS hora, EXTRACT(DOW FROM datahora) AS dow FROM {table_name} WHERE {base_where_sql} {extra_condition}")
            df = pd.read_sql(query, engine, params=params)
            
            # **NOVO: Prepara dados para o Heatmap Temporal**
            heatmap_data = {}
            if not df.empty:
                # Mapeia o dia da semana (número) para o nome abreviado
                dias_map = {0: "Dom", 1: "Seg", 2: "Ter", 3: "Qua", 4: "Qui", 5: "Sex", 6: "Sáb"}
                df['dia_semana'] = df['dow'].map(dias_map)
                
                # Cria a matriz para o heatmap
                heatmap_pivot = df.pivot_table(index='dia_semana', columns='hora', aggfunc='size', fill_value=0)
                heatmap_pivot = heatmap_pivot.reindex(list(dias_map.values())).dropna(how='all') # Ordena os dias
                heatmap_data = {
                    "y": heatmap_pivot.index.tolist(), # Dias da semana
                    "x": [str(int(h)) for h in heatmap_pivot.columns], # Horas
                    "z": heatmap_pivot.values.tolist() # Contagem
                }

            if df.empty:
                return {"municipio": {}, "rodovia": {}, "hora": {}, "dia_semana": {}, "heatmap_temporal": {}}
                
            df_mun, df_rodo = df['municipio'].value_counts().head(10), df['rodovia'].value_counts().head(10)
            df_hora = df['hora'].astype(int).value_counts().sort_index()
            df_dow = df['dia_semana'].value_counts().reindex(list(dias_map.values())).dropna()

            return {
                "municipio": {"labels": df_mun.index.tolist(), "data": df_mun.values.tolist()},
                "rodovia": {"labels": df_rodo.index.tolist(), "data": df_rodo.values.tolist()},
                "hora": {"labels": [str(h) for h in df_hora.index], "data": df_hora.values.tolist()},
                "dia_semana": {"labels": df_dow.index.tolist(), "data": df_dow.values.tolist()},
                "heatmap_temporal": heatmap_data,
                "pontos_geograficos": df['municipio'].value_counts().to_dict() # Para o mapa de calor geográfico
            }

        dados_ida = get_chart_data("passagens", "AND ilicito_ida IS TRUE")

        # --- Análise Logística ---
        query_lead_time = text(f"SELECT datahora, datahora_fim FROM ocorrencias WHERE tipo = 'Local de Entrega' AND datahora_fim IS NOT NULL AND {base_where_sql}")
        df_lead_time = pd.read_sql(query_lead_time, engine, params=params)
        tempo_medio_horas = 0
        if not df_lead_time.empty:
            df_lead_time['permanencia_horas'] = (df_lead_time['datahora_fim'] - df_lead_time['datahora']).dt.total_seconds() / 3600
            tempo_medio_horas = df_lead_time['permanencia_horas'].mean()
        logistica_data = {"tempo_medio": f"{tempo_medio_horas:.2f}"}

        # ================== SEÇÃO DE INTELIGÊNCIA ==================
        # --- Inteligência de Rotas Comuns ---
        query_rotas = text(f"""
            WITH viagens_ilicitas AS (
                SELECT DISTINCT ON (veiculo_id) veiculo_id, datahora, municipio AS municipio_partida
                FROM passagens
                WHERE {base_where_sql} AND ilicito_ida IS TRUE
                ORDER BY veiculo_id, datahora ASC
            ),
            chegadas AS (
                SELECT veiculo_id, relato AS municipio_chegada
                FROM ocorrencias
                WHERE tipo = 'Local de Entrega' AND {base_where_sql}
            )
            SELECT v.municipio_partida, c.municipio_chegada, COUNT(*) AS total
            FROM viagens_ilicitas v JOIN chegadas c ON v.veiculo_id = c.veiculo_id
            WHERE v.municipio_partida IS NOT NULL AND c.municipio_chegada IS NOT NULL
            GROUP BY v.municipio_partida, c.municipio_chegada ORDER BY total DESC LIMIT 15;
        """)
        df_rotas = pd.read_sql(query_rotas, engine, params=params)
        
        # **NOVO: Prepara dados para o Diagrama de Sankey e para o Mapa de Rotas**
        sankey_data = {}
        if not df_rotas.empty:
            # Prepara os nós (origens e destinos únicos)
            nodes = pd.concat([df_rotas['municipio_partida'], df_rotas['municipio_chegada']]).unique().tolist()
            node_map = {node: i for i, node in enumerate(nodes)}

            sankey_data = {
                "labels": nodes,
                "source": df_rotas['municipio_partida'].map(node_map).tolist(),
                "target": df_rotas['municipio_chegada'].map(node_map).tolist(),
                "value": df_rotas['total'].tolist()
            }
        
        rotas_formatadas = (df_rotas['municipio_partida'] + ' -> ' + df_rotas['municipio_chegada']).tolist()
        rotas_chart = {"labels": rotas_formatadas, "data": df_rotas['total'].values.tolist()}
        total_viagens = int(df_rotas['total'].sum())
        
        # --- Inteligência de Perfil de Veículos e Apreensões ---
        query_inteligencia = text(f"""
            SELECT v.marca_modelo, v.cor, a.tipo as tipo_apreensao
            FROM veiculos v
            JOIN ocorrencias o ON v.id = o.veiculo_id
            LEFT JOIN apreensoes a ON o.id = a.ocorrencia_id
            WHERE o.veiculo_id IN (SELECT veiculo_id FROM passagens WHERE {base_where_sql} AND ilicito_ida IS TRUE)
        """)
        df_intel = pd.read_sql(query_inteligencia, engine, params=params)
        modelos_chart, cores_chart, apreensoes_chart = {}, {}, {}
        if not df_intel.empty:
            df_modelos, df_cores = df_intel['marca_modelo'].value_counts().head(10), df_intel['cor'].value_counts().head(10)
            modelos_chart = {"labels": df_modelos.index.tolist(), "data": df_modelos.values.tolist()}
            cores_chart = {"labels": df_cores.index.tolist(), "data": df_cores.values.tolist()}
            
            df_apreensoes = df_intel['tipo_apreensao'].dropna().value_counts().head(10)
            apreensoes_chart = {"labels": df_apreensoes.index.tolist(), "data": df_apreensoes.values.tolist()}

        inteligencia_data = {
            "total_viagens": total_viagens, 
            "rotas": rotas_chart, 
            "veiculos_modelos": modelos_chart,
            "veiculos_cores": cores_chart, 
            "apreensoes": apreensoes_chart,
            "sankey": sankey_data,
            "rotas_geograficas": df_rotas.to_dict(orient='records') # Para o mapa de rotas
        }
        
        return jsonify(ida=dados_ida, logistica=logistica_data, inteligencia=inteligencia_data)

    except Exception as e:
        print(f"ERRO em api_analise_dados: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": "Não foi possível gerar os dados de análise."}), 500
    
# --- NOVO: interpretar 1 relato ---
@analise_bp.route('/api/analise_relato', methods=['POST'])
def api_analise_relato():
    data = request.get_json(force=True) or {}
    relato = data.get("relato", "") or ""
    resultado = analyze_text(relato)

    # persiste na tabela 'relato_extracao' (prevista no seu config):contentReference[oaicite:9]{index=9}
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO relato_extracao (relato, classe_risco, pontuacao, top_palavras)
                    VALUES (%s, %s, %s, %s)
                """, (relato, resultado["classe"], resultado["pontuacao"], json.dumps(resultado["keywords"])))
                conn.commit()
    except Exception as e:
        # não trava a API por erro de log
        print("WARN: falha ao salvar em relato_extracao:", e)

    return jsonify(resultado)

# --- NOVO: interpretar um lote de relatos ---
@analise_bp.route('/api/analise_relato/lote', methods=['POST'])
def api_analise_relato_lote():
    data = request.get_json(force=True) or {}
    relatos = data.get("relatos", [])
    resultados = []
    for r in relatos:
        res = analyze_text(r or "")
        resultados.append(res)
    return jsonify({"resultados": resultados})

@analise_bp.route('/api/analise_placa/<string:placa>')
def api_analise_placa(placa):
    try:
        resultado = analisar_placa_json(placa.upper())
        return jsonify(resultado)
    except FileNotFoundError:
        return jsonify({"error": "Modelos de ML não encontrados. Rode 'train_routes.py' e 'train_semantic.py' primeiro."}), 404
    except Exception as e:
        print(f"ERRO em api_analise_placa: {e}")
        return jsonify({"error": "Ocorreu um erro interno ao analisar a placa."}), 500
    
@feedback_bp.route('/feedback', methods=['POST'])
def add_feedback():
    data = request.get_json()
    if not data or 'text' not in data or 'prediction' not in data or 'is_correct' not in data:
        return jsonify({"error": "Dados de feedback inválidos"}), 400

    feedback_entry = {
        "text": data["text"],
        "prediction": data["prediction"],
        "is_correct": data["is_correct"]
    }

    # Define o caminho do arquivo de feedback
    feedback_file = os.path.join('data', 'feedback.csv')

    # Cria o diretório e o arquivo se não existirem
    os.makedirs(os.path.dirname(feedback_file), exist_ok=True)
    file_exists = os.path.isfile(feedback_file)

    try:
        with open(feedback_file, 'a', newline='', encoding='utf-8') as csvfile:
            fieldnames = ['text', 'prediction', 'is_correct']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

            if not file_exists:
                writer.writeheader()

            writer.writerow(feedback_entry)

        return jsonify({"message": "Feedback recebido com sucesso!"}), 201
    except Exception as e:
        return jsonify({"error": f"Erro ao salvar feedback: {e}"}), 500