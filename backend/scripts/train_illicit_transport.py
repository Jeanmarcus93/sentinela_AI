#!/usr/bin/env python3
"""
Treinamento de Detecção de Transporte de Ilícitos
=================================================

Este script treina um modelo específico para detectar padrões de ida e volta
com transporte de ilícitos, focando em rotas suspeitas e comportamentos
específicos de tráfico.
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
from sklearn.ensemble import RandomForestClassifier
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

class IllicitTransportTrainer:
    """Treinador especializado em detecção de transporte de ilícitos"""
    
    def __init__(self):
        self.model = None
        self.optimal_threshold = 0.35
        
        # PADRÕES ESPECÍFICOS DE TRANSPORTE DE ILÍCITOS
        self.illicit_transport_patterns = {
            # Drogas específicas
            'cocaína', 'maconha', 'crack', 'heroína', 'ecstasy', 'lsd', 'metanfetamina',
            'droga', 'drogas', 'entorpecente', 'entorpecentes', 'substância ilícita',
            'substâncias ilícitas', 'produto ilícito', 'produtos ilícitos',
            
            # Quantidades suspeitas
            'grande quantidade', 'grandes quantidades', 'volume considerável',
            'quantidade expressiva', 'muitos pacotes', 'vários pacotes',
            'pacotes suspeitos', 'embalagens suspeitas', 'pacotes de',
            
            # Esconderijos típicos
            'escondido no', 'escondida no', 'oculto no', 'oculta no',
            'dentro do', 'no interior do', 'embaixo do', 'atrás do',
            'compartimento secreto', 'compartimento oculto', 'falso fundo',
            'modificação no veículo', 'alteração no veículo',
            
            # Comportamentos de transporte
            'transportando', 'levando', 'carregando', 'conduzindo',
            'entrega de', 'distribuição de', 'comercialização de',
            'venda de', 'tráfico de', 'contrabando de'
        }
        
        # PADRÕES DE IDA E VOLTA SUSPEITOS
        self.round_trip_suspicious = {
            'ida e volta', 'ida e retorno', 'ida volta', 'ida retorno',
            'mesmo trajeto', 'trajeto idêntico', 'rota idêntica',
            'frequência alta', 'muitas viagens', 'viagens constantes',
            'mesmo percurso', 'percurso repetido', 'rota repetida',
            'viagem de ida e volta', 'deslocamento ida e volta',
            'trajeto de ida e volta', 'percurso de ida e volta'
        }
        
        # ROTAS CONHECIDAS DE TRÁFICO
        self.traffic_routes = {
            'fronteira', 'fronteira brasil', 'fronteira argentina', 'fronteira paraguai',
            'fronteira uruguai', 'fronteira bolívia', 'fronteira colômbia',
            'triângulo das bermudas', 'região do pantanal', 'mato grosso do sul',
            'rio grande do sul', 'santa catarina', 'paraná', 'são paulo',
            'rio de janeiro', 'minas gerais', 'goiás', 'mato grosso',
            'acre', 'rondônia', 'amazonas', 'roraima', 'amapá', 'pará',
            'fronteira seca', 'área de risco', 'zona de conflito',
            'região perigosa', 'área suspeita', 'local de risco',
            'ponto de tráfico', 'área de contrabando', 'zona de drogas'
        }
        
        # HORÁRIOS SUSPEITOS PARA TRANSPORTE
        self.suspicious_transport_hours = {
            '00:00', '01:00', '02:00', '03:00', '04:00', '05:00',
            '22:00', '23:00', '23:30', '00:30', '01:30', '02:30',
            'madrugada', 'noite', 'horário noturno', 'horário suspeito'
        }
        
        # COMPORTAMENTOS ESPECÍFICOS DE TRANSPORTADORES
        self.transporter_behaviors = {
            'nervoso', 'nervosismo', 'agressivo', 'agressividade',
            'evasivo', 'mentiu', 'mentindo', 'contradição', 'contradições',
            'história inconsistente', 'sem justificativa', 'sem explicação',
            'destino incerto', 'sem destino claro', 'viagem sem motivo',
            'tentou fugir', 'evadir', 'evasão', 'fuga', 'manobra perigosa',
            'manobra suspeita', 'mão na cintura', 'comportamento agressivo',
            'extremamente nervoso', 'atitude suspeita', 'comportamento estranho'
        }
        
        # INDICADORES DE DINHEIRO ILÍCITO
        self.illicit_money_indicators = {
            'dinheiro em espécie', 'grande quantidade de dinheiro',
            'muito dinheiro', 'dinheiro sem justificativa', 'dinheiro suspeito',
            'valor em espécie', 'quantia em dinheiro', 'dinheiro não declarado',
            'valor não declarado', 'quantia suspeita', 'dinheiro oculto'
        }
    
    def get_connection(self):
        """Cria conexão com banco"""
        try:
            return psycopg.connect(**DB_CONFIG)
        except Exception as e:
            print(f"❌ Erro de conexão: {e}")
            return None
    
    def load_transport_data(self, limit: int = 25000) -> Tuple[List[Dict], List[str]]:
        """Carrega dados focando em padrões de transporte de ilícitos"""
        print(f"🔄 Carregando {limit} ocorrências com foco em transporte de ilícitos...")
        
        conn = self.get_connection()
        if not conn:
            return [], []
        
        transport_data = []
        labels = []
        
        try:
            with conn.cursor() as cur:
                # Buscar ocorrências com foco em transporte
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
                        transport_info = {
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
                        transport_data.append(transport_info)
                
                print(f"✅ Carregados {len(transport_data)} ocorrências")
                
        except Exception as e:
            print(f"❌ Erro ao carregar dados: {e}")
        finally:
            conn.close()
        
        # Analisar padrões de transporte de ilícitos
        print("🧠 Analisando padrões de transporte de ilícitos...")
        labels = self.analyze_illicit_transport_patterns(transport_data)
        
        return transport_data, labels
    
    def analyze_illicit_transport_patterns(self, transport_data: List[Dict]) -> List[str]:
        """Analisa padrões específicos de transporte de ilícitos"""
        labels = []
        suspeito_count = 0
        normal_count = 0
        
        # Agrupar por placa para analisar histórico de transporte
        vehicle_groups = defaultdict(list)
        for i, data in enumerate(transport_data):
            if data['placa']:
                vehicle_groups[data['placa']].append((i, data))
        
        print(f"📊 Analisando {len(vehicle_groups)} veículos únicos...")
        
        for i, data in enumerate(transport_data):
            # Calcular score específico de transporte de ilícitos
            transport_score = self.calculate_illicit_transport_score(data, vehicle_groups)
            
            # Classificar baseado no score específico (mais seletivo)
            if transport_score > 0.6:  # Threshold mais alto para transporte de ilícitos
                labels.append('TRANSPORTE_ILICITO')
                suspeito_count += 1
            else:
                labels.append('TRANSPORTE_NORMAL')
                normal_count += 1
        
        print(f"📊 Labels de transporte: {suspeito_count} TRANSPORTE_ILICITO, {normal_count} TRANSPORTE_NORMAL")
        return labels
    
    def calculate_illicit_transport_score(self, data: Dict, vehicle_groups: Dict) -> float:
        """Calcula score específico de transporte de ilícitos"""
        score = 0.0
        relato_lower = data['relato'].lower()
        
        # 1. DETECÇÃO DE ILÍCITOS ESPECÍFICOS (prioridade máxima)
        illicit_score = 0.0
        illicit_matches = sum(1 for pattern in self.illicit_transport_patterns if pattern in relato_lower)
        if illicit_matches > 0:
            illicit_score = min(0.8 + (illicit_matches * 0.1), 1.0)  # Score alto para ilícitos
            return illicit_score  # Se tem ilícito, é suspeito independente do resto
        
        # 2. PADRÕES DE IDA E VOLTA + COMPORTAMENTO SUSPEITO
        round_trip_score = 0.0
        if any(pattern in relato_lower for pattern in self.round_trip_suspicious):
            round_trip_score += 0.4
            
            # Bonus se também tem comportamento suspeito
            if any(behavior in relato_lower for behavior in self.transporter_behaviors):
                round_trip_score += 0.3
        
        # 3. ROTAS DE TRÁFICO CONHECIDAS
        route_score = 0.0
        if data['local_emplacamento']:
            local_lower = data['local_emplacamento'].lower()
            if any(route in local_lower for route in self.traffic_routes):
                route_score += 0.3
        
        # 4. HORÁRIOS SUSPEITOS PARA TRANSPORTE
        time_score = 0.0
        if data['datahora']:
            hora_str = str(data['datahora'])
            if any(hora in hora_str for hora in self.suspicious_transport_hours):
                time_score += 0.2
        
        # 5. DINHEIRO ILÍCITO
        money_score = 0.0
        if any(indicator in relato_lower for indicator in self.illicit_money_indicators):
            money_score += 0.3
        
        # 6. HISTÓRICO DE TRANSPORTE (frequência de viagens suspeitas)
        history_score = 0.0
        if data['placa'] and data['placa'] in vehicle_groups:
            vehicle_history = vehicle_groups[data['placa']]
            if len(vehicle_history) > 3:  # Veículo com muitas ocorrências
                history_score += 0.2
                
                # Verificar se há padrões de transporte repetitivo
                transport_keywords = ['fronteira', 'fronteira', 'tráfico', 'droga', 'contrabando']
                transport_count = sum(1 for h in vehicle_history 
                                   if any(keyword in h[1]['relato'].lower() 
                                         for keyword in transport_keywords))
                if transport_count > 1:
                    history_score += 0.3
        
        # Score final
        total_score = round_trip_score + route_score + time_score + money_score + history_score
        
        # Normalizar entre 0 e 1
        return min(max(total_score, 0.0), 1.0)
    
    def create_transport_features(self, transport_data: List[Dict]) -> List[str]:
        """Cria features específicas para detecção de transporte de ilícitos"""
        enhanced_texts = []
        
        for data in transport_data:
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
            if data['tipo']:
                enhanced_text += f" [TIPO:{data['tipo']}]"
            
            # Marcar ilícitos específicos
            for pattern in self.illicit_transport_patterns:
                if pattern in relato_lower:
                    enhanced_text += f" [ILICITO:{pattern}]"
            
            # Marcar padrões de ida e volta
            for pattern in self.round_trip_suspicious:
                if pattern in relato_lower:
                    enhanced_text += f" [IDA_VOLTA:{pattern}]"
            
            # Marcar rotas de tráfico
            for route in self.traffic_routes:
                if route in relato_lower:
                    enhanced_text += f" [ROTA_TRAFICO:{route}]"
            
            # Marcar horários suspeitos
            if data['datahora']:
                hora_str = str(data['datahora'])
                if any(hora in hora_str for hora in self.suspicious_transport_hours):
                    enhanced_text += f" [HORARIO_SUSPEITO:{hora_str}]"
            
            # Marcar comportamentos de transportador
            for behavior in self.transporter_behaviors:
                if behavior in relato_lower:
                    enhanced_text += f" [COMPORTAMENTO:{behavior}]"
            
            # Marcar indicadores de dinheiro ilícito
            for indicator in self.illicit_money_indicators:
                if indicator in relato_lower:
                    enhanced_text += f" [DINHEIRO_ILICITO:{indicator}]"
            
            enhanced_texts.append(enhanced_text)
        
        return enhanced_texts
    
    def find_optimal_threshold(self, X_test, y_test, model):
        """Encontra o threshold ótimo usando precision-recall curve"""
        # Converter labels para numérico
        label_map = {'TRANSPORTE_NORMAL': 0, 'TRANSPORTE_ILICITO': 1}
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
    
    def train_model(self, transport_data: List[Dict], labels: List[str]) -> bool:
        """Treina o modelo de detecção de transporte de ilícitos"""
        if len(transport_data) < 100:
            print("❌ Dados insuficientes para treinamento")
            return False
        
        print(f"🚀 Treinando modelo de transporte de ilícitos com {len(transport_data)} ocorrências...")
        
        # Criar features específicas de transporte
        enhanced_texts = self.create_transport_features(transport_data)
        
        # Dividir dados
        X_train, X_test, y_train, y_test = train_test_split(
            enhanced_texts, labels, test_size=0.2, random_state=42, stratify=labels
        )
        
        # Criar pipeline otimizado para transporte de ilícitos
        pipeline = Pipeline([
            ('tfidf', TfidfVectorizer(
                max_features=6000,  # Mais features para padrões complexos
                ngram_range=(1, 6),  # Incluir 6-gramas para capturar padrões longos
                stop_words=None,
                min_df=2,
                max_df=0.8,
                sublinear_tf=True,
                analyzer='word'
            )),
            ('scaler', StandardScaler(with_mean=False)),
            ('classifier', RandomForestClassifier(
                n_estimators=800,  # Mais árvores para padrões complexos
                random_state=42,
                class_weight='balanced',
                max_depth=30,
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
        label_map = {'TRANSPORTE_NORMAL': 0, 'TRANSPORTE_ILICITO': 1}
        y_test_num = [label_map[label] for label in y_test]
        
        accuracy = accuracy_score(y_test_num, y_pred_optimal)
        
        print(f"📊 Acurácia com threshold ótimo: {accuracy:.3f}")
        print("\n📋 Relatório de Classificação:")
        print(classification_report(y_test_num, y_pred_optimal, 
                                  target_names=['TRANSPORTE_NORMAL', 'TRANSPORTE_ILICITO']))
        
        # Cross-validation
        print("\n🔄 Validação cruzada...")
        cv_scores = cross_val_score(pipeline, enhanced_texts, labels, cv=5, scoring='f1_macro')
        print(f"📊 CV F1-Score: {cv_scores.mean():.3f} ± {cv_scores.std():.3f}")
        
        # Salvar modelo
        self.model = pipeline
        self.save_model()
        
        return True
    
    def save_model(self):
        """Salva o modelo de detecção de transporte de ilícitos"""
        if not self.model:
            print("❌ Nenhum modelo para salvar")
            return
        
        # Salvar modelo
        model_path = MODELS_DIR / "illicit_transport_clf.joblib"
        joblib.dump(self.model, model_path)
        print(f"✅ Modelo de transporte de ilícitos salvo em: {model_path}")
        
        # Salvar metadados
        metadata = {
            'model_type': 'RandomForestClassifier_IllicitTransport',
            'features': 'TF-IDF_Transport_Patterns',
            'training_date': pd.Timestamp.now().isoformat(),
            'version': '1.0.0',
            'description': 'Modelo especializado em detecção de transporte de ilícitos e padrões de ida e volta',
            'optimal_threshold': self.optimal_threshold,
            'ngram_range': '(1, 6)',
            'max_features': 6000,
            'data_source': 'veiculos_db.ocorrencias',
            'illicit_transport_detection': True,
            'illicit_transport_patterns': list(self.illicit_transport_patterns),
            'round_trip_suspicious': list(self.round_trip_suspicious),
            'traffic_routes': list(self.traffic_routes),
            'transporter_behaviors': list(self.transporter_behaviors),
            'illicit_money_indicators': list(self.illicit_money_indicators)
        }
        
        metadata_path = MODELS_DIR / "illicit_transport_metadata.json"
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
        
        print(f"✅ Metadados de transporte de ilícitos salvos em: {metadata_path}")
        print(f"🎯 Threshold ótimo salvo: {self.optimal_threshold:.3f}")
    
    def test_transport_model(self):
        """Testa o modelo de transporte de ilícitos com casos específicos"""
        if not self.model:
            print("❌ Nenhum modelo carregado")
            return
        
        test_cases = [
            # Caso que DEVE ser TRANSPORTE_ILICITO (droga específica)
            {
                'texto': "Abordagem em veículo vindo da fronteira. Durante a revista, foi localizada grande quantidade de cocaína escondida no compartimento secreto do veículo.",
                'expected': 'TRANSPORTE_ILICITO',
                'description': 'Droga específica + fronteira + esconderijo'
            },
            # Caso que DEVE ser TRANSPORTE_ILICITO (ida e volta + comportamento)
            {
                'texto': "Veículo com frequência alta de viagens entre São Paulo e Mato Grosso do Sul. Motorista nervoso e sem justificativa clara para as viagens constantes.",
                'expected': 'TRANSPORTE_ILICITO',
                'description': 'Frequência alta + nervosismo + sem justificativa'
            },
            # Caso que DEVE ser TRANSPORTE_ILICITO (dinheiro ilícito)
            {
                'texto': "Abordagem de rotina. Foi encontrado grande quantidade de dinheiro em espécie sem justificativa. Motorista evasivo sobre a origem do valor.",
                'expected': 'TRANSPORTE_ILICITO',
                'description': 'Dinheiro ilícito + evasivo'
            },
            # Caso que DEVE ser TRANSPORTE_NORMAL (viagem legítima)
            {
                'texto': "Fiscalização de rotina em veículo de empresa de entregas. Carga conforme nota fiscal e destino comercial legítimo.",
                'expected': 'TRANSPORTE_NORMAL',
                'description': 'Viagem comercial legítima'
            },
            # Caso que DEVE ser TRANSPORTE_NORMAL (viagem familiar)
            {
                'texto': "Família voltando de férias. Documentação em ordem e destino residencial confirmado.",
                'expected': 'TRANSPORTE_NORMAL',
                'description': 'Viagem familiar legítima'
            }
        ]
        
        print(f"\n🧪 Testando modelo de transporte de ilícitos (threshold: {self.optimal_threshold:.3f}):")
        correct = 0
        
        for i, caso in enumerate(test_cases, 1):
            # Criar features específicas de transporte
            enhanced_text = self.create_transport_features([{'relato': caso['texto']}])[0]
            
            proba = self.model.predict_proba([enhanced_text])[0]
            ilicito_prob = proba[1] if len(proba) > 1 else proba[0]
            pred = "TRANSPORTE_ILICITO" if ilicito_prob >= self.optimal_threshold else "TRANSPORTE_NORMAL"
            
            is_correct = pred == caso['expected']
            status = "✅" if is_correct else "❌"
            
            if is_correct:
                correct += 1
            
            print(f"\n{status} CASO {i}: {caso['description']}")
            print(f"   Esperado: {caso['expected']} | Obtido: {pred} ({ilicito_prob:.3f})")
            print(f"   Texto: {caso['texto'][:80]}...")
        
        print(f"\n📊 RESULTADO GERAL: {correct}/{len(test_cases)} corretos ({correct/len(test_cases)*100:.1f}%)")

def main():
    """Função principal"""
    print("🚛 TREINAMENTO DE DETECÇÃO DE TRANSPORTE DE ILÍCITOS")
    print("=" * 70)
    
    trainer = IllicitTransportTrainer()
    
    # Carregar dados de transporte
    transport_data, labels = trainer.load_transport_data(25000)  # 25k ocorrências
    
    if len(transport_data) < 100:
        print("❌ Dados insuficientes")
        return
    
    # Treinar modelo de transporte de ilícitos
    success = trainer.train_model(transport_data, labels)
    
    if success:
        trainer.test_transport_model()
        print("\n✅ Treinamento de transporte de ilícitos concluído com sucesso!")
        print("🚛 O modelo agora detecta padrões de ida e volta com transporte de ilícitos!")
    else:
        print("\n❌ Falha no treinamento")

if __name__ == "__main__":
    main()
