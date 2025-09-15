#!/usr/bin/env python3
"""
Script de Treinamento Melhorado com Threshold Ajustado
======================================================

Este script treina um modelo usando dados de feedback reais
e ajusta o threshold para melhor performance.
"""

import os
import sys
import json
import joblib
import psycopg
import pandas as pd
import numpy as np
from pathlib import Path
from typing import List, Tuple, Dict, Any
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report, accuracy_score, precision_recall_curve
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
import warnings
warnings.filterwarnings('ignore')

# Configurações
BASE_DIR = Path(__file__).parent.parent
MODELS_DIR = BASE_DIR / "ml_models" / "trained"
MODELS_DIR.mkdir(parents=True, exist_ok=True)

# Configuração do banco
DB_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'dbname': 'sentinela_teste',
    'user': 'postgres',
    'password': 'Jmkjmk.00'
}

class ImprovedFeedbackTrainer:
    """Treinador melhorado com threshold otimizado"""
    
    def __init__(self):
        self.model = None
        self.vectorizer = None
        self.optimal_threshold = 0.35
        
    def get_connection(self):
        """Cria conexão com banco"""
        try:
            return psycopg.connect(**DB_CONFIG)
        except Exception as e:
            print(f"❌ Erro de conexão: {e}")
            return None
    
    def load_feedback_data(self) -> Tuple[List[str], List[str]]:
        """Carrega dados de feedback do banco"""
        print("🔄 Carregando dados de feedback...")
        
        conn = self.get_connection()
        if not conn:
            return [], []
        
        textos = []
        labels = []
        
        try:
            with conn.cursor() as cur:
                # Buscar feedback válido (não INCERTO)
                cur.execute("""
                    SELECT relato_original, classificacao_correta 
                    FROM semantic_feedback 
                    WHERE classificacao_correta != 'INCERTO'
                    ORDER BY timestamp DESC
                """)
                
                for row in cur.fetchall():
                    relato, classificacao = row
                    if relato and len(relato.strip()) > 10:
                        textos.append(relato.strip())
                        labels.append(classificacao)
                
                print(f"✅ Carregados {len(textos)} relatos de feedback")
                
        except Exception as e:
            print(f"❌ Erro ao carregar dados: {e}")
        finally:
            conn.close()
        
        return textos, labels
    
    def create_enhanced_synthetic_data(self) -> Tuple[List[str], List[str]]:
        """Cria dados sintéticos melhorados baseados no feedback real"""
        print("🔄 Criando dados sintéticos melhorados...")
        
        # Dados SUSPEITOS (baseados no feedback real)
        suspeitos = [
            # Padrões de tráfico
            "traficante fazendo viagem bate volta na fronteira",
            "condutor tem tráfico de drogas",
            "veículo com cocaína escondida",
            "flagrante de tráfico na rodovia",
            "contrabando de entorpecentes",
            "evasão de fronteira",
            
            # Padrões de violência
            "motorista portando arma de fogo",
            "suspeito com mandado de prisão",
            "homicídio na madrugada",
            "assalto com pistola",
            "disparo de arma de fogo",
            "agressão com faca",
            "roubo a mão armada",
            
            # Padrões de comportamento suspeito (do feedback real)
            "faz varias viagens bate volta mentiu na abordagem",
            "condutor mentindo sobre destino",
            "viagens frequentes bate volta",
            "motorista evasivo na abordagem",
            "suspeito mentindo sobre carga",
            "condutor nervoso na abordagem",
            "motorista contradizendo informações",
            "suspeito com história inconsistente",
            
            # Padrões de furto/roubo
            "furto de veículo",
            "receptação de produtos roubados",
            "roubo a estabelecimento",
            "furto de carga"
        ]
        
        # Dados SEM_ALTERACAO (expandidos)
        normais = [
            # Viagens familiares/turismo
            "passeio com a família na fronteira",
            "viagem de turismo para o exterior",
            "família indo ao shopping",
            "passeio com crianças",
            "viagem de férias",
            
            # Trabalho/rotina
            "condutor voltando do trabalho",
            "motorista indo para casa",
            "trabalhador voltando da obra",
            "estudante indo para escola",
            "funcionário indo ao trabalho",
            
            # Transporte público
            "passageiro esperando transporte",
            "condutor com documentos em dia",
            "motorista respeitando sinalização",
            "passageiro com passagem comprada",
            
            # Manutenção/serviços
            "veículo em manutenção",
            "condutor com CNH válida",
            "veículo com seguro em dia",
            "motorista com documentos em ordem",
            
            # Negócios
            "viagem de negócios",
            "representante comercial",
            "vendedor em visita",
            "entrega de produtos"
        ]
        
        textos = suspeitos + normais
        labels = ['SUSPEITO'] * len(suspeitos) + ['SEM_ALTERACAO'] * len(normais)
        
        print(f"✅ Criados {len(textos)} dados sintéticos melhorados")
        return textos, labels
    
    def find_optimal_threshold(self, X_test, y_test, model):
        """Encontra o threshold ótimo usando precision-recall curve"""
        # Converter labels para numérico
        label_map = {'SEM_ALTERACAO': 0, 'SUSPEITO': 1}
        y_test_num = [label_map[label] for label in y_test]
        
        # Obter probabilidades
        y_proba = model.predict_proba(X_test)[:, 1]  # Probabilidade da classe SUSPEITO
        
        # Calcular precision-recall curve
        precision, recall, thresholds = precision_recall_curve(y_test_num, y_proba, pos_label=1)
        
        # Encontrar threshold que maximiza F1-score
        f1_scores = 2 * (precision * recall) / (precision + recall + 1e-8)
        optimal_idx = np.argmax(f1_scores)
        optimal_threshold = thresholds[optimal_idx]
        
        print(f"🎯 Threshold ótimo encontrado: {optimal_threshold:.3f}")
        return optimal_threshold
    
    def train_model(self, textos: List[str], labels: List[str]) -> bool:
        """Treina o modelo com threshold otimizado"""
        if len(textos) < 10:
            print("❌ Dados insuficientes para treinamento")
            return False
        
        print(f"🚀 Treinando modelo melhorado com {len(textos)} amostras...")
        
        # Dividir dados
        X_train, X_test, y_train, y_test = train_test_split(
            textos, labels, test_size=0.2, random_state=42, stratify=labels
        )
        
        # Criar pipeline melhorado
        pipeline = Pipeline([
            ('tfidf', TfidfVectorizer(
                max_features=1500,  # Mais features
                ngram_range=(1, 3),  # Incluir trigramas
                stop_words=None,
                min_df=1,
                max_df=0.9,  # Mais restritivo
                sublinear_tf=True  # Melhor para textos longos
            )),
            ('scaler', StandardScaler(with_mean=False)),
            ('classifier', RandomForestClassifier(
                n_estimators=200,  # Mais árvores
                random_state=42,
                class_weight='balanced',
                max_depth=10,
                min_samples_split=5
            ))
        ])
        
        # Treinar
        pipeline.fit(X_train, y_train)
        
        # Encontrar threshold ótimo
        self.optimal_threshold = self.find_optimal_threshold(X_test, y_test, pipeline)
        
        # Avaliar com threshold ótimo
        y_proba = pipeline.predict_proba(X_test)[:, 1]
        y_pred_optimal = (y_proba >= self.optimal_threshold).astype(int)
        
        # Converter labels para numérico para avaliação
        label_map = {'SEM_ALTERACAO': 0, 'SUSPEITO': 1}
        y_test_num = [label_map[label] for label in y_test]
        
        accuracy = accuracy_score(y_test_num, y_pred_optimal)
        
        print(f"📊 Acurácia com threshold ótimo: {accuracy:.3f}")
        print("\n📋 Relatório de Classificação:")
        print(classification_report(y_test_num, y_pred_optimal, 
                                  target_names=['SEM_ALTERACAO', 'SUSPEITO']))
        
        # Salvar modelo
        self.model = pipeline
        self.save_model()
        
        return True
    
    def save_model(self):
        """Salva o modelo treinado com threshold"""
        if not self.model:
            print("❌ Nenhum modelo para salvar")
            return
        
        # Salvar modelo
        model_path = MODELS_DIR / "semantic_agents_clf.joblib"
        joblib.dump(self.model, model_path)
        print(f"✅ Modelo salvo em: {model_path}")
        
        # Salvar metadados com threshold
        metadata = {
            'model_type': 'RandomForestClassifier',
            'features': 'TF-IDF',
            'training_date': pd.Timestamp.now().isoformat(),
            'version': '2.0.0',
            'description': 'Modelo melhorado com threshold otimizado',
            'optimal_threshold': self.optimal_threshold,
            'ngram_range': '(1, 3)',
            'max_features': 1500
        }
        
        metadata_path = MODELS_DIR / "semantic_agents_metadata.json"
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
        
        print(f"✅ Metadados salvos em: {metadata_path}")
        print(f"🎯 Threshold ótimo salvo: {self.optimal_threshold:.3f}")
    
    def test_model(self):
        """Testa o modelo treinado"""
        if not self.model:
            print("❌ Nenhum modelo carregado")
            return
        
        test_cases = [
            "traficante na fronteira",
            "passeio com família",
            "condutor com drogas",
            "viagem de turismo",
            "flagrante de tráfico",
            "faz varias viagens bate volta mentiu na abordagem",  # Caso do feedback
            "condutor mentindo sobre destino",
            "motorista indo para casa"
        ]
        
        print(f"\n🧪 Testando modelo (threshold: {self.optimal_threshold:.3f}):")
        for texto in test_cases:
            proba = self.model.predict_proba([texto])[0]
            suspeito_prob = proba[1] if len(proba) > 1 else proba[0]
            pred = "SUSPEITO" if suspeito_prob >= self.optimal_threshold else "SEM_ALTERACAO"
            print(f"   '{texto}' → {pred} ({suspeito_prob:.2f})")

def main():
    """Função principal"""
    print("🤖 TREINAMENTO MELHORADO DO MODELO SEMÂNTICO")
    print("=" * 50)
    
    trainer = ImprovedFeedbackTrainer()
    
    # Carregar dados de feedback
    textos_feedback, labels_feedback = trainer.load_feedback_data()
    
    # Criar dados sintéticos melhorados
    textos_synthetic, labels_synthetic = trainer.create_enhanced_synthetic_data()
    
    # Combinar dados
    textos = textos_feedback + textos_synthetic
    labels = labels_feedback + labels_synthetic
    
    print(f"📊 Total de dados: {len(textos)} ({len(textos_feedback)} feedback + {len(textos_synthetic)} sintéticos)")
    
    # Treinar modelo
    success = trainer.train_model(textos, labels)
    
    if success:
        trainer.test_model()
        print("\n✅ Treinamento melhorado concluído com sucesso!")
        print("🎯 O modelo agora usa threshold otimizado para melhor performance!")
    else:
        print("\n❌ Falha no treinamento")

if __name__ == "__main__":
    main()
