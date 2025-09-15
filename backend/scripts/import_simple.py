#!/usr/bin/env python3
"""
Script simples para importar CSV para passagens
"""

import sys
import pandas as pd
from pathlib import Path

# Adicionar o diretório backend ao path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from app.models.database import DatabaseConfig, get_db_connection

def import_csv_simple(csv_file):
    """Importação simples de CSV"""
    
    print(f"📥 Importando: {csv_file}")
    
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
        print(f"✅ {len(df)} linhas carregadas")
        
        # Mostrar colunas
        print(f"\n📋 Colunas encontradas:")
        for i, col in enumerate(df.columns, 1):
            print(f"   {i:2d}. {col}")
        
        # Mostrar primeiras linhas
        print(f"\n📊 Primeiras 3 linhas:")
        print(df.head(3).to_string())
        
        # Perguntar se deve continuar
        resposta = input(f"\nDeseja importar {len(df)} linhas? (s/n): ").lower().strip()
        if resposta not in ['s', 'sim', 'y', 'yes']:
            print("❌ Importação cancelada")
            return
        
        # Importar dados
        print("🔄 Importando dados...")
        
        with get_db_connection(db_config) as conn:
            with conn.cursor() as cur:
                imported = 0
                errors = 0
                
                for index, row in df.iterrows():
                    try:
                        # Mapear dados (ajuste conforme necessário)
                        data = {
                            'dataHoraUTC': row.get('dataHoraUTC', row.get('datahora', row.get('timestamp'))),
                            'placa': row.get('placa', row.get('plate')),
                            'pontoCaptura': row.get('pontoCaptura', row.get('ponto')),
                            'cidade': row.get('cidade', row.get('city')),
                            'uf': row.get('uf', row.get('estado')),
                            'codigoEquipamento': row.get('codigoEquipamento', row.get('equipamento')),
                            'codigoRodovia': row.get('codigoRodovia', row.get('rodovia')),
                            'km': row.get('km', row.get('quilometro')),
                            'faixa': row.get('faixa', row.get('lane')),
                            'sentido': row.get('sentido', row.get('direction')),
                            'velocidade': row.get('velocidade', row.get('speed')),
                            'latitude': row.get('latitude', row.get('lat')),
                            'longitude': row.get('longitude', row.get('lng')),
                            'refImagem1': row.get('refImagem1', row.get('imagem1')),
                            'refImagem2': row.get('refImagem2', row.get('imagem2')),
                            'sistemaOrigem': row.get('sistemaOrigem', row.get('origem')),
                            'ehEquipamentoMovel': row.get('ehEquipamentoMovel', row.get('equipamento_movel')),
                            'ehLeituraHumana': row.get('ehLeituraHumana', row.get('leitura_humana')),
                            'tipoInferidoIA': row.get('tipoInferidoIA', row.get('tipo_ia')),
                            'marcaModeloInferidoIA': row.get('marcaModeloInferidoIA', row.get('marca_modelo_ia'))
                        }
                        
                        # Remover valores nulos
                        data = {k: v for k, v in data.items() if pd.notna(v) and v != ''}
                        
                        # Inserir
                        columns = list(data.keys())
                        values = list(data.values())
                        placeholders = ', '.join(['%s'] * len(values))
                        
                        sql = f"""
                            INSERT INTO passagens ({', '.join(columns)})
                            VALUES ({placeholders})
                        """
                        
                        cur.execute(sql, values)
                        imported += 1
                        
                        if imported % 100 == 0:
                            print(f"   📦 {imported} linhas importadas...")
                            
                    except Exception as e:
                        errors += 1
                        print(f"   ⚠️ Erro na linha {index + 1}: {e}")
                        continue
                
                conn.commit()
                
                print(f"\n✅ Importação concluída!")
                print(f"📊 Estatísticas:")
                print(f"   ✅ Importadas: {imported}")
                print(f"   ❌ Erros: {errors}")
                print(f"   📈 Sucesso: {(imported/(imported+errors)*100):.1f}%")
                
    except Exception as e:
        print(f"❌ Erro: {e}")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Uso: python import_simple.py <arquivo.csv>")
        sys.exit(1)
    
    csv_file = sys.argv[1]
    if not Path(csv_file).exists():
        print(f"❌ Arquivo não encontrado: {csv_file}")
        sys.exit(1)
    
    import_csv_simple(csv_file)

