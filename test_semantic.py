import joblib
import os
import sys
import numpy as np
import re

# Garante que a raiz do projeto esteja no sys.path para encontrar outros módulos
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Tenta importar as funções e variáveis necessárias
try:
    from semantic_local import embed, CLF_PATH, LBL_PATH
except ImportError:
    print("ERRO: Não foi possível encontrar o arquivo 'semantic_local.py'.")
    print("Certifique-se de que este script está na pasta raiz do projeto.")
    sys.exit(1)

# --- PALAVRAS-CHAVE PARA EXPLICAÇÃO ---
# Esta lista contém todos os indícios que o modelo aprendeu a reconhecer como suspeitos.
# Usamo-la para explicar por que uma decisão foi tomada.
INDICIOS_SUSPEITA = [
    # Tráfico
    "maconha", "skunk", "coca", "crack", "droga", "pó", "erva",
    "fronteira", "bate volta", "provavelmente entregando", "entregar",
    "suspeito de tráfico", "viagem sem justificativa",
    "corre", "buscar droga", "voltando de entrega", "odor",
    # Arma
    "arma", "revólver", "pistola", "munição", "fuzil",
    "mão na cintura", "comportamento agressivo",
    "pode estar armado", "suspeito de arma", "coldre",
    # Geral
    "história estranha", "ficou nervoso", "mentiu", "inquieto",
    "sem motivo aparente", "madrugada", "agitado",
    "entrevista ruim", "não soube explicar", "contradição",
    "denúncia", "manobra perigosa", "evasão", "atitude suspeita"
]


def carregar_modelo_treinado():
    """Carrega o classificador e os labels salvos."""
    if not os.path.exists(CLF_PATH) or not os.path.exists(LBL_PATH):
        print("="*80)
        print("ERRO: Modelo não encontrado!")
        print(f"Certifique-se de que os arquivos '{os.path.basename(CLF_PATH)}' e '{os.path.basename(LBL_PATH)}' existem na pasta 'models'.")
        print("Execute 'python train_semantic.py' primeiro.")
        print("="*80)
        return None, None
    
    clf = joblib.load(CLF_PATH)
    labels = joblib.load(LBL_PATH)
    return clf, labels

def encontrar_motivacoes(relato: str, indicios: list) -> list:
    """Encontra e retorna as palavras-chave de suspeita presentes no relato."""
    motivacoes = []
    relato_lower = relato.lower()
    for indicio in indicios:
        # Usamos expressões regulares para encontrar a palavra exata
        if re.search(r'\b' + re.escape(indicio) + r'\b', relato_lower):
            motivacoes.append(indicio)
    return motivacoes

def main():
    """Função principal que executa o loop interativo de análise."""
    clf, labels = carregar_modelo_treinado()
    if not clf or not labels:
        return

    print("="*80)
    print("🤖 MODO DE ANÁLISE INTERATIVA 🤖")
    print("="*80)
    print("Este script utiliza o modelo de IA treinado para classificar os seus relatos.")
    print("Digite um relato e pressione Enter para ver a análise.")
    print("Para encerrar, digite 'sair'.")

    while True:
        relato_usuario = input("\n> Digite o relato: ")
        if relato_usuario.lower() in ['sair', 'exit', 'quit', 'fechar']:
            print("Encerrando a análise interativa. Até logo!")
            break
        if not relato_usuario.strip():
            continue

        # --- Análise do Modelo ---
        X_vetorizado = embed([relato_usuario])
        probabilidades = clf.predict_proba(X_vetorizado)[0]
        indice_predicao = np.argmax(probabilidades)
        classe_predita = labels[indice_predicao]

        # --- Explicação da Decisão ---
        motivacoes = encontrar_motivacoes(relato_usuario, INDICIOS_SUSPEITA)

        # --- Apresentação do Resultado ---
        print("\n" + "-"*40)
        print("Resultado da Análise:")
        
        cor_classe = "\033[92m" if classe_predita == "SEM_ALTERACAO" else "\033[91m"
        print(f"  CLASSIFICAÇÃO: {cor_classe}{classe_predita}\033[0m") # Usa cores para destaque

        print("\n  Nível de Confiança:")
        for i, label in enumerate(labels):
            print(f"    - {label}: {(probabilidades[i] * 100):.2f}%")

        if motivacoes:
            print("\n  Motivação da Classificação (palavras-chave detetadas):")
            print(f"    - \033[93m{', '.join(motivacoes)}\033[0m")
        elif classe_predita == "SUSPEITO":
            print("\n  Motivação da Classificação:")
            print("    - O modelo detetou um padrão suspeito com base no contexto geral do relato,")
            print("      mesmo sem encontrar palavras-chave diretas da lista de indícios.")
        else: # SEM_ALTERACAO
            print("\n  Motivação da Classificação:")
            print("    - O modelo não encontrou indícios suficientes para classificar o relato como suspeito.")
        
        print("-" * 40)


if __name__ == "__main__":
    main()

