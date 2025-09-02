# server.py
from flask import Flask, jsonify, render_template, request
import pandas as pd
import psycopg
from sqlalchemy import create_engine, text
from datetime import datetime, date
import re
import json

# ================== CONFIGURAÇÃO CENTRAL ==================
DB_CONFIG = {
    "host": "localhost",
    "dbname": "veiculos_db",
    "user": "postgres",
    "password": "Jmkjmk.00"
}
from config import criar_tabelas
app = Flask(__name__)

# --- Funções Auxiliares ---
def get_engine():
    port = DB_CONFIG.get('port', 5432)
    return create_engine(
        f"postgresql+psycopg2://{DB_CONFIG['user']}:{DB_CONFIG['password']}@{DB_CONFIG['host']}:{port}/{DB_CONFIG['dbname']}"
    )

# ================== ROTAS DE API (GET) ==================

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/municipios')
def api_get_municipios():
    """API para buscar a lista de todos os municípios formatados."""
    try:
        with psycopg.connect(**DB_CONFIG) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT nome, uf FROM municipios ORDER BY nome, uf;")
                municipios = [f"{nome} - {uf}" for nome, uf in cur.fetchall()]
        return jsonify(municipios=municipios)
    except Exception as e:
        print(f"ERRO em api_get_municipios: {e}")
        return jsonify({"error": "Não foi possível carregar a lista de municípios."}), 500


@app.route('/api/consulta/<string:placa>')
def api_consulta_veiculo(placa):
    try:
        with psycopg.connect(**DB_CONFIG) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT id FROM veiculos WHERE placa = %s;", (placa.upper(),))
                veiculo_result = cur.fetchone()
                if not veiculo_result:
                    return jsonify({"error": "Placa não encontrada"}), 404
                veiculo_id = veiculo_result[0]

                cur.execute("SELECT * FROM veiculos WHERE id = %s;", (veiculo_id,))
                veiculo_cols = [desc[0] for desc in cur.description]
                veiculo_data = cur.fetchone()
                veiculo = dict(zip(veiculo_cols, veiculo_data)) if veiculo_data else {}

                cur.execute("SELECT * FROM pessoas WHERE veiculo_id = %s ORDER BY nome;", (veiculo_id,))
                pessoas_cols = [desc[0] for desc in cur.description]
                pessoas = [dict(zip(pessoas_cols, row)) for row in cur.fetchall()]

                cur.execute("SELECT * FROM passagens WHERE veiculo_id = %s ORDER BY datahora DESC;", (veiculo_id,))
                passagens_cols = [desc[0] for desc in cur.description]
                passagens = [dict(zip(passagens_cols, row)) for row in cur.fetchall()]

                cur.execute("SELECT * FROM ocorrencias WHERE veiculo_id = %s ORDER BY datahora DESC;", (veiculo_id,))
                ocorrencias_cols = [desc[0] for desc in cur.description]
                ocorrencias = [dict(zip(ocorrencias_cols, row)) for row in cur.fetchall()]

        def serialize_dates(obj):
            if isinstance(obj, (datetime, date)):
                return obj.isoformat()
            return obj

        pessoas = [{k: serialize_dates(v) for k, v in p.items()} for p in pessoas]
        passagens = [{k: serialize_dates(v) for k, v in p.items()} for p in passagens]
        ocorrencias = [{k: serialize_dates(v) for k, v in o.items()} for o in ocorrencias]

        resultado = {
            "veiculo": veiculo, "pessoas": pessoas,
            "passagens": passagens, "ocorrencias": ocorrencias
        }
        return jsonify(resultado)
    except Exception as e:
        print(f"ERRO em api_consulta_veiculo: {e}")
        return jsonify({"error": "Ocorreu um erro interno no servidor."}), 500

@app.route('/api/analise/filtros')
def api_analise_filtros():
    try:
        engine = get_engine()
        with engine.connect() as conn:
            df_locais = pd.read_sql(text("SELECT DISTINCT relato FROM ocorrencias WHERE tipo = 'Local de Entrega' AND relato IS NOT NULL ORDER BY 1;"), conn)
            return jsonify(locais=df_locais['relato'].tolist())
    except Exception as e:
        print(f"ERRO em api_analise_filtros: {e}")
        return jsonify({"error": "Não foi possível carregar os filtros."}), 500

@app.route('/api/analise')
def api_analise_dados():
    locais_selecionados = request.args.getlist('locais')
    engine = get_engine()
    try:
        params = {}
        filtro_sql = ""
        if locais_selecionados:
            query_veiculos_ids = "SELECT DISTINCT veiculo_id FROM ocorrencias WHERE tipo = 'Local de Entrega' AND relato = ANY(%(locais)s);"
            df_veiculos_ids = pd.read_sql(text(query_veiculos_ids), engine, params={"locais": locais_selecionados})
            veiculos_ids = df_veiculos_ids['veiculo_id'].tolist() if not df_veiculos_ids.empty else [-1]
            filtro_sql = "AND veiculo_id = ANY(%(veiculos_ids)s)"
            params['veiculos_ids'] = veiculos_ids

        def get_chart_data(query):
            df = pd.read_sql(text(query), engine, params=params)
            if df.empty:
                return {"municipio": {}, "rodovia": {}, "hora": {}, "dia_semana": {}}
            
            df_mun = df['municipio'].value_counts().head(10)
            df_rodo = df['rodovia'].value_counts().head(10)
            df_hora = df['hora'].astype(int).value_counts().sort_index()
            
            dias_map = {0: "Dom", 1: "Seg", 2: "Ter", 3: "Qua", 4: "Qui", 5: "Sex", 6: "Sáb"}
            df['dia_semana'] = df['dow'].map(dias_map)
            df_dow = df['dia_semana'].value_counts()
            dias_ordem = ["Dom", "Seg", "Ter", "Qua", "Qui", "Sex", "Sáb"]
            df_dow = df_dow.reindex(dias_ordem).dropna()

            return {
                "municipio": {"labels": df_mun.index.tolist(), "data": df_mun.values.tolist()},
                "rodovia": {"labels": df_rodo.index.tolist(), "data": df_rodo.values.tolist()},
                "hora": {"labels": df_hora.index.tolist(), "data": df_hora.values.tolist()},
                "dia_semana": {"labels": df_dow.index.tolist(), "data": df_dow.values.tolist()}
            }

        query_base = "SELECT municipio, rodovia, EXTRACT(HOUR FROM datahora) AS hora, EXTRACT(DOW FROM datahora) AS dow FROM passagens"
        dados_ida = get_chart_data(f"{query_base} WHERE ilicito_ida IS TRUE {filtro_sql}")
        dados_volta = get_chart_data(f"{query_base} WHERE ilicito_volta IS TRUE {filtro_sql}")
        
        return jsonify(ida=dados_ida, volta=dados_volta)

    except Exception as e:
        print(f"ERRO em api_analise_dados: {e}")
        return jsonify({"error": "Não foi possível gerar os dados de análise."}), 500

# ================== ROTAS DE API (POST/PUT/DELETE) ==================

@app.route('/api/ocorrencia', methods=['POST'])
def api_add_ocorrencia():
    data = request.get_json()
    try:
        veiculo_id = data.get('veiculo_id')
        tipo = data.get('tipo')
        datahora_str = data.get('datahora')
        datahora_fim_str = data.get('datahora_fim')
        relato = data.get('relato')
        ocupantes = data.get('ocupantes')

        if not all([veiculo_id, tipo, datahora_str]):
             return jsonify({"error": "Campos obrigatórios faltando."}), 400
        
        if tipo == 'Local de Entrega da Droga' and not relato:
            return jsonify({"error": "A cidade de entrega é obrigatória."}), 400

        datahora = datetime.fromisoformat(datahora_str)
        datahora_fim = datetime.fromisoformat(datahora_fim_str) if datahora_fim_str else None

        with psycopg.connect(**DB_CONFIG) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO ocorrencias (veiculo_id, tipo, datahora, datahora_fim, relato, ocupantes) VALUES (%s, %s, %s, %s, %s, %s)",
                    (veiculo_id, tipo, datahora, datahora_fim, relato, ocupantes)
                )
        return jsonify({"success": True, "message": "Ocorrência adicionada com sucesso."}), 201
    except Exception as e:
        print(f"ERRO em api_add_ocorrencia: {e}")
        return jsonify({"error": "Erro ao inserir ocorrência no banco de dados."}), 500

@app.route('/api/passagem/<int:passagem_id>', methods=['PUT'])
def api_update_passagem(passagem_id):
    data = request.get_json()
    field = data.get('field')
    value = data.get('value')

    if field not in ['ilicito_ida', 'ilicito_volta']:
        return jsonify({"error": "Campo inválido para atualização."}), 400

    try:
        with psycopg.connect(**DB_CONFIG) as conn:
            with conn.cursor() as cur:
                query = f"UPDATE passagens SET {field} = %s WHERE id = %s"
                cur.execute(query, (value, passagem_id))
        return jsonify({"success": True, "message": "Passagem atualizada."})
    except Exception as e:
        print(f"ERRO em api_update_passagem: {e}")
        return jsonify({"error": "Erro ao atualizar passagem."}), 500

@app.route('/api/ocorrencia/<int:ocorrencia_id>', methods=['DELETE'])
def api_delete_ocorrencia(ocorrencia_id):
    try:
        with psycopg.connect(**DB_CONFIG) as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM ocorrencias WHERE id = %s", (ocorrencia_id,))
        return jsonify({"success": True, "message": "Ocorrência excluída."})
    except Exception as e:
        print(f"ERRO em api_delete_ocorrencia: {e}")
        return jsonify({"error": "Erro ao excluir ocorrência."}), 500

@app.route('/api/pessoa/<int:pessoa_id>', methods=['DELETE'])
def api_delete_pessoa(pessoa_id):
    try:
        with psycopg.connect(**DB_CONFIG) as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM pessoas WHERE id = %s", (pessoa_id,))
        return jsonify({"success": True, "message": "Pessoa excluída."})
    except Exception as e:
        print(f"ERRO em api_delete_pessoa: {e}")
        return jsonify({"error": "Erro ao excluir pessoa."}), 500

# ================== INICIALIZAÇÃO ==================

if __name__ == '__main__':
    try:
        criar_tabelas()
        print("Tabelas do banco de dados verificadas/criadas com sucesso.")
    except Exception as e:
        print(f"ERRO ao conectar ao banco ou criar tabelas: {e}")
    app.run(debug=True)

