# app.py
from flask import Flask
from config import criar_tabelas
from routes import main_bp
from database import get_db_connection
import json
import os

# Cria a instância da aplicação Flask
app = Flask(__name__)

# Registra o Blueprint principal com todas as rotas
app.register_blueprint(main_bp)

# --- Bloco de Migração de Dados ---
def migrar_apreensoes_para_tabela_normalizada():
    """
    Migra dados da coluna JSON 'apreensoes' para a nova tabela normalizada 'apreensoes'.
    Esta função foi movida para app.py para ser executada durante a inicialização.
    """
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
                    if isinstance(apreensoes_data, str):
                        try:
                            apreensoes_list = json.loads(apreensoes_data)
                        except json.JSONDecodeError:
                            print(f"AVISO: Não foi possível decodificar o JSON para a ocorrência ID {occ_id}. Dados: {apreensoes_data}")
                            continue
                    elif isinstance(apreensoes_data, list):
                        apreensoes_list = apreensoes_data

                    for item in apreensoes_list:
                        tipo = item.get('tipo')
                        if tipo == 'Armas':
                            tipo = 'Arma'
                        
                        quantidade = item.get('quantidade')
                        unidade = item.get('unidade')
                        
                        if not all([tipo, quantidade, unidade]):
                            print(f"AVISO: Item de apreensão incompleto para ocorrência ID {occ_id}. Item: {item}")
                            continue
                        
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
        criar_tabelas()
        migrar_apreensoes_para_tabela_normalizada()
    except Exception as e:
        print(f"Erro ao inicializar o banco de dados ou migrar dados: {e}")

    # Executa a aplicação com o modo de depuração ATIVO, 
    # mas com a reinicialização automática DESATIVADA.
    app.run(debug=True, use_reloader=False)
