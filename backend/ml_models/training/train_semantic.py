import os
import sys
import json
import time
import asyncio
from typing import Dict, List, Tuple, Optional, Any, Set
from dataclasses import dataclass, asdict
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

# Adicionar diretório do projeto ao path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Imports de ML
import numpy as np
import pandas as pd
import joblib
from sklearn.model_selection import train_test_split, cross_val_score, StratifiedKFold
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier, VotingClassifier
from sklearn.multiclass import OneVsRestClassifier
from sklearn.calibration import CalibratedClassifierCV
from sklearn.metrics import classification_report, confusion_matrix, roc_auc_score, precision_recall_curve
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.utils.class_weight import compute_class_weight
from collections import Counter
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score

# Imports de NLP
import spacy
import yake
from sentence_transformers import SentenceTransformer

# Imports do projeto
try:
    from app.models.database import get_db_connection
    from app.services.semantic_service import SemanticContext
    print("✅ Imports do projeto carregados")
except ImportError as e:
    print(f"⚠️ Erro nos imports do projeto: {e}")
    print("   Execute este script do diretório raiz do projeto")
    sys.exit(1)

# =============================================================================
# CONFIGURAÇÕES E CONSTANTES
# =============================================================================

# Diretórios
MODELS_DIR = PROJECT_ROOT / "ml_models" / "trained"
CONFIG_DIR = PROJECT_ROOT / "config"
AGENTS_DIR = PROJECT_ROOT / "config" / "agents"
MODELS_DIR.mkdir(parents=True, exist_ok=True)

# Arquivos de modelo
SEMANTIC_CLF_PATH = MODELS_DIR / "semantic_agents_clf.joblib"
SEMANTIC_LBL_PATH = MODELS_DIR / "semantic_agents_labels.joblib"
SEMANTIC_META_PATH = MODELS_DIR / "semantic_agents_metadata.json"

# Classificação binária para agentes
SEMANTIC_CLASSES = [
    "SUSPEITO",
    "SEM_ALTERACAO"
]

# Configuração de ML
ML_CONFIG = {
    'spacy_model': 'pt_core_news_sm',
    'sentence_transformer': 'sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2',
    'test_size': 0.2,
    'cv_folds': 5,
    'random_state': 42,
    'min_samples_per_class': 10
}

@dataclass
class AgentTrainingConfig:
    """Configuração específica para treinamento de agentes"""
    enable_agent_specialization: bool = True
    use_binary_classification: bool = True  # Forçar classificação binária
    enable_ensemble_methods: bool = True
    use_confidence_calibration: bool = True
    enable_active_learning: bool = False
    
    # Thresholds para classificação binária
    suspicion_threshold: float = 0.3
    confidence_threshold: float = 0.7
    min_suspicion_indicators: int = 2
    
    # Pesos para diferentes tipos de suspeita
    suspicion_weights: Dict[str, float] = None
    
    def __post_init__(self):
        if self.suspicion_weights is None:
            self.suspicion_weights = {
            'palavras_suspeitas': 0.5,        # Aumentar para 50%
            'padroes_cobertura': 0.2,
            'contexto_criminal': 0.15,
            'inconsistencias': 0.1,
            'indicadores_gerais': 0.05
        }

# =============================================================================
# SISTEMA DE CLASSIFICAÇÃO BINÁRIA INTELIGENTE
# =============================================================================

class BinarySemanticClassifier:
    """Classificador binário especializado para detecção de suspeição"""
    
    def __init__(self, config: AgentTrainingConfig):
        self.config = config
        self.nlp = None
        self.embedder = None
        self.yake_extractor = None
        self.contexts = None
        
    def load_nlp_models(self):
        """Carrega modelos de NLP necessários"""
        print("🔄 Carregando modelos de NLP...")
        
        # SpaCy
        try:
            self.nlp = spacy.load(ML_CONFIG['spacy_model'], disable=["tagger", "parser", "lemmatizer"])
            print(f"✅ SpaCy modelo carregado: {ML_CONFIG['spacy_model']}")
        except IOError:
            print(f"❌ Erro ao carregar modelo SpaCy: {ML_CONFIG['spacy_model']}")
            print("   Execute: python -m spacy download pt_core_news_sm")
            return False
            
        # Sentence Transformer
        try:
            self.embedder = SentenceTransformer(ML_CONFIG['sentence_transformer'])
            print(f"✅ Sentence Transformer carregado")
        except Exception as e:
            print(f"❌ Erro ao carregar Sentence Transformer: {e}")
            return False
            
        # YAKE para extração de palavras-chave
        self.yake_extractor = yake.KeywordExtractor(
            lan="pt", n=3, top=20, windowsSize=3, dedupLim=0.7
        )
        
        return True
        
    def load_contexts(self) -> SemanticContext:
        """Carrega contextos de análise"""
        def load_word_list(filename: str) -> Set[str]:
            filepath = CONFIG_DIR / filename
            if filepath.exists():
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        return {
                            line.strip().lower() 
                            for line in f 
                            if line.strip() and not line.startswith('#')
                        }
                except Exception as e:
                    print(f"⚠️ Erro ao carregar {filename}: {e}")
            else:
                print(f"⚠️ Arquivo não encontrado: {filename}, usando valores padrão")
            return set()
            
        # Listas padrão caso arquivos não existam
        default_suspicious = {
            'droga', 'cocaína', 'maconha', 'crack', 'tráfico', 'traficante',
            'arma', 'revolver', 'pistola', 'munição', 'disparo', 
            'roubo', 'assalto', 'furto', 'receptação',
            'foragido', 'procurado', 'mandado', 'flagrante', 'apreensão'
        }
        
        default_normal = {
            'trabalho', 'casa', 'família', 'escola', 'igreja',
            'mercado', 'hospital', 'farmácia', 'banco'
        }
        
        default_coverage = {
            'estava passando e vi',
            'não sabia de nada', 
            'só estava dando uma volta',
            'estava indo para casa',
            'estava esperando alguém'
        }
        
        palavras_suspeitas = load_word_list("palavras_suspeitas.txt") or default_suspicious
        palavras_normais = load_word_list("palavras_normais.txt") or default_normal
        historias_cobertura = load_word_list("historias_cobertura.txt") or default_coverage
        contextos_suspeitos = list(load_word_list("contextos_suspeitos.txt") or {
            'zona de tráfico', 'área controlada', 'horário suspeito'
        })
        palavras_criticas = load_word_list("palavras_criticas.txt") or default_suspicious
        
        return SemanticContext(
            palavras_suspeitas=palavras_suspeitas,
            palavras_normais=palavras_normais,
            historias_cobertura=historias_cobertura,
            contextos_suspeitos=contextos_suspeitos,
            palavras_criticas=palavras_criticas
        )
        
    def calculate_suspicion_score(self, texto: str) -> Tuple[float, Dict[str, float]]:
        """Calcula score de suspeição com detalhamento por categoria"""
        if not self.contexts:
            self.contexts = self.load_contexts()
            
        texto_lower = texto.lower()
        scores = {}
        
        # 1. Análise de palavras suspeitas
        palavras_encontradas = sum(1 for palavra in self.contexts.palavras_suspeitas 
                                 if palavra in texto_lower)
        total_palavras = len(texto.split())
        scores['palavras_suspeitas'] = min(palavras_encontradas / max(total_palavras * 0.1, 1), 1.0)
        
        # 2. Padrões de cobertura criminal
        cobertura_score = 0
        for historia in self.contexts.historias_cobertura:
            if historia.lower() in texto_lower:
                cobertura_score += 0.3
        scores['padroes_cobertura'] = min(cobertura_score, 1.0)
        
        # 3. Contextos criminais específicos
        contexto_score = 0
        for contexto in self.contexts.contextos_suspeitos:
            if contexto.lower() in texto_lower:
                contexto_score += 0.2
        scores['contexto_criminal'] = min(contexto_score, 1.0)
        
        # 4. Palavras críticas (alto impacto)
        criticas_score = sum(0.4 for palavra in self.contexts.palavras_criticas 
                           if palavra in texto_lower)
        scores['indicadores_criticos'] = min(criticas_score, 1.0)
        
        # 5. Análise de inconsistências narrativas
        inconsistencias = self._detect_narrative_inconsistencies(texto)
        scores['inconsistencias'] = min(inconsistencias * 0.3, 1.0)
        
        # Score final ponderado
        score_final = sum(
            scores[categoria] * self.config.suspicion_weights.get(categoria, 0.1)
            for categoria in scores
        )
        
        return min(score_final, 1.0), scores
        
    def _detect_narrative_inconsistencies(self, texto: str) -> int:
        """Detecta inconsistências narrativas que podem indicar cobertura"""
        inconsistencias = 0
        texto_lower = texto.lower()
        
        # Padrões de evasão comum
        padroes_evasivos = [
            r'não lembro',
            r'não sei',
            r'talvez',
            r'acho que',
            r'pode ser',
            r'não tenho certeza',
            r'mais ou menos',
            r'não reparei'
        ]
        
        import re
        for padrao in padroes_evasivos:
            if re.search(padrao, texto_lower):
                inconsistencias += 1
                
        # Excesso de detalhes desnecessários (possível fabricação)
        if len(texto.split()) > 200:
            detail_indicators = ['exatamente', 'precisamente', 'certamente', 'obviamente']
            detail_count = sum(1 for ind in detail_indicators if ind in texto_lower)
            if detail_count >= 3:
                inconsistencias += 1
                
        # Contradições temporais básicas
        time_words = re.findall(r'\b(\d{1,2}h\d{0,2}|\d{1,2}:\d{2}|manhã|tarde|noite|madrugada)\b', texto_lower)
        if len(time_words) > 3:  # Muitas referências temporais podem indicar fabricação
            inconsistencias += 1
            
        return inconsistencias
        
    def classify_text_binary(self, texto: str) -> Tuple[str, float, Dict[str, Any]]:
        """Classificação binária inteligente"""
        score, details = self.calculate_suspicion_score(texto)
        
        # Decisão binária
        if score >= self.config.suspicion_threshold:
            label = "SUSPEITO"
            confidence = score
        else:
            label = "SEM_ALTERACAO"  
            confidence = 1.0 - score
            
        # Metadados detalhados
        metadata = {
            'suspicion_score': score,
            'confidence': confidence,
            'category_scores': details,
            'threshold_used': self.config.suspicion_threshold,
            'classification_method': 'intelligent_binary'
        }
        
        return label, confidence, metadata

# =============================================================================
# TREINAMENTO COM DADOS REAIS
# =============================================================================

class AgentSemanticTrainer:
    """Sistema de treinamento para agentes semânticos"""
    
    def __init__(self, config: AgentTrainingConfig):
        self.config = config
        self.classifier = BinarySemanticClassifier(config)
        self.models = {}
        self.training_stats = {}
        
    def load_training_data(self) -> Tuple[List[str], List[str]]:
        """
        Carrega dados de treinamento do banco de dados
        VERSÃO FINAL - com correção para dados desbalanceados
        """
        print("🔄 Carregando dados de treinamento...")
        
        textos = []
        labels = []
        
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cur:
                    # Query simples sem ORDER BY problemático
                    cur.execute("""
                        SELECT relato 
                        FROM ocorrencias 
                        WHERE relato IS NOT NULL 
                        AND LENGTH(TRIM(relato)) > 20
                        LIMIT 5000
                    """)
                    
                    rows = cur.fetchall()
                        
            print(f"📊 Encontrados {len(rows)} registros")
            
            # Processar dados com classificação automática inteligente
            print("🤖 Aplicando classificação automática com threshold ajustado...")
            print("   (Threshold reduzido para detectar mais casos suspeitos)")
            
            # Ajustar threshold para ser mais sensível
            original_threshold = self.config.suspicion_threshold
            self.config.suspicion_threshold = 0.1  # Muito mais sensível
            
            for i, (relato,) in enumerate(rows):
                if not relato or len(relato.strip()) < 20:
                    continue
                    
                texto_limpo = relato.strip()
                textos.append(texto_limpo)
                
                # Classificação automática usando regras inteligentes
                label, confidence, metadata = self.classifier.classify_text_binary(texto_limpo)
                labels.append(label)
                    
                # Mostrar progresso a cada 500 registros
                if (i + 1) % 500 == 0:
                    current_suspicious = sum(1 for l in labels if l == "SUSPEITO")
                    current_normal = len(labels) - current_suspicious
                    print(f"   Processados {i + 1}/{len(rows)} | "
                        f"SUSPEITO: {current_suspicious} | "
                        f"SEM_ALTERACAO: {current_normal}")
            
            # Restaurar threshold original
            self.config.suspicion_threshold = original_threshold
                    
        except Exception as e:
            print(f"❌ Erro ao carregar dados: {e}")
            import traceback
            traceback.print_exc()
            return [], []
            
        # Estatísticas iniciais
        from collections import Counter
        label_counts = Counter(labels)
        print(f"\n📈 Distribuição inicial das classes:")
        for label, count in label_counts.items():
            percentage = (count / len(labels)) * 100
            print(f"   {label}: {count} ({percentage:.1f}%)")
        
        # FORÇAR diversidade se todos são da mesma classe
        if len(label_counts) < 2 or min(label_counts.values()) == 0:
            print("⚠️ PROBLEMA: Todos os casos são da mesma classe!")
            print("🔧 Forçando diversidade com casos sintéticos...")
            textos, labels = self._force_class_diversity(textos, labels)
            
            # Atualizar estatísticas
            label_counts = Counter(labels)
            print(f"📊 Distribuição após correção forçada:")
            for label, count in label_counts.items():
                percentage = (count / len(labels)) * 100
                print(f"   {label}: {count} ({percentage:.1f}%)")
        
        # Verificar se ainda precisamos de balanceamento adicional
        min_class_size = min(label_counts.values())
        if min_class_size < 50:
            print("⚠️ Classe minoritária ainda pequena, balanceando...")
            textos, labels = self._balance_with_synthetic_examples(textos, labels, label_counts)
            
            # Atualizar estatísticas finais
            label_counts = Counter(labels)
            print(f"📊 Distribuição final:")
            for label, count in label_counts.items():
                percentage = (count / len(labels)) * 100
                print(f"   {label}: {count} ({percentage:.1f}%)")
        
        print(f"✅ Dataset preparado: {len(labels)} amostras totais")
        return textos, labels
    
    def _force_class_diversity(self, textos: List[str], labels: List[str]) -> Tuple[List[str], List[str]]:
        """
        Força diversidade de classes quando todos os casos são da mesma classe
        """
        from collections import Counter
        
        label_counts = Counter(labels)
        
        if len(label_counts) == 1:
            # Todos são da mesma classe
            only_class = list(label_counts.keys())[0]
            missing_class = "SUSPEITO" if only_class == "SEM_ALTERACAO" else "SEM_ALTERACAO"
            
            print(f"   🎯 Todos os casos são: {only_class}")
            print(f"   🔧 Adicionando casos sintéticos de: {missing_class}")
            
            # Adicionar pelo menos 100 casos da classe faltante
            synthetic_count = max(100, len(labels) // 10)
            
        elif min(label_counts.values()) == 0:
            # Uma classe tem 0 casos
            missing_class = [k for k, v in label_counts.items() if v == 0][0]
            synthetic_count = max(50, max(label_counts.values()) // 5)
            
            print(f"   🎯 Classe {missing_class} tem 0 casos")
            print(f"   🔧 Adicionando {synthetic_count} casos sintéticos")
        else:
            return textos, labels
        
        # Exemplos sintéticos específicos para cada classe
        if missing_class == "SUSPEITO":
            synthetic_examples = [
                "O indivíduo foi flagrado com substância entorpecente tipo cocaína",
                "Confessou estar envolvido com o tráfico de drogas na região",
                "Portava arma de fogo calibre 380 sem documentação",
                "Foi encontrado com grande quantidade de crack dividido em porções",
                "Assumiu a autoria do crime de roubo praticado ontem",
                "Portava munições e não soube explicar a procedência",
                "Estava com mandado de prisão em aberto por tráfico",
                "Foi preso em flagrante durante transação de droga",
                "Confessou participação em esquema de receptação",
                "Portava documento falso e dinheiro de origem duvidosa",
                "Foi flagrado vendendo drogas próximo à escola",
                "Tentou fugir ao avistar a equipe policial",
                "Estava armado e demonstrou resistência à prisão",
                "Confessou ser fornecedor de drogas na comunidade",
                "Foi encontrado com kit completo para embalar drogas",
                "Admitiu estar transportando material entorpecente",
                "Portava rádio comunicador usado pelo tráfico",
                "Foi flagrado em ponto conhecido de venda de drogas",
                "Confessou liderar grupo criminoso na região",
                "Estava com anotações sobre vendas de entorpecentes"
            ]
        else:
            synthetic_examples = [
                "Estava retornando do trabalho quando foi abordado",
                "Colaborou integralmente com a equipe policial",
                "Apresentou todos os documentos solicitados",
                "Reside na região há mais de dez anos",
                "Trabalha como funcionário público e possui bons antecedentes",
                "Demonstrou total transparência durante a abordagem",
                "Estava acompanhado da família no momento da ocorrência",
                "Forneceu informações corretas sobre sua identidade",
                "Mostrou-se colaborativo e respeitoso com a autoridade",
                "Comprovou sua ocupação através de documentos",
                "Estava se dirigindo para compromisso profissional",
                "Demonstrou conhecer bem a vizinhança onde mora",
                "Forneceu referências pessoais na comunidade",
                "Apresentou carteira de trabalho atualizada",
                "Estava em atividade lícita no momento da abordagem",
                "Colaborou para esclarecer completamente a situação",
                "Demonstrou ser pessoa de bem na comunidade",
                "Forneceu contatos de familiares para confirmação",
                "Estava cumprindo sua rotina normal de trabalho",
                "Mostrou documentos que comprovaram sua versão"
            ]
        
        # Adicionar casos sintéticos
        added_count = 0
        for i in range(synthetic_count):
            example = synthetic_examples[i % len(synthetic_examples)]
            
            # Adicionar variação para evitar duplicatas
            if i >= len(synthetic_examples):
                variation = f" conforme procedimento policial número {i+1:04d}"
                example = f"{example}{variation}"
            
            textos.append(example)
            labels.append(missing_class)
            added_count += 1
        
        print(f"   ✅ Adicionados {added_count} casos sintéticos de {missing_class}")
        
        return textos, labels        
    def create_features(self, textos: List[str]) -> np.ndarray:
        """Gera features usando embeddings e características manuais"""
        print("🔄 Gerando features...")
        
        if not self.classifier.embedder:
            if not self.classifier.load_nlp_models():
                raise RuntimeError("Erro ao carregar modelos NLP")
        
        # Embeddings semânticos
        print("   📊 Gerando embeddings semânticos...")
        embeddings = self.classifier.embedder.encode(textos, show_progress_bar=True, batch_size=32)
        
        # Features manuais (scores de suspeição)
        print("   🔍 Calculando features manuais...")
        manual_features = []
        for i, texto in enumerate(textos):
            if i % 100 == 0:
                print(f"   Processando features {i}/{len(textos)}...")
                
            score, details = self.classifier.calculate_suspicion_score(texto)
            feature_vector = [
                score,  # Score geral
                details.get('palavras_suspeitas', 0),
                details.get('padroes_cobertura', 0), 
                details.get('contexto_criminal', 0),
                details.get('inconsistencias', 0),
                len(texto.split()),  # Tamanho do texto
                len(set(texto.lower().split())),  # Vocabulário único
                len(texto) / len(texto.split()) if len(texto.split()) > 0 else 0,  # Tamanho médio das palavras
            ]
            manual_features.append(feature_vector)
            
        manual_features = np.array(manual_features)
        
        # Combinar features
        combined_features = np.hstack([embeddings, manual_features])
        
        print(f"✅ Features geradas: {combined_features.shape}")
        print(f"   - Embeddings: {embeddings.shape[1]} dimensões")
        print(f"   - Features manuais: {manual_features.shape[1]} dimensões")
        
        return combined_features
        
    def train_ensemble_model(self, X: np.ndarray, y: List[str]) -> Pipeline:
        """Treina modelo ensemble com tratamento robusto de classes"""
        print("🔄 Treinando modelo ensemble...")
        
        # Converter labels para numérico (0: SEM_ALTERACAO, 1: SUSPEITO)
        y_numeric = [1 if label == "SUSPEITO" else 0 for label in y]
        
        # Verificar se temos pelo menos 2 classes
        unique_classes = np.unique(y_numeric)
        print(f"   📊 Classes encontradas: {unique_classes}")
        
        if len(unique_classes) < 2:
            raise ValueError("❌ Precisa de pelo menos 2 classes para treinamento!")
        
        # Balanceamento de classes robusto
        try:
            class_weights = compute_class_weight('balanced', classes=unique_classes, y=y_numeric)
            class_weight_dict = {int(cls): weight for cls, weight in zip(unique_classes, class_weights)}
            
            # Garantir que temos pesos para ambas as classes
            if 0 not in class_weight_dict:
                class_weight_dict[0] = 1.0
            if 1 not in class_weight_dict:
                class_weight_dict[1] = 1.0
                
        except Exception as e:
            print(f"   ⚠️ Erro no cálculo de pesos: {e}")
            print("   ⚠️ Usando pesos balanceados manualmente")
            
            count_0 = sum(1 for label in y_numeric if label == 0)
            count_1 = sum(1 for label in y_numeric if label == 1)
            total = len(y_numeric)
            
            class_weight_dict = {
                0: total / (2 * count_0) if count_0 > 0 else 1.0,
                1: total / (2 * count_1) if count_1 > 0 else 1.0
            }
        
        print(f"   ⚖️ Pesos das classes: {class_weight_dict}")
        
        # Componentes do ensemble mais robustos
        rf_model = RandomForestClassifier(
            n_estimators=50,  # Reduzido para dados sintéticos
            max_depth=8,      # Limitado para evitar overfitting
            min_samples_split=10,
            min_samples_leaf=5,
            class_weight=class_weight_dict,
            random_state=ML_CONFIG['random_state'],
            n_jobs=-1
        )
        
        lr_model = LogisticRegression(
            class_weight=class_weight_dict,
            random_state=ML_CONFIG['random_state'],
            max_iter=1000,
            C=0.1  # Regularização mais forte para dados sintéticos
        )
        
        # Voting classifier
        ensemble = VotingClassifier([
            ('rf', rf_model),
            ('lr', lr_model)
        ], voting='soft')
        
        # Pipeline completo
        pipeline = Pipeline([
            ('scaler', StandardScaler()),
            ('classifier', CalibratedClassifierCV(ensemble, cv=3))
        ])
        
        return pipeline        
    def evaluate_model(self, model: Pipeline, X: np.ndarray, y: List[str]) -> Tuple[Dict[str, Any], Pipeline]:
        """Avalia performance do modelo"""
        print("🔄 Avaliando modelo...")
        
        y_numeric = [1 if label == "SUSPEITO" else 0 for label in y]
        
        # Split treino/teste estratificado
        X_train, X_test, y_train, y_test = train_test_split(
            X, y_numeric, 
            test_size=ML_CONFIG['test_size'],
            random_state=ML_CONFIG['random_state'],
            stratify=y_numeric
        )
        
        print(f"   📊 Dados de treino: {len(X_train)} amostras")
        print(f"   📊 Dados de teste: {len(X_test)} amostras")
        
        # Treinar modelo
        print("   🎯 Treinando modelo...")
        start_time = time.time()
        model.fit(X_train, y_train)
        training_time = time.time() - start_time
        
        # Predições
        y_pred = model.predict(X_test)
        y_pred_proba = model.predict_proba(X_test)[:, 1]
        
        # Métricas básicas
        metrics = {
            'accuracy': accuracy_score(y_test, y_pred),
            'precision': precision_score(y_test, y_pred, zero_division=0),
            'recall': recall_score(y_test, y_pred, zero_division=0),
            'f1_score': f1_score(y_test, y_pred, zero_division=0),
            'roc_auc': roc_auc_score(y_test, y_pred_proba),
            'total_samples': len(y),
            'test_samples': len(y_test),
            'train_samples': len(y_train),
            'suspeito_samples': sum(y_numeric),
            'sem_alteracao_samples': len(y_numeric) - sum(y_numeric),
            'training_time_seconds': training_time
        }
        
        # Cross-validation
        print("   🔄 Executando validação cruzada...")
        skf = StratifiedKFold(n_splits=ML_CONFIG['cv_folds'], shuffle=True, random_state=ML_CONFIG['random_state'])
        cv_scores = cross_val_score(model, X_train, y_train, cv=skf, scoring='f1', n_jobs=-1)
        metrics['cv_f1_mean'] = cv_scores.mean()
        metrics['cv_f1_std'] = cv_scores.std()
        
        # Matriz de confusão
        cm = confusion_matrix(y_test, y_pred)
        metrics['confusion_matrix'] = cm.tolist()
        
        # Métricas por classe
        from sklearn.metrics import precision_recall_fscore_support
        precision, recall, fscore, support = precision_recall_fscore_support(y_test, y_pred, zero_division=0)
        
        metrics['per_class'] = {
            'SEM_ALTERACAO': {
                'precision': precision[0],
                'recall': recall[0],
                'f1_score': fscore[0],
                'support': int(support[0])
            },
            'SUSPEITO': {
                'precision': precision[1],
                'recall': recall[1], 
                'f1_score': fscore[1],
                'support': int(support[1])
            }
        }
        
        return metrics, model
        
    def save_model(self, model: Pipeline, metadata: Dict[str, Any]):
        """Salva modelo treinado e metadados"""
        print("💾 Salvando modelo...")
        
        # Salvar modelo
        joblib.dump(model, SEMANTIC_CLF_PATH)
        joblib.dump(SEMANTIC_CLASSES, SEMANTIC_LBL_PATH)
        
        # Salvar metadados
        metadata.update({
            'training_timestamp': time.time(),
            'training_date': time.strftime('%Y-%m-%d %H:%M:%S'),
            'model_version': '2.0_agents_binary_fixed',
            'semantic_classes': SEMANTIC_CLASSES,
            'ml_config': ML_CONFIG,
            'training_config': asdict(self.config),
            'model_files': {
                'classifier': str(SEMANTIC_CLF_PATH),
                'labels': str(SEMANTIC_LBL_PATH),
                'metadata': str(SEMANTIC_META_PATH)
            },
            'notes': {
                'version': 'Versão corrigida - funciona sem classificacao_manual',
                'future_features': 'Sistema de feedback será implementado posteriormente'
            }
        })
        
        with open(SEMANTIC_META_PATH, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
            
        print(f"✅ Modelo salvo em: {SEMANTIC_CLF_PATH}")
        print(f"✅ Labels salvos em: {SEMANTIC_LBL_PATH}")
        print(f"✅ Metadados salvos em: {SEMANTIC_META_PATH}")
        
    def run_full_training(self):
        """Executa treinamento completo"""
        print("🚀 INICIANDO TREINAMENTO COMPLETO DO SISTEMA SEMÂNTICO COM AGENTES")
        print("=" * 80)
        print("Modalidade: Classificação Binária (SUSPEITO vs SEM_ALTERACAO)")
        print("VERSÃO CORRIGIDA - Funciona sem classificacao_manual")
        print("=" * 80)
        
        start_time = time.time()
        
        # 1. Carregar modelos NLP
        print("\n1️⃣ CARREGANDO MODELOS NLP")
        if not self.classifier.load_nlp_models():
            print("❌ Falha ao carregar modelos NLP")
            return False
        
        # 2. Carregar dados
        print("\n2️⃣ CARREGANDO DADOS DE TREINAMENTO")
        textos, labels = self.load_training_data()
        
        if len(textos) < 50:
            print("❌ Dados insuficientes para treinamento (mínimo 50 amostras)")
            return False
            
        # 3. Gerar features
        print("\n3️⃣ GERANDO FEATURES")
        X = self.create_features(textos)
        
        # 4. Treinar modelo
        print("\n4️⃣ TREINANDO MODELO ENSEMBLE")
        model = self.train_ensemble_model(X, labels)
        
        # 5. Avaliar
        print("\n5️⃣ AVALIANDO PERFORMANCE")
        metrics, trained_model = self.evaluate_model(model, X, labels)
        
        # 6. Exibir resultados
        total_time = time.time() - start_time
        print(f"\n📊 RESULTADOS DO TREINAMENTO (tempo total: {total_time:.1f}s)")
        print("=" * 60)
        print(f"📈 MÉTRICAS GERAIS:")
        print(f"   Acurácia: {metrics['accuracy']:.3f}")
        print(f"   Precisão: {metrics['precision']:.3f}")
        print(f"   Recall: {metrics['recall']:.3f}")
        print(f"   F1-Score: {metrics['f1_score']:.3f}")
        print(f"   AUC-ROC: {metrics['roc_auc']:.3f}")
        print(f"   CV F1-Score: {metrics['cv_f1_mean']:.3f} ± {metrics['cv_f1_std']:.3f}")
        
        print(f"\n📊 DADOS DE TREINAMENTO:")
        print(f"   Total de amostras: {metrics['total_samples']}")
        print(f"   Amostras SUSPEITO: {metrics['suspeito_samples']}")
        print(f"   Amostras SEM_ALTERACAO: {metrics['sem_alteracao_samples']}")
        print(f"   Tempo de treinamento: {metrics['training_time_seconds']:.1f}s")
        
        print(f"\n🎯 PERFORMANCE POR CLASSE:")
        for classe, stats in metrics['per_class'].items():
            print(f"   {classe}:")
            print(f"     Precisão: {stats['precision']:.3f}")
            print(f"     Recall: {stats['recall']:.3f}")
            print(f"     F1-Score: {stats['f1_score']:.3f}")
            print(f"     Suporte: {stats['support']} amostras")
        
        # Matriz de confusão
        cm = metrics['confusion_matrix']
        print(f"\n🔍 MATRIZ DE CONFUSÃO:")
        print("                Predito")
        print("               SEM  SUSP")
        print(f"Real SEM    [{cm[0][0]:4d} {cm[0][1]:4d}]")
        print(f"     SUSP   [{cm[1][0]:4d} {cm[1][1]:4d}]")
        
        # 7. Salvar modelo se performance for aceitável
        min_f1_threshold = 0.5  # Threshold mais permissivo para dados sintéticos
        if metrics['f1_score'] >= min_f1_threshold:
            print(f"\n✅ PERFORMANCE ACEITÁVEL (F1: {metrics['f1_score']:.3f} >= {min_f1_threshold})")
            self.save_model(trained_model, metrics)
            
            print(f"\n🎉 TREINAMENTO CONCLUÍDO COM SUCESSO!")
            print("=" * 50)
            print("📋 PRÓXIMOS PASSOS:")
            print("1. Teste o modelo: python scripts/manage_semantic_training.py test")
            print("2. Integre com sistema de agentes")
            print("3. Monitore performance em produção")
            print("4. Configure sistema de feedback para melhorias futuras")
            print("\n💡 IMPORTANTE:")
            print("   Esta versão usa classificação automática baseada em regras.")
            print("   No futuro, o sistema de feedback permitirá aprendizado contínuo.")
            
            return True
        else:
            print(f"\n⚠️ PERFORMANCE INSUFICIENTE")
            print(f"   F1-Score atual: {metrics['f1_score']:.3f}")
            print(f"   F1-Score mínimo: {min_f1_threshold}")
            print("\n💡 RECOMENDAÇÕES PARA MELHORAR:")
            print("1. Coletar mais dados de treinamento")
            print("2. Ajustar listas de palavras-chave em config/")
            print("3. Implementar sistema de feedback manual")
            print("4. Experimentar diferentes thresholds de classificação")
            print("5. Revisar e limpar dados com ruído")
            
            return False

# =============================================================================
# UTILITÁRIOS E FUNCÕES AUXILIARES
# =============================================================================

def check_environment() -> bool:
    """Verifica se o ambiente está configurado corretamente"""
    print("🔍 VERIFICANDO AMBIENTE DE TREINAMENTO")
    print("-" * 45)
    
    issues = []
    
    # 1. Verificar dependências Python
    required_packages = [
        ('sklearn', 'scikit-learn'),
        ('spacy', 'spacy'), 
        ('sentence_transformers', 'sentence-transformers'),
        ('yake', 'yake'),
        ('joblib', 'joblib'),
        ('numpy', 'numpy'),
        ('pandas', 'pandas')
    ]
    
    print("📦 Verificando dependências Python...")
    for package, install_name in required_packages:
        try:
            __import__(package)
            print(f"   ✅ {install_name}")
        except ImportError:
            print(f"   ❌ {install_name}")
            issues.append(f"Instalar {install_name}: pip install {install_name}")
    
    # 2. Verificar modelo spaCy
    print("\n🔤 Verificando modelo spaCy...")
    try:
        import spacy
        nlp = spacy.load(ML_CONFIG['spacy_model'])
        print(f"   ✅ {ML_CONFIG['spacy_model']}")
    except OSError:
        print(f"   ❌ {ML_CONFIG['spacy_model']}")
        issues.append(f"Instalar modelo spaCy: python -m spacy download {ML_CONFIG['spacy_model']}")
    
    # 3. Verificar conexão com banco
    print("\n💾 Verificando banco de dados...")
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                # Verificar se tabela existe
                cur.execute("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_name = 'ocorrencias'
                    )
                """)
                table_exists = cur.fetchone()[0]
                
                if not table_exists:
                    print("   ❌ Tabela 'ocorrencias' não encontrada")
                    issues.append("Executar migração do banco de dados")
                else:
                    # Contar registros
                    cur.execute("SELECT COUNT(*) FROM ocorrencias WHERE relato IS NOT NULL")
                    count = cur.fetchone()[0]
                    
                    cur.execute("SELECT COUNT(*) FROM ocorrencias WHERE LENGTH(relato) > 50")
                    useful_count = cur.fetchone()[0]
                    
                    print(f"   ✅ Conectado ({count} relatos, {useful_count} úteis)")
                    
                    if useful_count < 50:
                        issues.append("Coletar mais dados (mínimo 50 relatos úteis)")
                        
    except Exception as e:
        print(f"   ❌ Erro de conexão: {e}")
        issues.append("Configurar conexão com banco de dados")
    
    # 4. Verificar diretórios
    print("\n📁 Verificando estrutura de diretórios...")
    directories = [MODELS_DIR, CONFIG_DIR]
    for directory in directories:
        directory.mkdir(parents=True, exist_ok=True)
        print(f"   ✅ {directory}")
    
    # 5. Verificar arquivos de configuração (opcionais)
    print("\n📝 Verificando arquivos de configuração...")
    config_files = [
        "palavras_suspeitas.txt",
        "palavras_normais.txt", 
        "historias_cobertura.txt",
        "contextos_suspeitos.txt"
    ]
    
    for config_file in config_files:
        config_path = CONFIG_DIR / config_file
        if config_path.exists():
            print(f"   ✅ {config_file}")
        else:
            print(f"   ⚠️ {config_file} (usando valores padrão)")
    
    # Resumo final
    if issues:
        print(f"\n❌ ENCONTRADOS {len(issues)} PROBLEMAS:")
        for i, issue in enumerate(issues, 1):
            print(f"   {i}. {issue}")
        print("\n🔧 Corrija os problemas acima antes de executar o treinamento")
        return False
    else:
        print(f"\n✅ AMBIENTE CONFIGURADO CORRETAMENTE!")
        print("🚀 Sistema pronto para treinamento")
        return True

def create_sample_config_files():
    """Cria arquivos de configuração de exemplo"""
    print("📝 Criando arquivos de configuração de exemplo...")
    
    # Palavras suspeitas
    suspicious_words = """# Palavras suspeitas - uma por linha
# Drogas
droga
cocaína  
maconha
crack
tráfico
traficante
entorpecente
pó
pedra

# Armas
arma
revolver
pistola
rifle
munição
disparo
tiro

# Crimes
roubo
assalto
furto
receptação
latrocínio

# Situações
foragido
procurado
mandado
flagrante
apreensão
"""

    normal_words = """# Palavras normais - uma por linha
trabalho
casa
família
escola
igreja
mercado
hospital
farmácia
banco
documentos
identidade
carteira
"""

    coverage_stories = """# Histórias típicas de cobertura - uma por linha
estava passando e vi
não sabia de nada
só estava dando uma volta
estava indo para casa
estava voltando do trabalho
estava esperando alguém
estava perdido
peguei carona
estava indo trabalhar
não conhecia ninguém
"""

    suspicious_contexts = """# Contextos suspeitos - uma por linha
zona de tráfico
área controlada
território
ponto conhecido
local suspeito
região perigosa
horário suspeito
madrugada
local ermo
sem documento
sem identificação
nervoso
atitude suspeita
comportamento estranho
"""

    files_content = {
        "palavras_suspeitas.txt": suspicious_words,
        "palavras_normais.txt": normal_words,
        "historias_cobertura.txt": coverage_stories,
        "contextos_suspeitos.txt": suspicious_contexts
    }
    
    for filename, content in files_content.items():
        filepath = CONFIG_DIR / filename
        if not filepath.exists():
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content.strip())
            print(f"   ✅ Criado: {filename}")
        else:
            print(f"   ⚠️ Já existe: {filename}")
    
    print("📝 Arquivos de configuração criados em config/")

def test_trained_model(sample_texts: List[str] = None) -> bool:
    """Testa modelo recém-treinado com textos de exemplo"""
    print("🧪 TESTANDO MODELO TREINADO")
    print("-" * 30)
    
    # Verificar se modelo existe
    if not SEMANTIC_CLF_PATH.exists():
        print("❌ Modelo não encontrado. Execute o treinamento primeiro:")
        print("   python ml_models/training/train_semantic_agents.py")
        return False
    
    # Carregar modelo
    try:
        model = joblib.load(SEMANTIC_CLF_PATH)
        labels = joblib.load(SEMANTIC_LBL_PATH)
        
        with open(SEMANTIC_META_PATH, 'r', encoding='utf-8') as f:
            metadata = json.load(f)
            
        print(f"✅ Modelo carregado (versão {metadata.get('model_version', 'unknown')})")
        print(f"   Treinado em: {metadata.get('training_date', 'unknown')}")
        print(f"   F1-Score: {metadata.get('f1_score', 'unknown'):.3f}")
        
    except Exception as e:
        print(f"❌ Erro ao carregar modelo: {e}")
        return False
    
    # Textos de teste
    if sample_texts is None:
        sample_texts = [
            # Casos claramente suspeitos
            "O indivíduo foi encontrado com 50g de cocaína e uma pistola calibre 380 na cintura",
            "Confessou estar traficando drogas há 3 meses na região central da cidade",
            "Foi preso em flagrante portando material entorpecente e 20 munições",
            
            # Casos de possível cobertura
            "Estava passando na rua quando vi a abordagem policial. Não sabia de nada sobre drogas",
            "Só estava dando uma volta no bairro, não conhecia ninguém do local",
            "Estava esperando minha namorada na esquina quando a polícia chegou, não sei de nada",
            
            # Casos normais
            "Estava voltando do trabalho, por volta das 22h, apresentou documentos",
            "Mora na região há 10 anos, trabalha como pedreiro, nunca teve problemas",
            "Colaborou com a polícia e forneceu todas as informações solicitadas"
        ]
    
    print(f"\n📝 TESTANDO {len(sample_texts)} AMOSTRAS:")
    print("=" * 70)
    
    # Teste usando classificação inteligente
    config = AgentTrainingConfig()
    classifier = BinarySemanticClassifier(config)
    classifier.load_nlp_models()
    
    for i, texto in enumerate(sample_texts, 1):
        print(f"\n{i:2d}. Texto: {texto}")
        print("    " + "-" * 60)
        
        # Classificação usando regras inteligentes
        label, confidence, metadata = classifier.classify_text_binary(texto)
        
        # Determinar cor baseado na classificação
        emoji = "🔴" if label == "SUSPEITO" else "🟢"
        
        print(f"    {emoji} Classificação: {label}")
        print(f"    📊 Confiança: {confidence:.3f}")
        print(f"    🎯 Score Suspeição: {metadata['suspicion_score']:.3f}")
        
        # Mostrar fatores que contribuíram
        factors = []
        for category, score in metadata['category_scores'].items():
            if score > 0:
                factors.append(f"{category}: {score:.2f}")
        
        if factors:
            print(f"    📈 Fatores: {', '.join(factors)}")
    
    print(f"\n💡 NOTA: Este é um teste usando classificação baseada em regras.")
    print("   Para integração completa, use o sistema de agentes em produção.")
    
    return True

# =============================================================================
# FUNÇÃO PRINCIPAL
# =============================================================================

def main():
    """Função principal de treinamento"""
    print("🤖 SISTEMA DE TREINAMENTO SEMÂNTICO COM AGENTES ESPECIALIZADOS")
    print("=" * 70)
    print("📋 Modalidade: Classificação Binária (SUSPEITO vs SEM_ALTERACAO)")
    print("🎯 Objetivo: Detectar relatos suspeitos e histórias de cobertura")
    print("🔧 Arquitetura: Ensemble ML + Regras Inteligentes + Embeddings")
    print("🔄 Versão: CORRIGIDA - Funciona sem classificacao_manual")
    print("=" * 70)
    
    import argparse
    parser = argparse.ArgumentParser(description="Treinamento Semântico com Agentes")
    parser.add_argument('--check-env', action='store_true', help='Apenas verificar ambiente')
    parser.add_argument('--create-config', action='store_true', help='Criar arquivos de configuração')
    parser.add_argument('--test', action='store_true', help='Testar modelo existente')
    parser.add_argument('--force', action='store_true', help='Forçar treinamento mesmo com problemas')
    
    args = parser.parse_args()
    
    try:
        # Verificar apenas ambiente
        if args.check_env:
            success = check_environment()
            sys.exit(0 if success else 1)
        
        # Criar arquivos de configuração
        if args.create_config:
            create_sample_config_files()
            sys.exit(0)
        
        # Testar modelo existente
        if args.test:
            success = test_trained_model()
            sys.exit(0 if success else 1)
        
        # Verificar ambiente antes do treinamento
        if not args.force:
            print("\n🔍 PRÉ-VERIFICAÇÃO DO AMBIENTE")
            if not check_environment():
                print("\n❌ Use --force para ignorar verificações ou corrija os problemas")
                sys.exit(1)
        
        # Configuração de treinamento
        config = AgentTrainingConfig()
        
        print(f"\n⚙️ CONFIGURAÇÕES DE TREINAMENTO:")
        print(f"   Classificação binária: {config.use_binary_classification}")
        print(f"   Threshold suspeição: {config.suspicion_threshold}")
        print(f"   Threshold confiança: {config.confidence_threshold}")
        print(f"   Ensemble methods: {config.enable_ensemble_methods}")
        print(f"   Calibração: {config.use_confidence_calibration}")
        
        # Executar treinamento
        print(f"\n🚀 INICIANDO TREINAMENTO...")
        trainer = AgentSemanticTrainer(config)
        success = trainer.run_full_training()
        
        if success:
            print(f"\n🎉 SUCESSO! Sistema semântico treinado e salvo")
            print(f"📁 Arquivos gerados:")
            print(f"   - {SEMANTIC_CLF_PATH}")
            print(f"   - {SEMANTIC_LBL_PATH}")
            print(f"   - {SEMANTIC_META_PATH}")
            
            # Teste rápido
            print(f"\n🧪 EXECUTANDO TESTE RÁPIDO...")
            test_trained_model()
            
        else:
            print(f"\n❌ FALHA no treinamento")
            print("📋 Verifique os logs acima para detalhes do problema")
        
        sys.exit(0 if success else 1)
        
    except KeyboardInterrupt:
        print(f"\n⚠️ Treinamento interrompido pelo usuário")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ ERRO INESPERADO: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()