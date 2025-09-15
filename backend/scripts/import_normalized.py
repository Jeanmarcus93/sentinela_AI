#!/usr/bin/env python3
"""
Script de importação normalizada
- Cria/atualiza veículos na tabela veiculos
- Insere passagens referenciando os veículos
- Atualiza estatísticas automaticamente via triggers
"""

import sys
import pandas as pd
from pathlib import Path
import time
import re
from collections import defaultdict

# Adicionar o diretório backend ao path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from app.models.database import DatabaseConfig, get_db_connection
import psycopg

def fix_coordinate_format(value):
    """Converte coordenadas do formato brasileiro (vírgula) para formato internacional (ponto)"""
    if pd.isna(value) or value == '' or str(value).lower() == 'null':
        return None
    
    str_value = str(value).strip()
    
    if ',' in str_value:
        try:
            fixed_value = str_value.replace(',', '.')
            return float(fixed_value)
        except:
            return None
    
    try:
        return float(str_value)
    except:
        return None

def fix_date_format(value):
    """Converte data do formato brasileiro para formato ISO"""
    if pd.isna(value) or value == '' or str(value).lower() == 'null':
        return None
    
    str_value = str(value).strip()
    
    if '/' in str_value and ',' in str_value:
        try:
            date_part, time_part = str_value.split(', ')
            day, month, year = date_part.split('/')
            iso_format = f"{year}-{month.zfill(2)}-{day.zfill(2)} {time_part}"
            return iso_format
        except:
            return None
    
    return str_value

def extract_vehicle_info(row):
    """Extrai informações do veículo da linha"""
    vehicle_info = {
        'placa': str(row['placa']).strip() if pd.notna(row['placa']) else None
    }
    
    # Tentar extrair marca/modelo de campos disponíveis
    if 'marcaModeloInferidoIA' in row and pd.notna(row['marcaModeloInferidoIA']):
        vehicle_info['marca_modelo'] = str(row['marcaModeloInferidoIA']).strip()
    elif 'tipoInferidoIA' in row and pd.notna(row['tipoInferidoIA']):
        vehicle_info['tipo'] = str(row['tipoInferidoIA']).strip()
    
    return vehicle_info

def extract_passage_info(row, veiculo_id):
    """Extrai informações da passagem da linha"""
    passage_info = {
        'veiculo_id': veiculo_id,
        'dataHoraUTC': fix_date_format(row['dataHoraUTC']),
        'pontoCaptura': str(row['pontoCaptura']).strip() if pd.notna(row['pontoCaptura']) else None,
        'cidade': str(row['cidade']).strip() if pd.notna(row['cidade']) else None,
        'uf': str(row['uf']).strip() if pd.notna(row['uf']) else None,
        'codigoEquipamento': str(row['codigoEquipamento']).strip() if pd.notna(row['codigoEquipamento']) else None,
        'codigoRodovia': str(row['codigoRodovia']).strip() if pd.notna(row['codigoRodovia']) else None,
        'km': fix_coordinate_format(row['km']),
        'faixa': int(float(row['faixa'])) if pd.notna(row['faixa']) else None,
        'sentido': str(row['sentido']).strip() if pd.notna(row['sentido']) else None,
        'velocidade': fix_coordinate_format(row['velocidade']),
        'latitude': fix_coordinate_format(row['latitude']),
        'longitude': fix_coordinate_format(row['longitude']),
        'refImagem1': str(row['refImagem1']).strip() if pd.notna(row['refImagem1']) else None,
        'refImagem2': str(row['refImagem2']).strip() if pd.notna(row['refImagem2']) else None,
        'sistemaOrigem': str(row['sistemaOrigem']).strip() if pd.notna(row['sistemaOrigem']) else None,
        'ehEquipamentoMovel': str(row['ehEquipamentoMovel']).lower() in ['true', '1', 'sim', 'yes'] if pd.notna(row['ehEquipamentoMovel']) else False,
        'ehLeituraHumana': str(row['ehLeituraHumana']).lower() in ['true', '1', 'sim', 'yes'] if pd.notna(row['ehLeituraHumana']) else False,
        'tipoInferidoIA': str(row['tipoInferidoIA']).strip() if pd.notna(row['tipoInferidoIA']) else None,
        'marcaModeloInferidoIA': str(row['marcaModeloInferidoIA']).strip() if pd.notna(row['marcaModeloInferidoIA']) else None
    }
    
    return passage_info

def import_normalized_csv(csv_file):
    """Importa CSV com estrutura normalizada"""
    
    print(f"📥 Importando CSV normalizado: {csv_file}")
    
    if not Path(csv_file).exists():
        print(f"❌ Arquivo não encontrado: {csv_file}")
        return False
    
    file_size = Path(csv_file).stat().st_size / (1024 * 1024)
    print(f"📁 Tamanho do arquivo: {file_size:.2f} MB")
    
    db_config = DatabaseConfig(
        host='localhost',
        port=5432,
        dbname='sentinela_treino',
        user='postgres',
        password='Jmkjmk.00'
    )
    
    try:
        # Ler CSV
        print("📊 Lendo arquivo CSV...")
        df = pd.read_csv(csv_file, low_memory=False)
        print(f"✅ {len(df):,} linhas carregadas")
        
        # Mostrar colunas
        print(f"\n📋 Colunas encontradas:")
        for i, col in enumerate(df.columns, 1):
            print(f"   {i:2d}. {col}")
        
        # Mostrar primeiras linhas
        print(f"\n📊 Primeiras 3 linhas:")
        print(df.head(3).to_string())
        
        # Perguntar se deve continuar
        resposta = input(f"\nDeseja importar {len(df):,} linhas com estrutura normalizada? (s/n): ").lower().strip()
        if resposta not in ['s', 'sim', 'y', 'yes']:
            print("❌ Importação cancelada")
            return False
        
        # Limpar dados existentes
        print("🧹 Limpando dados existentes...")
        with get_db_connection(db_config) as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM passagens")
                cur.execute("DELETE FROM veiculos")
                conn.commit()
                print("✅ Dados limpos!")
        
        # Processar dados em lotes
        print("🔄 Processando dados em lotes...")
        start_time = time.time()
        
        batch_size = 100
        total_vehicles = 0
        total_passages = 0
        total_errors = 0
        
        # Dicionário para armazenar veículos únicos
        vehicles_dict = {}
        
        for batch_start in range(0, len(df), batch_size):
            batch_end = min(batch_start + batch_size, len(df))
            batch_df = df.iloc[batch_start:batch_end]
            
            print(f"📦 Processando lote {batch_start//batch_size + 1} (linhas {batch_start+1}-{batch_end})")
            
            with get_db_connection(db_config) as conn:
                with conn.cursor() as cur:
                    batch_vehicles = 0
                    batch_passages = 0
                    batch_errors = 0
                    
                    for index, row in batch_df.iterrows():
                        try:
                            # Extrair informações do veículo
                            vehicle_info = extract_vehicle_info(row)
                            
                            if not vehicle_info['placa'] or vehicle_info['placa'] == 'nan':
                                batch_errors += 1
                                continue
                            
                            # Verificar se veículo já existe no dicionário
                            placa = vehicle_info['placa']
                            if placa not in vehicles_dict:
                                # Inserir veículo
                                vehicle_columns = list(vehicle_info.keys())
                                vehicle_values = list(vehicle_info.values())
                                vehicle_placeholders = ', '.join(['%s'] * len(vehicle_values))
                                
                                vehicle_sql = f"""
                                    INSERT INTO veiculos ({', '.join(vehicle_columns)})
                                    VALUES ({vehicle_placeholders})
                                    RETURNING id
                                """
                                
                                cur.execute(vehicle_sql, vehicle_values)
                                veiculo_id = cur.fetchone()[0]
                                vehicles_dict[placa] = veiculo_id
                                batch_vehicles += 1
                            else:
                                veiculo_id = vehicles_dict[placa]
                            
                            # Extrair informações da passagem
                            passage_info = extract_passage_info(row, veiculo_id)
                            
                            if not passage_info['dataHoraUTC']:
                                batch_errors += 1
                                continue
                            
                            # Inserir passagem
                            passage_columns = list(passage_info.keys())
                            passage_values = list(passage_info.values())
                            passage_placeholders = ', '.join(['%s'] * len(passage_values))
                            
                            passage_sql = f"""
                                INSERT INTO passagens ({', '.join(passage_columns)})
                                VALUES ({passage_placeholders})
                            """
                            
                            cur.execute(passage_sql, passage_values)
                            batch_passages += 1
                            
                        except Exception as e:
                            batch_errors += 1
                            if batch_errors <= 3:
                                print(f"   ⚠️ Erro na linha {index + 1}: {e}")
                            continue
                    
                    # Commit do lote
                    conn.commit()
                    total_vehicles += batch_vehicles
                    total_passages += batch_passages
                    total_errors += batch_errors
                    
                    print(f"   ✅ Lote: {batch_vehicles} veículos, {batch_passages} passagens, {batch_errors} erros")
        
        total_time = time.time() - start_time
        
        print(f"\n✅ Importação normalizada concluída!")
        print(f"📊 Estatísticas finais:")
        print(f"   🚗 Veículos únicos: {total_vehicles:,}")
        print(f"   📋 Passagens: {total_passages:,}")
        print(f"   ❌ Erros: {total_errors:,}")
        print(f"   📈 Sucesso: {(total_passages/(total_passages+total_errors)*100):.1f}%")
        print(f"   ⏱️ Tempo: {total_time:.1f} segundos")
        print(f"   🚀 Velocidade: {total_passages/total_time:.0f} passagens/segundo")
        
        # Verificar dados no banco
        print(f"\n🔍 Verificando dados no banco...")
        with get_db_connection(db_config) as conn:
            with conn.cursor() as cur:
                # Contar veículos
                cur.execute("SELECT COUNT(*) FROM veiculos")
                vehicles_count = cur.fetchone()[0]
                
                # Contar passagens
                cur.execute("SELECT COUNT(*) FROM passagens")
                passages_count = cur.fetchone()[0]
                
                # Estatísticas dos veículos
                cur.execute("""
                    SELECT 
                        COUNT(*) as total_veiculos,
                        AVG(total_passagens) as media_passagens,
                        MAX(total_passagens) as max_passagens,
                        COUNT(DISTINCT unnest(cidades_visitadas)) as cidades_unicas,
                        COUNT(DISTINCT unnest(ufs_visitadas)) as ufs_unicas
                    FROM veiculos
                """)
                stats = cur.fetchone()
                
                print(f"📊 Dados no banco:")
                print(f"   🚗 Veículos: {vehicles_count:,}")
                print(f"   📋 Passagens: {passages_count:,}")
                print(f"   📈 Média de passagens por veículo: {stats[1]:.1f}")
                print(f"   🏆 Máximo de passagens: {stats[2]}")
                print(f"   🏙️ Cidades únicas visitadas: {stats[3]}")
                print(f"   🗺️ UFs únicas visitadas: {stats[4]}")
                
                # Mostrar alguns veículos com mais passagens
                cur.execute("""
                    SELECT placa, total_passagens, cidades_visitadas, ufs_visitadas
                    FROM veiculos 
                    ORDER BY total_passagens DESC 
                    LIMIT 5
                """)
                top_vehicles = cur.fetchall()
                
                print(f"\n🏆 Top 5 veículos com mais passagens:")
                for i, vehicle in enumerate(top_vehicles, 1):
                    print(f"   {i}. {vehicle[0]} - {vehicle[1]} passagens")
                    print(f"      Cidades: {len(vehicle[2]) if vehicle[2] else 0}, UFs: {len(vehicle[3]) if vehicle[3] else 0}")
        
        return True
                
    except Exception as e:
        print(f"❌ Erro: {e}")
        return False

def main():
    """Função principal"""
    if len(sys.argv) != 2:
        print("Uso: python import_normalized.py <caminho_para_seu_arquivo.csv>")
        print("\nExemplos:")
        print("  python import_normalized.py C:\\Users\\Usuario\\Desktop\\dados.csv")
        print("  python import_normalized.py dados/passagens.csv")
        sys.exit(1)
    
    csv_file = sys.argv[1]
    import_normalized_csv(csv_file)

if __name__ == "__main__":
    main()

