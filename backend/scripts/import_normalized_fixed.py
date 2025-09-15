#!/usr/bin/env python3
"""
Script de importação normalizada corrigido
- Primeiro coleta todos os veículos únicos
- Depois insere as passagens com referência correta
"""

import sys
import pandas as pd
from pathlib import Path
import time
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

def collect_unique_vehicles(df):
    """Coleta informações únicas de veículos do DataFrame"""
    vehicles_dict = {}
    
    print("🔍 Coletando veículos únicos...")
    
    for index, row in df.iterrows():
        placa = str(row['placa']).strip() if pd.notna(row['placa']) else None
        
        if not placa or placa == 'nan':
            continue
        
        if placa not in vehicles_dict:
            vehicle_info = {
                'placa': placa,
                'marca_modelo': str(row['marcaModeloInferidoIA']).strip() if pd.notna(row['marcaModeloInferidoIA']) else None,
                'tipo': str(row['tipoInferidoIA']).strip() if pd.notna(row['tipoInferidoIA']) else None
            }
            
            # Limpar valores vazios
            if vehicle_info['marca_modelo'] == 'nan':
                vehicle_info['marca_modelo'] = None
            if vehicle_info['tipo'] == 'nan':
                vehicle_info['tipo'] = None
                
            vehicles_dict[placa] = vehicle_info
    
    print(f"✅ {len(vehicles_dict):,} veículos únicos encontrados")
    return vehicles_dict

def insert_vehicles(vehicles_dict, db_config):
    """Insere veículos únicos no banco"""
    print("🚗 Inserindo veículos no banco...")
    
    vehicles_inserted = 0
    vehicles_dict_db = {}  # Mapear placa -> id do banco
    
    with get_db_connection(db_config) as conn:
        with conn.cursor() as cur:
            for placa, vehicle_info in vehicles_dict.items():
                try:
                    # Inserir veículo
                    cur.execute("""
                        INSERT INTO veiculos (placa, marca_modelo, tipo)
                        VALUES (%s, %s, %s)
                        RETURNING id
                    """, (vehicle_info['placa'], vehicle_info['marca_modelo'], vehicle_info['tipo']))
                    
                    veiculo_id = cur.fetchone()[0]
                    vehicles_dict_db[placa] = veiculo_id
                    vehicles_inserted += 1
                    
                except Exception as e:
                    # Se já existe, buscar o ID
                    cur.execute("SELECT id FROM veiculos WHERE placa = %s", (placa,))
                    result = cur.fetchone()
                    if result:
                        vehicles_dict_db[placa] = result[0]
                    else:
                        print(f"   ⚠️ Erro ao inserir veículo {placa}: {e}")
            
            conn.commit()
    
    print(f"✅ {vehicles_inserted:,} veículos inseridos")
    return vehicles_dict_db

def insert_passages(df, vehicles_dict_db, db_config):
    """Insere passagens no banco"""
    print("📋 Inserindo passagens no banco...")
    
    batch_size = 1000
    total_passages = 0
    total_errors = 0
    
    for batch_start in range(0, len(df), batch_size):
        batch_end = min(batch_start + batch_size, len(df))
        batch_df = df.iloc[batch_start:batch_end]
        
        print(f"📦 Processando lote {batch_start//batch_size + 1} (linhas {batch_start+1}-{batch_end})")
        
        with get_db_connection(db_config) as conn:
            with conn.cursor() as cur:
                batch_passages = 0
                batch_errors = 0
                
                for index, row in batch_df.iterrows():
                    try:
                        placa = str(row['placa']).strip() if pd.notna(row['placa']) else None
                        
                        if not placa or placa == 'nan':
                            batch_errors += 1
                            continue
                        
                        if placa not in vehicles_dict_db:
                            batch_errors += 1
                            continue
                        
                        veiculo_id = vehicles_dict_db[placa]
                        
                        # Preparar dados da passagem
                        passage_data = {
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
                        
                        # Limpar valores vazios
                        for key, value in passage_data.items():
                            if isinstance(value, str) and value == 'nan':
                                passage_data[key] = None
                        
                        if not passage_data['dataHoraUTC']:
                            batch_errors += 1
                            continue
                        
                        # Inserir passagem
                        cur.execute("""
                            INSERT INTO passagens (
                                veiculo_id, dataHoraUTC, pontoCaptura, cidade, uf,
                                codigoEquipamento, codigoRodovia, km, faixa, sentido,
                                velocidade, latitude, longitude, refImagem1, refImagem2,
                                sistemaOrigem, ehEquipamentoMovel, ehLeituraHumana,
                                tipoInferidoIA, marcaModeloInferidoIA
                            ) VALUES (
                                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                            )
                        """, (
                            passage_data['veiculo_id'], passage_data['dataHoraUTC'], 
                            passage_data['pontoCaptura'], passage_data['cidade'], passage_data['uf'],
                            passage_data['codigoEquipamento'], passage_data['codigoRodovia'], 
                            passage_data['km'], passage_data['faixa'], passage_data['sentido'],
                            passage_data['velocidade'], passage_data['latitude'], passage_data['longitude'],
                            passage_data['refImagem1'], passage_data['refImagem2'], passage_data['sistemaOrigem'],
                            passage_data['ehEquipamentoMovel'], passage_data['ehLeituraHumana'],
                            passage_data['tipoInferidoIA'], passage_data['marcaModeloInferidoIA']
                        ))
                        
                        batch_passages += 1
                        
                    except Exception as e:
                        batch_errors += 1
                        if batch_errors <= 3:
                            print(f"   ⚠️ Erro na linha {index + 1}: {e}")
                        continue
                
                conn.commit()
                total_passages += batch_passages
                total_errors += batch_errors
                
                print(f"   ✅ Lote: {batch_passages} passagens, {batch_errors} erros")
    
    return total_passages, total_errors

def import_normalized_csv_fixed(csv_file):
    """Importa CSV com estrutura normalizada corrigida"""
    
    print(f"📥 Importando CSV normalizado corrigido: {csv_file}")
    
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
        
        # Perguntar se deve continuar
        resposta = input(f"\nDeseja importar {len(df):,} linhas com estrutura normalizada corrigida? (s/n): ").lower().strip()
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
        
        start_time = time.time()
        
        # Passo 1: Coletar veículos únicos
        vehicles_dict = collect_unique_vehicles(df)
        
        # Passo 2: Inserir veículos
        vehicles_dict_db = insert_vehicles(vehicles_dict, db_config)
        
        # Passo 3: Inserir passagens
        total_passages, total_errors = insert_passages(df, vehicles_dict_db, db_config)
        
        total_time = time.time() - start_time
        
        print(f"\n✅ Importação normalizada corrigida concluída!")
        print(f"📊 Estatísticas finais:")
        print(f"   🚗 Veículos únicos: {len(vehicles_dict_db):,}")
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
                        MAX(total_passagens) as max_passagens
                    FROM veiculos
                """)
                stats = cur.fetchone()
                
                print(f"📊 Dados no banco:")
                print(f"   🚗 Veículos: {vehicles_count:,}")
                print(f"   📋 Passagens: {passages_count:,}")
                print(f"   📈 Média de passagens por veículo: {stats[1]:.1f}")
                print(f"   🏆 Máximo de passagens: {stats[2]}")
                
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
                    if vehicle[2]:
                        print(f"      Cidades: {len(vehicle[2])}, UFs: {len(vehicle[3]) if vehicle[3] else 0}")
        
        return True
                
    except Exception as e:
        print(f"❌ Erro: {e}")
        return False

def main():
    """Função principal"""
    if len(sys.argv) != 2:
        print("Uso: python import_normalized_fixed.py <caminho_para_seu_arquivo.csv>")
        print("\nExemplos:")
        print("  python import_normalized_fixed.py C:\\Users\\Usuario\\Desktop\\dados.csv")
        print("  python import_normalized_fixed.py dados/passagens.csv")
        sys.exit(1)
    
    csv_file = sys.argv[1]
    import_normalized_csv_fixed(csv_file)

if __name__ == "__main__":
    main()

