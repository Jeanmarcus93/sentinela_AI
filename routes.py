# routes.py
from flask import Blueprint, jsonify, render_template, request
from datetime import datetime, date
import re
import json

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
    return obj

# --- Rotas ---
@main_bp.route('/')
def index():
    return render_template('index.html')

@main_bp.route('/api/municipios')
def api_get_municipios():
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT nome, uf FROM municipios ORDER BY nome, uf;")
                municipios = [f"{nome} - {uf}" for nome, uf in cur.fetchall()]
        return jsonify(municipios=municipios)
    except Exception as e:
        print(f"ERRO em api_get_municipios: {e}")
        return jsonify({"error": "Não foi possível carregar a lista de municípios."}), 500

@main_bp.route('/api/consulta_placa/<string:placa>')
def api_consulta_placa(placa):
    try:
        with get_db_connection() as conn:
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

                cur.execute("SELECT p.*, v.placa FROM passagens p JOIN veiculos v ON p.veiculo_id = v.id WHERE p.veiculo_id = %s ORDER BY p.datahora DESC;", (veiculo_id,))
                passagens_cols = [desc[0] for desc in cur.description]
                passagens = [dict(zip(passagens_cols, row)) for row in cur.fetchall()]

                cur.execute("SELECT o.*, v.placa FROM ocorrencias o JOIN veiculos v ON o.veiculo_id = v.id WHERE o.veiculo_id = %s ORDER BY o.datahora DESC;", (veiculo_id,))
                ocorrencias_cols = [desc[0] for desc in cur.description]
                ocorrencias = [dict(zip(ocorrencias_cols, row)) for row in cur.fetchall()]
        
        # Serializa as datas para o formato JSON
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
            with conn.cursor() as cur:
                cur.execute("SELECT id, nome, cpf_cnpj, veiculo_id FROM pessoas WHERE cpf_cnpj = %s;", (cpf_normalizado,))
                pessoas = [dict(zip([c[0] for c in cur.description], row)) for row in cur.fetchall()]
                if not pessoas:
                    return jsonify({"error": "CPF não encontrado."}), 404

                veiculo_ids = list(set([p['veiculo_id'] for p in pessoas]))
                cur.execute("SELECT * FROM veiculos WHERE id = ANY(%s);", (veiculo_ids,))
                veiculos = [dict(zip([c[0] for c in cur.description], row)) for row in cur.fetchall()]
                
                cur.execute("SELECT o.*, v.placa FROM ocorrencias o JOIN veiculos v ON o.veiculo_id = v.id WHERE o.veiculo_id = ANY(%s) ORDER BY o.datahora DESC;", (veiculo_ids,))
                ocorrencias = [dict(zip([c[0] for c in cur.description], row)) for row in cur.fetchall()]

                cur.execute("SELECT p.*, v.placa FROM passagens p JOIN veiculos v ON p.veiculo_id = v.id WHERE p.veiculo_id = ANY(%s) ORDER BY p.datahora DESC;", (veiculo_ids,))
                passagens = [dict(zip([c[0] for c in cur.description], row)) for row in cur.fetchall()]
        
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
        datahora_str = data.get('datahora')
        
        if not all([veiculo_id, tipo, datahora_str]):
            return jsonify({"error": "Campos obrigatórios faltando."}), 400
        
        if tipo == 'Local de Entrega' and not data.get('relato'):
            return jsonify({"error": "A cidade de entrega é obrigatória."}), 400

        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """INSERT INTO ocorrencias (veiculo_id, tipo, datahora, datahora_fim, relato, ocupantes, apreensoes, presos, veiculos) 
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                    (
                        veiculo_id, tipo, data.get('datahora'), data.get('datahora_fim'), data.get('relato'),
                        data.get('ocupantes'), data.get('apreensoes'), data.get('presos'), data.get('veiculos')
                    )
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
        return jsonify({"error": "Erro ao inserir ocorrência."}), 500

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

@main_bp.route('/api/ocorrencia/<int:ocorrencia_id>', methods=['PUT'])
def api_update_ocorrencia(ocorrencia_id):
    data = request.get_json()
    fields_to_update = {k: v for k, v in data.items() if v is not None}
    if not fields_to_update:
        return jsonify({"error": "Nenhum campo para atualizar."}), 400

    update_str = ", ".join([f"{key} = %s" for key in fields_to_update.keys()])
    params = list(fields_to_update.values()) + [ocorrencia_id]
    
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(f"UPDATE ocorrencias SET {update_str} WHERE id = %s", tuple(params))
        return jsonify({"success": True, "message": "Ocorrência atualizada."})
    except Exception as e:
        print(f"ERRO ao atualizar ocorrência: {e}")
        return jsonify({"error": "Erro ao atualizar ocorrência."}), 500