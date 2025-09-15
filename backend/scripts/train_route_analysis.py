#!/usr/bin/env python3
"""
Treinamento de Análise de Rotas e Padrões de Viagem
==================================================

Este script analisa rotas de veículos para detectar padrões de viagens ilícitas,
incluindo ida e volta, frequência, horários suspeitos e trajetos conhecidos.
"""

import os
import sys
import json
import joblib
import psycopg
import pandas as pd
import numpy as np
from pathlib import Path
from typing import List, Tuple, Dict, Any, Set
from datetime import datetime, timedelta
from collections import defaultdict, Counter
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report, accuracy_score, precision_recall_curve
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler, LabelEncoder
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

class RouteAnalysisTrainer:
    """Treinador especializado em análise de rotas e padrões de viagem"""
    
    def __init__(self):
        self.model = None
        self.optimal_threshold = 0.35
        self.route_patterns = {}
        self.vehicle_history = defaultdict(list)
        
        # ROTAS CONHECIDAS COMO SUSPEITAS (fronteiras, áreas de risco)
        self.suspicious_routes = {
            'fronteira', 'fronteira brasil', 'fronteira argentina', 'fronteira paraguai',
            'fronteira uruguai', 'fronteira bolívia', 'fronteira colômbia',
            'triângulo das bermudas', 'região do pantanal', 'mato grosso do sul',
            'rio grande do sul', 'santa catarina', 'paraná', 'são paulo',
            'rio de janeiro', 'minas gerais', 'goiás', 'mato grosso',
            'acre', 'rondônia', 'amazonas', 'roraima', 'amapá', 'pará'
        }
        
        # HORÁRIOS SUSPEITOS (madrugada, horários não comerciais)
        self.suspicious_hours = {
            '00:00', '01:00', '02:00', '03:00', '04:00', '05:00',
            '22:00', '23:00', '23:30', '00:30', '01:30', '02:30'
        }
        
        # PADRÕES DE IDA E VOLTA SUSPEITOS
        self.round_trip_patterns = {
            'ida e volta', 'ida e retorno', 'ida volta', 'ida retorno',
            'mesmo dia', 'mesmo trajeto', 'trajeto idêntico', 'rota idêntica',
            'frequência alta', 'muitas viagens', 'viagens constantes'
        }
        
        # INDICADORES DE VIAGEM ILÍCITA
        self.illicit_travel_indicators = {
            'sem destino claro', 'destino incerto', 'sem justificativa',
            'viagem sem motivo', 'sem explicação', 'destino suspeito',
            'rota incomum', 'trajeto estranho', 'caminho suspeito',
            'frequência suspeita', 'padrão estranho', 'comportamento repetitivo'
        }
        
        # ÁREAS DE ALTO RISCO (conhecidas por tráfico, contrabando)
        self.high_risk_areas = {
            'fronteira seca', 'área de risco', 'zona de conflito',
            'região perigosa', 'área suspeita', 'local de risco',
            'ponto de tráfico', 'área de contrabando', 'zona de drogas'
        }
    
    def get_connection(self):
        """Cria conexão com banco"""
        try:
            return psycopg.connect(**DB_CONFIG)
        except Exception as e:
            print(f"❌ Erro de conexão: {e}")
            return None
    
    def load_route_data(self, limit: int = 30000) -> Tuple[List[Dict], List[str]]:
        """Carrega dados de rotas e cria labels baseadas em padrões"""
        print(f"🔄 Carregando {limit} ocorrências com dados de rota...")
        
        conn = self.get_connection()
        if not conn:
            return [], []
        
        route_data = []
        labels = []
        
        try:
            with conn.cursor() as cur:
                # Buscar ocorrências com informações de rota, localização e horário
                cur.execute("""
                    SELECT 
                        o.relato,
                        o.datahora,
                        o.datahora_fim,
                        o.ocupantes,
                        o.presos,
                        o.veiculos,
                        o.id as ocorrencia_id,
                        v.placa,
                        v.marca_modelo,
                        v.tipo,
                        v.ano_modelo,
                        v.cor,
                        v.local_emplacamento,
                        v.transferencia_recente,
                        v.comunicacao_venda,
                        v.crime_prf,
                        v.abordagem_prf
                    FROM ocorrencias o
                    LEFT JOIN veiculos v ON o.veiculo_id = v.id
                    WHERE o.relato IS NOT NULL 
                    AND o.relato != '' 
                    AND LENGTH(o.relato) > 30
                    ORDER BY RANDOM()
                    LIMIT %s
                """, (limit,))
                
                for row in cur.fetchall():
                    relato, datahora, datahora_fim, ocupantes, presos, veiculos, \
                    ocorrencia_id, placa, marca_modelo, tipo, ano_modelo, cor, \
                    local_emplacamento, transferencia_recente, comunicacao_venda, \
                    crime_prf, abordagem_prf = row
                    
                    if relato and len(relato.strip()) > 10:
                        route_info = {
                            'relato': relato.strip(),
                            'datahora': datahora,
                            'datahora_fim': datahora_fim,
                            'ocupantes': ocupantes,
                            'presos': presos,
                            'veiculos': veiculos,
                            'ocorrencia_id': ocorrencia_id,
                            'placa': placa,
                            'marca_modelo': marca_modelo,
                            'tipo': tipo,
                            'ano_modelo': ano_modelo,
                            'cor': cor,
                            'local_emplacamento': local_emplacamento,
                            'transferencia_recente': transferencia_recente,
                            'comunicacao_venda': comunicacao_venda,
                            'crime_prf': crime_prf,
                            'abordagem_prf': abordagem_prf
                        }
                        route_data.append(route_info)
                
                print(f"✅ Carregados {len(route_data)} ocorrências com dados de rota")
                
        except Exception as e:
            print(f"❌ Erro ao carregar dados: {e}")
        finally:
            conn.close()
        
        # Analisar padrões de rota e criar labels
        print("🧠 Analisando padrões de rota e criando labels...")
        labels = self.analyze_route_patterns(route_data)
        
        return route_data, labels
    
    def analyze_route_patterns(self, route_data: List[Dict]) -> List[str]:
        """Analisa padrões de rota para criar labels inteligentes"""
        labels = []
        suspeito_count = 0
        normal_count = 0
        
        # Agrupar por placa para analisar histórico
        vehicle_groups = defaultdict(list)
        for i, data in enumerate(route_data):
            if data['placa']:
                vehicle_groups[data['placa']].append((i, data))
        
        print(f"📊 Analisando {len(vehicle_groups)} veículos únicos...")
        
        for i, data in enumerate(route_data):
            # Calcular score de suspeição baseado em padrões de rota
            suspicion_score = self.calculate_route_suspicion(data, vehicle_groups)
            
            # Classificar baseado no score (mais seletivo)
            if suspicion_score > 0.3:  # Threshold ajustado para scores menores
                labels.append('SUSPEITO')
                suspeito_count += 1
            else:
                labels.append('SEM_ALTERACAO')
                normal_count += 1
        
        print(f"📊 Labels de rota: {suspeito_count} SUSPEITO, {normal_count} SEM_ALTERACAO")
        return labels
    
    def calculate_route_suspicion(self, data: Dict, vehicle_groups: Dict) -> float:
        """Calcula suspeição baseada em padrões de rota"""
        score = 0.0
        relato_lower = data['relato'].lower()
        
        # 1. ANÁLISE DE LOCALIZAÇÃO
        location_score = 0.0
        if data['local_emplacamento']:
            local_lower = data['local_emplacamento'].lower()
            if any(area in local_lower for area in self.suspicious_routes):
                location_score += 0.3
        
        # 2. ANÁLISE DE HORÁRIO
        time_score = 0.0
        if data['datahora']:
            hora_str = str(data['datahora'])
            if any(hora in hora_str for hora in self.suspicious_hours):
                time_score += 0.2
        
        # 3. ANÁLISE DE PADRÕES DE IDA E VOLTA
        round_trip_score = 0.0
        if any(pattern in relato_lower for pattern in self.round_trip_patterns):
            round_trip_score += 0.3
        
        # 4. ANÁLISE DE INDICADORES DE VIAGEM ILÍCITA
        illicit_score = 0.0
        if any(indicator in relato_lower for indicator in self.illicit_travel_indicators):
            illicit_score += 0.2
        
        # 5. ANÁLISE DE ÁREAS DE ALTO RISCO
        risk_area_score = 0.0
        if any(area in relato_lower for area in self.high_risk_areas):
            risk_area_score += 0.3
        
        # 6. ANÁLISE DE HISTÓRICO DO VEÍCULO (frequência, padrões)
        history_score = 0.0
        if data['placa'] and data['placa'] in vehicle_groups:
            vehicle_history = vehicle_groups[data['placa']]
            if len(vehicle_history) > 5:  # Veículo com muitas ocorrências
                history_score += 0.2
            
            # Verificar se há padrões de ida e volta
            if len(vehicle_history) > 2:
                # Analisar se há ocorrências em locais similares
                locations = [h[1]['local_emplacamento'] for h in vehicle_history if h[1]['local_emplacamento']]
                if len(set(locations)) < len(locations) * 0.5:  # Muitos locais repetidos
                    history_score += 0.3
        
        # 7. ANÁLISE DE INDICADORES ESPECÍFICOS DO VEÍCULO
        vehicle_score = 0.0
        # Ajustar scores baseado no contexto do relato
        if data['crime_prf']:  # Veículo com histórico de crime
            # Só adicionar score se o relato mencionar comportamento suspeito
            if any(word in relato_lower for word in ['suspeito', 'nervoso', 'mentiu', 'contradição', 'evadir', 'fuga']):
                vehicle_score += 0.3
        if data['abordagem_prf']:  # Veículo com histórico de abordagem
            # Só adicionar score se houver padrões suspeitos no relato
            if any(word in relato_lower for word in ['frequência', 'muitas vezes', 'repetido', 'constante']):
                vehicle_score += 0.2
        if data['transferencia_recente']:  # Transferência recente (suspeito)
            vehicle_score += 0.2
        
        # Score final
        total_score = location_score + time_score + round_trip_score + illicit_score + risk_area_score + history_score + vehicle_score
        
        # Normalizar entre 0 e 1
        return min(max(total_score, 0.0), 1.0)
    
    def create_route_features(self, route_data: List[Dict]) -> List[str]:
        """Cria features específicas para análise de rotas"""
        enhanced_texts = []
        
        for data in route_data:
            relato_lower = data['relato'].lower()
            enhanced_text = data['relato']
            
            # Adicionar informações de localização
            if data['local_emplacamento']:
                enhanced_text += f" [LOCAL_EMPLACAMENTO:{data['local_emplacamento']}]"
            
            # Adicionar informações de horário
            if data['datahora']:
                enhanced_text += f" [DATAHORA:{data['datahora']}]"
            
            # Adicionar informações do veículo
            if data['placa']:
                enhanced_text += f" [PLACA:{data['placa']}]"
            if data['marca_modelo']:
                enhanced_text += f" [MARCA_MODELO:{data['marca_modelo']}]"
            if data['cor']:
                enhanced_text += f" [COR:{data['cor']}]"
            if data['tipo']:
                enhanced_text += f" [TIPO:{data['tipo']}]"
            
            # Adicionar indicadores específicos do veículo
            if data['crime_prf']:
                enhanced_text += f" [CRIME_PRF:{data['crime_prf']}]"
            if data['abordagem_prf']:
                enhanced_text += f" [ABORDAGEM_PRF:{data['abordagem_prf']}]"
            if data['transferencia_recente']:
                enhanced_text += f" [TRANSFERENCIA_RECENTE:{data['transferencia_recente']}]"
            
            # Marcar rotas suspeitas
            for route in self.suspicious_routes:
                if route in relato_lower:
                    enhanced_text += f" [ROTA_SUSPEITA:{route}]"
            
            # Marcar horários suspeitos
            if data['datahora']:
                hora_str = str(data['datahora'])
                if any(hora in hora_str for hora in self.suspicious_hours):
                    enhanced_text += f" [HORARIO_SUSPEITO:{hora_str}]"
            
            # Marcar padrões de ida e volta
            for pattern in self.round_trip_patterns:
                if pattern in relato_lower:
                    enhanced_text += f" [IDA_VOLTA:{pattern}]"
            
            # Marcar indicadores de viagem ilícita
            for indicator in self.illicit_travel_indicators:
                if indicator in relato_lower:
                    enhanced_text += f" [VIAGEM_ILICITA:{indicator}]"
            
            # Marcar áreas de alto risco
            for area in self.high_risk_areas:
                if area in relato_lower:
                    enhanced_text += f" [AREA_RISCO:{area}]"
            
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
    
    def train_model(self, route_data: List[Dict], labels: List[str]) -> bool:
        """Treina o modelo de análise de rotas"""
        if len(route_data) < 100:
            print("❌ Dados insuficientes para treinamento")
            return False
        
        print(f"🚀 Treinando modelo de análise de rotas com {len(route_data)} ocorrências...")
        
        # Criar features específicas de rota
        enhanced_texts = self.create_route_features(route_data)
        
        # Dividir dados
        X_train, X_test, y_train, y_test = train_test_split(
            enhanced_texts, labels, test_size=0.2, random_state=42, stratify=labels
        )
        
        # Criar pipeline otimizado para análise de rotas
        pipeline = Pipeline([
            ('tfidf', TfidfVectorizer(
                max_features=5000,  # Mais features para análise de rotas
                ngram_range=(1, 5),  # Incluir 5-gramas para capturar padrões complexos
                stop_words=None,
                min_df=2,
                max_df=0.7,
                sublinear_tf=True,
                analyzer='word'
            )),
            ('scaler', StandardScaler(with_mean=False)),
            ('classifier', GradientBoostingClassifier(
                n_estimators=800,  # Mais árvores para padrões complexos
                random_state=42,
                learning_rate=0.1,
                max_depth=20,
                min_samples_split=2,
                min_samples_leaf=1,
                subsample=0.8
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
        """Salva o modelo de análise de rotas"""
        if not self.model:
            print("❌ Nenhum modelo para salvar")
            return
        
        # Salvar modelo
        model_path = MODELS_DIR / "route_analysis_clf.joblib"
        joblib.dump(self.model, model_path)
        print(f"✅ Modelo de análise de rotas salvo em: {model_path}")
        
        # Salvar metadados
        metadata = {
            'model_type': 'GradientBoostingClassifier_RouteAnalysis',
            'features': 'TF-IDF_Route_Patterns',
            'training_date': pd.Timestamp.now().isoformat(),
            'version': '1.0.0',
            'description': 'Modelo especializado em análise de rotas e padrões de viagem',
            'optimal_threshold': self.optimal_threshold,
            'ngram_range': '(1, 5)',
            'max_features': 5000,
            'data_source': 'veiculos_db.ocorrencias',
            'route_analysis': True,
            'suspicious_routes': list(self.suspicious_routes),
            'suspicious_hours': list(self.suspicious_hours),
            'round_trip_patterns': list(self.round_trip_patterns),
            'illicit_travel_indicators': list(self.illicit_travel_indicators),
            'high_risk_areas': list(self.high_risk_areas)
        }
        
        metadata_path = MODELS_DIR / "route_analysis_metadata.json"
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
        
        print(f"✅ Metadados de análise de rotas salvos em: {metadata_path}")
        print(f"🎯 Threshold ótimo salvo: {self.optimal_threshold:.3f}")
    
    def test_route_model(self):
        """Testa o modelo de análise de rotas com casos específicos"""
        if not self.model:
            print("❌ Nenhum modelo carregado")
            return
        
        test_cases = [
            # Caso que DEVE ser SUSPEITO (rota de fronteira + horário suspeito)
            {
                'texto': "Abordagem em veículo vindo da fronteira com Argentina. Ocorrência registrada às 02:30 da madrugada. Motorista sem justificativa clara para a viagem.",
                'expected': 'SUSPEITO',
                'description': 'Fronteira + horário suspeito + sem justificativa'
            },
            # Caso que DEVE ser SUSPEITO (padrão de ida e volta)
            {
                'texto': "Veículo com frequência alta de viagens entre São Paulo e Mato Grosso do Sul. Mesmo trajeto repetido várias vezes no mesmo dia.",
                'expected': 'SUSPEITO',
                'description': 'Frequência alta + mesmo trajeto + ida e volta'
            },
            # Caso que DEVE ser SUSPEITO (área de alto risco)
            {
                'texto': "Abordagem em região conhecida por tráfico de drogas. Veículo com comportamento suspeito e sem destino claro.",
                'expected': 'SUSPEITO',
                'description': 'Área de alto risco + sem destino claro'
            },
            # Caso que DEVE ser SEM_ALTERACAO (viagem normal)
            {
                'texto': "Fiscalização de rotina em veículo de empresa de entregas. Carga conforme nota fiscal e destino comercial legítimo.",
                'expected': 'SEM_ALTERACAO',
                'description': 'Viagem comercial legítima'
            },
            # Caso que DEVE ser SEM_ALTERACAO (viagem familiar)
            {
                'texto': "Família voltando de férias. Documentação em ordem e destino residencial confirmado.",
                'expected': 'SEM_ALTERACAO',
                'description': 'Viagem familiar legítima'
            }
        ]
        
        print(f"\n🧪 Testando modelo de análise de rotas (threshold: {self.optimal_threshold:.3f}):")
        correct = 0
        
        for i, caso in enumerate(test_cases, 1):
            # Criar features específicas de rota
            enhanced_text = self.create_route_features([{'relato': caso['texto']}])[0]
            
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
    print("🗺️ TREINAMENTO DE ANÁLISE DE ROTAS E PADRÕES DE VIAGEM")
    print("=" * 70)
    
    trainer = RouteAnalysisTrainer()
    
    # Carregar dados de rotas
    route_data, labels = trainer.load_route_data(30000)  # 30k ocorrências
    
    if len(route_data) < 100:
        print("❌ Dados insuficientes")
        return
    
    # Treinar modelo de análise de rotas
    success = trainer.train_model(route_data, labels)
    
    if success:
        trainer.test_route_model()
        print("\n✅ Treinamento de análise de rotas concluído com sucesso!")
        print("🗺️ O modelo agora detecta padrões de viagens ilícitas!")
    else:
        print("\n❌ Falha no treinamento")

if __name__ == "__main__":
    main()
