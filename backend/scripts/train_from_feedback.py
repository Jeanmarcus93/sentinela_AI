#!/usr/bin/env python3
"""
Script para treinar o modelo semântico usando feedbacks coletados
"""

import os
import sys
import json
import psycopg
from datetime import datetime
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, accuracy_score
import joblib
import numpy as np

# Adicionar o diretório pai ao path para importar módulos
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configuração do banco de dados
DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": int(os.getenv("DB_PORT", "5432")),
    "dbname": os.getenv("DB_NAME", "veiculos_db"),
    "user": os.getenv("DB_USER", "postgres"),
    "password": os.getenv("DB_PASSWORD", "Jmkjmk.00")
}

def carregar_feedbacks():
    """Carrega feedbacks do banco de dados"""
    try:
        with psycopg.connect(**DB_CONFIG) as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT 
                        texto_relato,
                        classificacao_usuario,
                        classificacao_modelo,
                        feedback_usuario,
                        confianca_modelo,
                        observacoes
                    FROM feedback 
                    WHERE texto_relato IS NOT NULL 
                    AND texto_relato != ''
                    AND classificacao_usuario IN ('suspeito', 'normal')
                    ORDER BY datahora DESC
                """)
                
                feedbacks = cur.fetchall()
                print(f"📊 Carregados {len(feedbacks)} feedbacks do banco de dados")
                return feedbacks
                
    except Exception as e:
        print(f"❌ Erro ao carregar feedbacks: {e}")
        return []

def preparar_dados_treinamento(feedbacks):
    """Prepara dados para treinamento"""
    textos = []
    labels = []
    pesos = []
    
    for feedback in feedbacks:
        texto_relato, classificacao_usuario, classificacao_modelo, feedback_usuario, confianca_modelo, observacoes = feedback
        
        # Usar classificação do usuário como label
        textos.append(texto_relato)
        labels.append(classificacao_usuario)
        
        # Calcular peso baseado no feedback do usuário
        if feedback_usuario == 'correto':
            peso = 1.0  # Peso normal
        elif feedback_usuario == 'incorreto':
            peso = 2.0  # Peso maior para correções
        elif feedback_usuario == 'duvidoso':
            peso = 0.5  # Peso menor para casos duvidosos
        else:
            peso = 1.0
            
        pesos.append(peso)
    
    return textos, labels, pesos

def treinar_modelo(textos, labels, pesos):
    """Treina o modelo semântico"""
    print("🔧 Preparando dados para treinamento...")
    
    # Vectorização TF-IDF
    vectorizer = TfidfVectorizer(
        max_features=5000,
        ngram_range=(1, 2),
        stop_words='portuguese',
        min_df=2,
        max_df=0.95
    )
    
    X = vectorizer.fit_transform(textos)
    y = np.array(labels)
    sample_weights = np.array(pesos)
    
    print(f"📈 Dimensões dos dados: {X.shape}")
    print(f"📊 Distribuição das classes: {np.bincount([1 if label == 'suspeito' else 0 for label in labels])}")
    
    # Divisão treino/teste
    X_train, X_test, y_train, y_test, weights_train, weights_test = train_test_split(
        X, y, sample_weights, test_size=0.2, random_state=42, stratify=y
    )
    
    # Treinamento do modelo
    print("🤖 Treinando modelo Random Forest...")
    model = RandomForestClassifier(
        n_estimators=100,
        max_depth=20,
        min_samples_split=5,
        min_samples_leaf=2,
        random_state=42,
        class_weight='balanced'
    )
    
    # Treinar com pesos
    model.fit(X_train, y_train, sample_weight=weights_train)
    
    # Avaliação
    y_pred = model.predict(X_test)
    accuracy = accuracy_score(y_test, y_pred)
    
    print(f"📊 Acurácia do modelo: {accuracy:.3f}")
    print("\n📋 Relatório de classificação:")
    print(classification_report(y_test, y_pred))
    
    return model, vectorizer, accuracy

def salvar_modelo(model, vectorizer, accuracy):
    """Salva o modelo treinado"""
    try:
        # Criar diretório se não existir
        models_dir = os.path.join(os.path.dirname(__file__), '..', 'ml_models', 'trained')
        os.makedirs(models_dir, exist_ok=True)
        
        # Salvar modelo
        model_path = os.path.join(models_dir, 'semantic_agents_clf_feedback.joblib')
        joblib.dump(model, model_path)
        
        # Salvar vectorizer
        vectorizer_path = os.path.join(models_dir, 'semantic_vectorizer_feedback.joblib')
        joblib.dump(vectorizer, vectorizer_path)
        
        # Salvar metadados
        metadata = {
            "model_type": "RandomForestClassifier",
            "training_date": datetime.now().isoformat(),
            "accuracy": accuracy,
            "features": vectorizer.get_feature_names_out().tolist(),
            "training_source": "feedback_system"
        }
        
        metadata_path = os.path.join(models_dir, 'semantic_agents_metadata_feedback.json')
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
        
        print(f"✅ Modelo salvo em: {model_path}")
        print(f"✅ Vectorizer salvo em: {vectorizer_path}")
        print(f"✅ Metadados salvos em: {metadata_path}")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro ao salvar modelo: {e}")
        return False

def main():
    """Função principal"""
    print("🎓 Sistema de Treinamento Semântico com Feedback")
    print("=" * 50)
    
    # Carregar feedbacks
    feedbacks = carregar_feedbacks()
    
    if len(feedbacks) < 10:
        print("⚠️ Poucos feedbacks disponíveis para treinamento (mínimo: 10)")
        print("💡 Continue coletando feedbacks antes de treinar o modelo")
        return
    
    # Preparar dados
    textos, labels, pesos = preparar_dados_treinamento(feedbacks)
    
    # Treinar modelo
    model, vectorizer, accuracy = treinar_modelo(textos, labels, pesos)
    
    # Salvar modelo
    if salvar_modelo(model, vectorizer, accuracy):
        print("\n🎉 Treinamento concluído com sucesso!")
        print(f"📊 Acurácia final: {accuracy:.3f}")
        print("💡 O modelo foi salvo e pode ser usado para novas análises")
    else:
        print("\n❌ Falha ao salvar o modelo treinado")

if __name__ == "__main__":
    main()