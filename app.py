# app.py
from flask import Flask
from config import criar_tabelas, atualizar_esquema, finalizar_migracao_apreensoes
from routes import main_bp
from analise import analise_bp
from database import get_db_connection
import json

# Cria a instância da aplicação Flask
app = Flask(__name__)

# Registra os Blueprints (módulos de rotas)
app.register_blueprint(main_bp)
app.register_blueprint(analise_bp)


# --- Bloco de Migração de Dados ---
def migrar_apreensoes_para_tabela_normalizada():
    """Migra dados da coluna JSON 'apreensoes' para a nova tabela normalizada 'apreensoes'."""
    print("Iniciando migração de apreensões para tabela normalizada...")
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                # Verifica se a migração já foi executada para não duplicar dados
                cur.execute("SELECT COUNT(*) FROM apreensoes;")
                if cur.fetchone()[0] > 0:
                    print("A tabela 'apreensoes' já contém dados. A migração não será executada novamente.")
                    return

                # Busca todas as ocorrências que possuem dados de apreensões no formato antigo (JSON)
                cur.execute("SELECT id, apreensoes FROM ocorrencias WHERE apreensoes IS NOT NULL AND apreensoes::text != '[]';")
                ocorrencias = cur.fetchall()

                if not ocorrencias:
                    print("Nenhum dado de apreensão para migrar.")
                    return

                print(f"Encontrados {len(ocorrencias)} ocorrências com dados de apreensões para migrar.")
                
                for occ_id, apreensoes_data in ocorrencias:
                    apreensoes_list = []
                    # O dado pode ser uma string JSON ou já uma lista/dicionário Python
                    if isinstance(apreensoes_data, str):
                        try:
                            apreensoes_list = json.loads(apreensoes_data)
                        except json.JSONDecodeError:
                            print(f"AVISO: Não foi possível decodificar o JSON para a ocorrência ID {occ_id}. Dados: {apreensoes_data}")
                            continue
                    elif isinstance(apreensoes_data, list):
                        apreensoes_list = apreensoes_data

                    for item in apreensoes_list:
                        # Pega os dados do item, com valores padrão para evitar erros
                        tipo = item.get('tipo')
                        # Padroniza 'Armas' para 'Arma' para corresponder ao novo ENUM
                        if tipo == 'Armas':
                            tipo = 'Arma'
                        
                        quantidade = item.get('quantidade')
                        unidade = item.get('unidade')
                        
                        # Validação para garantir que os dados essenciais existem
                        if not all([tipo, quantidade, unidade]):
                            print(f"AVISO: Item de apreensão incompleto para ocorrência ID {occ_id}. Item: {item}")
                            continue
                        
                        # Insere na nova tabela 'apreensoes'
                        cur.execute(
                            """
                            INSERT INTO apreensoes (ocorrencia_id, tipo, quantidade, unidade)
                            VALUES (%s, %s, %s, %s)
                            """,
                            (occ_id, tipo, quantidade, unidade)
                        )
                conn.commit()
                print("Migração de apreensões para a tabela normalizada concluída com sucesso.")

    except Exception as e:
        print(f"Ocorreu um erro CRÍTICO durante a migração de apreensões: {e}")
        print("A migração foi interrompida. Verifique os dados e o erro acima.")


# Bloco de execução principal
if __name__ == '__main__':
    try:
        # 1. Garante que todas as tabelas, tipos e colunas existam
        # A função 'criar_tabelas' já cria a nova tabela 'apreensoes'
        criar_tabelas()
        
        # 2. Garante que a coluna JSON antiga exista para podermos ler os dados dela
        atualizar_esquema()
        
        # 3. Migra os dados do formato JSON antigo para a nova tabela estruturada
        migrar_apreensoes_para_tabela_normalizada()
        
        # 4. ETAPA FINAL (EXECUTAR APENAS UMA VEZ, DEPOIS DE VERIFICAR A MIGRAÇÃO)
        # Após confirmar que os dados estão corretos na nova tabela 'apreensoes',
        # descomente a linha abaixo e rode a aplicação mais uma vez para limpar a coluna antiga.
        # finalizar_migracao_apreensoes()

    except Exception as e:
        print(f"ERRO CRÍTICO ao conectar ao banco ou preparar as tabelas: {e}")
        exit()

    app.run(debug=True)
