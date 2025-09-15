#!/usr/bin/env python3
"""
Rotas específicas para o banco sentinela_treino
APIs adaptadas para a estrutura normalizada de veículos e passagens
"""

from flask import Blueprint, jsonify, request
from datetime import datetime, date
import re
import json
from collections import defaultdict
from psycopg.rows import dict_row

# Importar configuração específica do sentinela_treino
from config.sentinela_treino_config import (
    get_sentinela_treino_connection,
    get_sentinela_treino_engine,
    validate_sentinela_treino_connection,
    serialize_dates,
    get_vehicle_stats,
    get_passages_by_vehicle,
    search_vehicles,
    get_analytics_data,
    get_passages_analytics
)

# Criar Blueprint para as rotas do sentinela_treino
sentinela_treino_bp = Blueprint('sentinela_treino_bp', __name__)

# =============================================================================
# ROTAS DE SAÚDE E INFORMAÇÕES
# =============================================================================

@sentinela_treino_bp.route('/api/treino/health')
def api_health():
    """Endpoint de saúde da API do sentinela_treino"""
    try:
        # Testar conexão com banco
        db_status = "ok" if validate_sentinela_treino_connection() else "error"
    except Exception as e:
        db_status = f"error: {str(e)}"
    
    return jsonify({
        "status": "ok" if db_status == "ok" else "degraded",
        "database": db_status,
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0",
        "database_name": "sentinela_treino"
    })

@sentinela_treino_bp.route('/api/treino/info')
def api_info():
    """Informações sobre a API do sentinela_treino"""
    return jsonify({
        "message": "Sentinela IA - Banco de Treino API",
        "version": "1.0.0",
        "database": "sentinela_treino",
        "description": "API para análise de dados de veículos e passagens normalizados",
        "endpoints": {
            "health": "/api/treino/health",
            "info": "/api/treino/info",
            "search_vehicles": "/api/treino/vehicles/search",
            "vehicle_details": "/api/treino/vehicles/<int:vehicle_id>",
            "vehicle_passages": "/api/treino/vehicles/<int:vehicle_id>/passages",
            "analytics": "/api/treino/analytics",
            "passages_analytics": "/api/treino/passages/analytics",
            "municipios": "/api/treino/municipios"
        }
    })

# =============================================================================
# ROTAS DE VEÍCULOS
# =============================================================================

@sentinela_treino_bp.route('/api/treino/vehicles/search')
def api_search_vehicles():
    """Busca veículos por placa ou outros critérios"""
    try:
        search_term = request.args.get('q', '').strip()
        limit = request.args.get('limit', 50, type=int)
        
        if not search_term:
            return jsonify({"error": "Parâmetro de busca 'q' é obrigatório"}), 400
        
        if limit > 100:
            limit = 100
        
        resultado = search_vehicles(search_term, limit)
        
        if resultado is None:
            return jsonify({"error": "Erro interno ao buscar veículos"}), 500
        
        return jsonify(resultado)
        
    except Exception as e:
        print(f"❌ Erro em api_search_vehicles: {e}")
        return jsonify({"error": "Ocorreu um erro interno no servidor."}), 500

@sentinela_treino_bp.route('/api/treino/vehicles/<int:vehicle_id>')
def api_get_vehicle_details(vehicle_id):
    """Retorna detalhes completos de um veículo"""
    try:
        resultado = get_vehicle_stats(vehicle_id)
        
        if resultado is None:
            return jsonify({"error": "Veículo não encontrado"}), 404
        
        return jsonify(resultado)
        
    except Exception as e:
        print(f"❌ Erro em api_get_vehicle_details: {e}")
        return jsonify({"error": "Ocorreu um erro interno no servidor."}), 500

@sentinela_treino_bp.route('/api/treino/vehicles/<int:vehicle_id>/passages')
def api_get_vehicle_passages(vehicle_id):
    """Retorna passagens de um veículo com paginação"""
    try:
        limit = request.args.get('limit', 100, type=int)
        offset = request.args.get('offset', 0, type=int)
        
        if limit > 1000:
            limit = 1000
        
        resultado = get_passages_by_vehicle(vehicle_id, limit, offset)
        
        if resultado is None:
            return jsonify({"error": "Erro interno ao buscar passagens"}), 500
        
        return jsonify(resultado)
        
    except Exception as e:
        print(f"❌ Erro em api_get_vehicle_passages: {e}")
        return jsonify({"error": "Ocorreu um erro interno no servidor."}), 500

# =============================================================================
# ROTAS DE ANÁLISES E ESTATÍSTICAS
# =============================================================================

@sentinela_treino_bp.route('/api/treino/analytics')
def api_get_analytics():
    """Retorna análises gerais do sistema"""
    try:
        resultado = get_analytics_data()
        
        if resultado is None:
            return jsonify({"error": "Erro interno ao buscar análises"}), 500
        
        return jsonify(resultado)
        
    except Exception as e:
        print(f"❌ Erro em api_get_analytics: {e}")
        return jsonify({"error": "Ocorreu um erro interno no servidor."}), 500

@sentinela_treino_bp.route('/api/treino/passages/analytics')
def api_get_passages_analytics():
    """Retorna análises das passagens com filtros"""
    try:
        # Extrair filtros da query string
        filters = {}
        
        cidade = request.args.get('cidade')
        if cidade:
            filters['cidade'] = cidade
        
        uf = request.args.get('uf')
        if uf:
            filters['uf'] = uf
        
        data_inicio = request.args.get('data_inicio')
        if data_inicio:
            filters['data_inicio'] = data_inicio
        
        data_fim = request.args.get('data_fim')
        if data_fim:
            filters['data_fim'] = data_fim
        
        resultado = get_passages_analytics(filters)
        
        if resultado is None:
            return jsonify({"error": "Erro interno ao buscar análises de passagens"}), 500
        
        return jsonify(resultado)
        
    except Exception as e:
        print(f"❌ Erro em api_get_passages_analytics: {e}")
        return jsonify({"error": "Ocorreu um erro interno no servidor."}), 500

# =============================================================================
# ROTAS DE MUNICÍPIOS
# =============================================================================

@sentinela_treino_bp.route('/api/treino/municipios')
def api_get_municipios():
    """Retorna lista de municípios"""
    try:
        with get_sentinela_treino_connection() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute("""
                    SELECT nome, uf, eh_fronteira, eh_suspeito
                    FROM municipios 
                    ORDER BY nome, uf
                """)
                municipios = cur.fetchall()
        
        return jsonify({
            "municipios": serialize_dates(municipios),
            "total": len(municipios)
        })
        
    except Exception as e:
        print(f"❌ Erro em api_get_municipios: {e}")
        return jsonify({"error": "Não foi possível carregar a lista de municípios."}), 500

# =============================================================================
# ROTAS DE CONSULTA POR PLACA (COMPATIBILIDADE)
# =============================================================================

@sentinela_treino_bp.route('/api/treino/consulta_placa/<string:placa>')
def api_consulta_placa_treino(placa):
    """Consulta veículo por placa - versão adaptada para sentinela_treino"""
    try:
        placa_upper = placa.upper().strip()
        
        with get_sentinela_treino_connection() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                # Buscar veículo por placa
                cur.execute("SELECT * FROM veiculos WHERE placa = %s", (placa_upper,))
                veiculo = cur.fetchone()
                
                if not veiculo:
                    return jsonify({"error": "Veículo não encontrado"}), 404
                
                # Buscar passagens recentes
                cur.execute("""
                    SELECT 
                        id, dataHoraUTC, pontoCaptura, cidade, uf,
                        codigoEquipamento, codigoRodovia, km, faixa, sentido,
                        velocidade, latitude, longitude, refImagem1, refImagem2,
                        sistemaOrigem, ehEquipamentoMovel, ehLeituraHumana,
                        tipoInferidoIA, marcaModeloInferidoIA
                    FROM passagens 
                    WHERE veiculo_id = %s
                    ORDER BY dataHoraUTC DESC
                    LIMIT 50
                """, (veiculo['id'],))
                
                passagens = cur.fetchall()
                
                # Buscar estatísticas
                cur.execute("""
                    SELECT 
                        COUNT(*) as total_passagens,
                        MIN(dataHoraUTC) as primeira_passagem,
                        MAX(dataHoraUTC) as ultima_passagem,
                        COUNT(DISTINCT cidade) as cidades_unicas,
                        COUNT(DISTINCT uf) as ufs_unicas,
                        COUNT(DISTINCT codigoRodovia) as rodovias_unicas
                    FROM passagens 
                    WHERE veiculo_id = %s
                """, (veiculo['id'],))
                
                estatisticas = cur.fetchone()
                
                # Buscar top cidades
                cur.execute("""
                    SELECT cidade, uf, COUNT(*) as passagens
                    FROM passagens 
                    WHERE veiculo_id = %s AND cidade IS NOT NULL
                    GROUP BY cidade, uf
                    ORDER BY passagens DESC
                    LIMIT 10
                """, (veiculo['id'],))
                
                top_cidades = cur.fetchall()
        
        # Organizar resposta
        resultado = {
            "veiculo": serialize_dates(veiculo),
            "passagens": serialize_dates(passagens),
            "estatisticas": serialize_dates(estatisticas),
            "top_cidades": serialize_dates(top_cidades),
            "resumo": {
                "placa": veiculo['placa'],
                "total_passagens": estatisticas['total_passagens'],
                "cidades_visitadas": estatisticas['cidades_unicas'],
                "ufs_visitadas": estatisticas['ufs_unicas'],
                "rodovias_utilizadas": estatisticas['rodovias_unicas'],
                "primeira_passagem": estatisticas['primeira_passagem'],
                "ultima_passagem": estatisticas['ultima_passagem'],
                "passagens_recentes": len(passagens)
            }
        }
        
        return jsonify(resultado)
        
    except Exception as e:
        print(f"❌ Erro em api_consulta_placa_treino: {e}")
        return jsonify({"error": "Ocorreu um erro interno no servidor."}), 500

# =============================================================================
# ROTAS DE DASHBOARD E RELATÓRIOS
# =============================================================================

@sentinela_treino_bp.route('/api/treino/dashboard')
def api_get_dashboard():
    """Retorna dados para dashboard principal"""
    try:
        with get_sentinela_treino_connection() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                # Estatísticas gerais
                cur.execute("""
                    SELECT 
                        COUNT(*) as total_veiculos,
                        SUM(total_passagens) as total_passagens,
                        AVG(total_passagens) as media_passagens_por_veiculo,
                        MAX(total_passagens) as max_passagens
                    FROM veiculos
                """)
                
                stats_gerais = cur.fetchone()
                
                # Top 10 veículos com mais passagens
                cur.execute("""
                    SELECT 
                        placa, total_passagens, 
                        primeira_passagem, ultima_passagem,
                        array_length(cidades_visitadas, 1) as total_cidades,
                        array_length(ufs_visitadas, 1) as total_ufs
                    FROM veiculos 
                    ORDER BY total_passagens DESC
                    LIMIT 10
                """)
                
                top_veiculos = cur.fetchall()
                
                # Distribuição por UF
                cur.execute("""
                    SELECT 
                        unnest(ufs_visitadas) as uf,
                        COUNT(*) as veiculos
                    FROM veiculos 
                    WHERE ufs_visitadas IS NOT NULL
                    GROUP BY unnest(ufs_visitadas)
                    ORDER BY veiculos DESC
                    LIMIT 10
                """)
                
                distribuicao_uf = cur.fetchall()
                
                # Passagens por hora do dia
                cur.execute("""
                    SELECT 
                        EXTRACT(HOUR FROM dataHoraUTC) as hora,
                        COUNT(*) as passagens
                    FROM passagens 
                    GROUP BY EXTRACT(HOUR FROM dataHoraUTC)
                    ORDER BY hora
                """)
                
                passagens_por_hora = cur.fetchall()
                
                # Passagens por dia da semana
                cur.execute("""
                    SELECT 
                        EXTRACT(DOW FROM dataHoraUTC) as dia_semana,
                        COUNT(*) as passagens
                    FROM passagens 
                    GROUP BY EXTRACT(DOW FROM dataHoraUTC)
                    ORDER BY dia_semana
                """)
                
                passagens_por_dia = cur.fetchall()
        
        # Mapear dias da semana
        dias_semana = {0: "Dom", 1: "Seg", 2: "Ter", 3: "Qua", 4: "Qui", 5: "Sex", 6: "Sáb"}
        
        resultado = {
            "estatisticas_gerais": serialize_dates(stats_gerais),
            "top_veiculos": serialize_dates(top_veiculos),
            "distribuicao_uf": serialize_dates(distribuicao_uf),
            "passagens_por_hora": serialize_dates(passagens_por_hora),
            "passagens_por_dia": serialize_dates(passagens_por_dia),
            "dias_semana_map": dias_semana,
            "timestamp": datetime.now().isoformat()
        }
        
        return jsonify(resultado)
        
    except Exception as e:
        print(f"❌ Erro em api_get_dashboard: {e}")
        return jsonify({"error": "Ocorreu um erro interno no servidor."}), 500

# =============================================================================
# ROTAS DE EXPORTAÇÃO
# =============================================================================

@sentinela_treino_bp.route('/api/treino/export/vehicles')
def api_export_vehicles():
    """Exporta dados de veículos em formato CSV"""
    try:
        limit = request.args.get('limit', 1000, type=int)
        
        if limit > 10000:
            limit = 10000
        
        with get_sentinela_treino_connection() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute("""
                    SELECT 
                        placa, marca_modelo, tipo, total_passagens,
                        primeira_passagem, ultima_passagem,
                        array_length(cidades_visitadas, 1) as total_cidades,
                        array_length(ufs_visitadas, 1) as total_ufs,
                        array_length(sistemas_origem, 1) as total_sistemas
                    FROM veiculos 
                    ORDER BY total_passagens DESC
                    LIMIT %s
                """, (limit,))
                
                veiculos = cur.fetchall()
        
        # Converter para CSV
        import csv
        import io
        
        output = io.StringIO()
        writer = csv.writer(output)
        
        if veiculos:
            # Cabeçalho
            writer.writerow(veiculos[0].keys())
            
            # Dados
            for veiculo in veiculos:
                writer.writerow(veiculo.values())
        
        output.seek(0)
        
        from flask import Response
        
        return Response(
            output.getvalue(),
            mimetype='text/csv',
            headers={
                'Content-Disposition': f'attachment; filename=veiculos_sentinela_treino_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
            }
        )
        
    except Exception as e:
        print(f"❌ Erro em api_export_vehicles: {e}")
        return jsonify({"error": "Ocorreu um erro interno no servidor."}), 500

@sentinela_treino_bp.route('/api/treino/export/passages/<int:vehicle_id>')
def api_export_vehicle_passages(vehicle_id):
    """Exporta passagens de um veículo específico"""
    try:
        with get_sentinela_treino_connection() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                # Verificar se veículo existe
                cur.execute("SELECT placa FROM veiculos WHERE id = %s", (vehicle_id,))
                veiculo = cur.fetchone()
                
                if not veiculo:
                    return jsonify({"error": "Veículo não encontrado"}), 404
                
                # Buscar passagens
                cur.execute("""
                    SELECT 
                        dataHoraUTC, pontoCaptura, cidade, uf,
                        codigoEquipamento, codigoRodovia, km, faixa, sentido,
                        velocidade, latitude, longitude, sistemaOrigem
                    FROM passagens 
                    WHERE veiculo_id = %s
                    ORDER BY dataHoraUTC DESC
                """, (vehicle_id,))
                
                passagens = cur.fetchall()
        
        # Converter para CSV
        import csv
        import io
        
        output = io.StringIO()
        writer = csv.writer(output)
        
        if passagens:
            # Cabeçalho
            writer.writerow(passagens[0].keys())
            
            # Dados
            for passagem in passagens:
                writer.writerow(passagem.values())
        
        output.seek(0)
        
        from flask import Response
        
        return Response(
            output.getvalue(),
            mimetype='text/csv',
            headers={
                'Content-Disposition': f'attachment; filename=passagens_{veiculo["placa"]}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
            }
        )
        
    except Exception as e:
        print(f"❌ Erro em api_export_vehicle_passages: {e}")
        return jsonify({"error": "Ocorreu um erro interno no servidor."}), 500

print("✅ Sentinela Treino routes module loaded successfully")

