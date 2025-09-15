#!/usr/bin/env python3
"""
Script para importar dados CSV para o banco sentinela_treino
Especificamente para a tabela passagens
"""

import argparse
import csv
import logging
import sys
from pathlib import Path
from datetime import datetime
import pandas as pd

# Adicionar o diretório backend ao path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from app.models.database import DatabaseConfig, get_db_connection
import psycopg
from psycopg.rows import dict_row

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def analyze_csv_structure(csv_file):
    """Analisa a estrutura do arquivo CSV"""
    
    logger.info(f"📊 Analisando arquivo: {csv_file}")
    
    try:
        # Ler apenas as primeiras linhas para análise
        df = pd.read_csv(csv_file, nrows=5)
        
        logger.info(f"✅ Arquivo CSV carregado com sucesso")
        logger.info(f"📋 Colunas encontradas: {len(df.columns)}")
        
        print("\n📋 Estrutura do CSV:")
        print("=" * 50)
        for i, col in enumerate(df.columns, 1):
            print(f"{i:2d}. {col}")
        
        print(f"\n📊 Primeiras 3 linhas:")
        print("-" * 50)
        print(df.head(3).to_string())
        
        return df.columns.tolist()
        
    except Exception as e:
        logger.error(f"❌ Erro ao analisar CSV: {e}")
        return None

def map_csv_to_database(csv_columns):
    """Mapeia colunas do CSV para colunas do banco"""
    
    logger.info("🔗 Mapeando colunas do CSV para o banco")
    
    # Mapeamento esperado (case-insensitive)
    mapping = {
        'dataHoraUTC': ['datahorautc', 'data_hora_utc', 'timestamp', 'datahora'],
        'placa': ['placa', 'plate', 'matricula'],
        'pontoCaptura': ['pontocaptura', 'ponto_captura', 'ponto'],
        'cidade': ['cidade', 'city', 'municipio'],
        'uf': ['uf', 'estado', 'state'],
        'codigoEquipamento': ['codigoequipamento', 'codigo_equipamento', 'equipamento'],
        'codigoRodovia': ['codigorodovia', 'codigo_rodovia', 'rodovia'],
        'km': ['km', 'quilometro', 'quilometragem'],
        'faixa': ['faixa', 'lane'],
        'sentido': ['sentido', 'direction'],
        'velocidade': ['velocidade', 'speed', 'vel'],
        'latitude': ['latitude', 'lat'],
        'longitude': ['longitude', 'lng', 'lon'],
        'refImagem1': ['refimagem1', 'ref_imagem1', 'imagem1'],
        'refImagem2': ['refimagem2', 'ref_imagem2', 'imagem2'],
        'sistemaOrigem': ['sistemaorigem', 'sistema_origem', 'origem'],
        'ehEquipamentoMovel': ['ehequipamentomovel', 'eh_equipamento_movel', 'equipamento_movel'],
        'ehLeituraHumana': ['ehleiturahumana', 'eh_leitura_humana', 'leitura_humana'],
        'tipoInferidoIA': ['tipoinferidoia', 'tipo_inferido_ia', 'tipo_ia'],
        'marcaModeloInferidoIA': ['marcamodeloinferidoia', 'marca_modelo_inferido_ia', 'marca_modelo_ia']
    }
    
    column_mapping = {}
    unmapped_columns = []
    
    for csv_col in csv_columns:
        csv_col_lower = csv_col.lower().strip()
        mapped = False
        
        for db_col, possible_names in mapping.items():
            if csv_col_lower in possible_names:
                column_mapping[csv_col] = db_col
                mapped = True
                break
        
        if not mapped:
            unmapped_columns.append(csv_col)
    
    print("\n🔗 Mapeamento de colunas:")
    print("=" * 50)
    for csv_col, db_col in column_mapping.items():
        print(f"📝 {csv_col:<30} → {db_col}")
    
    if unmapped_columns:
        print(f"\n⚠️ Colunas não mapeadas:")
        for col in unmapped_columns:
            print(f"   ❓ {col}")
    
    return column_mapping, unmapped_columns

def import_csv_data(csv_file, column_mapping, batch_size=1000):
    """Importa dados do CSV para o banco"""
    
    logger.info(f"📥 Iniciando importação de: {csv_file}")
    
    db_config = DatabaseConfig(
        host='localhost',
        port=5432,
        dbname='sentinela_treino',
        user='postgres',
        password='Jmkjmk.00'
    )
    
    try:
        # Ler CSV em chunks para economizar memória
        total_rows = 0
        imported_rows = 0
        errors = 0
        
        # Primeiro, contar total de linhas
        with open(csv_file, 'r', encoding='utf-8') as f:
            total_rows = sum(1 for line in f) - 1  # -1 para cabeçalho
        
        logger.info(f"📊 Total de linhas a importar: {total_rows}")
        
        # Ler CSV em chunks
        chunk_iter = pd.read_csv(csv_file, chunksize=batch_size)
        
        with get_db_connection(db_config) as conn:
            with conn.cursor() as cur:
                for chunk_num, chunk in enumerate(chunk_iter, 1):
                    logger.info(f"📦 Processando chunk {chunk_num} ({len(chunk)} linhas)")
                    
                    for index, row in chunk.iterrows():
                        try:
                            # Preparar dados para inserção
                            insert_data = {}
                            
                            for csv_col, db_col in column_mapping.items():
                                value = row[csv_col]
                                
                                # Tratar valores nulos
                                if pd.isna(value) or value == '' or str(value).lower() == 'null':
                                    insert_data[db_col] = None
                                else:
                                    insert_data[db_col] = value
                            
                            # Inserir dados
                            columns = list(insert_data.keys())
                            values = list(insert_data.values())
                            placeholders = ', '.join(['%s'] * len(values))
                            
                            sql = f"""
                                INSERT INTO passagens ({', '.join(columns)})
                                VALUES ({placeholders})
                            """
                            
                            cur.execute(sql, values)
                            imported_rows += 1
                            
                        except Exception as e:
                            errors += 1
                            logger.warning(f"⚠️ Erro na linha {index + 1}: {e}")
                            continue
                    
                    # Commit a cada chunk
                    conn.commit()
                    logger.info(f"✅ Chunk {chunk_num} importado com sucesso")
        
        logger.info(f"🎉 Importação concluída!")
        logger.info(f"📊 Estatísticas:")
        logger.info(f"   ✅ Linhas importadas: {imported_rows}")
        logger.info(f"   ❌ Erros: {errors}")
        logger.info(f"   📈 Taxa de sucesso: {(imported_rows/(imported_rows+errors)*100):.1f}%")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Erro na importação: {e}")
        return False

def verify_import():
    """Verifica os dados importados"""
    
    logger.info("🔍 Verificando dados importados...")
    
    db_config = DatabaseConfig(
        host='localhost',
        port=5432,
        dbname='sentinela_treino',
        user='postgres',
        password='Jmkjmk.00'
    )
    
    try:
        with get_db_connection(db_config) as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                # Contar registros
                cur.execute("SELECT COUNT(*) as count FROM passagens")
                total_count = cur.fetchone()['count']
                
                logger.info(f"📊 Total de registros na tabela passagens: {total_count}")
                
                # Estatísticas básicas
                cur.execute("""
                    SELECT 
                        COUNT(DISTINCT placa) as placas_unicas,
                        COUNT(DISTINCT cidade) as cidades_unicas,
                        COUNT(DISTINCT uf) as ufs_unicas,
                        MIN(dataHoraUTC) as data_mais_antiga,
                        MAX(dataHoraUTC) as data_mais_recente
                    FROM passagens
                """)
                stats = cur.fetchone()
                
                print(f"\n📈 Estatísticas dos dados:")
                print(f"   🚗 Placas únicas: {stats['placas_unicas']}")
                print(f"   🏙️ Cidades únicas: {stats['cidades_unicas']}")
                print(f"   🗺️ UFs únicas: {stats['ufs_unicas']}")
                print(f"   📅 Período: {stats['data_mais_antiga']} até {stats['data_mais_recente']}")
                
                # Mostrar algumas amostras
                cur.execute("SELECT * FROM passagens ORDER BY dataHoraUTC DESC LIMIT 5")
                samples = cur.fetchall()
                
                print(f"\n📋 Últimas 5 passagens:")
                for sample in samples:
                    print(f"   🚗 {sample['placa']} - {sample['cidade']}/{sample['uf']} - {sample['dataHoraUTC']}")
                
                return True
                
    except Exception as e:
        logger.error(f"❌ Erro na verificação: {e}")
        return False

def main():
    """Função principal"""
    parser = argparse.ArgumentParser(description='Importar CSV para banco sentinela_treino')
    
    parser.add_argument('csv_file', help='Caminho para o arquivo CSV')
    parser.add_argument('--batch-size', type=int, default=1000, help='Tamanho do lote para importação')
    parser.add_argument('--analyze-only', action='store_true', help='Apenas analisar o CSV, não importar')
    parser.add_argument('--verify', action='store_true', help='Apenas verificar dados já importados')
    
    args = parser.parse_args()
    
    if args.verify:
        verify_import()
        return
    
    if not Path(args.csv_file).exists():
        logger.error(f"❌ Arquivo não encontrado: {args.csv_file}")
        return
    
    # Analisar estrutura do CSV
    csv_columns = analyze_csv_structure(args.csv_file)
    if not csv_columns:
        return
    
    # Mapear colunas
    column_mapping, unmapped = map_csv_to_database(csv_columns)
    
    if not column_mapping:
        logger.error("❌ Nenhuma coluna foi mapeada!")
        return
    
    if args.analyze_only:
        logger.info("✅ Análise concluída. Use sem --analyze-only para importar.")
        return
    
    # Confirmar importação
    resposta = input(f"\nDeseja importar {args.csv_file} para o banco? (s/n): ").lower().strip()
    if resposta not in ['s', 'sim', 'y', 'yes']:
        logger.info("❌ Importação cancelada")
        return
    
    # Importar dados
    if import_csv_data(args.csv_file, column_mapping, args.batch_size):
        verify_import()
        logger.info("🎉 Importação concluída com sucesso!")
    else:
        logger.error("❌ Falha na importação")

if __name__ == "__main__":
    main()

