#!/usr/bin/env python3
"""
Script corrigido para importar CSV com tratamento de coordenadas brasileiras
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

def create_table_with_larger_coordinates():
    """Cria a tabela passagens com colunas de coordenadas maiores"""
    
    db_config = DatabaseConfig(
        host='localhost',
        port=5432,
        dbname='sentinela_treino',
        user='postgres',
        password='Jmkjmk.00'
    )
    
    try:
        with get_db_connection(db_config) as conn:
            with conn.cursor() as cur:
                # Dropar tabela se existir
                cur.execute("DROP TABLE IF EXISTS passagens CASCADE")
                
                # Criar tabela com colunas de coordenadas maiores
                cur.execute("""
                CREATE TABLE passagens (
                    id SERIAL PRIMARY KEY,
                    dataHoraUTC TIMESTAMP NOT NULL,
                    placa VARCHAR(10) NOT NULL,
                    pontoCaptura VARCHAR(500),
                    cidade VARCHAR(200),
                    uf VARCHAR(5),
                    codigoEquipamento VARCHAR(200),
                    codigoRodovia VARCHAR(100),
                    km NUMERIC(15,6),
                    faixa INTEGER,
                    sentido VARCHAR(100),
                    velocidade NUMERIC(10,3),
                    latitude NUMERIC(20,15),
                    longitude NUMERIC(20,15),
                    refImagem1 VARCHAR(1000),
                    refImagem2 VARCHAR(1000),
                    sistemaOrigem VARCHAR(200),
                    ehEquipamentoMovel BOOLEAN DEFAULT FALSE,
                    ehLeituraHumana BOOLEAN DEFAULT FALSE,
                    tipoInferidoIA VARCHAR(200),
                    marcaModeloInferidoIA VARCHAR(500),
                    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    atualizado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """)
                
                # Criar índices
                cur.execute("CREATE INDEX idx_passagens_dataHoraUTC ON passagens(dataHoraUTC)")
                cur.execute("CREATE INDEX idx_passagens_placa ON passagens(placa)")
                cur.execute("CREATE INDEX idx_passagens_cidade ON passagens(cidade)")
                cur.execute("CREATE INDEX idx_passagens_uf ON passagens(uf)")
                cur.execute("CREATE INDEX idx_passagens_codigoRodovia ON passagens(codigoRodovia)")
                cur.execute("CREATE INDEX idx_passagens_codigoEquipamento ON passagens(codigoEquipamento)")
                cur.execute("CREATE INDEX idx_passagens_sistemaOrigem ON passagens(sistemaOrigem)")
                cur.execute("CREATE INDEX idx_passagens_placa_data ON passagens(placa, dataHoraUTC)")
                
                conn.commit()
                print("✅ Tabela passagens recriada com colunas maiores!")
                
    except Exception as e:
        print(f"❌ Erro ao criar tabela: {e}")

def import_csv_fixed(csv_file):
    """Importa CSV com tratamento correto de coordenadas"""
    
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
        
        # Recriar tabela com colunas maiores
        print("🔧 Recriando tabela com colunas maiores...")
        create_table_with_larger_coordinates()
        
        # Importar dados
        print("🔄 Importando dados...")
        start_time = time.time()
        
        with get_db_connection(db_config) as conn:
            with conn.cursor() as cur:
                imported = 0
                errors = 0
                
                for index, row in df.iterrows():
                    try:
                        # Mapear dados com tratamento especial
                        data = {}
                        
                        # Tratar data
                        if 'dataHoraUTC' in df.columns:
                            data['dataHoraUTC'] = fix_date_format(row['dataHoraUTC'])
                        
                        # Tratar placa
                        if 'placa' in df.columns:
                            data['placa'] = str(row['placa']).strip() if pd.notna(row['placa']) else None
                        
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
                                if pd.notna(value) and str(value).strip() != '':
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
                            imported += 1
                            
                            if imported % 1000 == 0:
                                print(f"   📦 {imported:,} linhas importadas...")
                        else:
                            errors += 1
                            if errors <= 5:
                                print(f"   ⚠️ Linha {index + 1} ignorada (falta dataHoraUTC ou placa)")
                            
                    except Exception as e:
                        errors += 1
                        if errors <= 5:
                            print(f"   ⚠️ Erro na linha {index + 1}: {e}")
                        continue
                
                conn.commit()
                
                total_time = time.time() - start_time
                
                print(f"\n✅ Importação concluída!")
                print(f"📊 Estatísticas:")
                print(f"   ✅ Importadas: {imported:,}")
                print(f"   ❌ Erros: {errors}")
                print(f"   📈 Sucesso: {(imported/(imported+errors)*100):.1f}%")
                print(f"   ⏱️ Tempo: {total_time:.1f} segundos")
                print(f"   🚀 Velocidade: {imported/total_time:.0f} linhas/segundo")
                
                return True
                
    except Exception as e:
        print(f"❌ Erro: {e}")
        return False

def main():
    """Função principal"""
    if len(sys.argv) != 2:
        print("Uso: python fix_coordinates_and_import.py <caminho_para_seu_arquivo.csv>")
        sys.exit(1)
    
    csv_file = sys.argv[1]
    import_csv_fixed(csv_file)

if __name__ == "__main__":
    main()

