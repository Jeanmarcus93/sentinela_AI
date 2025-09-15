#!/usr/bin/env python3
"""
Debug de Scores de Análise de Rotas
===================================

Script para debugar os scores de suspeição e entender por que todos
os casos estão sendo classificados como suspeitos.
"""

import psycopg
from pathlib import Path
from collections import defaultdict

# Configuração do banco veiculos_db
DB_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'dbname': 'veiculos_db',
    'user': 'postgres',
    'password': 'Jmkjmk.00'
}

def get_connection():
    """Cria conexão com banco"""
    try:
        return psycopg.connect(**DB_CONFIG)
    except Exception as e:
        print(f"❌ Erro de conexão: {e}")
        return None

def debug_route_scores():
    """Debug dos scores de análise de rotas"""
    print("🔍 DEBUG DE SCORES DE ANÁLISE DE ROTAS")
    print("=" * 50)
    
    conn = get_connection()
    if not conn:
        return
    
    try:
        with conn.cursor() as cur:
            # Buscar algumas ocorrências para debug
            cur.execute("""
                SELECT 
                    o.relato,
                    o.datahora,
                    o.datahora_fim,
                    o.ocupantes,
                    o.presos,
                    o.veiculos,
                    o.id as ocorrencia_id,
                    v.placa,
                    v.marca_modelo,
                    v.tipo,
                    v.ano_modelo,
                    v.cor,
                    v.local_emplacamento,
                    v.transferencia_recente,
                    v.comunicacao_venda,
                    v.crime_prf,
                    v.abordagem_prf
                FROM ocorrencias o
                LEFT JOIN veiculos v ON o.veiculo_id = v.id
                WHERE o.relato IS NOT NULL 
                AND o.relato != '' 
                AND LENGTH(o.relato) > 30
                ORDER BY RANDOM()
                LIMIT 10
            """)
            
            rows = cur.fetchall()
            print(f"📊 Analisando {len(rows)} ocorrências...")
            
            for i, row in enumerate(rows, 1):
                relato, datahora, datahora_fim, ocupantes, presos, veiculos, \
                ocorrencia_id, placa, marca_modelo, tipo, ano_modelo, cor, \
                local_emplacamento, transferencia_recente, comunicacao_venda, \
                crime_prf, abordagem_prf = row
                
                print(f"\n🔍 OCORRÊNCIA {i}:")
                print(f"   ID: {ocorrencia_id}")
                print(f"   Placa: {placa}")
                print(f"   Local Emplacamento: {local_emplacamento}")
                print(f"   Data/Hora: {datahora}")
                print(f"   Crime PRF: {crime_prf}")
                print(f"   Abordagem PRF: {abordagem_prf}")
                print(f"   Transferência Recente: {transferencia_recente}")
                print(f"   Relato: {relato[:100]}...")
                
                # Calcular score manualmente
                score = calculate_debug_score(row)
                print(f"   Score Total: {score:.3f}")
                
                if score > 0.6:
                    print(f"   Classificação: SUSPEITO ✅")
                else:
                    print(f"   Classificação: SEM_ALTERACAO ✅")
    
    except Exception as e:
        print(f"❌ Erro: {e}")
    finally:
        conn.close()

def calculate_debug_score(row):
    """Calcula score de debug"""
    relato, datahora, datahora_fim, ocupantes, presos, veiculos, \
    ocorrencia_id, placa, marca_modelo, tipo, ano_modelo, cor, \
    local_emplacamento, transferencia_recente, comunicacao_venda, \
    crime_prf, abordagem_prf = row
    
    relato_lower = relato.lower()
    score = 0.0
    
    # 1. ANÁLISE DE LOCALIZAÇÃO
    location_score = 0.0
    if local_emplacamento:
        local_lower = local_emplacamento.lower()
        suspicious_routes = {
            'fronteira', 'fronteira brasil', 'fronteira argentina', 'fronteira paraguai',
            'fronteira uruguai', 'fronteira bolívia', 'fronteira colômbia',
            'triângulo das bermudas', 'região do pantanal', 'mato grosso do sul',
            'rio grande do sul', 'santa catarina', 'paraná', 'são paulo',
            'rio de janeiro', 'minas gerais', 'goiás', 'mato grosso',
            'acre', 'rondônia', 'amazonas', 'roraima', 'amapá', 'pará'
        }
        if any(area in local_lower for area in suspicious_routes):
            location_score += 0.3
            print(f"     + Localização suspeita: {local_emplacamento} (+0.3)")
    
    # 2. ANÁLISE DE HORÁRIO
    time_score = 0.0
    if datahora:
        hora_str = str(datahora)
        suspicious_hours = {
            '00:00', '01:00', '02:00', '03:00', '04:00', '05:00',
            '22:00', '23:00', '23:30', '00:30', '01:30', '02:30'
        }
        if any(hora in hora_str for hora in suspicious_hours):
            time_score += 0.2
            print(f"     + Horário suspeito: {datahora} (+0.2)")
    
    # 3. ANÁLISE DE PADRÕES DE IDA E VOLTA
    round_trip_score = 0.0
    round_trip_patterns = {
        'ida e volta', 'ida e retorno', 'ida volta', 'ida retorno',
        'mesmo dia', 'mesmo trajeto', 'trajeto idêntico', 'rota idêntica',
        'frequência alta', 'muitas viagens', 'viagens constantes'
    }
    if any(pattern in relato_lower for pattern in round_trip_patterns):
        round_trip_score += 0.3
        print(f"     + Padrão de ida e volta detectado (+0.3)")
    
    # 4. ANÁLISE DE INDICADORES DE VIAGEM ILÍCITA
    illicit_score = 0.0
    illicit_travel_indicators = {
        'sem destino claro', 'destino incerto', 'sem justificativa',
        'viagem sem motivo', 'sem explicação', 'destino suspeito',
        'rota incomum', 'trajeto estranho', 'caminho suspeito',
        'frequência suspeita', 'padrão estranho', 'comportamento repetitivo'
    }
    if any(indicator in relato_lower for indicator in illicit_travel_indicators):
        illicit_score += 0.2
        print(f"     + Indicador de viagem ilícita detectado (+0.2)")
    
    # 5. ANÁLISE DE ÁREAS DE ALTO RISCO
    risk_area_score = 0.0
    high_risk_areas = {
        'fronteira seca', 'área de risco', 'zona de conflito',
        'região perigosa', 'área suspeita', 'local de risco',
        'ponto de tráfico', 'área de contrabando', 'zona de drogas'
    }
    if any(area in relato_lower for area in high_risk_areas):
        risk_area_score += 0.3
        print(f"     + Área de alto risco detectada (+0.3)")
    
    # 6. ANÁLISE DE INDICADORES ESPECÍFICOS DO VEÍCULO
    vehicle_score = 0.0
    if crime_prf:
        vehicle_score += 0.4
        print(f"     + Histórico de crime PRF (+0.4)")
    if abordagem_prf:
        vehicle_score += 0.2
        print(f"     + Histórico de abordagem PRF (+0.2)")
    if transferencia_recente:
        vehicle_score += 0.1
        print(f"     + Transferência recente (+0.1)")
    
    # Score final
    total_score = location_score + time_score + round_trip_score + illicit_score + risk_area_score + vehicle_score
    
    print(f"     Scores: Local={location_score:.1f}, Hora={time_score:.1f}, IdaVolta={round_trip_score:.1f}, Ilícita={illicit_score:.1f}, Risco={risk_area_score:.1f}, Veículo={vehicle_score:.1f}")
    
    return total_score

if __name__ == "__main__":
    debug_route_scores()

