# ml_system.py - Sistema de ML aprimorado
import os
import pickle
import joblib
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from sklearn.metrics import classification_report, confusion_matrix
from sklearn.model_selection import cross_val_score, train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ModelManager:
    """Gerenciador central dos modelos de ML."""
    
    def __init__(self, models_dir="models"):
        self.models_dir = models_dir
        os.makedirs(models_dir, exist_ok=True)
        self.models = {}
        self.scalers = {}
        self.last_training = {}
    
    def save_model(self, model, model_name: str, version: str = None):
        """Salva modelo com versionamento."""
        if version is None:
            version = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        model_path = os.path.join(self.models_dir, f"{model_name}_v{version}.joblib")
        joblib.dump(model, model_path)
        
        # Salva também como versão atual
        current_path = os.path.join(self.models_dir, f"{model_name}_current.joblib")
        joblib.dump(model, current_path)
        
        logger.info(f"Modelo {model_name} salvo: {model_path}")
        self.last_training[model_name] = datetime.now()
        
        return model_path
    
    def load_model(self, model_name: str, version: str = "current"):
        """Carrega modelo específico."""
        model_path = os.path.join(self.models_dir, f"{model_name}_{version}.joblib")
        
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"Modelo não encontrado: {model_path}")
        
        model = joblib.load(model_path)
        self.models[model_name] = model
        logger.info(f"Modelo {model_name} carregado: {model_path}")
        
        return model
    
    def needs_retraining(self, model_name: str, max_age_days: int = 30) -> bool:
        """Verifica se modelo precisa ser retreinado."""
        if model_name not in self.last_training:
            return True
        
        age = datetime.now() - self.last_training[model_name]
        return age.days > max_age_days

class ImprovedSemanticAnalyzer:
    """Analisador semântico melhorado com cache e validação."""
    
    def __init__(self, model_manager: ModelManager):
        self.model_manager = model_manager
        self.cache = {}
        self.confidence_threshold = 0.7
        
    def analyze_text_batch(self, texts: list) -> list:
        """Análise em lote para melhor performance."""
        results = []
        
        # Separa textos já analisados dos novos
        cached_results = {}
        new_texts = []
        
        for i, text in enumerate(texts):
            text_hash = hash(text)
            if text_hash in self.cache:
                cached_results[i] = self.cache[text_hash]
            else:
                new_texts.append((i, text))
        
        # Processa textos novos em lote
        if new_texts:
            indices, text_list = zip(*new_texts)
            
            try:
                # Importa módulos necessários
                from semantic_local import analyze_text
                
                new_results = []
                for text in text_list:
                    result = analyze_text(text)
                    # Adiciona confiança baseada na pontuação
                    result['confidence'] = min(result['pontuacao'] / 100.0, 1.0)
                    new_results.append(result)
                
                # Atualiza cache
                for (idx, text), result in zip(new_texts, new_results):
                    text_hash = hash(text)
                    self.cache[text_hash] = result
                    cached_results[idx] = result
                    
            except Exception as e:
                logger.error(f"Erro na análise semântica: {e}")
                # Fallback para análise individual
                for idx, text in new_texts:
                    cached_results[idx] = {"classe": "OUTROS", "pontuacao": 0, "confidence": 0}
        
        # Reconstrói lista de resultados na ordem original
        for i in range(len(texts)):
            results.append(cached_results[i])
        
        return results
    
    def get_suspicious_patterns(self, texts: list) -> dict:
        """Identifica padrões suspeitos em conjunto de textos."""
        results = self.analyze_text_batch(texts)
        
        patterns = {
            "high_risk_count": sum(1 for r in results if r['pontuacao'] > 80),
            "medium_risk_count": sum(1 for r in results if 50 < r['pontuacao'] <= 80),
            "low_risk_count": sum(1 for r in results if r['pontuacao'] <= 50),
            "common_keywords": {},
            "risk_evolution": []
        }
        
        # Analisa palavras-chave mais comuns
        all_keywords = []
        for result in results:
            if 'keywords' in result:
                all_keywords.extend([kw['term'] for kw in result['keywords'][:5]])
        
        from collections import Counter
        patterns['common_keywords'] = dict(Counter(all_keywords).most_common(10))
        
        return patterns

class RouteRiskAnalyzer:
    """Analisador de risco de rotas melhorado."""
    
    def __init__(self, model_manager: ModelManager):
        self.model_manager = model_manager
        
    def build_enhanced_features(self, passagens: list) -> tuple:
        """Constrói features melhoradas para análise de rotas."""
        if not passagens:
            return None, None
        
        df = pd.DataFrame(passagens)
        df['datahora'] = pd.to_datetime(df['datahora'])
        df = df.sort_values('datahora')
        
        features = []
        
        # Features básicas
        total_passagens = len(df)
        unique_municipios = df['municipio'].nunique()
        unique_rodovias = df['rodovia'].nunique()
        
        # Features temporais
        if len(df) > 1:
            duracao_total = (df['datahora'].max() - df['datahora'].min()).total_seconds() / 3600
            velocidade_media = unique_municipios / max(duracao_total, 1) if duracao_total > 0 else 0
        else:
            duracao_total = 0
            velocidade_media = 0
        
        # Features de padrão
        hora_passagens = df['datahora'].dt.hour
        passagens_noturnas = sum((hora_passagens >= 22) | (hora_passagens <= 6))
        passagens_fins_semana = sum(df['datahora'].dt.weekday >= 5)
        
        # Features geográficas
        municipios_fronteira = ['Foz do Iguaçu', 'Corumbá', 'Uruguaiana', 'Santana do Livramento']
        passagens_fronteira = sum(df['municipio'].isin(municipios_fronteira))
        
        # Features de risco
        ilicito_ida_count = sum(df.get('ilicito_ida', [False] * len(df)))
        ilicito_volta_count = sum(df.get('ilicito_volta', [False] * len(df)))
        
        features.extend([
            total_passagens,
            unique_municipios,
            unique_rodovias,
            duracao_total,
            velocidade_media,
            passagens_noturnas / max(total_passagens, 1),
            passagens_fins_semana / max(total_passagens, 1),
            passagens_fronteira / max(total_passagens, 1),
            ilicito_ida_count / max(total_passagens, 1),
            ilicito_volta_count / max(total_passagens, 1)
        ])
        
        # Label (para treinamento)
        label = "ILICITO" if (ilicito_ida_count > 0 or ilicito_volta_count > 0) else "NORMAL"
        
        return np.array(features).reshape(1, -1), label

class ComprehensiveRiskAssessor:
    """Avaliador de risco integrado."""
    
    def __init__(self):
        self.model_manager = ModelManager()
        self.semantic_analyzer = ImprovedSemanticAnalyzer(self.model_manager)
        self.route_analyzer = RouteRiskAnalyzer(self.model_manager)
    
    def assess_vehicle_risk(self, placa: str, include_history: bool = True) -> dict:
        """Avaliação completa de risco de um veículo."""
        try:
            # Busca dados (assumindo função existente)
            from analisar_placa import fetch_passagens_duplo, fetch_ocorrencias_duplo
            
            passagens = fetch_passagens_duplo(placa)
            ocorrencias = fetch_ocorrencias_duplo(placa)
            
            # Análise de rotas
            route_risk = 0.0
            route_features = None
            
            if passagens:
                try:
                    route_clf = self.model_manager.load_model("route_classifier")
                    route_features, _ = self.route_analyzer.build_enhanced_features(passagens)
                    
                    if route_features is not None:
                        route_proba = route_clf.predict_proba(route_features)[0]
                        route_risk = max(route_proba)
                        
                except Exception as e:
                    logger.warning(f"Erro na análise de rotas: {e}")
            
            # Análise semântica
            semantic_risk = 0.0
            semantic_details = []
            
            if ocorrencias:
                try:
                    texts = [oc.get('relato', '') for oc in ocorrencias if oc.get('relato')]
                    if texts:
                        results = self.semantic_analyzer.analyze_text_batch(texts)
                        semantic_details = results
                        # Calcula risco médio ponderado pela confiança
                        weighted_risks = [r['pontuacao'] * r['confidence'] for r in results if r['confidence'] > 0.3]
                        if weighted_risks:
                            semantic_risk = np.mean(weighted_risks) / 100.0
                            
                except Exception as e:
                    logger.warning(f"Erro na análise semântica: {e}")
            
            # Cálculo do risco final
            final_risk = self._calculate_final_risk(route_risk, semantic_risk, passagens, ocorrencias)
            
            return {
                "placa": placa,
                "risk_score": final_risk,
                "risk_level": self._get_risk_level(final_risk),
                "route_risk": route_risk,
                "semantic_risk": semantic_risk,
                "analysis_details": {
                    "total_passages": len(passagens) if passagens else 0,
                    "total_occurrences": len(ocorrencias) if ocorrencias else 0,
                    "semantic_details": semantic_details[:5],  # Primeiros 5 relatos
                    "confidence": self._calculate_confidence(route_features, semantic_details)
                },
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Erro na avaliação de risco para {placa}: {e}")
            return {
                "placa": placa,
                "risk_score": 0.0,
                "risk_level": "UNKNOWN",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    def _calculate_final_risk(self, route_risk: float, semantic_risk: float, 
                            passagens: list, ocorrencias: list) -> float:
        """Calcula risco final com pesos adaptativos."""
        # Pesos base
        route_weight = 0.6
        semantic_weight = 0.4
        
        # Ajusta pesos baseado na quantidade de dados
        if passagens and len(passagens) < 5:
            route_weight *= 0.7  # Reduz confiança em poucas passagens
        
        if ocorrencias and len([o for o in ocorrencias if o.get('relato')]) < 3:
            semantic_weight *= 0.7  # Reduz confiança em poucos relatos
        
        # Normaliza pesos
        total_weight = route_weight + semantic_weight
        route_weight /= total_weight
        semantic_weight /= total_weight
        
        return route_weight * route_risk + semantic_weight * semantic_risk
    
    def _get_risk_level(self, risk_score: float) -> str:
        """Converte score numérico em nível de risco."""
        if risk_score >= 0.8:
            return "MUITO_ALTO"
        elif risk_score >= 0.6:
            return "ALTO"
        elif risk_score >= 0.4:
            return "MEDIO"
        elif risk_score >= 0.2:
            return "BAIXO"
        else:
            return "MUITO_BAIXO"
    
    def _calculate_confidence(self, route_features, semantic_details: list) -> float:
        """Calcula confiança na análise."""
        confidence_factors = []
        
        # Confiança baseada em dados de rota
        if route_features is not None:
            confidence_factors.append(0.8)  # Alta confiança se há dados suficientes
        else:
            confidence_factors.append(0.3)
        
        # Confiança baseada em análise semântica
        if semantic_details:
            avg_semantic_confidence = np.mean([d['confidence'] for d in semantic_details])
            confidence_factors.append(avg_semantic_confidence)
        else:
            confidence_factors.append(0.3)
        
        return np.mean(confidence_factors)