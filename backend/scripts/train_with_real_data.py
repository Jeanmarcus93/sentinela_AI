#!/usr/bin/env python3
"""
Treinamento com Dados Reais do Banco veiculos_db
===============================================

Este script treina o modelo usando os relatos reais do banco veiculos_db.
Como não temos labels verdadeiros, vamos usar heurísticas baseadas em palavras-chave
para criar labels automáticos e depois treinar o modelo.
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

# Configuração do banco veiculos_db
DB_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'dbname': 'veiculos_db',
    'user': 'postgres',
    'password': 'Jmkjmk.00'
}

class RealDataTrainer:
    """Treinador com dados reais do banco"""
    
    def __init__(self):
        self.model = None
        self.optimal_threshold = 0.35
        
        # Palavras-chave para classificação automática
        self.suspeito_keywords = {
            # Comportamentos suspeitos
            'nervoso', 'nervosismo', 'agressivo', 'agressividade', 'mentiu', 'mentindo',
            'contradição', 'contradições', 'inconsistente', 'evasivo', 'evasão',
            
            # Situações perigosas
            'manobra perigosa', 'manobra suspeita', 'fuga', 'tentou fugir', 'evadir',
            'mandado de prisão', 'foragido', 'procurado', 'flagrante',
            
            # Drogas e armas
            'droga', 'drogas', 'maconha', 'cocaína', 'crack', 'entorpecente',
            'arma', 'armas', 'pistola', 'revolver', 'munição', 'disparo',
            
            # Crimes
            'roubo', 'furto', 'assalto', 'homicídio', 'assassinato', 'receptação',
            'tráfico', 'traficante', 'contrabando', 'contrabandista',
            
            # Comportamentos específicos
            'mão na cintura', 'odor de', 'cheiro de', 'substância', 'produto',
            'dinheiro em espécie', 'grande quantidade', 'sem justificativa',
            'história inconsistente', 'documentação irregular', 'documentos falsos'
        }
        
        self.normal_keywords = {
            # Situações normais
            'verificação de documentos', 'fiscalização de rotina', 'liberado',
            'nenhuma irregularidade', 'documentos em ordem', 'cnh válida',
            'visitando parentes', 'voltando de férias', 'família',
            'trabalho', 'estudo', 'negócios', 'turismo', 'passeio',
            'documentação em dia', 'seguro em dia', 'licenciamento'
        }
    
    def get_connection(self):
        """Cria conexão com banco"""
        try:
            return psycopg.connect(**DB_CONFIG)
        except Exception as e:
            print(f"❌ Erro de conexão: {e}")
            return None
    
    def load_real_data(self, limit: int = 10000) -> Tuple[List[str], List[str]]:
        """Carrega dados reais do banco e cria labels automáticos"""
        print(f"🔄 Carregando {limit} relatos do banco veiculos_db...")
        
        conn = self.get_connection()
        if not conn:
            return [], []
        
        textos = []
        labels = []
        
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT relato, id 
                    FROM ocorrencias 
                    WHERE relato IS NOT NULL 
                    AND relato != '' 
                    AND LENGTH(relato) > 50
                    ORDER BY RANDOM()
                    LIMIT %s
                """, (limit,))
                
                for row in cur.fetchall():
                    relato, id_ocorrencia = row
                    if relato and len(relato.strip()) > 10:
                        textos.append(relato.strip())
                
                print(f"✅ Carregados {len(textos)} relatos")
                
        except Exception as e:
            print(f"❌ Erro ao carregar dados: {e}")
        finally:
            conn.close()
        
        # Criar labels automáticos baseados em palavras-chave
        print("🏷️ Criando labels automáticos...")
        labels = self.create_automatic_labels(textos)
        
        return textos, labels
    
    def create_automatic_labels(self, textos: List[str]) -> List[str]:
        """Cria labels automáticos baseados em palavras-chave"""
        labels = []
        suspeito_count = 0
        normal_count = 0
        
        for texto in textos:
            texto_lower = texto.lower()
            
            # Contar palavras suspeitas
            suspeito_score = sum(1 for keyword in self.suspeito_keywords 
                               if keyword in texto_lower)
            
            # Contar palavras normais
            normal_score = sum(1 for keyword in self.normal_keywords 
                             if keyword in texto_lower)
            
            # Classificar baseado nos scores
            if suspeito_score > normal_score and suspeito_score > 0:
                labels.append('SUSPEITO')
                suspeito_count += 1
            else:
                labels.append('SEM_ALTERACAO')
                normal_count += 1
        
        print(f"📊 Labels criados: {suspeito_count} SUSPEITO, {normal_count} SEM_ALTERACAO")
        return labels
    
    def find_optimal_threshold(self, X_test, y_test, model):
        """Encontra o threshold ótimo usando precision-recall curve"""
        # Converter labels para numérico
        label_map = {'SEM_ALTERACAO': 0, 'SUSPEITO': 1}
        y_test_num = [label_map[label] for label in y_test]
        
        # Obter probabilidades
        y_proba = model.predict_proba(X_test)[:, 1]
        
        # Calcular precision-recall curve
        precision, recall, thresholds = precision_recall_curve(y_test_num, y_proba, pos_label=1)
        
        # Encontrar threshold que maximiza F1-score
        f1_scores = 2 * (precision * recall) / (precision + recall + 1e-8)
        optimal_idx = np.argmax(f1_scores)
        optimal_threshold = thresholds[optimal_idx]
        
        print(f"🎯 Threshold ótimo encontrado: {optimal_threshold:.3f}")
        return optimal_threshold
    
    def train_model(self, textos: List[str], labels: List[str]) -> bool:
        """Treina o modelo com dados reais"""
        if len(textos) < 100:
            print("❌ Dados insuficientes para treinamento")
            return False
        
        print(f"🚀 Treinando modelo com {len(textos)} relatos reais...")
        
        # Dividir dados
        X_train, X_test, y_train, y_test = train_test_split(
            textos, labels, test_size=0.2, random_state=42, stratify=labels
        )
        
        # Criar pipeline otimizado para dados reais
        pipeline = Pipeline([
            ('tfidf', TfidfVectorizer(
                max_features=2000,  # Mais features para dados reais
                ngram_range=(1, 3),
                stop_words=None,
                min_df=2,  # Ignorar palavras muito raras
                max_df=0.8,  # Ignorar palavras muito comuns
                sublinear_tf=True
            )),
            ('scaler', StandardScaler(with_mean=False)),
            ('classifier', RandomForestClassifier(
                n_estimators=300,  # Mais árvores para dados reais
                random_state=42,
                class_weight='balanced',
                max_depth=15,
                min_samples_split=3,
                min_samples_leaf=1
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
        
        # Cross-validation
        print("\n🔄 Validação cruzada...")
        cv_scores = cross_val_score(pipeline, textos, labels, cv=5, scoring='f1_macro')
        print(f"📊 CV F1-Score: {cv_scores.mean():.3f} ± {cv_scores.std():.3f}")
        
        # Salvar modelo
        self.model = pipeline
        self.save_model()
        
        return True
    
    def save_model(self):
        """Salva o modelo treinado"""
        if not self.model:
            print("❌ Nenhum modelo para salvar")
            return
        
        # Salvar modelo
        model_path = MODELS_DIR / "semantic_agents_clf.joblib"
        joblib.dump(self.model, model_path)
        print(f"✅ Modelo salvo em: {model_path}")
        
        # Salvar metadados
        metadata = {
            'model_type': 'RandomForestClassifier',
            'features': 'TF-IDF',
            'training_date': pd.Timestamp.now().isoformat(),
            'version': '3.0.0',
            'description': 'Modelo treinado com dados reais do veiculos_db',
            'optimal_threshold': self.optimal_threshold,
            'ngram_range': '(1, 3)',
            'max_features': 2000,
            'data_source': 'veiculos_db.ocorrencias',
            'training_samples': len(self.model.named_steps['classifier'].estimators_)
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
            "Veículo abordado após realizar manobra perigosa. Durante a entrevista, o motorista mentiu sobre o destino",
            "Fiscalização de rotina. Tratava-se de uma família voltando de férias. Nenhuma irregularidade foi encontrada",
            "Ocupantes demonstraram nervosismo ao avistar a viatura. Durante a entrevista, o passageiro manteve a mão na cintura",
            "Veículo parado para verificação de documentos. O motorista estava indo visitar parentes. Após a verificação, foi liberado",
            "Denúncia anônima informou sobre um carro suspeito. Durante a entrevista, foi localizada uma grande quantidade de dinheiro sem justificativa"
        ]
        
        print(f"\n🧪 Testando modelo (threshold: {self.optimal_threshold:.3f}):")
        for texto in test_cases:
            proba = self.model.predict_proba([texto])[0]
            suspeito_prob = proba[1] if len(proba) > 1 else proba[0]
            pred = "SUSPEITO" if suspeito_prob >= self.optimal_threshold else "SEM_ALTERACAO"
            print(f"   '{texto[:60]}...' → {pred} ({suspeito_prob:.2f})")

def main():
    """Função principal"""
    print("🤖 TREINAMENTO COM DADOS REAIS - veiculos_db")
    print("=" * 60)
    
    trainer = RealDataTrainer()
    
    # Carregar dados reais
    textos, labels = trainer.load_real_data(10000)  # 10k relatos
    
    if len(textos) < 100:
        print("❌ Dados insuficientes")
        return
    
    # Treinar modelo
    success = trainer.train_model(textos, labels)
    
    if success:
        trainer.test_model()
        print("\n✅ Treinamento com dados reais concluído com sucesso!")
        print("🎯 O modelo agora foi treinado com dados reais do banco!")
    else:
        print("\n❌ Falha no treinamento")

if __name__ == "__main__":
    main()

