# routes.py
from flask import Blueprint, jsonify, render_template, request
from datetime import datetime, date
import re
import json
from collections import defaultdict
from psycopg.rows import dict_row

from database import get_db_connection

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
    # Adicionado para lidar com Decimals, se houver
    from decimal import Decimal
    if isinstance(obj, Decimal):
        return str(obj)
    return obj

# --- Rotas para renderizar as páginas ---
@main_bp.route('/')
@main_bp.route('/consulta')
def consulta():
    return render_template('consulta.html')

@main_bp.route('/nova_ocorrencia')
def nova_ocorrencia():
    return render_template('nova_ocorrencia.html')

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

def fetch_and_attach_details(cur, ocorrencias):
    """Busca apreensões para uma lista de ocorrências e as anexa."""
    if not ocorrencias:
        return ocorrencias
    
    ocorrencia_ids = [o['id'] for o in ocorrencias]
    # Busca todas as apreensões de uma vez para evitar múltiplas queries
    cur.execute("SELECT ocorrencia_id, tipo, quantidade, unidade FROM apreensoes WHERE ocorrencia_id = ANY(%s);", (ocorrencia_ids,))
    apreensoes_rows = cur.fetchall()
    
    # Agrupa as apreensões por ocorrencia_id
    apreensoes_map = defaultdict(list)
    for row in apreensoes_rows:
        apreensoes_map[row['ocorrencia_id']].append({
            "tipo": row['tipo'],
            "quantidade": str(row['quantidade']), # Converte Decimal para string para JSON
            "unidade": row['unidade']
        })
        
    # Anexa a lista de apreensões a cada ocorrência
    for o in ocorrencias:
        o['apreensoes'] = apreensoes_map.get(o['id'], [])
        
    return ocorrencias

@main_bp.route('/api/consulta_placa/<string:placa>')
def api_consulta_placa(placa):
    try:
        with get_db_connection() as conn:
            # CORREÇÃO: Utiliza o 'dict_row' para que o cursor retorne dicionários
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
        
        # Serializa as datas para o formato JSON
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
            # CORREÇÃO: Utiliza o 'dict_row' para que o cursor retorne dicionários
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
        
        veiculos = [{k: serialize_dates(v) for k, v in veiculo.items()} for veiculo in veiculos]
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
                # Insere a ocorrência principal e obtém o ID
                cur.execute(
                    """INSERT INTO ocorrencias (veiculo_id, tipo, datahora, datahora_fim, relato, ocupantes, presos, veiculos) 
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s) RETURNING id""",
                    (veiculo_id, tipo, data.get('datahora'), data.get('datahora_fim'), data.get('relato'),
                     data.get('ocupantes'), data.get('presos'), data.get('veiculos'))
                )
                ocorrencia_id = cur.fetchone()[0]
                
                # Se for BOP, insere os itens de apreensão na nova tabela
                if tipo == 'BOP' and data.get('apreensoes'):
                    apreensoes_list = json.loads(data.get('apreensoes'))
                    for item in apreensoes_list:
                        cur.execute(
                            "INSERT INTO apreensoes (ocorrencia_id, tipo, quantidade, unidade) VALUES (%s, %s, %s, %s)",
                            (ocorrencia_id, item['tipo'], item['quantidade'], item['unidade'])
                        )
                
                # Lógica para inserir pessoas (presos/ocupantes)
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
                # Atualiza os campos da tabela 'ocorrencias'
                fields_to_update = {k: v for k, v in data.items() if k != 'apreensoes'}
                if fields_to_update:
                    update_str = ", ".join([f"{key} = %s" for key in fields_to_update.keys()])
                    params = list(fields_to_update.values()) + [ocorrencia_id]
                    cur.execute(f"UPDATE ocorrencias SET {update_str} WHERE id = %s", tuple(params))

                # Atualiza os itens de apreensão (delete all e insert all)
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

# O resto das rotas (DELETE, PUT pessoa, PUT passagem) permanece o mesmo...

@main_bp.route('/api/passagem/<int:passagem_id>', methods=['PUT'])
def api_update_passagem(passagem_id):
    # ... (código inalterado)
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
    # ... (código inalterado)
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
    # ... (código inalterado)
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
    # ... (código inalterado)
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
