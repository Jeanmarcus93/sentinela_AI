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

def normalizar_cpf(cpf: str) -> str:
    """Remove caracteres não numéricos de um CPF/CNPJ."""
    if not cpf: return None
    return re.sub(r'\D', '', str(cpf))

# ================== ROTAS DE API (GET) ==================

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/municipios')
def api_get_municipios():
    try:
        with psycopg.connect(**DB_CONFIG) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT nome, uf FROM municipios ORDER BY nome, uf;")
                municipios = [f"{nome} - {uf}" for nome, uf in cur.fetchall()]
        return jsonify(municipios=municipios)
    except Exception as e:
        print(f"ERRO em api_get_municipios: {e}")
        return jsonify({"error": "Não foi possível carregar a lista de municípios."}), 500

@app.route('/api/consulta_placa/<string:placa>')
def api_consulta_placa(placa):
    try:
        with psycopg.connect(**DB_CONFIG) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT id FROM veiculos WHERE placa = %s;", (placa.upper(),))
                veiculo_result = cur.fetchone()
                if not veiculo_result:
                    return jsonify({"error": "Matrícula não encontrada"}), 404
                veiculo_id = veiculo_result[0]

                cur.execute("SELECT * FROM veiculos WHERE id = %s;", (veiculo_id,))
                veiculo_cols = [desc[0] for desc in cur.description]
                veiculo_data = cur.fetchone()
                veiculo = dict(zip(veiculo_cols, veiculo_data)) if veiculo_data else {}

                cur.execute("SELECT * FROM pessoas WHERE veiculo_id = %s ORDER BY nome;", (veiculo_id,))
                pessoas_cols = [desc[0] for desc in cur.description]
                pessoas = [dict(zip(pessoas_cols, row)) for row in cur.fetchall()]

                # Ajuste para incluir a placa nas passagens
                cur.execute("SELECT p.*, v.placa FROM passagens p JOIN veiculos v ON p.veiculo_id = v.id WHERE p.veiculo_id = %s ORDER BY p.datahora DESC;", (veiculo_id,))
                passagens_cols = [desc[0] for desc in cur.description]
                passagens = [dict(zip(passagens_cols, row)) for row in cur.fetchall()]

                # Ajuste para incluir a placa nas ocorrências
                cur.execute("SELECT o.*, v.placa FROM ocorrencias o JOIN veiculos v ON o.veiculo_id = v.id WHERE o.veiculo_id = %s ORDER BY o.datahora DESC;", (veiculo_id,))
                ocorrencias_cols = [desc[0] for desc in cur.description]
                ocorrencias = [dict(zip(ocorrencias_cols, row)) for row in cur.fetchall()]

        def serialize_dates(obj):
            if isinstance(obj, (datetime, date)):
                return obj.isoformat()
            return obj

        pessoas = [{k: serialize_dates(v) for k, v in p.items()} for p in pessoas]
        passagens = [{k: serialize_dates(v) for k, v in p.items()} for p in passagens]
        ocorrencias = [{k: serialize_dates(v) for k, v in o.items()} for o in ocorrencias]

        resultado = { "veiculos": [veiculo], "pessoas": pessoas, "passagens": passagens, "ocorrencias": ocorrencias }
        return jsonify(resultado)
    except Exception as e:
        print(f"ERRO em api_consulta_placa: {e}")
        return jsonify({"error": "Ocorreu um erro interno no servidor."}), 500

@app.route('/api/consulta_cpf/<string:cpf>')
def api_consulta_cpf(cpf):
    cpf_normalizado = normalizar_cpf(cpf)
    if not cpf_normalizado:
        return jsonify({"error": "Formato de CPF inválido."}), 400
        
    try:
        with psycopg.connect(**DB_CONFIG) as conn:
            with conn.cursor() as cur:
                # --- CORREÇÃO AQUI ---
                # A função REGEXP_REPLACE remove todos os caracteres não numéricos ('\D') da coluna cpf_cnpj antes da comparação
                query = "SELECT id, nome, cpf_cnpj, veiculo_id FROM pessoas WHERE cpf_cnpj = %s;"
                cur.execute(query, (cpf_normalizado,))
                pessoas_encontradas = cur.fetchall()
                
                if not pessoas_encontradas:
                    return jsonify({"error": "CPF não encontrado."}), 404

                pessoas_cols = [desc[0] for desc in cur.description]
                pessoas = [dict(zip(pessoas_cols, row)) for row in pessoas_encontradas]
                veiculo_ids = list(set([p['veiculo_id'] for p in pessoas]))

                cur.execute("SELECT * FROM veiculos WHERE id = ANY(%s);", (veiculo_ids,))
                veiculos_cols = [desc[0] for desc in cur.description]
                veiculos = [dict(zip(veiculos_cols, row)) for row in cur.fetchall()]

                cur.execute("SELECT o.*, v.placa FROM ocorrencias o JOIN veiculos v ON o.veiculo_id = v.id WHERE o.veiculo_id = ANY(%s) ORDER BY o.datahora DESC;", (veiculo_ids,))
                ocorrencias_cols = [desc[0] for desc in cur.description]
                ocorrencias = [dict(zip(ocorrencias_cols, row)) for row in cur.fetchall()]

                cur.execute("SELECT p.*, v.placa FROM passagens p JOIN veiculos v ON p.veiculo_id = v.id WHERE p.veiculo_id = ANY(%s) ORDER BY p.datahora DESC;", (veiculo_ids,))
                passagens_cols = [desc[0] for desc in cur.description]
                passagens = [dict(zip(passagens_cols, row)) for row in cur.fetchall()]
        
        def serialize_dates(obj):
            if isinstance(obj, (datetime, date)):
                return obj.isoformat()
            return obj

        pessoas = [{k: serialize_dates(v) for k, v in p.items()} for p in pessoas]
        passagens = [{k: serialize_dates(v) for k, v in p.items()} for p in passagens]
        ocorrencias = [{k: serialize_dates(v) for k, v in o.items()} for o in ocorrencias]
        
        resultado = { "veiculos": veiculos, "pessoas": pessoas, "passagens": passagens, "ocorrencias": ocorrencias }
        return jsonify(resultado)

    except Exception as e:
        print(f"ERRO em api_consulta_cpf: {e}")
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
    placa = request.args.get('placa', None)
    engine = get_engine()
    
    try:
        params = {}
        where_clauses = ["1=1"]

        if locais_selecionados:
            where_clauses.append("veiculo_id IN (SELECT DISTINCT veiculo_id FROM ocorrencias WHERE tipo = 'Local de Entrega' AND relato = ANY(:locais))")
            params['locais'] = locais_selecionados

        if placa:
            with psycopg.connect(**DB_CONFIG) as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT id FROM veiculos WHERE placa = %s;", (placa.upper(),))
                    veiculo_result = cur.fetchone()
                    if veiculo_result:
                        where_clauses.append("veiculo_id = :placa_veiculo_id")
                        params['placa_veiculo_id'] = veiculo_result[0]
                    else:
                        where_clauses.append("1=0")

        base_where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"

        def get_chart_data(table_name, extra_condition=""):
            query = f"""
                SELECT municipio, rodovia, EXTRACT(HOUR FROM datahora) AS hora, EXTRACT(DOW FROM datahora) AS dow 
                FROM {table_name} 
                WHERE {base_where_sql} {extra_condition}
            """
            df = pd.read_sql(text(query), engine, params=params)
            if df.empty:
                return {"municipio": {}, "rodovia": {}, "hora": {}, "dia_semana": {}}
            
            df_mun = df['municipio'].value_counts().head(10)
            df_rodo = df['rodovia'].value_counts().head(10)
            df_hora = df['hora'].astype(int).value_counts().sort_index()
            
            dias_map = {0: "Dom", 1: "Seg", 2: "Ter", 3: "Qua", 4: "Qui", 5: "Sex", 6: "Sáb"}
            df['dia_semana'] = df['dow'].map(dias_map)
            df_dow = df['dia_semana'].value_counts().reindex(["Dom", "Seg", "Ter", "Qua", "Qui", "Sex", "Sáb"]).dropna()

            return {
                "municipio": {"labels": df_mun.index.tolist(), "data": df_mun.values.tolist()},
                "rodovia": {"labels": df_rodo.index.tolist(), "data": df_rodo.values.tolist()},
                "hora": {"labels": df_hora.index.tolist(), "data": df_hora.values.tolist()},
                "dia_semana": {"labels": df_dow.index.tolist(), "data": df_dow.values.tolist()}
            }

        dados_ida = get_chart_data("passagens", "AND ilicito_ida IS TRUE")
        dados_volta = get_chart_data("passagens", "AND ilicito_volta IS TRUE")
        
        logistica_data = {}
        if locais_selecionados or placa:
            query_lead_time = f"SELECT datahora, datahora_fim FROM ocorrencias WHERE tipo = 'Local de Entrega' AND datahora_fim IS NOT NULL AND {base_where_sql}"
            df_lead_time = pd.read_sql(text(query_lead_time), engine, params=params)
            
            tempo_medio_horas = 0
            if not df_lead_time.empty:
                df_lead_time['permanencia_horas'] = (df_lead_time['datahora_fim'] - df_lead_time['datahora']).dt.total_seconds() / 3600
                tempo_medio_horas = df_lead_time['permanencia_horas'].mean()

            rotas_where_sql = base_where_sql.replace('veiculo_id', 'p.veiculo_id')
            query_rotas = f"""
                SELECT DISTINCT ON (p.veiculo_id) p.municipio AS municipio_partida
                FROM passagens p
                WHERE p.ilicito_ida IS TRUE AND {rotas_where_sql}
                ORDER BY p.veiculo_id, p.datahora ASC;
            """
            df_rotas = pd.read_sql(text(query_rotas), engine, params=params)
            
            partidas_chart = {}
            if not df_rotas.empty:
                df_partidas = df_rotas['municipio_partida'].value_counts().head(10)
                partidas_chart = {"labels": df_partidas.index.tolist(), "data": df_partidas.values.tolist()}

            logistica_data = {
                "tempo_medio": f"{tempo_medio_horas:.2f}",
                "partidas": partidas_chart
            }
        
        return jsonify(ida=dados_ida, volta=dados_volta, logistica=logistica_data)

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
        ocupantes_json = data.get('ocupantes')
        # Novos campos adicionados
        apreensoes_json = data.get('apreensoes')
        presos_json = data.get('presos')
        veiculos_json = data.get('veiculos')

        if not all([veiculo_id, tipo, datahora_str]):
             return jsonify({"error": "Campos obrigatórios faltando."}), 400
        
        if tipo == 'Local de Entrega' and not relato:
            return jsonify({"error": "A cidade de entrega é obrigatória."}), 400

        datahora = datetime.fromisoformat(datahora_str)
        datahora_fim = datetime.fromisoformat(datahora_fim_str) if datahora_fim_str else None
        
        # Ocupantes/Presos são tratados separadamente para a tabela 'pessoas'
        pessoas_list = []
        if tipo == 'Abordagem' and ocupantes_json:
            try:
                pessoas_list = json.loads(ocupantes_json)
            except json.JSONDecodeError:
                return jsonify({"error": "Formato de ocupantes inválido."}), 400
        elif tipo == 'BOP' and presos_json:
            try:
                pessoas_list = json.loads(presos_json)
            except json.JSONDecodeError:
                return jsonify({"error": "Formato de presos inválido."}), 400

        with psycopg.connect(**DB_CONFIG) as conn:
            with conn.cursor() as cur:
                # 1. Inserir a ocorrência na tabela 'ocorrencias'
                cur.execute(
                    "INSERT INTO ocorrencias (veiculo_id, tipo, datahora, datahora_fim, relato, ocupantes, apreensoes, presos, veiculos) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)",
                    (veiculo_id, tipo, datahora, datahora_fim, relato, ocupantes_json, apreensoes_json, presos_json, veiculos_json)
                )

                # 2. Inserir cada pessoa na tabela 'pessoas' (ocupantes ou presos)
                if pessoas_list:
                    for pessoa in pessoas_list:
                        cpf_normalizado = normalizar_cpf(pessoa.get('cpf_cnpj'))
                        if not cpf_normalizado:
                            continue
                        
                        cur.execute("""
                            INSERT INTO pessoas (nome, cpf_cnpj, veiculo_id, relevante, condutor, possuidor)
                            VALUES (%s, %s, %s, TRUE, TRUE, TRUE)
                            ON CONFLICT (cpf_cnpj) DO UPDATE SET veiculo_id = EXCLUDED.veiculo_id;
                        """, (pessoa.get('nome'), cpf_normalizado, veiculo_id))
            conn.commit()

        return jsonify({"success": True, "message": "Ocorrência e ocupantes/presos adicionados com sucesso."}), 201
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
    
@app.route('/api/pessoa/<int:pessoa_id>', methods=['PUT'])
def api_update_pessoa(pessoa_id):
    """Atualiza os dados de uma pessoa."""
    data = request.get_json()
    nome = data.get('nome')
    cpf_cnpj = data.get('cpf_cnpj')

    try:
        with psycopg.connect(**DB_CONFIG) as conn:
            with conn.cursor() as cur:
                # Verificando se os campos existem e atualizando apenas os que foram enviados
                updates = []
                params = []

                if nome is not None:
                    updates.append("nome = %s")
                    params.append(nome)

                if cpf_cnpj is not None:
                    updates.append("cpf_cnpj = %s")
                    params.append(normalizar_cpf(cpf_cnpj))
                
                if not updates:
                    return jsonify({"error": "Nenhum campo para atualizar."}), 400

                query = f"UPDATE pessoas SET {', '.join(updates)} WHERE id = %s"
                params.append(pessoa_id)
                
                cur.execute(query, tuple(params))
                conn.commit()

        return jsonify({"success": True, "message": "Pessoa atualizada com sucesso."}), 200
    except Exception as e:
        print(f"ERRO ao atualizar pessoa: {e}")
        return jsonify({"error": "Erro interno ao atualizar pessoa."}), 500

@app.route('/api/ocorrencia/<int:ocorrencia_id>', methods=['PUT'])
def api_update_ocorrencia(ocorrencia_id):
    """Atualiza os dados de uma ocorrência."""
    data = request.get_json()
    
    # Obter todos os dados do request
    datahora_str = data.get('datahora')
    datahora_fim_str = data.get('datahora_fim')
    relato = data.get('relato')
    apreensoes = data.get('apreensoes')
    presos = data.get('presos')
    veiculos = data.get('veiculos')

    try:
        # Converter strings para objetos datetime
        datahora = datetime.fromisoformat(datahora_str) if datahora_str else None
        datahora_fim = datetime.fromisoformat(datahora_fim_str) if datahora_fim_str else None
    except (ValueError, TypeError):
        return jsonify({"error": "Formato de data/hora inválido."}), 400
    
    try:
        with psycopg.connect(**DB_CONFIG) as conn:
            with conn.cursor() as cur:
                # Montar a query de atualização dinamicamente
                updates = []
                params = []

                # Adiciona os campos à query apenas se eles foram enviados no request
                if datahora is not None:
                    updates.append("datahora = %s")
                    params.append(datahora)
                
                # A datahora_fim pode ser None, então a incluímos se for fornecida
                if 'datahora_fim' in data:
                    updates.append("datahora_fim = %s")
                    params.append(datahora_fim)

                if relato is not None:
                    updates.append("relato = %s")
                    params.append(relato)

                if apreensoes is not None:
                    updates.append("apreensoes = %s")
                    params.append(apreensoes)

                if presos is not None:
                    updates.append("presos = %s")
                    params.append(presos)

                if veiculos is not None:
                    updates.append("veiculos = %s")
                    params.append(veiculos)

                if not updates:
                    return jsonify({"error": "Nenhum campo para atualizar."}), 400
                
                # Junta tudo na query final
                query = f"UPDATE ocorrencias SET {', '.join(updates)} WHERE id = %s"
                params.append(ocorrencia_id)

                cur.execute(query, tuple(params))
            conn.commit()

        return jsonify({"success": True, "message": "Ocorrência atualizada com sucesso."}), 200
    except Exception as e:
        print(f"ERRO ao atualizar ocorrência: {e}")
        return jsonify({"error": "Erro interno ao atualizar ocorrência."}), 500

# ================== INICIALIZAÇÃO ==================

if __name__ == '__main__':
    try:
        criar_tabelas()
        print("Tabelas do banco de dados verificadas/criadas com sucesso.")
    except Exception as e:
        print(f"ERRO ao conectar ao banco ou criar tabelas: {e}")
    app.run(debug=True)
