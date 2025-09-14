import requests
import json
import csv
import os

# URL da sua API rodando localmente
API_URL = "http://127.0.0.1:5000"

# Textos para teste
test_texts = [
    "Aquele produto é suspeito, não compre.",
    "Gostei muito do atendimento, foi excelente.",
    "O pacote chegou com um atraso de duas semanas, um absurdo.",
    "Acho que ele está escondendo alguma coisa.",
    "Recomendo fortemente esta loja, os preços são ótimos.",
    "O comportamento dele é muito estranho ultimamente."
]

def run_tests():
    feedback_data = []
    for text in test_texts:
        try:
            # Envia o texto para o endpoint de análise
            response = requests.post(f"{API_URL}/analise", json={"text": text})
            if response.status_code == 200:
                result = response.json()
                prediction = result.get('analysis', {}).get('semantic_agents', {}).get('result')

                print(f"Texto: '{text}'")
                print(f"Predição do Modelo: '{prediction}'")

                # Coleta o feedback do usuário
                feedback = input("A predição está correta? (s/n): ").lower()
                is_correct = True if feedback == 's' else False

                feedback_data.append({
                    "text": text,
                    "prediction": prediction,
                    "is_correct": is_correct
                })
            else:
                print(f"Erro ao analisar o texto: '{text}'. Status Code: {response.status_code}")

        except requests.exceptions.RequestException as e:
            print(f"Erro de conexão: {e}")
            break

    # Salva o feedback em um arquivo CSV
    if feedback_data:
        save_feedback_to_csv(feedback_data)
        print("\nFeedback salvo em 'backend/data/feedback.csv'")

def save_feedback_to_csv(data):
    # Cria a pasta 'data' se não existir
    if not os.path.exists('backend/data'):
        os.makedirs('backend/data')

    # Salva os dados no arquivo CSV
    with open('backend/data/feedback.csv', 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = ['text', 'prediction', 'is_correct']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

        writer.writeheader()
        writer.writerows(data)

if __name__ == "__main__":
    run_tests()