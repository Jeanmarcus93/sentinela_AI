#!/usr/bin/env python3
"""
Script simples para importar seu arquivo CSV
"""

import sys
import pandas as pd
from pathlib import Path
import time

# Adicionar o diretório backend ao path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from app.models.database import DatabaseConfig, get_db_connection

def import_my_csv(csv_file):
    """Importa seu arquivo CSV"""
    
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
        # Ler CSV
        print("📊 Lendo arquivo CSV...")
        df = pd.read_csv(csv_file)
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
        
        # Importar dados
        print("🔄 Importando dados...")
        start_time = time.time()
        
        with get_db_connection(db_config) as conn:
            with conn.cursor() as cur:
                imported = 0
                errors = 0
                
                for index, row in df.iterrows():
                    try:
                        # Mapear dados automaticamente
                        data = {}
                        
                        # Mapeamento inteligente de colunas
                        for col in df.columns:
                            col_lower = col.lower().strip()
                            value = row[col]
                            
                            # Pular valores nulos
                            if pd.isna(value) or value == '' or str(value).lower() == 'null':
                                continue
                            
                            # Mapear colunas
                            if col_lower in ['datahorautc', 'data_hora_utc', 'timestamp', 'datahora']:
                                data['dataHoraUTC'] = value
                            elif col_lower in ['placa', 'plate', 'matricula']:
                                data['placa'] = value
                            elif col_lower in ['pontocaptura', 'ponto_captura', 'ponto']:
                                data['pontoCaptura'] = value
                            elif col_lower in ['cidade', 'city', 'municipio']:
                                data['cidade'] = value
                            elif col_lower in ['uf', 'estado', 'state']:
                                data['uf'] = value
                            elif col_lower in ['codigoequipamento', 'codigo_equipamento', 'equipamento']:
                                data['codigoEquipamento'] = value
                            elif col_lower in ['codigorodovia', 'codigo_rodovia', 'rodovia']:
                                data['codigoRodovia'] = value
                            elif col_lower in ['km', 'quilometro', 'quilometragem']:
                                data['km'] = value
                            elif col_lower in ['faixa', 'lane']:
                                data['faixa'] = value
                            elif col_lower in ['sentido', 'direction']:
                                data['sentido'] = value
                            elif col_lower in ['velocidade', 'speed', 'vel']:
                                data['velocidade'] = value
                            elif col_lower in ['latitude', 'lat']:
                                data['latitude'] = value
                            elif col_lower in ['longitude', 'lng', 'lon']:
                                data['longitude'] = value
                            elif col_lower in ['refimagem1', 'ref_imagem1', 'imagem1']:
                                data['refImagem1'] = value
                            elif col_lower in ['refimagem2', 'ref_imagem2', 'imagem2']:
                                data['refImagem2'] = value
                            elif col_lower in ['sistemaorigem', 'sistema_origem', 'origem']:
                                data['sistemaOrigem'] = value
                            elif col_lower in ['ehequipamentomovel', 'eh_equipamento_movel', 'equipamento_movel']:
                                data['ehEquipamentoMovel'] = value
                            elif col_lower in ['ehleiturahumana', 'eh_leitura_humana', 'leitura_humana']:
                                data['ehLeituraHumana'] = value
                            elif col_lower in ['tipoinferidoia', 'tipo_inferido_ia', 'tipo_ia']:
                                data['tipoInferidoIA'] = value
                            elif col_lower in ['marcamodeloinferidoia', 'marca_modelo_inferido_ia', 'marca_modelo_ia']:
                                data['marcaModeloInferidoIA'] = value
                        
                        # Inserir apenas se tiver dados essenciais
                        if 'dataHoraUTC' in data and 'placa' in data:
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
        print("Uso: python import_my_csv.py <caminho_para_seu_arquivo.csv>")
        print("\nExemplos:")
        print("  python import_my_csv.py C:\\Users\\Usuario\\Desktop\\dados.csv")
        print("  python import_my_csv.py dados/passagens.csv")
        print("  python import_my_csv.py \"C:\\Users\\Usuario\\Documents\\arquivo com espaços.csv\"")
        sys.exit(1)
    
    csv_file = sys.argv[1]
    import_my_csv(csv_file)

if __name__ == "__main__":
    main()

