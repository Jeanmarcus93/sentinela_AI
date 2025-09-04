import psycopg
import random
from datetime import datetime, timedelta
from faker import Faker
import sys
import os

# Garante que o script encontre os outros arquivos do projeto
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from database import DB_CONFIG
from config import criar_tabelas # IMPORTANTE: Importa a função de criar tabelas

# Inicializa o Faker para gerar dados fictícios em português
fake = Faker('pt_BR')

# --- CONFIGURAÇÕES FINAIS ---
NUM_SUSPEITO = 2000
NUM_SEM_ALTERACAO = 3000 

def buscar_veiculos(cursor):
    """Busca uma lista de IDs de veículos existentes no banco."""
    cursor.execute("SELECT id FROM veiculos ORDER BY RANDOM() LIMIT 100;")
    veiculos = cursor.fetchall()
    if not veiculos:
        print("AVISO: Nenhum veículo encontrado. Crie alguns veículos primeiro.")
        return []
    return [v[0] for v in veiculos]

def gerar_relato_dinamico(categoria: str) -> str:
    """
    Gera um relato único e dinâmico, com foco em ensinar o contexto ao modelo.
    """
    if categoria == "SUSPEITO":
        partes = {
            "observacao_inicial": [
                "Veículo abordado após realizar manobra perigosa.", "Carro com vidros escuros em atitude suspeita.",
                "Abordagem em veículo vindo da fronteira.", "Ocupantes demonstraram nervosismo ao avistar a viatura.",
                "Denúncia anônima informou sobre um carro com essas características.", "Motorista tentou evadir-se da fiscalização."
            ],
            "comportamento": [
                "o condutor ficou extremamente nervoso", "o motorista mentiu sobre o destino da viagem",
                "os ocupantes entraram em contradição", "o abordado não soube explicar a origem do dinheiro",
                "o passageiro manteve a mão na cintura o tempo todo", "o motorista apresentou comportamento agressivo"
            ],
            "detalhe_suspeito": [
                f"foi encontrado cerca de R$ {random.randint(5, 20)*500} em espécie.", "a história contada não tinha coerência.",
                "havia um forte odor de maconha no interior do veículo.", "foi localizada uma caixa de munições no porta-luvas.",
                "a documentação do veículo apresentava sinais de adulteração.", "a viagem não tinha justificativa plausível."
            ],
            "conclusao": [
                "Relato de entrevista ruim.", "Situação de alta suspeição.", "Encaminhado para verificação detalhada.",
                "Comportamento altamente suspeito apesar de nada ilícito ter sido encontrado."
            ]
        }
        
        relato = f"{random.choice(partes['observacao_inicial'])} Durante a entrevista, {random.choice(partes['comportamento'])} e {random.choice(partes['detalhe_suspeito'])} {random.choice(partes['conclusao'])}"
        return relato

    elif categoria == "SEM_ALTERACAO":
        pistas_falsas = [
            f"Veículo parado em local ermo de madrugada. O condutor explicou que é fotógrafo e estava a registar a via láctea. Equipamento compatível (câmara, tripé) no porta-malas. Documentação em ordem.",
            f"Abordagem a veículo com matrícula de {fake.state_abbr()}. O condutor, nervoso no início, explicou que era a sua primeira vez a conduzir na autoestrada. Documentos e teste de álcool em conformidade.",
            f"Denúncia de atitude suspeita. Na abordagem, constatou-se que o motorista era um detetive privado em vigilância, devidamente identificado e com autorização.",
            f"Motorista a conduzir de forma errática. Após a paragem, verificou-se que era um pai a tentar acalmar um bebé que chorava no banco de trás. Orientado a parar em segurança.",
            f"Carro de luxo com condutor de aparência simples. Na verificação, constatou-se que era o motorista particular do proprietário, a caminho de o ir buscar ao aeroporto. Contacto com o proprietário confirmou a história."
        ]
        
        normais = [
            f"Abordagem de rotina na BR-116. O condutor era um(a) {fake.job()} que viajava a trabalho. Documentação do veículo e do condutor em dia.",
            f"Fiscalização de rotina em frente ao posto da PRF. Tratava-se de uma família voltando de férias. Nenhuma irregularidade foi encontrada.",
            f"Veículo parado para verificação de documentos. O motorista estava indo visitar parentes em {fake.city()}. Após a verificação, o veículo foi liberado.",
            f"Atendimento a um veículo com problemas mecânicos. O condutor foi apenas orientado sobre segurança no trânsito.",
            f"Veículo de uma empresa de entregas. A carga do caminhão estava de acordo com a nota fiscal."
        ]
        
        return random.choice(pistas_falsas * 2 + normais)

    return ""


def inserir_ocorrencias(conn, veiculos_ids):
    """Gera e insere os dados no banco de dados usando o gerador dinâmico."""
    
    with conn.cursor() as cur:
        print(f"Gerando {NUM_SUSPEITO} ocorrências de SUSPEITO (relatos únicos)...")
        for _ in range(NUM_SUSPEITO):
            relato = gerar_relato_dinamico("SUSPEITO")
            veiculo_id = random.choice(veiculos_ids)
            datahora = fake.date_time_between(start_date="-3y", end_date="now")
            cur.execute(
                "INSERT INTO ocorrencias (veiculo_id, tipo, datahora, relato) VALUES (%s, %s, %s, %s)",
                (veiculo_id, 'Abordagem', datahora, relato)
            )

        print(f"Gerando {NUM_SEM_ALTERACAO} ocorrências de SEM ALTERAÇÃO (com treino de contexto)...")
        for _ in range(NUM_SEM_ALTERACAO):
            relato = gerar_relato_dinamico("SEM_ALTERACAO")
            veiculo_id = random.choice(veiculos_ids)
            datahora = fake.date_time_between(start_date="-3y", end_date="now")
            cur.execute(
                "INSERT INTO ocorrencias (veiculo_id, tipo, datahora, relato) VALUES (%s, %s, %s, %s)",
                (veiculo_id, 'Abordagem', datahora, relato)
            )
        
        conn.commit()
        print("\nDados simulados e únicos inseridos com sucesso!")

def main():
    try:
        # IMPORTANTE: Garante que as tabelas existem antes de qualquer operação
        criar_tabelas()

        with psycopg.connect(**DB_CONFIG) as conn:
            print("Limpando dados de ocorrências antigas para um novo treino...")
            with conn.cursor() as cur:
                # O comando TRUNCATE agora deve funcionar pois as tabelas já foram criadas
                cur.execute("TRUNCATE TABLE apreensoes, ocorrencias RESTART IDENTITY;")
                print("Tabelas 'apreensoes' e 'ocorrencias' limpas.")

            with conn.cursor() as cur:
                veiculos_ids = buscar_veiculos(cur)
            
            if not veiculos_ids:
                return

            # CORREÇÃO: O nome da variável aqui deve ser 'veiculos_ids' (plural)
            inserir_ocorrencias(conn, veiculos_ids)

    except psycopg.Error as e:
        print(f"Erro de banco de dados: {e}")
    except ImportError:
        print("Erro: A biblioteca 'Faker' não está instalada.")
        print("Por favor, instale com: pip install Faker")

if __name__ == "__main__":
    main()

