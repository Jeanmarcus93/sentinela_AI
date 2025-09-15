#!/usr/bin/env python3
"""
Script para importar arquivo CSV completo para o banco sentinela_treino
Otimizado para arquivos grandes com progresso detalhado
"""

import argparse
import csv
import logging
import sys
import time
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

def analyze_csv_file(csv_file):
    """Analisa o arquivo CSV antes da importação"""
    
    logger.info(f"📊 Analisando arquivo: {csv_file}")
    
    try:
        # Verificar tamanho do arquivo
        file_size = Path(csv_file).stat().st_size
        file_size_mb = file_size / (1024 * 1024)
        
        logger.info(f"📁 Tamanho do arquivo: {file_size_mb:.2f} MB")
        
        # Contar linhas sem carregar tudo na memória
        with open(csv_file, 'r', encoding='utf-8') as f:
            total_lines = sum(1 for line in f) - 1  # -1 para cabeçalho
        
        logger.info(f"📋 Total de linhas: {total_lines:,}")
        
        # Ler apenas o cabeçalho e algumas linhas para análise
        df_sample = pd.read_csv(csv_file, nrows=5)
        
        logger.info(f"📝 Colunas encontradas: {len(df_sample.columns)}")
        
        print(f"\n📋 Estrutura do CSV:")
        print("=" * 60)
        for i, col in enumerate(df_sample.columns, 1):
            print(f"{i:2d}. {col}")
        
        print(f"\n📊 Amostra dos dados (primeiras 3 linhas):")
        print("-" * 60)
        print(df_sample.head(3).to_string())
        
        return {
            'total_lines': total_lines,
            'file_size_mb': file_size_mb,
            'columns': df_sample.columns.tolist(),
            'sample_data': df_sample
        }
        
    except Exception as e:
        logger.error(f"❌ Erro ao analisar CSV: {e}")
        return None

def estimate_import_time(total_lines, file_size_mb):
    """Estima o tempo de importação"""
    
    # Estimativa baseada em experiência (linhas por segundo)
    lines_per_second = 1000 if file_size_mb < 100 else 500
    
    estimated_seconds = total_lines / lines_per_second
    estimated_minutes = estimated_seconds / 60
    
    logger.info(f"⏱️ Tempo estimado de importação: {estimated_minutes:.1f} minutos")
    
    return estimated_seconds

def import_csv_chunked(csv_file, batch_size=1000):
    """Importa CSV em chunks para economizar memória"""
    
    logger.info(f"📥 Iniciando importação de: {csv_file}")
    
    db_config = DatabaseConfig(
        host='localhost',
        port=5432,
        dbname='sentinela_treino',
        user='postgres',
        password='Jmkjmk.00'
    )
    
    start_time = time.time()
    
    try:
        imported_rows = 0
        errors = 0
        batch_count = 0
        
        # Ler CSV em chunks
        chunk_iter = pd.read_csv(csv_file, chunksize=batch_size)
        
        with get_db_connection(db_config) as conn:
            with conn.cursor() as cur:
                for chunk in chunk_iter:
                    batch_count += 1
                    batch_start = time.time()
                    
                    logger.info(f"📦 Processando lote {batch_count} ({len(chunk)} linhas)")
                    
                    for index, row in chunk.iterrows():
                        try:
                            # Preparar dados para inserção
                            insert_data = {}
                            
                            # Mapear colunas (ajuste conforme necessário)
                            column_mapping = {
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
                            
                            # Mapear dados automaticamente
                            for csv_col in row.index:
                                csv_col_lower = csv_col.lower().strip()
                                
                                for db_col, possible_names in column_mapping.items():
                                    if csv_col_lower in possible_names:
                                        value = row[csv_col]
                                        
                                        # Tratar valores nulos
                                        if pd.isna(value) or value == '' or str(value).lower() in ['null', 'none']:
                                            insert_data[db_col] = None
                                        else:
                                            insert_data[db_col] = value
                                        break
                            
                            # Inserir dados
                            if insert_data:
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
                            if errors <= 10:  # Mostrar apenas os primeiros 10 erros
                                logger.warning(f"⚠️ Erro na linha {index + 1}: {e}")
                    
                    # Commit do lote
                    conn.commit()
                    
                    batch_time = time.time() - batch_start
                    logger.info(f"✅ Lote {batch_count} concluído em {batch_time:.2f}s")
                    
                    # Mostrar progresso
                    progress = (imported_rows / (imported_rows + errors)) * 100 if (imported_rows + errors) > 0 else 0
                    logger.info(f"📊 Progresso: {imported_rows:,} importadas, {errors} erros ({progress:.1f}% sucesso)")
        
        total_time = time.time() - start_time
        
        logger.info(f"🎉 Importação concluída!")
        logger.info(f"📊 Estatísticas finais:")
        logger.info(f"   ✅ Linhas importadas: {imported_rows:,}")
        logger.info(f"   ❌ Erros: {errors}")
        logger.info(f"   📈 Taxa de sucesso: {(imported_rows/(imported_rows+errors)*100):.1f}%")
        logger.info(f"   ⏱️ Tempo total: {total_time:.1f} segundos")
        logger.info(f"   🚀 Velocidade: {imported_rows/total_time:.0f} linhas/segundo")
        
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
                
                logger.info(f"📊 Total de registros na tabela passagens: {total_count:,}")
                
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
                print(f"   🚗 Placas únicas: {stats['placas_unicas']:,}")
                print(f"   🏙️ Cidades únicas: {stats['cidades_unicas']:,}")
                print(f"   🗺️ UFs únicas: {stats['ufs_unicas']:,}")
                print(f"   📅 Período: {stats['data_mais_antiga']} até {stats['data_mais_recente']}")
                
                # Top 10 cidades com mais passagens
                cur.execute("""
                    SELECT cidade, uf, COUNT(*) as total
                    FROM passagens 
                    WHERE cidade IS NOT NULL
                    GROUP BY cidade, uf 
                    ORDER BY total DESC 
                    LIMIT 10
                """)
                top_cities = cur.fetchall()
                
                print(f"\n🏆 Top 10 cidades com mais passagens:")
                for i, city in enumerate(top_cities, 1):
                    print(f"   {i:2d}. {city['cidade']}/{city['uf']}: {city['total']:,} passagens")
                
                return True
                
    except Exception as e:
        logger.error(f"❌ Erro na verificação: {e}")
        return False

def main():
    """Função principal"""
    parser = argparse.ArgumentParser(description='Importar CSV completo para banco sentinela_treino')
    
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
    
    # Analisar arquivo
    analysis = analyze_csv_file(args.csv_file)
    if not analysis:
        return
    
    if args.analyze_only:
        logger.info("✅ Análise concluída. Use sem --analyze-only para importar.")
        return
    
    # Estimar tempo
    estimate_import_time(analysis['total_lines'], analysis['file_size_mb'])
    
    # Confirmar importação
    print(f"\n⚠️ ATENÇÃO: Você está prestes a importar {analysis['total_lines']:,} linhas!")
    print(f"📁 Arquivo: {args.csv_file}")
    print(f"💾 Tamanho: {analysis['file_size_mb']:.2f} MB")
    print(f"📦 Lote: {args.batch_size} linhas por lote")
    
    resposta = input(f"\nDeseja continuar com a importação? (s/n): ").lower().strip()
    if resposta not in ['s', 'sim', 'y', 'yes']:
        logger.info("❌ Importação cancelada")
        return
    
    # Importar dados
    if import_csv_chunked(args.csv_file, args.batch_size):
        verify_import()
        logger.info("🎉 Importação completa concluída com sucesso!")
    else:
        logger.error("❌ Falha na importação")

if __name__ == "__main__":
    main()

