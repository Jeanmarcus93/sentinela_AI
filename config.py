import psycopg
import pandas as pd
import os

DB_CONFIG = {
    "host": "localhost",
    "dbname": "veiculos_db",
    "user": "postgres",
    "password": "Jmkjmk.00"
}

def criar_tabelas():
    """Cria/atualiza todas as tabelas e popula a de municípios se estiver vazia."""
    with psycopg.connect(**DB_CONFIG) as conn:
        with conn.cursor() as cur:
            # Tabela veículos
            cur.execute("""
                CREATE TABLE IF NOT EXISTS veiculos (
                    id SERIAL PRIMARY KEY, placa TEXT UNIQUE NOT NULL, marca_modelo TEXT, tipo TEXT,
                    ano_modelo TEXT, cor TEXT, local_emplacamento TEXT, transferencia_recente BOOLEAN,
                    comunicacao_venda BOOLEAN, crime_prf BOOLEAN, abordagem_prf BOOLEAN
                );
            """)

            # Tabela pessoas
            cur.execute("""
                CREATE TABLE IF NOT EXISTS pessoas (
                    id SERIAL PRIMARY KEY, veiculo_id INTEGER REFERENCES veiculos(id) ON DELETE CASCADE,
                    nome TEXT, cpf_cnpj TEXT UNIQUE, cnh TEXT, validade_cnh DATE, local_cnh TEXT,
                    suspeito BOOLEAN, relevante BOOLEAN, proprietario BOOLEAN, condutor BOOLEAN, possuidor BOOLEAN
                );
            """)

            # Tabela passagens
            cur.execute("""
                CREATE TABLE IF NOT EXISTS passagens (
                    id SERIAL PRIMARY KEY, veiculo_id INTEGER REFERENCES veiculos(id) ON DELETE CASCADE,
                    estado TEXT, municipio TEXT, rodovia TEXT, datahora TIMESTAMP, ilicito_ida BOOLEAN DEFAULT FALSE,
                    ilicito_volta BOOLEAN DEFAULT FALSE, ilicito_local_entrega TEXT
                );
            """)

            # Tabela ocorrências
            cur.execute("""
                CREATE TABLE IF NOT EXISTS ocorrencias (
                    id SERIAL PRIMARY KEY, veiculo_id INTEGER REFERENCES veiculos(id) ON DELETE CASCADE,
                    tipo TEXT NOT NULL CHECK (tipo IN ('Local de Entrega', 'Abordagem', 'BOP')),
                    datahora TIMESTAMP NOT NULL, relato TEXT, ocupantes TEXT, presos TEXT,
                    apreensoes TEXT, veiculos TEXT
                );
            """)
            cur.execute("ALTER TABLE ocorrencias ADD COLUMN IF NOT EXISTS datahora_fim TIMESTAMP;")

            # Nova tabela de municípios
            cur.execute("""
                CREATE TABLE IF NOT EXISTS municipios (
                    id SERIAL PRIMARY KEY,
                    nome TEXT NOT NULL,
                    uf VARCHAR(2) NOT NULL,
                    UNIQUE (nome, uf)
                );
            """)

            # Popular tabela de municípios a partir do CSV
            cur.execute("SELECT 1 FROM municipios LIMIT 1;")
            if cur.fetchone() is None:
                caminho_csv = 'municipios (1).csv'
                print(f"\nTentando popular a tabela 'municipios' a partir de '{caminho_csv}'...")
                
                if not os.path.exists(caminho_csv):
                    print(f"ERRO CRÍTICO: O arquivo '{caminho_csv}' não foi encontrado no diretório do projeto.")
                    print("Por favor, verifique se o arquivo está na pasta correta e tente novamente.")
                else:
                    print("Arquivo CSV encontrado. Tentando carregar os dados...")
                    df = None
                    try:
                        # LÓGICA CORRIGIDA: Pula o cabeçalho original e nomeia as colunas diretamente
                        df = pd.read_csv(
                            caminho_csv, 
                            sep=';', 
                            encoding='utf-8', 
                            header=None,      # Trata o arquivo como se não tivesse cabeçalho
                            skiprows=1,       # Pula a primeira linha (que é o cabeçalho real)
                            names=['nome', 'uf']  # Nomeia as colunas
                        )
                        print("Arquivo lido com sucesso usando encoding UTF-8.")
                    except UnicodeDecodeError:
                        print("Falha ao ler com UTF-8. Tentando com Latin-1...")
                        try:
                            df = pd.read_csv(
                                caminho_csv, 
                                sep=';', 
                                encoding='latin-1',
                                header=None,
                                skiprows=1,
                                names=['nome', 'uf']
                            )
                            print("Arquivo lido com sucesso usando encoding Latin-1.")
                        except Exception as e:
                            print(f"ERRO: Falha ao ler o arquivo CSV com ambos os encodings. Erro: {e}")
                    except Exception as e:
                        print(f"ERRO inesperado ao ler o arquivo CSV: {e}")

                    if df is not None and not df.empty:
                        try:
                            df['nome'] = df['nome'].str.strip()
                            df['uf'] = df['uf'].str.strip()
                            df.dropna(inplace=True)
                            
                            data_to_insert = list(df.itertuples(index=False, name=None))
                            
                            if data_to_insert:
                                print(f"Preparando para inserir {len(data_to_insert)} registros...")
                                cur.executemany(
                                    "INSERT INTO municipios (nome, uf) VALUES (%s, %s) ON CONFLICT (nome, uf) DO NOTHING",
                                    data_to_insert
                                )
                                print(f"SUCESSO: {cur.rowcount} novos municípios foram inseridos na tabela.")
                            else:
                                print("AVISO: Nenhum dado válido para inserir foi encontrado no CSV após a limpeza.")
                        except Exception as e:
                            print(f"ERRO ao processar os dados do DataFrame ou inserir no banco: {e}")

        conn.commit()

