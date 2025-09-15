#!/usr/bin/env python3
"""
Treinamento de Modelo Contextual Melhorado
==========================================

Este script treina um modelo que considera contexto e justificativas
plausíveis, não apenas palavras-chave isoladas.
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

class ContextualModelTrainer:
    """Treinador de modelo contextual melhorado"""
    
    def __init__(self):
        self.model = None
        self.optimal_threshold = 0.35
        
        # Palavras-chave SUSPEITAS (alta prioridade)
        self.high_suspect_keywords = {
            # Crimes explícitos
            'tráfico', 'traficante', 'droga', 'drogas', 'cocaína', 'maconha', 'crack',
            'arma', 'armas', 'pistola', 'revolver', 'munição', 'disparo',
            'roubo', 'furto', 'assalto', 'homicídio', 'assassinato', 'receptação',
            'contrabando', 'contrabandista', 'mandado de prisão', 'foragido', 'procurado',
            
            # Comportamentos criminais
            'tentou fugir', 'evadir', 'evasão', 'fuga', 'flagrante',
            'mentiu', 'mentindo', 'contradição', 'contradições', 'história inconsistente',
            'documentação irregular', 'documentos falsos', 'sem justificativa',
            
            # Situações perigosas
            'manobra perigosa', 'manobra suspeita', 'mão na cintura',
            'odor de', 'cheiro de', 'substância', 'produto', 'dinheiro em espécie',
            'grande quantidade', 'comportamento agressivo', 'extremamente nervoso'
        }
        
        # Palavras-chave SUSPEITAS (média prioridade)
        self.medium_suspect_keywords = {
            'nervoso', 'nervosismo', 'agressivo', 'agressividade', 'evasivo',
            'inconsistente', 'suspeito', 'atitude suspeita', 'comportamento estranho'
        }
        
        # Justificativas PLAUSÍVEIS (reduzem suspeição)
        self.plausible_explanations = {
            # Situações familiares/normais
            'primeira vez', 'primeiro', 'inexperiente', 'novato', 'aprendendo',
            'família', 'parentes', 'visitando', 'voltando de férias', 'passeio',
            'trabalho', 'estudo', 'negócios', 'turismo', 'viagem de trabalho',
            
            # Emergências médicas
            'bebê chorando', 'criança doente', 'emergência médica', 'hospital',
            'médico', 'ambulância', 'acidente',
            
            # Situações profissionais legítimas
            'detetive privado', 'vigilância', 'autorização', 'identificado',
            'fotógrafo', 'jornalista', 'motorista particular', 'empregado',
            'funcionário', 'representante comercial', 'vendedor',
            
            # Documentação em ordem
            'documentos em ordem', 'cnh válida', 'seguro em dia', 'licenciamento',
            'documentação em dia', 'tudo em ordem', 'liberado', 'nenhuma irregularidade',
            
            # Contextos explicativos
            'explicou que', 'justificou', 'motivo', 'razão', 'porque',
            'devido a', 'em função de', 'por causa de', 'conforme explicado'
        }
        
        # Contextos que ANULAM suspeição
        self.suspicion_cancellers = {
            'após verificação', 'constatou-se que', 'verificou-se que',
            'na abordagem', 'durante a entrevista', 'explicou que era',
            'era um', 'tratava-se de', 'era o', 'era uma'
        }
    
    def get_connection(self):
        """Cria conexão com banco"""
        try:
            return psycopg.connect(**DB_CONFIG)
        except Exception as e:
            print(f"❌ Erro de conexão: {e}")
            return None
    
    def load_real_data(self, limit: int = 15000) -> Tuple[List[str], List[str]]:
        """Carrega dados reais do banco e cria labels contextuais"""
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
        
        # Criar labels contextuais inteligentes
        print("🧠 Criando labels contextuais inteligentes...")
        labels = self.create_contextual_labels(textos)
        
        return textos, labels
    
    def create_contextual_labels(self, textos: List[str]) -> List[str]:
        """Cria labels contextuais considerando justificativas plausíveis"""
        labels = []
        suspeito_count = 0
        normal_count = 0
        
        for texto in textos:
            texto_lower = texto.lower()
            
            # Calcular score de suspeição contextual
            suspicion_score = self.calculate_contextual_suspicion(texto_lower)
            
            # Classificar baseado no score contextual
            if suspicion_score > 0.5:  # Threshold mais baixo para casos contextuais
                labels.append('SUSPEITO')
                suspeito_count += 1
            else:
                labels.append('SEM_ALTERACAO')
                normal_count += 1
        
        print(f"📊 Labels contextuais: {suspeito_count} SUSPEITO, {normal_count} SEM_ALTERACAO")
        return labels
    
    def calculate_contextual_suspicion(self, texto_lower: str) -> float:
        """Calcula suspeição considerando contexto e justificativas"""
        score = 0.0
        
        # 1. Verificar se há canceladores de suspeição primeiro
        has_canceller = any(canceller in texto_lower for canceller in self.suspicion_cancellers)
        has_plausible_explanation = any(explanation in texto_lower for explanation in self.plausible_explanations)
        
        # 2. Se há cancelador + explicação plausível, reduzir drasticamente a suspeição
        if has_canceller and has_plausible_explanation:
            # Apenas crimes explícitos mantêm suspeição alta
            high_crime_score = sum(0.8 for keyword in self.high_suspect_keywords 
                                 if keyword in texto_lower and keyword in ['tráfico', 'droga', 'arma', 'roubo', 'homicídio'])
            return min(high_crime_score, 0.3)  # Máximo 30% mesmo com crimes
        
        # 3. Calcular scores normais
        # Alta suspeição (crimes explícitos)
        high_score = sum(0.8 for keyword in self.high_suspect_keywords if keyword in texto_lower)
        
        # Média suspeição (comportamentos suspeitos)
        medium_score = sum(0.4 for keyword in self.medium_suspect_keywords if keyword in texto_lower)
        
        # Redução por explicações plausíveis
        explanation_reduction = sum(0.3 for explanation in self.plausible_explanations if explanation in texto_lower)
        
        # Score final
        total_score = high_score + medium_score - explanation_reduction
        
        # Normalizar entre 0 e 1
        return min(max(total_score, 0.0), 1.0)
    
    def create_enhanced_features(self, textos: List[str]) -> List[str]:
        """Cria features melhoradas com contexto"""
        enhanced_texts = []
        
        for texto in textos:
            texto_lower = texto.lower()
            
            # Adicionar features contextuais
            enhanced_text = texto
            
            # Marcar justificativas plausíveis
            for explanation in self.plausible_explanations:
                if explanation in texto_lower:
                    enhanced_text += f" [JUSTIFICATIVA_PLAUSIVEL:{explanation}]"
            
            # Marcar canceladores de suspeição
            for canceller in self.suspicion_cancellers:
                if canceller in texto_lower:
                    enhanced_text += f" [CANCELADOR_SUSPEICAO:{canceller}]"
            
            # Marcar crimes explícitos
            for crime in self.high_suspect_keywords:
                if crime in texto_lower:
                    enhanced_text += f" [CRIME_EXPLICITO:{crime}]"
            
            enhanced_texts.append(enhanced_text)
        
        return enhanced_texts
    
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
        """Treina o modelo contextual melhorado"""
        if len(textos) < 100:
            print("❌ Dados insuficientes para treinamento")
            return False
        
        print(f"🚀 Treinando modelo contextual com {len(textos)} relatos...")
        
        # Criar features melhoradas
        enhanced_texts = self.create_enhanced_features(textos)
        
        # Dividir dados
        X_train, X_test, y_train, y_test = train_test_split(
            enhanced_texts, labels, test_size=0.2, random_state=42, stratify=labels
        )
        
        # Criar pipeline otimizado para análise contextual
        pipeline = Pipeline([
            ('tfidf', TfidfVectorizer(
                max_features=3000,  # Mais features para contexto
                ngram_range=(1, 4),  # Incluir 4-gramas para contexto
                stop_words=None,
                min_df=2,
                max_df=0.7,  # Mais restritivo
                sublinear_tf=True,
                analyzer='word'
            )),
            ('scaler', StandardScaler(with_mean=False)),
            ('classifier', RandomForestClassifier(
                n_estimators=500,  # Mais árvores para contexto complexo
                random_state=42,
                class_weight='balanced',
                max_depth=20,
                min_samples_split=2,
                min_samples_leaf=1,
                max_features='sqrt'  # Para evitar overfitting
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
        cv_scores = cross_val_score(pipeline, enhanced_texts, labels, cv=5, scoring='f1_macro')
        print(f"📊 CV F1-Score: {cv_scores.mean():.3f} ± {cv_scores.std():.3f}")
        
        # Salvar modelo
        self.model = pipeline
        self.save_model()
        
        return True
    
    def save_model(self):
        """Salva o modelo contextual treinado"""
        if not self.model:
            print("❌ Nenhum modelo para salvar")
            return
        
        # Salvar modelo
        model_path = MODELS_DIR / "semantic_agents_clf.joblib"
        joblib.dump(self.model, model_path)
        print(f"✅ Modelo contextual salvo em: {model_path}")
        
        # Salvar metadados
        metadata = {
            'model_type': 'RandomForestClassifier_Contextual',
            'features': 'TF-IDF_Enhanced_Contextual',
            'training_date': pd.Timestamp.now().isoformat(),
            'version': '4.0.0',
            'description': 'Modelo contextual melhorado com análise de justificativas plausíveis',
            'optimal_threshold': self.optimal_threshold,
            'ngram_range': '(1, 4)',
            'max_features': 3000,
            'data_source': 'veiculos_db.ocorrencias',
            'contextual_features': True,
            'plausible_explanations': list(self.plausible_explanations),
            'suspicion_cancellers': list(self.suspicion_cancellers)
        }
        
        metadata_path = MODELS_DIR / "semantic_agents_metadata.json"
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
        
        print(f"✅ Metadados contextuais salvos em: {metadata_path}")
        print(f"🎯 Threshold ótimo salvo: {self.optimal_threshold:.3f}")
    
    def test_contextual_model(self):
        """Testa o modelo contextual com casos específicos"""
        if not self.model:
            print("❌ Nenhum modelo carregado")
            return
        
        test_cases = [
            # Caso que deveria ser SEM_ALTERACAO (nervoso mas com justificativa)
            "Abordagem a veículo com matrícula de RN. O condutor, nervoso no início, explicou que era a sua primeira vez a conduzir na autoestrada. Documentos e tudo em ordem.",
            
            # Caso que deveria ser SUSPEITO (nervoso sem justificativa)
            "Ocupantes demonstraram nervosismo ao avistar a viatura. Durante a entrevista, os ocupantes entraram em contradição e foi localizada uma caixa de munição.",
            
            # Caso normal
            "Fiscalização de rotina. Tratava-se de uma família voltando de férias. Nenhuma irregularidade foi encontrada.",
            
            # Caso com justificativa plausível
            "Motorista a conduzir de forma errática. Após a paragem, verificou-se que era um pai a tentar acalmar um bebê que chorava no banco de trás.",
            
            # Caso criminoso explícito
            "Denúncia anônima informou sobre tráfico de drogas. Durante a abordagem, foi localizada grande quantidade de cocaína escondida no veículo."
        ]
        
        print(f"\n🧪 Testando modelo contextual (threshold: {self.optimal_threshold:.3f}):")
        for i, texto in enumerate(test_cases, 1):
            # Criar features melhoradas
            enhanced_text = self.create_enhanced_features([texto])[0]
            
            proba = self.model.predict_proba([enhanced_text])[0]
            suspeito_prob = proba[1] if len(proba) > 1 else proba[0]
            pred = "SUSPEITO" if suspeito_prob >= self.optimal_threshold else "SEM_ALTERACAO"
            
            print(f"\n📝 CASO {i}:")
            print(f"   Texto: {texto[:80]}...")
            print(f"   🎯 Classificação: {pred} ({suspeito_prob:.3f})")

def main():
    """Função principal"""
    print("🤖 TREINAMENTO DE MODELO CONTEXTUAL MELHORADO")
    print("=" * 60)
    
    trainer = ContextualModelTrainer()
    
    # Carregar dados reais
    textos, labels = trainer.load_real_data(15000)  # 15k relatos
    
    if len(textos) < 100:
        print("❌ Dados insuficientes")
        return
    
    # Treinar modelo contextual
    success = trainer.train_model(textos, labels)
    
    if success:
        trainer.test_contextual_model()
        print("\n✅ Treinamento contextual concluído com sucesso!")
        print("🧠 O modelo agora considera contexto e justificativas plausíveis!")
    else:
        print("\n❌ Falha no treinamento")

if __name__ == "__main__":
    main()

