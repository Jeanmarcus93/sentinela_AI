#!/usr/bin/env python3
"""
Teste de Ajuste de Threshold
============================

Este script testa diferentes thresholds para encontrar o melhor
balanceamento entre precisão e recall.
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
from sklearn.metrics import classification_report, confusion_matrix, precision_recall_curve
import warnings
warnings.filterwarnings('ignore')

# Configurações
BASE_DIR = Path(__file__).parent.parent
MODELS_DIR = BASE_DIR / "ml_models" / "trained"

# Configuração do banco veiculos_db
DB_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'dbname': 'veiculos_db',
    'user': 'postgres',
    'password': 'Jmkjmk.00'
}

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

def get_connection():
    """Cria conexão com banco"""
    try:
        return psycopg.connect(**DB_CONFIG)
    except Exception as e:
        print(f"❌ Erro de conexão: {e}")
        return None

def load_sample_relatos(limit: int = 200):
    """Carrega uma amostra de relatos reais"""
    print(f"🔄 Carregando {limit} relatos do banco veiculos_db...")
    
    conn = get_connection()
    if not conn:
        return []
    
    relatos = []
    
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
                    relatos.append((relato.strip(), id_ocorrencia))
            
            print(f"✅ Carregados {len(relatos)} relatos")
            
    except Exception as e:
        print(f"❌ Erro ao carregar dados: {e}")
    finally:
        conn.close()
    
    return relatos

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

def test_different_thresholds(model, relatos, thresholds_to_test):
    """Testa diferentes thresholds"""
    print(f"\n🧪 TESTANDO DIFERENTES THRESHOLDS")
    print("=" * 50)
    
    results = {}
    
    for threshold in thresholds_to_test:
        print(f"\n🎯 Testando threshold: {threshold:.3f}")
        
        suspeitos_count = 0
        casos_suspeitos = []
        casos_normais = []
        
        for relato, id_ocorrencia in relatos:
            classification, confidence, suspeito_prob = classify_relato(model, relato, threshold)
            
            if classification == "SUSPEITO":
                suspeitos_count += 1
                casos_suspeitos.append({
                    'relato': relato[:100] + "..." if len(relato) > 100 else relato,
                    'prob': suspeito_prob
                })
            else:
                casos_normais.append({
                    'relato': relato[:100] + "..." if len(relato) > 100 else relato,
                    'prob': suspeito_prob
                })
        
        # Estatísticas
        total = len(relatos)
        taxa_suspeitos = (suspeitos_count / total) * 100
        
        print(f"   📊 SUSPEITOS: {suspeitos_count}/{total} ({taxa_suspeitos:.1f}%)")
        
        # Mostrar alguns casos suspeitos
        if casos_suspeitos:
            casos_suspeitos.sort(key=lambda x: x['prob'], reverse=True)
            print(f"   🔴 TOP 3 SUSPEITOS:")
            for i, caso in enumerate(casos_suspeitos[:3]):
                print(f"      {i+1}. [{caso['prob']:.2f}] {caso['relato']}")
        
        # Mostrar alguns casos normais
        if casos_normais:
            casos_normais.sort(key=lambda x: x['prob'])
            print(f"   🟢 TOP 3 NORMALS:")
            for i, caso in enumerate(casos_normais[:3]):
                print(f"      {i+1}. [{caso['prob']:.2f}] {caso['relato']}")
        
        results[threshold] = {
            'suspeitos_count': suspeitos_count,
            'taxa_suspeitos': taxa_suspeitos,
            'casos_suspeitos': casos_suspeitos[:5],
            'casos_normais': casos_normais[:5]
        }
    
    return results

def analyze_specific_case(model, relato: str, thresholds_to_test):
    """Analisa um caso específico com diferentes thresholds"""
    print(f"\n🔍 ANÁLISE DE CASO ESPECÍFICO")
    print("=" * 50)
    print(f"📝 RELATO: {relato}")
    print()
    
    for threshold in thresholds_to_test:
        classification, confidence, suspeito_prob = classify_relato(model, relato, threshold)
        print(f"🎯 Threshold {threshold:.3f}: {classification} ({suspeito_prob:.3f})")

def main():
    """Função principal"""
    print("🤖 TESTE DE AJUSTE DE THRESHOLD")
    print("=" * 50)
    
    # Carregar modelo
    model, current_threshold = load_model()
    if not model:
        print("❌ Não foi possível carregar o modelo")
        return
    
    # Carregar relatos
    relatos = load_sample_relatos(200)
    
    if not relatos:
        print("❌ Nenhum relato carregado")
        return
    
    # Thresholds para testar
    thresholds_to_test = [0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9]
    
    # Testar diferentes thresholds
    results = test_different_thresholds(model, relatos, thresholds_to_test)
    
    # Analisar caso específico mencionado pelo usuário
    caso_especifico = "Abordagem a veículo com matrícula de RN. O condutor, nervoso no início, explicou que era a sua primeira vez a conduzir na autoestrada. Documentos e te..."
    analyze_specific_case(model, caso_especifico, thresholds_to_test)
    
    # Recomendação
    print(f"\n💡 RECOMENDAÇÃO:")
    print(f"   Threshold atual: {current_threshold:.3f}")
    print(f"   Para casos como 'nervoso mas com justificativa plausível':")
    print(f"   - Threshold 0.5-0.6 pode ser mais adequado")
    print(f"   - Threshold 0.7-0.8 para casos mais conservadores")
    print(f"   - Threshold 0.9+ para casos extremamente suspeitos")

if __name__ == "__main__":
    main()

