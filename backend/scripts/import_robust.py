#!/usr/bin/env python3
"""
Script robusto para importar CSV com tratamento correto de dados
"""

import sys
import pandas as pd
from pathlib import Path
import time
import re

# Adicionar o diretório backend ao path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from app.models.database import DatabaseConfig, get_db_connection
import psycopg

def fix_coordinate_format(value):
    """Converte coordenadas do formato brasileiro (vírgula) para formato internacional (ponto)"""
    if pd.isna(value) or value == '' or str(value).lower() == 'null':
        return None
    
    # Converter para string
    str_value = str(value).strip()
    
    # Se já tem ponto, retornar como está
    if '.' in str_value and ',' not in str_value:
        try:
            return float(str_value)
        except:
            return None
    
    # Se tem vírgula, substituir por ponto
    if ',' in str_value:
        try:
            # Substituir vírgula por ponto
            fixed_value = str_value.replace(',', '.')
            return float(fixed_value)
        except:
            return None
    
    # Tentar converter diretamente
    try:
        return float(str_value)
    except:
        return None

def fix_date_format(value):
    """Converte data do formato brasileiro para formato ISO"""
    if pd.isna(value) or value == '' or str(value).lower() == 'null':
        return None
    
    str_value = str(value).strip()
    
    # Formato: DD/MM/YYYY, HH:MM:SS
    if '/' in str_value and ',' in str_value:
        try:
            # Separar data e hora
            date_part, time_part = str_value.split(', ')
            day, month, year = date_part.split('/')
            
            # Reorganizar para YYYY-MM-DD HH:MM:SS
            iso_format = f"{year}-{month.zfill(2)}-{day.zfill(2)} {time_part}"
            return iso_format
        except:
            return None
    
    return str_value

def import_csv_robust(csv_file):
    """Importa CSV de forma robusta com commits frequentes"""
    
    print(f"📥 Importando: {csv_file}")
    
    # Verificar se arquivo existe
    if not Path(csv_file).exists():
        print(f"❌ Arquivo não encontrado: {csv_file}")
        return False
    
    # Verificar tamanho
    file_size = Path(csv_file).stat().st_size / (1024 * 1024)
    print(f"📁 Tamanho do arquivo: {file_size:.2f} MB")
    
    # Configuração do banco
    db_config = DatabaseConfig(
        host='localhost',
        port=5432,
        dbname='sentinela_treino',
        user='postgres',
        password='Jmkjmk.00'
    )
    
    try:
        # Ler CSV com configurações especiais
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
        resposta = input(f"\nDeseja importar {len(df):,} linhas? (s/n): ").lower().strip()
        if resposta not in ['s', 'sim', 'y', 'yes']:
            print("❌ Importação cancelada")
            return False
        
        # Limpar tabela existente
        print("🧹 Limpando tabela existente...")
        with get_db_connection(db_config) as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM passagens")
                conn.commit()
                print("✅ Tabela limpa!")
        
        # Importar dados em lotes pequenos
        print("🔄 Importando dados em lotes...")
        start_time = time.time()
        
        batch_size = 100  # Lotes pequenos para garantir commits
        total_imported = 0
        total_errors = 0
        
        for batch_start in range(0, len(df), batch_size):
            batch_end = min(batch_start + batch_size, len(df))
            batch_df = df.iloc[batch_start:batch_end]
            
            print(f"📦 Processando lote {batch_start//batch_size + 1} (linhas {batch_start+1}-{batch_end})")
            
            with get_db_connection(db_config) as conn:
                with conn.cursor() as cur:
                    batch_imported = 0
                    batch_errors = 0
                    
                    for index, row in batch_df.iterrows():
                        try:
                            # Mapear dados com tratamento especial
                            data = {}
                            
                            # Tratar data
                            if 'dataHoraUTC' in df.columns:
                                data['dataHoraUTC'] = fix_date_format(row['dataHoraUTC'])
                            
                            # Tratar placa
                            if 'placa' in df.columns:
                                placa_val = str(row['placa']).strip() if pd.notna(row['placa']) else None
                                if placa_val and placa_val != 'nan' and placa_val != '':
                                    data['placa'] = placa_val
                            
                            # Tratar coordenadas com vírgula
                            if 'latitude' in df.columns:
                                data['latitude'] = fix_coordinate_format(row['latitude'])
                            
                            if 'longitude' in df.columns:
                                data['longitude'] = fix_coordinate_format(row['longitude'])
                            
                            # Tratar outros campos numéricos
                            if 'km' in df.columns:
                                data['km'] = fix_coordinate_format(row['km'])
                            
                            if 'velocidade' in df.columns:
                                data['velocidade'] = fix_coordinate_format(row['velocidade'])
                            
                            if 'faixa' in df.columns:
                                faixa_val = row['faixa']
                                if pd.notna(faixa_val):
                                    try:
                                        data['faixa'] = int(float(faixa_val))
                                    except:
                                        data['faixa'] = None
                            
                            # Tratar outros campos de texto
                            text_fields = [
                                'pontoCaptura', 'cidade', 'uf', 'codigoEquipamento', 
                                'codigoRodovia', 'sentido', 'refImagem1', 'refImagem2',
                                'sistemaOrigem', 'tipoInferidoIA', 'marcaModeloInferidoIA'
                            ]
                            
                            for field in text_fields:
                                if field in df.columns:
                                    value = row[field]
                                    if pd.notna(value) and str(value).strip() != '' and str(value).strip() != 'nan':
                                        data[field] = str(value).strip()
                            
                            # Tratar campos booleanos
                            bool_fields = ['ehEquipamentoMovel', 'ehLeituraHumana']
                            for field in bool_fields:
                                if field in df.columns:
                                    value = row[field]
                                    if pd.notna(value):
                                        if str(value).lower() in ['true', '1', 'sim', 'yes']:
                                            data[field] = True
                                        elif str(value).lower() in ['false', '0', 'não', 'no']:
                                            data[field] = False
                            
                            # Inserir apenas se tiver dados essenciais
                            if 'dataHoraUTC' in data and 'placa' in data and data['dataHoraUTC'] and data['placa']:
                                columns = list(data.keys())
                                values = list(data.values())
                                placeholders = ', '.join(['%s'] * len(values))
                                
                                sql = f"""
                                    INSERT INTO passagens ({', '.join(columns)})
                                    VALUES ({placeholders})
                                """
                                
                                cur.execute(sql, values)
                                batch_imported += 1
                            else:
                                batch_errors += 1
                                
                        except Exception as e:
                            batch_errors += 1
                            if batch_errors <= 3:  # Mostrar apenas os primeiros 3 erros por lote
                                print(f"   ⚠️ Erro na linha {index + 1}: {e}")
                            continue
                    
                    # Commit do lote
                    conn.commit()
                    total_imported += batch_imported
                    total_errors += batch_errors
                    
                    print(f"   ✅ Lote importado: {batch_imported} sucessos, {batch_errors} erros")
        
        total_time = time.time() - start_time
        
        print(f"\n✅ Importação concluída!")
        print(f"📊 Estatísticas finais:")
        print(f"   ✅ Importadas: {total_imported:,}")
        print(f"   ❌ Erros: {total_errors:,}")
        print(f"   📈 Sucesso: {(total_imported/(total_imported+total_errors)*100):.1f}%")
        print(f"   ⏱️ Tempo: {total_time:.1f} segundos")
        print(f"   🚀 Velocidade: {total_imported/total_time:.0f} linhas/segundo")
        
        # Verificar se os dados foram realmente inseridos
        print(f"\n🔍 Verificando dados no banco...")
        with get_db_connection(db_config) as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute("SELECT COUNT(*) as count FROM passagens")
                count = cur.fetchone()['count']
                print(f"📊 Registros no banco: {count:,}")
                
                if count > 0:
                    cur.execute("SELECT placa, cidade, uf, dataHoraUTC FROM passagens ORDER BY dataHoraUTC DESC LIMIT 3")
                    samples = cur.fetchall()
                    print(f"📋 Últimas 3 passagens:")
                    for i, sample in enumerate(samples, 1):
                        print(f"   {i}. {sample['placa']} - {sample['cidade']}/{sample['uf']} - {sample['dataHoraUTC']}")
        
        return True
                
    except Exception as e:
        print(f"❌ Erro: {e}")
        return False

def main():
    """Função principal"""
    if len(sys.argv) != 2:
        print("Uso: python import_robust.py <caminho_para_seu_arquivo.csv>")
        sys.exit(1)
    
    csv_file = sys.argv[1]
    import_csv_robust(csv_file)

if __name__ == "__main__":
    main()

