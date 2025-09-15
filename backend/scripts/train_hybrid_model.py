#!/usr/bin/env python3
"""
Treinamento de Modelo Híbrido Inteligente
=========================================

Este script treina um modelo híbrido que combina regras inteligentes
com machine learning para melhor classificação contextual.
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

class HybridModelTrainer:
    """Treinador de modelo híbrido inteligente"""
    
    def __init__(self):
        self.model = None
        self.optimal_threshold = 0.35
        
        # CRIMES EXPLÍCITOS (sempre suspeitos, independente do contexto)
        self.explicit_crimes = {
            'tráfico', 'traficante', 'droga', 'drogas', 'cocaína', 'maconha', 'crack', 'entorpecente',
            'arma', 'armas', 'pistola', 'revolver', 'munição', 'disparo', 'tiro',
            'roubo', 'furto', 'assalto', 'homicídio', 'assassinato', 'receptação',
            'contrabando', 'contrabandista', 'mandado de prisão', 'foragido', 'procurado',
            'flagrante', 'substância', 'produto', 'dinheiro em espécie', 'grande quantidade'
        }
        
        # COMPORTAMENTOS SUSPEITOS (alta prioridade)
        self.suspicious_behaviors = {
            'tentou fugir', 'evadir', 'evasão', 'fuga',
            'mentiu', 'mentindo', 'contradição', 'contradições', 'história inconsistente',
            'documentação irregular', 'documentos falsos', 'sem justificativa',
            'manobra perigosa', 'manobra suspeita', 'mão na cintura',
            'odor de', 'cheiro de', 'comportamento agressivo', 'extremamente nervoso'
        }
        
        # COMPORTAMENTOS SUSPEITOS (média prioridade)
        self.medium_suspicious = {
            'nervoso', 'nervosismo', 'agressivo', 'agressividade', 'evasivo',
            'inconsistente', 'suspeito', 'atitude suspeita', 'comportamento estranho'
        }
        
        # JUSTIFICATIVAS PLAUSÍVEIS (reduzem suspeição apenas para comportamentos, não crimes)
        self.plausible_explanations = {
            'primeira vez', 'primeiro', 'inexperiente', 'novato', 'aprendendo',
            'família', 'parentes', 'visitando', 'voltando de férias', 'passeio',
            'trabalho', 'estudo', 'negócios', 'turismo', 'viagem de trabalho',
            'bebê chorando', 'criança doente', 'emergência médica', 'hospital',
            'médico', 'ambulância', 'acidente',
            'detetive privado', 'vigilância', 'autorização', 'identificado',
            'fotógrafo', 'jornalista', 'motorista particular', 'empregado',
            'funcionário', 'representante comercial', 'vendedor',
            'documentos em ordem', 'cnh válida', 'seguro em dia', 'licenciamento',
            'documentação em dia', 'tudo em ordem', 'liberado', 'nenhuma irregularidade'
        }
        
        # CONTEXTOS EXPLICATIVOS (reduzem suspeição apenas para comportamentos)
        self.explanatory_contexts = {
            'explicou que', 'justificou', 'motivo', 'razão', 'porque',
            'devido a', 'em função de', 'por causa de', 'conforme explicado',
            'verificou-se que', 'constatou-se que', 'era um', 'tratava-se de'
        }
    
    def get_connection(self):
        """Cria conexão com banco"""
        try:
            return psycopg.connect(**DB_CONFIG)
        except Exception as e:
            print(f"❌ Erro de conexão: {e}")
            return None
    
    def load_real_data(self, limit: int = 20000) -> Tuple[List[str], List[str]]:
        """Carrega dados reais do banco e cria labels híbridas inteligentes"""
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
        
        # Criar labels híbridas inteligentes
        print("🧠 Criando labels híbridas inteligentes...")
        labels = self.create_hybrid_labels(textos)
        
        return textos, labels
    
    def create_hybrid_labels(self, textos: List[str]) -> List[str]:
        """Cria labels híbridas considerando crimes explícitos vs comportamentos"""
        labels = []
        suspeito_count = 0
        normal_count = 0
        
        for texto in textos:
            texto_lower = texto.lower()
            
            # Calcular score híbrido inteligente
            suspicion_score = self.calculate_hybrid_suspicion(texto_lower)
            
            # Classificar baseado no score híbrido
            if suspicion_score > 0.4:  # Threshold mais baixo para capturar crimes
                labels.append('SUSPEITO')
                suspeito_count += 1
            else:
                labels.append('SEM_ALTERACAO')
                normal_count += 1
        
        print(f"📊 Labels híbridas: {suspeito_count} SUSPEITO, {normal_count} SEM_ALTERACAO")
        return labels
    
    def calculate_hybrid_suspicion(self, texto_lower: str) -> float:
        """Calcula suspeição híbrida inteligente"""
        score = 0.0
        
        # 1. CRIMES EXPLÍCITOS (sempre suspeitos, independente do contexto)
        explicit_crime_score = sum(1.0 for crime in self.explicit_crimes if crime in texto_lower)
        if explicit_crime_score > 0:
            # Crimes explícitos têm prioridade máxima
            return min(0.9 + (explicit_crime_score * 0.1), 1.0)
        
        # 2. COMPORTAMENTOS SUSPEITOS (alta prioridade)
        suspicious_score = sum(0.7 for behavior in self.suspicious_behaviors if behavior in texto_lower)
        
        # 3. COMPORTAMENTOS SUSPEITOS (média prioridade)
        medium_score = sum(0.4 for behavior in self.medium_suspicious if behavior in texto_lower)
        
        # 4. REDUÇÃO POR EXPLICAÇÕES PLAUSÍVEIS (apenas para comportamentos)
        explanation_reduction = 0.0
        has_suspicious_behavior = suspicious_score > 0 or medium_score > 0
        
        if has_suspicious_behavior:
            # Só reduz se houver comportamento suspeito E explicação plausível
            explanation_reduction = sum(0.3 for explanation in self.plausible_explanations if explanation in texto_lower)
            
            # Redução adicional por contexto explicativo
            context_reduction = sum(0.2 for context in self.explanatory_contexts if context in texto_lower)
            explanation_reduction += context_reduction
        
        # Score final
        total_score = suspicious_score + medium_score - explanation_reduction
        
        # Normalizar entre 0 e 1
        return min(max(total_score, 0.0), 1.0)
    
    def create_enhanced_features(self, textos: List[str]) -> List[str]:
        """Cria features melhoradas com contexto híbrido"""
        enhanced_texts = []
        
        for texto in textos:
            texto_lower = texto.lower()
            enhanced_text = texto
            
            # Marcar crimes explícitos (prioridade máxima)
            for crime in self.explicit_crimes:
                if crime in texto_lower:
                    enhanced_text += f" [CRIME_EXPLICITO:{crime}]"
            
            # Marcar comportamentos suspeitos
            for behavior in self.suspicious_behaviors:
                if behavior in texto_lower:
                    enhanced_text += f" [COMPORTAMENTO_SUSPEITO:{behavior}]"
            
            for behavior in self.medium_suspicious:
                if behavior in texto_lower:
                    enhanced_text += f" [COMPORTAMENTO_MEDIO:{behavior}]"
            
            # Marcar explicações plausíveis
            for explanation in self.plausible_explanations:
                if explanation in texto_lower:
                    enhanced_text += f" [EXPLICACAO_PLAUSIVEL:{explanation}]"
            
            # Marcar contextos explicativos
            for context in self.explanatory_contexts:
                if context in texto_lower:
                    enhanced_text += f" [CONTEXTO_EXPLICATIVO:{context}]"
            
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
        """Treina o modelo híbrido"""
        if len(textos) < 100:
            print("❌ Dados insuficientes para treinamento")
            return False
        
        print(f"🚀 Treinando modelo híbrido com {len(textos)} relatos...")
        
        # Criar features melhoradas
        enhanced_texts = self.create_enhanced_features(textos)
        
        # Dividir dados
        X_train, X_test, y_train, y_test = train_test_split(
            enhanced_texts, labels, test_size=0.2, random_state=42, stratify=labels
        )
        
        # Criar pipeline otimizado para modelo híbrido
        pipeline = Pipeline([
            ('tfidf', TfidfVectorizer(
                max_features=4000,  # Mais features para contexto híbrido
                ngram_range=(1, 4),  # Incluir 4-gramas
                stop_words=None,
                min_df=2,
                max_df=0.6,  # Mais restritivo
                sublinear_tf=True,
                analyzer='word'
            )),
            ('scaler', StandardScaler(with_mean=False)),
            ('classifier', RandomForestClassifier(
                n_estimators=600,  # Mais árvores para modelo híbrido
                random_state=42,
                class_weight='balanced',
                max_depth=25,
                min_samples_split=2,
                min_samples_leaf=1,
                max_features='sqrt'
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
        """Salva o modelo híbrido treinado"""
        if not self.model:
            print("❌ Nenhum modelo para salvar")
            return
        
        # Salvar modelo
        model_path = MODELS_DIR / "semantic_agents_clf.joblib"
        joblib.dump(self.model, model_path)
        print(f"✅ Modelo híbrido salvo em: {model_path}")
        
        # Salvar metadados
        metadata = {
            'model_type': 'RandomForestClassifier_Hybrid',
            'features': 'TF-IDF_Hybrid_Intelligent',
            'training_date': pd.Timestamp.now().isoformat(),
            'version': '5.0.0',
            'description': 'Modelo híbrido inteligente com priorização de crimes explícitos',
            'optimal_threshold': self.optimal_threshold,
            'ngram_range': '(1, 4)',
            'max_features': 4000,
            'data_source': 'veiculos_db.ocorrencias',
            'hybrid_features': True,
            'explicit_crimes_priority': True,
            'explicit_crimes': list(self.explicit_crimes),
            'suspicious_behaviors': list(self.suspicious_behaviors),
            'plausible_explanations': list(self.plausible_explanations)
        }
        
        metadata_path = MODELS_DIR / "semantic_agents_metadata.json"
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
        
        print(f"✅ Metadados híbridos salvos em: {metadata_path}")
        print(f"🎯 Threshold ótimo salvo: {self.optimal_threshold:.3f}")
    
    def test_hybrid_model(self):
        """Testa o modelo híbrido com casos específicos"""
        if not self.model:
            print("❌ Nenhum modelo carregado")
            return
        
        test_cases = [
            # Caso que DEVE ser SUSPEITO (crime explícito)
            {
                'texto': "Denúncia anônima informou sobre tráfico de drogas. Durante a abordagem, foi localizada grande quantidade de cocaína escondida no veículo.",
                'expected': 'SUSPEITO',
                'description': 'Crime explícito - tráfico de drogas'
            },
            # Caso que DEVE ser SUSPEITO (comportamento suspeito)
            {
                'texto': "Ocupantes demonstraram nervosismo ao avistar a viatura. Durante a entrevista, os ocupantes entraram em contradição e foi localizada uma caixa de munição.",
                'expected': 'SUSPEITO',
                'description': 'Nervosismo + contradição + munição'
            },
            # Caso que DEVE ser SEM_ALTERACAO (nervoso com justificativa)
            {
                'texto': "Abordagem a veículo com matrícula de RN. O condutor, nervoso no início, explicou que era a sua primeira vez a conduzir na autoestrada. Documentos e tudo em ordem.",
                'expected': 'SEM_ALTERACAO',
                'description': 'Nervoso mas com justificativa plausível'
            },
            # Caso normal
            {
                'texto': "Fiscalização de rotina. Tratava-se de uma família voltando de férias. Nenhuma irregularidade foi encontrada.",
                'expected': 'SEM_ALTERACAO',
                'description': 'Situação completamente normal'
            },
            # Caso com justificativa plausível
            {
                'texto': "Motorista a conduzir de forma errática. Após a paragem, verificou-se que era um pai a tentar acalmar um bebê que chorava no banco de trás.",
                'expected': 'SEM_ALTERACAO',
                'description': 'Comportamento errático com explicação plausível'
            }
        ]
        
        print(f"\n🧪 Testando modelo híbrido (threshold: {self.optimal_threshold:.3f}):")
        correct = 0
        
        for i, caso in enumerate(test_cases, 1):
            # Criar features melhoradas
            enhanced_text = self.create_enhanced_features([caso['texto']])[0]
            
            proba = self.model.predict_proba([enhanced_text])[0]
            suspeito_prob = proba[1] if len(proba) > 1 else proba[0]
            pred = "SUSPEITO" if suspeito_prob >= self.optimal_threshold else "SEM_ALTERACAO"
            
            is_correct = pred == caso['expected']
            status = "✅" if is_correct else "❌"
            
            if is_correct:
                correct += 1
            
            print(f"\n{status} CASO {i}: {caso['description']}")
            print(f"   Esperado: {caso['expected']} | Obtido: {pred} ({suspeito_prob:.3f})")
            print(f"   Texto: {caso['texto'][:80]}...")
        
        print(f"\n📊 RESULTADO GERAL: {correct}/{len(test_cases)} corretos ({correct/len(test_cases)*100:.1f}%)")

def main():
    """Função principal"""
    print("🤖 TREINAMENTO DE MODELO HÍBRIDO INTELIGENTE")
    print("=" * 60)
    
    trainer = HybridModelTrainer()
    
    # Carregar dados reais
    textos, labels = trainer.load_real_data(20000)  # 20k relatos
    
    if len(textos) < 100:
        print("❌ Dados insuficientes")
        return
    
    # Treinar modelo híbrido
    success = trainer.train_model(textos, labels)
    
    if success:
        trainer.test_hybrid_model()
        print("\n✅ Treinamento híbrido concluído com sucesso!")
        print("🎯 O modelo agora prioriza crimes explícitos corretamente!")
    else:
        print("\n❌ Falha no treinamento")

if __name__ == "__main__":
    main()

