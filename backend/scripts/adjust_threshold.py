#!/usr/bin/env python3
"""
Ajuste de Threshold para Crimes Explícitos
==========================================

Este script ajusta o threshold do modelo para capturar corretamente
crimes explícitos como tráfico de drogas.
"""

import os
import sys
import json
import joblib
import pandas as pd
import numpy as np
from pathlib import Path
from typing import List, Tuple, Dict, Any
from sklearn.metrics import classification_report, accuracy_score
import warnings
warnings.filterwarnings('ignore')

# Configurações
BASE_DIR = Path(__file__).parent.parent
MODELS_DIR = BASE_DIR / "ml_models" / "trained"

def load_model():
    """Carrega o modelo treinado"""
    model_path = MODELS_DIR / "semantic_agents_clf.joblib"
    metadata_path = MODELS_DIR / "semantic_agents_metadata.json"
    
    model = None
    threshold = 0.35
    
    try:
        model = joblib.load(model_path)
        print(f"✅ Modelo carregado de: {model_path}")
        
        # Carregar threshold se disponível
        if metadata_path.exists():
            with open(metadata_path, 'r', encoding='utf-8') as f:
                metadata = json.load(f)
                if 'optimal_threshold' in metadata:
                    threshold = metadata['optimal_threshold']
                    print(f"🎯 Threshold atual: {threshold:.3f}")
        
    except Exception as e:
        print(f"❌ Erro ao carregar modelo: {e}")
        return None, 0.35
    
    return model, threshold

def classify_relato(model, relato: str, threshold: float):
    """Classifica um relato usando o modelo"""
    if not model:
        return "ERRO", 0.0, 0.0
    
    try:
        # Obter probabilidades
        proba = model.predict_proba([relato])[0]
        
        # Assumir que a classe SUSPEITO é o índice 1
        suspeito_prob = proba[1] if len(proba) > 1 else proba[0]
        
        # Classificar baseado no threshold
        if suspeito_prob >= threshold:
            classification = "SUSPEITO"
            confidence = suspeito_prob
        else:
            classification = "SEM_ALTERACAO"
            confidence = 1.0 - suspeito_prob
        
        return classification, confidence, suspeito_prob
        
    except Exception as e:
        print(f"❌ Erro na classificação: {e}")
        return "ERRO", 0.0, 0.0

def test_critical_cases(model, thresholds_to_test):
    """Testa casos críticos com diferentes thresholds"""
    print(f"\n🧪 TESTANDO CASOS CRÍTICOS COM DIFERENTES THRESHOLDS")
    print("=" * 60)
    
    # Casos críticos que devem ser SUSPEITO
    critical_cases = [
        {
            'texto': "Denúncia anônima informou sobre tráfico de drogas. Durante a abordagem, foi localizada grande quantidade de cocaína escondida no veículo.",
            'expected': 'SUSPEITO',
            'description': 'Crime explícito - tráfico de drogas'
        },
        {
            'texto': "Ocupantes demonstraram nervosismo ao avistar a viatura. Durante a entrevista, os ocupantes entraram em contradição e foi localizada uma caixa de munição.",
            'expected': 'SUSPEITO', 
            'description': 'Nervosismo + contradição + munição'
        },
        {
            'texto': "Motorista tentou evadir-se da fiscalização. Durante a entrevista, o motorista mentiu sobre o destino da viagem e havia um forte odor de maconha no interior do veículo.",
            'expected': 'SUSPEITO',
            'description': 'Tentativa de fuga + mentira + drogas'
        }
    ]
    
    # Casos que devem ser SEM_ALTERACAO
    normal_cases = [
        {
            'texto': "Abordagem a veículo com matrícula de RN. O condutor, nervoso no início, explicou que era a sua primeira vez a conduzir na autoestrada. Documentos e tudo em ordem.",
            'expected': 'SEM_ALTERACAO',
            'description': 'Nervoso mas com justificativa plausível'
        },
        {
            'texto': "Motorista a conduzir de forma errática. Após a paragem, verificou-se que era um pai a tentar acalmar um bebê que chorava no banco de trás. Orientado a parar em local seguro.",
            'expected': 'SEM_ALTERACAO',
            'description': 'Comportamento errático com explicação plausível'
        },
        {
            'texto': "Fiscalização de rotina. Tratava-se de uma família voltando de férias. Nenhuma irregularidade foi encontrada.",
            'expected': 'SEM_ALTERACAO',
            'description': 'Situação completamente normal'
        }
    ]
    
    all_cases = critical_cases + normal_cases
    
    for threshold in thresholds_to_test:
        print(f"\n🎯 THRESHOLD: {threshold:.3f}")
        print("-" * 40)
        
        correct_critical = 0
        correct_normal = 0
        
        for i, caso in enumerate(all_cases, 1):
            classification, confidence, suspeito_prob = classify_relato(model, caso['texto'], threshold)
            
            is_correct = classification == caso['expected']
            status = "✅" if is_correct else "❌"
            
            print(f"{status} CASO {i}: {caso['description']}")
            print(f"   Esperado: {caso['expected']} | Obtido: {classification} ({suspeito_prob:.3f})")
            
            if i <= len(critical_cases):
                if is_correct:
                    correct_critical += 1
            else:
                if is_correct:
                    correct_normal += 1
        
        # Estatísticas
        total_critical = len(critical_cases)
        total_normal = len(normal_cases)
        
        print(f"\n📊 RESULTADOS:")
        print(f"   Crimes explícitos corretos: {correct_critical}/{total_critical} ({correct_critical/total_critical*100:.1f}%)")
        print(f"   Casos normais corretos: {correct_normal}/{total_normal} ({correct_normal/total_normal*100:.1f}%)")
        print(f"   Total correto: {correct_critical + correct_normal}/{len(all_cases)} ({(correct_critical + correct_normal)/len(all_cases)*100:.1f}%)")

def find_best_threshold(model, thresholds_to_test):
    """Encontra o melhor threshold baseado nos casos críticos"""
    print(f"\n🔍 ENCONTRANDO MELHOR THRESHOLD")
    print("=" * 40)
    
    # Casos críticos que DEVEM ser SUSPEITO
    critical_cases = [
        "Denúncia anônima informou sobre tráfico de drogas. Durante a abordagem, foi localizada grande quantidade de cocaína escondida no veículo.",
        "Ocupantes demonstraram nervosismo ao avistar a viatura. Durante a entrevista, os ocupantes entraram em contradição e foi localizada uma caixa de munição.",
        "Motorista tentou evadir-se da fiscalização. Durante a entrevista, o motorista mentiu sobre o destino da viagem e havia um forte odor de maconha no interior do veículo.",
        "Abordagem a veículo suspeito. Durante a entrevista, foi localizada arma de fogo escondida e grande quantidade de dinheiro sem justificativa.",
        "Denúncia de tráfico. Durante a abordagem, foi encontrada substância entorpecente e o condutor apresentou comportamento agressivo."
    ]
    
    # Casos normais que DEVEM ser SEM_ALTERACAO
    normal_cases = [
        "Abordagem a veículo com matrícula de RN. O condutor, nervoso no início, explicou que era a sua primeira vez a conduzir na autoestrada. Documentos e tudo em ordem.",
        "Motorista a conduzir de forma errática. Após a paragem, verificou-se que era um pai a tentar acalmar um bebê que chorava no banco de trás. Orientado a parar em local seguro.",
        "Fiscalização de rotina. Tratava-se de uma família voltando de férias. Nenhuma irregularidade foi encontrada.",
        "Veículo parado para verificação de documentos. O motorista estava indo visitar parentes. Após a verificação, foi liberado.",
        "Denúncia de atitude suspeita. Na abordagem, constatou-se que o motorista era um detetive privado em vigilância, devidamente identificado e com autorização."
    ]
    
    best_threshold = 0.5
    best_score = 0
    
    for threshold in thresholds_to_test:
        # Testar casos críticos (devem ser SUSPEITO)
        critical_correct = 0
        for caso in critical_cases:
            classification, _, suspeito_prob = classify_relato(model, caso, threshold)
            if classification == 'SUSPEITO':
                critical_correct += 1
        
        # Testar casos normais (devem ser SEM_ALTERACAO)
        normal_correct = 0
        for caso in normal_cases:
            classification, _, suspeito_prob = classify_relato(model, caso, threshold)
            if classification == 'SEM_ALTERACAO':
                normal_correct += 1
        
        # Calcular score (peso maior para casos críticos)
        critical_score = critical_correct / len(critical_cases)
        normal_score = normal_correct / len(normal_cases)
        
        # Score ponderado (70% casos críticos, 30% casos normais)
        total_score = 0.7 * critical_score + 0.3 * normal_score
        
        print(f"Threshold {threshold:.3f}: Críticos {critical_correct}/{len(critical_cases)} ({critical_score:.2f}) | Normais {normal_correct}/{len(normal_cases)} ({normal_score:.2f}) | Total: {total_score:.3f}")
        
        if total_score > best_score:
            best_score = total_score
            best_threshold = threshold
    
    print(f"\n🏆 MELHOR THRESHOLD: {best_threshold:.3f} (Score: {best_score:.3f})")
    return best_threshold

def save_adjusted_threshold(new_threshold):
    """Salva o threshold ajustado"""
    metadata_path = MODELS_DIR / "semantic_agents_metadata.json"
    
    try:
        with open(metadata_path, 'r', encoding='utf-8') as f:
            metadata = json.load(f)
        
        # Atualizar threshold
        metadata['optimal_threshold'] = new_threshold
        metadata['threshold_adjustment_date'] = pd.Timestamp.now().isoformat()
        metadata['threshold_reason'] = 'Ajustado para capturar crimes explícitos corretamente'
        
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
        
        print(f"✅ Threshold ajustado salvo: {new_threshold:.3f}")
        
    except Exception as e:
        print(f"❌ Erro ao salvar threshold: {e}")

def main():
    """Função principal"""
    print("🤖 AJUSTE DE THRESHOLD PARA CRIMES EXPLÍCITOS")
    print("=" * 60)
    
    # Carregar modelo
    model, current_threshold = load_model()
    if not model:
        print("❌ Não foi possível carregar o modelo")
        return
    
    # Thresholds para testar
    thresholds_to_test = [0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9]
    
    # Testar casos críticos
    test_critical_cases(model, thresholds_to_test)
    
    # Encontrar melhor threshold
    best_threshold = find_best_threshold(model, thresholds_to_test)
    
    # Salvar threshold ajustado
    save_adjusted_threshold(best_threshold)
    
    print(f"\n✅ AJUSTE CONCLUÍDO!")
    print(f"🎯 Threshold anterior: {current_threshold:.3f}")
    print(f"🎯 Threshold ajustado: {best_threshold:.3f}")
    print(f"💡 O modelo agora deve capturar crimes explícitos corretamente!")

if __name__ == "__main__":
    main()

