# routes.py
from flask import Blueprint, jsonify, render_template, request
from datetime import datetime, date
import re
import json
from collections import defaultdict
from psycopg.rows import dict_row
from app.models.database import get_db_connection, get_engine
from app.services.placa_service import analisar_placa_json
from app.services.semantic_service import analyze_text
from sqlalchemy import text
import pandas as pd
import traceback

# Cria um Blueprint para as rotas principais
main_bp = Blueprint('main_bp', __name__)

# --- Funções Auxiliares ---
def normalizar_cpf(cpf: str) -> str:
    """Remove caracteres não numéricos de um CPF/CNPJ."""
    if not cpf: return None
    return re.sub(r'\D', '', str(cpf))

def serialize_dates(obj):
    """Converte objetos de data/hora para o formato ISO para serialização JSON."""
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    from decimal import Decimal
    if isinstance(obj, Decimal):
        return str(obj)
    return obj

def fetch_and_attach_details(cur, ocorrencias):
    """Busca apreensões para uma lista de ocorrências e as anexa."""
    if not ocorrencias:
        return ocorrencias
    
    ocorrencia_ids = [o['id'] for o in ocorrencias]
    cur.execute("SELECT ocorrencia_id, tipo, quantidade, unidade FROM apreensoes WHERE ocorrencia_id = ANY(%s);", (ocorrencia_ids,))
    apreensoes_rows = cur.fetchall()
    
    apreensoes_map = defaultdict(list)
    for row in apreensoes_rows:
        apreensoes_map[row['ocorrencia_id']].append({
            "tipo": row['tipo'],
            "quantidade": str(row['quantidade']),
            "unidade": row['unidade']
        })
        
    for o in ocorrencias:
        o['apreensoes'] = apreensoes_map.get(o['id'], [])
        
    return ocorrencias


# --- Rotas para renderizar as páginas ---
@main_bp.route('/')
@main_bp.route('/consulta')
def consulta():
    return render_template('consulta.html')

@main_bp.route('/nova_ocorrencia')
def nova_ocorrencia():
    return render_template('nova_ocorrencia.html')

@main_bp.route('/analise')
def analise():
    return render_template('analise.html')

@main_bp.route('/analise_IA')
def analise_IA():
    return render_template('analise_IA.html')

# --- Rotas de API ---
@main_bp.route('/api/municipios')
def api_get_municipios():
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT nome, uf FROM municipios ORDER BY nome, uf;")
                municipios = [f"{nome} - {uf}" for nome, uf in cur.fetchall()]
        return jsonify(municipios=municipios)
    except Exception as e:
        return jsonify({"error": "Não foi possível carregar a lista de municípios."}), 500

@main_bp.route('/api/consulta_placa/<string:placa>')
def api_consulta_placa(placa):
    try:
        with get_db_connection() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute("SELECT id FROM veiculos WHERE placa = %s;", (placa.upper(),))
                veiculo_result = cur.fetchone()
                if not veiculo_result:
                    return jsonify({"error": "Matrícula não encontrada"}), 404
                veiculo_id = veiculo_result['id']

                cur.execute("SELECT * FROM veiculos WHERE id = %s;", (veiculo_id,))
                veiculo = cur.fetchone() or {}

                cur.execute("SELECT * FROM pessoas WHERE veiculo_id = %s ORDER BY nome;", (veiculo_id,))
                pessoas = cur.fetchall()

                cur.execute("SELECT p.*, v.placa FROM passagens p JOIN veiculos v ON p.veiculo_id = v.id WHERE p.veiculo_id = %s ORDER BY p.datahora DESC;", (veiculo_id,))
                passagens = cur.fetchall()

                cur.execute("SELECT o.*, v.placa FROM ocorrencias o JOIN veiculos v ON o.veiculo_id = v.id WHERE o.veiculo_id = %s ORDER BY o.datahora DESC;", (veiculo_id,))
                ocorrencias = cur.fetchall()
                ocorrencias = fetch_and_attach_details(cur, ocorrencias)
        
        veiculo = {k: serialize_dates(v) for k, v in veiculo.items()}
        pessoas = [{k: serialize_dates(v) for k, v in p.items()} for p in pessoas]
        passagens = [{k: serialize_dates(v) for k, v in p.items()} for p in passagens]
        ocorrencias = [{k: serialize_dates(v) for k, v in o.items()} for o in ocorrencias]

        resultado = { "veiculos": [veiculo], "pessoas": pessoas, "passagens": passagens, "ocorrencias": ocorrencias }
        return jsonify(resultado)
    except Exception as e:
        print(f"ERRO em api_consulta_placa: {e}")
        return jsonify({"error": "Ocorreu um erro interno no servidor."}), 500

@main_bp.route('/api/consulta_cpf/<string:cpf>')
def api_consulta_cpf(cpf):
    cpf_normalizado = normalizar_cpf(cpf)
    if not cpf_normalizado:
        return jsonify({"error": "Formato de CPF inválido."}), 400
    try:
        with get_db_connection() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute("SELECT id, nome, cpf_cnpj, veiculo_id FROM pessoas WHERE cpf_cnpj = %s;", (cpf_normalizado,))
                pessoas = cur.fetchall()
                if not pessoas:
                    return jsonify({"error": "CPF não encontrado."}), 404

                veiculo_ids = list(set([p['veiculo_id'] for p in pessoas if p['veiculo_id'] is not None]))
                veiculos = []
                if veiculo_ids:
                    cur.execute("SELECT * FROM veiculos WHERE id = ANY(%s);", (veiculo_ids,))
                    veiculos = cur.fetchall()
                
                ocorrencias, passagens = [], []
                if veiculo_ids:
                    cur.execute("SELECT o.*, v.placa FROM ocorrencias o JOIN veiculos v ON o.veiculo_id = v.id WHERE o.veiculo_id = ANY(%s) ORDER BY o.datahora DESC;", (veiculo_ids,))
                    ocorrencias = cur.fetchall()
                    ocorrencias = fetch_and_attach_details(cur, ocorrencias)

                    cur.execute("SELECT p.*, v.placa FROM passagens p JOIN veiculos v ON p.veiculo_id = v.id WHERE p.veiculo_id = ANY(%s) ORDER BY p.datahora DESC;", (veiculo_ids,))
                    passagens = cur.fetchall()
        
        veiculos = [{k: serialize_dates(v) for k, v in veiculos.items()} for veiculos in veiculos]
        pessoas = [{k: serialize_dates(v) for k, v in p.items()} for p in pessoas]
        passagens = [{k: serialize_dates(v) for k, v in p.items()} for p in passagens]
        ocorrencias = [{k: serialize_dates(v) for k, v in o.items()} for o in ocorrencias]
        
        return jsonify({ "veiculos": veiculos, "pessoas": pessoas, "passagens": passagens, "ocorrencias": ocorrencias })
    except Exception as e:
        print(f"ERRO em api_consulta_cpf: {e}")
        return jsonify({"error": "Ocorreu um erro interno no servidor."}), 500

@main_bp.route('/api/ocorrencia', methods=['POST'])
def api_add_ocorrencia():
    data = request.get_json()
    try:
        veiculo_id = data.get('veiculo_id')
        tipo = data.get('tipo')
        if not all([veiculo_id, tipo, data.get('datahora')]):
            return jsonify({"error": "Campos obrigatórios faltando."}), 400

        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """INSERT INTO ocorrencias (veiculo_id, tipo, datahora, datahora_fim, relato, ocupantes, presos, veiculos) 
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s) RETURNING id""",
                    (veiculo_id, tipo, data.get('datahora'), data.get('datahora_fim'), data.get('relato'),
                     data.get('ocupantes'), data.get('presos'), data.get('veiculos'))
                )
                ocorrencia_id = cur.fetchone()[0]
                
                if tipo == 'BOP' and data.get('apreensoes'):
                    apreensoes_list = json.loads(data.get('apreensoes'))
                    for item in apreensoes_list:
                        cur.execute(
                            "INSERT INTO apreensoes (ocorrencia_id, tipo, quantidade, unidade) VALUES (%s, %s, %s, %s)",
                            (ocorrencia_id, item['tipo'], item['quantidade'], item['unidade'])
                        )
                
                pessoas_json = data.get('ocupantes') if tipo == 'Abordagem' else data.get('presos')
                if pessoas_json:
                    for pessoa in json.loads(pessoas_json):
                        cpf = normalizar_cpf(pessoa.get('cpf_cnpj'))
                        if cpf:
                            cur.execute("""
                                INSERT INTO pessoas (nome, cpf_cnpj, veiculo_id, relevante, condutor, possuidor) VALUES (%s, %s, %s, TRUE, TRUE, TRUE)
                                ON CONFLICT (cpf_cnpj) DO UPDATE SET veiculo_id = EXCLUDED.veiculo_id;
                            """, (pessoa.get('nome'), cpf, veiculo_id))
        return jsonify({"success": True, "message": "Ocorrência adicionada com sucesso."}), 201
    except Exception as e:
        print(f"ERRO em api_add_ocorrencia: {e}")
        return jsonify({"error": f"Erro ao inserir ocorrência: {e}"}), 500

@main_bp.route('/api/ocorrencia/<int:ocorrencia_id>', methods=['PUT'])
def api_update_ocorrencia(ocorrencia_id):
    data = request.get_json()
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                fields_to_update = {k: v for k, v in data.items() if k != 'apreensoes'}
                if fields_to_update:
                    update_str = ", ".join([f"{key} = %s" for key in fields_to_update.keys()])
                    params = list(fields_to_update.values()) + [ocorrencia_id]
                    cur.execute(f"UPDATE ocorrencias SET {update_str} WHERE id = %s", tuple(params))

                if 'apreensoes' in data:
                    cur.execute("DELETE FROM apreensoes WHERE ocorrencia_id = %s", (ocorrencia_id,))
                    apreensoes_list = json.loads(data['apreensoes'])
                    for item in apreensoes_list:
                        cur.execute(
                            "INSERT INTO apreensoes (ocorrencia_id, tipo, quantidade, unidade) VALUES (%s, %s, %s, %s)",
                            (ocorrencia_id, item['tipo'], item['quantidade'], item['unidade'])
                        )
        return jsonify({"success": True, "message": "Ocorrência atualizada."})
    except Exception as e:
        print(f"ERRO ao atualizar ocorrência: {e}")
        return jsonify({"error": "Erro ao atualizar ocorrência."}), 500

@main_bp.route('/api/passagem/<int:passagem_id>', methods=['PUT'])
def api_update_passagem(passagem_id):
    data = request.get_json()
    field = data.get('field')
    if field not in ['ilicito_ida', 'ilicito_volta']:
        return jsonify({"error": "Campo inválido."}), 400
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(f"UPDATE passagens SET {field} = %s WHERE id = %s", (data.get('value'), passagem_id))
        return jsonify({"success": True, "message": "Passagem atualizada."})
    except Exception as e:
        print(f"ERRO em api_update_passagem: {e}")
        return jsonify({"error": "Erro ao atualizar passagem."}), 500

@main_bp.route('/api/ocorrencia/<int:ocorrencia_id>', methods=['DELETE'])
def api_delete_ocorrencia(ocorrencia_id):
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM ocorrencias WHERE id = %s", (ocorrencia_id,))
        return jsonify({"success": True, "message": "Ocorrência excluída."})
    except Exception as e:
        print(f"ERRO em api_delete_ocorrencia: {e}")
        return jsonify({"error": "Erro ao excluir ocorrência."}), 500

@main_bp.route('/api/pessoa/<int:pessoa_id>', methods=['DELETE'])
def api_delete_pessoa(pessoa_id):
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM pessoas WHERE id = %s", (pessoa_id,))
        return jsonify({"success": True, "message": "Pessoa excluída."})
    except Exception as e:
        print(f"ERRO em api_delete_pessoa: {e}")
        return jsonify({"error": "Erro ao excluir pessoa."}), 500
    
@main_bp.route('/api/pessoa/<int:pessoa_id>', methods=['PUT'])
def api_update_pessoa(pessoa_id):
    data = request.get_json()
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("UPDATE pessoas SET nome = %s, cpf_cnpj = %s WHERE id = %s", 
                            (data.get('nome'), normalizar_cpf(data.get('cpf_cnpj')), pessoa_id))
        return jsonify({"success": True, "message": "Pessoa atualizada."})
    except Exception as e:
        print(f"ERRO ao atualizar pessoa: {e}")
        return jsonify({"error": "Erro ao atualizar pessoa."}), 500

@main_bp.route('/api/local_entrega', methods=['POST'])
def api_add_local_entrega():
    """Cria uma ocorrência do tipo Local de Entrega, salvando apenas município (NOME - UF) no relato."""
    data = request.get_json()
    try:
        placa = data.get('placa')
        inicio_iso = data.get('inicio_iso')
        fim_iso = data.get('fim_iso')
        municipio = data.get('municipio')

        if not placa or not inicio_iso or not fim_iso or not municipio:
            return jsonify({"error": "Campos obrigatórios: placa, inicio_iso, fim_iso, municipio"}), 400

        inicio_dt = datetime.fromisoformat(inicio_iso.replace("Z", "+00:00"))
        fim_dt = datetime.fromisoformat(fim_iso.replace("Z", "+00:00"))

        if fim_dt < inicio_dt:
            return jsonify({"error": "Data de fim não pode ser anterior ao início"}), 400

        relato = municipio.strip().upper()

        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT id FROM veiculos WHERE placa = %s;", (placa.upper(),))
                veiculo = cur.fetchone()
                if not veiculo:
                    return jsonify({"error": "Veículo não encontrado"}), 404
                veiculo_id = veiculo[0]

                cur.execute(
                    """INSERT INTO ocorrencias (veiculo_id, tipo, datahora, datahora_fim, relato) 
                       VALUES (%s, %s, %s, %s, %s) RETURNING id""",
                    (veiculo_id, "Local de Entrega", inicio_dt, fim_dt, relato)
                )
                ocorrencia_id = cur.fetchone()[0]

        return jsonify({"success": True, "message": "Local de Entrega registrado.", "id": ocorrencia_id}), 201
    except Exception as e:
        print(f"ERRO em api_add_local_entrega: {e}")
        return jsonify({"error": f"Erro ao registrar Local de Entrega: {e}"}), 500

@main_bp.route('/api/analise_IA', methods=['GET'])
def api_analise_ia():
    placa = request.args.get('placa', '')
    if not placa:
        return jsonify({"error": "Placa é um campo obrigatório para a análise de IA."}), 400
    try:
        resultado = analisar_placa_json(placa.upper())
        return jsonify(resultado)
    except FileNotFoundError as e:
        return jsonify({"error": f"Modelos não encontrados: {e}. Certifique-se de que os modelos de ML foram treinados."}), 404
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": f"Erro interno ao processar a análise: {e}"}), 500

@main_bp.route('/api/analise/filtros')
def api_analise_filtros():
    """Fornece a lista de locais de entrega e tipos de apreensão para preencher os filtros da UI."""
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT DISTINCT relato FROM ocorrencias WHERE tipo = 'Local de Entrega' AND relato IS NOT NULL ORDER BY 1;")
                locais = [row[0] for row in cur.fetchall()]

                cur.execute("SELECT unnest(enum_range(NULL::tipo_apreensao_enum))::text ORDER BY 1;")
                apreensoes = [row[0] for row in cur.fetchall()]

        return jsonify(locais=locais, apreensoes=apreensoes)
    except Exception as e:
        print(f"ERRO em api_analise_filtros: {e}")
        return jsonify({"error": "Não foi possível carregar os filtros."}), 500

@main_bp.route('/api/analise')
def api_analise_dados():
    locais_selecionados = request.args.getlist('locais')
    apreensoes_selecionadas = request.args.getlist('apreensoes')
    placa = request.args.get('placa', None)
    data_inicio = request.args.get('data_inicio', None)
    data_fim = request.args.get('data_fim', None)

    engine = get_engine()

    try:
        params = {}
        subqueries = []

        if locais_selecionados:
            subqueries.append("SELECT DISTINCT veiculo_id FROM ocorrencias WHERE tipo = 'Local de Entrega' AND relato = ANY(:locais)")
            params['locais'] = locais_selecionados

        if apreensoes_selecionadas:
            subqueries.append("SELECT DISTINCT o.veiculo_id FROM ocorrencias o JOIN apreensoes a ON o.id = a.ocorrencia_id WHERE a.tipo::text = ANY(:apreensoes)")
            params['apreensoes'] = apreensoes_selecionadas

        veiculo_id_filter = ""
        if subqueries:
            veiculo_id_filter = f"veiculo_id IN ({ ' INTERSECT '.join(subqueries) })"

        where_clauses = ["1=1"]
        if veiculo_id_filter:
            where_clauses.append(veiculo_id_filter)

        if placa:
            where_clauses.append("veiculo_id = (SELECT id FROM veiculos WHERE placa = :placa)")
            params['placa'] = placa.upper()

        if data_inicio:
            where_clauses.append("datahora >= :data_inicio")
            params['data_inicio'] = data_inicio

        if data_fim:
            where_clauses.append("datahora <= :data_fim_inclusive")
            params['data_fim_inclusive'] = f"{data_fim} 23:59:59"

        base_where_sql = " AND ".join(where_clauses)

        def get_chart_data(table_name, extra_condition=""):
            query = text(f"SELECT municipio, rodovia, EXTRACT(HOUR FROM datahora) AS hora, EXTRACT(DOW FROM datahora) AS dow FROM {table_name} WHERE {base_where_sql} {extra_condition}")
            df = pd.read_sql(query, engine, params=params)
            
            heatmap_data = {}
            if not df.empty:
                dias_map = {0: "Dom", 1: "Seg", 2: "Ter", 3: "Qua", 4: "Qui", 5: "Sex", 6: "Sáb"}
                df['dia_semana'] = df['dow'].map(dias_map)
                
                heatmap_pivot = df.pivot_table(index='dia_semana', columns='hora', aggfunc='size', fill_value=0)
                heatmap_pivot = heatmap_pivot.reindex(list(dias_map.values())).dropna(how='all')
                heatmap_data = {
                    "y": heatmap_pivot.index.tolist(),
                    "x": [str(int(h)) for h in heatmap_pivot.columns],
                    "z": heatmap_pivot.values.tolist()
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
                "pontos_geograficos": df['municipio'].value_counts().to_dict()
            }

        dados_ida = get_chart_data("passagens", "AND ilicito_ida IS TRUE")

        query_lead_time = text(f"SELECT datahora, datahora_fim FROM ocorrencias WHERE tipo = 'Local de Entrega' AND datahora_fim IS NOT NULL AND {base_where_sql}")
        df_lead_time = pd.read_sql(query_lead_time, engine, params=params)
        tempo_medio_horas = 0
        if not df_lead_time.empty:
            df_lead_time['permanencia_horas'] = (df_lead_time['datahora_fim'] - df_lead_time['datahora']).dt.total_seconds() / 3600
            tempo_medio_horas = df_lead_time['permanencia_horas'].mean()
        logistica_data = {"tempo_medio": f"{tempo_medio_horas:.2f}"}

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
        
        sankey_data = {}
        if not df_rotas.empty:
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
            "rotas_geograficas": df_rotas.to_dict(orient='records')
        }
        
        return jsonify(ida=dados_ida, logistica=logistica_data, inteligencia=inteligencia_data)

    except Exception as e:
        print(f"ERRO em api_analise_dados: {e}")
        traceback.print_exc()
        return jsonify({"error": "Não foi possível gerar os dados de análise."}), 500
    
@main_bp.route('/api/analise_relato', methods=['POST'])
def api_analise_relato():
    data = request.get_json(force=True) or {}
    relato = data.get("relato", "") or ""
    resultado = analyze_text(relato)

    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO relato_extracao (relato, classe_risco, pontuacao, top_palavras)
                    VALUES (%s, %s, %s, %s)
                """, (relato, resultado["classe"], resultado["pontuacao"], json.dumps(resultado["keywords"])))
                conn.commit()
    except Exception as e:
        print("WARN: falha ao salvar em relato_extracao:", e)

    return jsonify(resultado)

@main_bp.route('/api/analise_relato/lote', methods=['POST'])
def api_analise_relato_lote():
    data = request.get_json(force=True) or {}
    relatos = data.get("relatos", [])
    resultados = []
    for r in relatos:
        res = analyze_text(r or "")
        resultados.append(res)
    return jsonify({"resultados": resultados})

@main_bp.route('/api/analise_placa/<string:placa>')
def api_analise_placa(placa):
    try:
        resultado = analisar_placa_json(placa.upper())
        return jsonify(resultado)
    except FileNotFoundError:
        return jsonify({"error": "Modelos de ML não encontrados. Rode 'train_routes.py' e 'train_semantic.py' primeiro."}), 404
    except Exception as e:
        print(f"ERRO em api_analise_placa: {e}")
        return jsonify({"error": "Ocorreu um erro interno ao analisar a placa."}), 500
